import logging
import socket
import requests
from urllib.parse import urlparse
from flask import current_app
from db.db import db
from db.database import Cloudflare, MailServerDomainStatus
from functions.pages_forms import getSiteOwner

DKIM_RECORD_NAME = "default._domainkey"
DMARC_RECORD_NAME = "_dmarc"
DMARC_RECORD_VALUE = "v=DMARC1; p=reject; adkim=r; aspf=r; rf=afrf; sp=reject"

def _resolve_mailserver_ip():
  """Resolves the IPv4 address of the host configured in MAIL_SERVER_API_URL, for use in the SPF ip4: mechanism."""
  try:
    url = current_app.config.get("MAIL_SERVER_API_URL", "")
    if not url:
      return None
    host = urlparse(url).hostname
    if not host:
      return None
    return socket.gethostbyname(host)
  except Exception as err:
    logging.error(f"_resolve_mailserver_ip(): failed to resolve IP for MAIL_SERVER_API_URL: {err}")
    return None

def _mailserver_post(path: str, payload: dict) -> dict:
  """POSTs JSON to the configured mail server API (authenticating with the shared secret the remote
  email_sender_configurator.py script expects in X-Api-Key) and safely parses the JSON response.
  Raises RuntimeError with a clear message (HTTP status + body snippet) if the response isn't valid
  JSON, or if the mail server URL isn't configured at all."""
  base_url = (current_app.config.get("MAIL_SERVER_API_URL") or "").rstrip("/")
  if not base_url:
    raise RuntimeError("MAIL_SERVER_API_URL не налаштовано в /admin_panel/settings/")
  headers = {"X-Api-Key": current_app.config.get("MAIL_SERVER_API_SECRET", ""), "Content-Type": "application/json"}
  response = requests.post(f"{base_url}{path}", headers=headers, json=payload, timeout=20)
  try:
    return response.json()
  except ValueError:
    snippet = response.text[:200].replace("\n", " ") if response.text else "(порожня відповідь)"
    raise RuntimeError(f"Поштовий сервер {path} повернув не-JSON відповідь (HTTP {response.status_code}): {snippet}")

def _cf_headers(account_email: str):
  """Returns (headers, error) for the given Cloudflare account."""
  acc = Cloudflare.query.filter_by(account=account_email).first()
  if not acc:
    return None, f"Аккаунт Cloudflare {account_email} не знайдено в базі"
  return {"X-Auth-Email": acc.account, "X-Auth-Key": acc.token, "Content-Type": "application/json"}, None

def _cf_zone_id(headers: dict, domain: str):
  """Returns (zone_id, error) for the given domain."""
  r = requests.get(f"https://api.cloudflare.com/client/v4/zones?name={domain}", headers=headers, timeout=10).json()
  if not (r.get("success") and r.get("result")):
    return None, f"Не вдалося отримати ID зони для домену {domain}"
  return r["result"][0]["id"], None

def _find_txt_records(headers: dict, zone_id: str, full_name: str) -> list:
  """Returns every TXT record on the zone whose name exactly matches full_name (fully-qualified)."""
  r = requests.get(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=TXT&name={full_name}", headers=headers, timeout=10).json()
  if not r.get("success"):
    return []
  return r.get("result", [])

def _write_dkim_dmarc(headers: dict, zone_id: str, dkim_value: str) -> list:
  """Creates the default._domainkey and _dmarc TXT records. Returns a list of (name, ok, message) tuples."""
  results = []
  for name, content in ((DKIM_RECORD_NAME, dkim_value), (DMARC_RECORD_NAME, DMARC_RECORD_VALUE)):
    data = {"type": "TXT", "name": name, "content": content, "ttl": 1, "comment": "Mail server sender configuration"}
    r = requests.post(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records", headers=headers, json=data, timeout=10).json()
    if r.get("success"):
      results.append((name, True, "OK"))
    else:
      error_msg = (r.get("errors") or [{}])[0].get("message", "Unknown error")
      results.append((name, False, error_msg))
  return results

def _upsert_spf(headers: dict, zone_id: str, domain: str, ip: str):
  """Adds ip4:<ip> to the domain's SPF record, creating a fresh one if it doesn't exist yet.
  Returns (ok, spf_created, message)."""
  try:
    records = _find_txt_records(headers, zone_id, domain)
    #Cloudflare sometimes returns TXT content wrapped in literal double quotes, and "v=spf1" isn't
    #always guaranteed to be the very first thing recorded - so search with "in", not "startswith"
    spf_record = next((r for r in records if "v=spf1" in r.get("content", "")), None)
    if spf_record:
      #strip any wrapping quotes Cloudflare returned before editing, they're not part of the real value
      old_content = spf_record["content"].strip().strip('"')
      if f"ip4:{ip}" in old_content:
        return True, False, "SPF вже містить цю IP-адресу"
      #insert right after "v=spf1" (wherever it sits) so ip4: is evaluated before any include:/-all catch-all
      insert_at = old_content.find("v=spf1") + len("v=spf1")
      new_content = f"{old_content[:insert_at]} ip4:{ip}{old_content[insert_at:]}"
      new_content = " ".join(new_content.split())
      data = {"type": "TXT", "name": domain, "content": new_content, "ttl": spf_record.get("ttl", 1)}
      r = requests.put(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{spf_record['id']}", headers=headers, json=data, timeout=10).json()
      if r.get("success"):
        return True, False, "IP додано в існуючий SPF запис"
      error_msg = (r.get("errors") or [{}])[0].get("message", "Unknown error")
      return False, False, f"Помилка оновлення SPF: {error_msg}"
    else:
      data = {"type": "TXT", "name": "@", "content": f"v=spf1 ip4:{ip} ~all", "ttl": 1, "comment": "Mail server sender configuration"}
      r = requests.post(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records", headers=headers, json=data, timeout=10).json()
      if r.get("success"):
        return True, True, "SPF запис створено"
      error_msg = (r.get("errors") or [{}])[0].get("message", "Unknown error")
      return False, False, f"Помилка створення SPF: {error_msg}"
  except Exception as err:
    logging.error(f"_upsert_spf(): error for domain {domain}: {err}")
    return False, False, str(err)

def _get_or_create_status_row(domain: str) -> MailServerDomainStatus:
  row = MailServerDomainStatus.query.filter_by(domain=domain).first()
  if not row:
    row = MailServerDomainStatus(domain=domain, action="add", status="error", message="", actor="")
    db.session.add(row)
    db.session.commit()
  return row

def provision_mail_domain(domain: str, mailbox: str, cf_account: str, actor: str):
  """Main pipeline: registers domain+mailbox on the remote mail server, then writes DKIM/DMARC/SPF DNS
  records on Cloudflare. Every domain has exactly one MailServerDomainStatus row, upserted in place -
  if it already shows a successful "add", this is a no-op (idempotent, safe to call from every
  domain-creation code path in the project without double-provisioning)."""
  row = _get_or_create_status_row(domain)
  if row.action == "add" and row.status == "success":
    logging.info(f"provision_mail_domain(): domain {domain} is already configured, skipping")
    return True, "Домен вже налаштовано на поштовому сервері"
  logging.info(f"-----------------------Starting mail server provisioning for domain {domain} (mailbox {mailbox}) by {actor}-----------------------")

  def _fail(message: str):
    logging.error(f"provision_mail_domain(): {message}")
    row.action = "add"
    row.status = "error"
    row.message = message
    row.mailbox = mailbox
    row.cloudflare_account = cf_account
    row.actor = actor
    db.session.commit()
    return False, message

  try:
    #mailbox is intentionally not sent - email_sender_configurator.py always uses its own hardcoded "order" login
    result = _mailserver_post("/api/add_new_domain", {"domain": domain})
  except RuntimeError as err:
    return _fail(f"Помилка звернення до поштового сервера: {err}")
  if not result.get("success"):
    return _fail(f"Поштовий сервер відхилив запит на додавання домену {domain}: {result}")
  dkim_value = result.get("dkim")
  if not dkim_value:
    return _fail("Поштовий сервер повідомив про успіх, але не повернув DKIM запис")
  headers, err = _cf_headers(cf_account)
  if err:
    return _fail(err)
  zone_id, err = _cf_zone_id(headers, domain)
  if err:
    return _fail(err)
  dns_results = _write_dkim_dmarc(headers, zone_id, dkim_value)
  ip = _resolve_mailserver_ip()
  spf_created = False
  if ip:
    spf_ok, spf_created, spf_msg = _upsert_spf(headers, zone_id, domain, ip)
    dns_results.append(("SPF", spf_ok, spf_msg))
  else:
    dns_results.append(("SPF", False, "Не вдалося резолвити IP поштового сервера, SPF пропущено"))
  failed = [f"{name}: {msg}" for name, ok, msg in dns_results if not ok]
  overall_ok = not failed
  message = "DKIM, DMARC та SPF записи успішно додано" if overall_ok else f"Часткова помилка: {'; '.join(failed)}"
  logging.info(f"provision_mail_domain(): {domain} finished, ok={overall_ok}: {message}")
  row.action = "add"
  row.status = "success" if overall_ok else "error"
  row.message = message
  row.mailbox = mailbox
  row.cloudflare_account = cf_account
  row.mail_server_ip = ip
  row.spf_record_created = spf_created
  row.actor = actor
  db.session.commit()
  return overall_ok, message

def deprovision_mail_domain(domain: str, actor: str):
  """Main pipeline: deletes domain+mailbox from the remote mail server, then rolls back the DKIM/DMARC/SPF
  DNS records that provision_mail_domain() wrote. Updates the same one row per domain in place."""
  row = MailServerDomainStatus.query.filter_by(domain=domain).first()
  if not row or not row.mailbox:
    message = f"Немає збереженої інформації (mailbox) для домену {domain}, видалення неможливе"
    logging.error(f"deprovision_mail_domain(): {message}")
    return False, message
  if row.action == "delete" and row.status == "success":
    logging.info(f"deprovision_mail_domain(): domain {domain} is already removed, skipping")
    return True, "Домен вже видалено з поштового сервера"
  mailbox = row.mailbox
  cf_account = row.cloudflare_account
  logging.info(f"-----------------------Starting mail server deprovisioning for domain {domain} (mailbox {mailbox}) by {actor}-----------------------")

  def _fail(message: str):
    logging.error(f"deprovision_mail_domain(): {message}")
    row.action = "delete"
    row.status = "error"
    row.message = message
    row.actor = actor
    db.session.commit()
    return False, message

  try:
    #mailbox is intentionally not sent - email_sender_configurator.py always uses its own hardcoded "order" login
    result = _mailserver_post("/api/delete_domain", {"domain": domain})
  except RuntimeError as err:
    return _fail(f"Помилка звернення до поштового сервера: {err}")
  if not result.get("success"):
    return _fail(f"Поштовий сервер відхилив запит на видалення домену {domain}: {result}")
  #mail server confirmed deletion - now roll back the DNS records we wrote at add-time
  dns_notes = []
  if cf_account:
    headers, err = _cf_headers(cf_account)
    if err:
      dns_notes.append(err)
    else:
      zone_id, err = _cf_zone_id(headers, domain)
      if err:
        dns_notes.append(err)
      else:
        for name in (f"{DKIM_RECORD_NAME}.{domain}", f"{DMARC_RECORD_NAME}.{domain}"):
          for rec in _find_txt_records(headers, zone_id, name):
            r = requests.delete(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{rec['id']}", headers=headers, timeout=10).json()
            if not r.get("success"):
              dns_notes.append(f"Не вдалося видалити {name}")
        #SPF rollback: delete entirely if we created it from scratch, otherwise just strip our ip4: token
        #(same "in" check as _upsert_spf() - Cloudflare doesn't guarantee v=spf1 is at position 0 or unquoted)
        spf_record = next((r for r in _find_txt_records(headers, zone_id, domain) if "v=spf1" in r.get("content", "")), None)
        if spf_record:
          if row.spf_record_created:
            r = requests.delete(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{spf_record['id']}", headers=headers, timeout=10).json()
            if not r.get("success"):
              dns_notes.append("Не вдалося видалити SPF запис")
          elif row.mail_server_ip and f"ip4:{row.mail_server_ip}" in spf_record["content"]:
            old_content = spf_record["content"].strip().strip('"')
            new_content = " ".join(old_content.replace(f"ip4:{row.mail_server_ip}", "").split())
            data = {"type": "TXT", "name": domain, "content": new_content, "ttl": spf_record.get("ttl", 1)}
            r = requests.put(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{spf_record['id']}", headers=headers, json=data, timeout=10).json()
            if not r.get("success"):
              dns_notes.append("Не вдалося оновити SPF запис")
  message = "Домен видалено з поштового сервера" + (f"; DNS: {'; '.join(dns_notes)}" if dns_notes else ", DNS записи прибрано")
  logging.info(f"deprovision_mail_domain(): {domain} finished: {message}")
  row.action = "delete"
  row.status = "success"
  row.message = message
  row.actor = actor
  db.session.commit()
  return True, message

def load_mail_domains_list():
  """Returns every domain's MailServerDomainStatus row (one per domain), most recently updated first -
  this single table now serves both as the current-status list and the history for Крок 2."""
  return MailServerDomainStatus.query.order_by(MailServerDomainStatus.updated.desc()).all()

def render_mail_domains_list(rows: list) -> str:
  """Builds the Крок 2 table rows. Retry is shown unless the domain is currently actively configured;
  Delete is shown unless the domain is currently in a successfully-removed state."""
  if not rows:
    return '<tr><td colspan="7" class="text-center text-muted">Немає доменів, налаштованих для розсилок</td></tr>'
  status_labels = {
    ("add", "success"): "Налаштовано",
    ("add", "error"): "Помилка налаштування",
    ("delete", "success"): "Видалено",
    ("delete", "error"): "Помилка видалення"
  }
  html = ""
  for r in rows:
    is_active = (r.action == "add" and r.status == "success")
    is_removed = (r.action == "delete" and r.status == "success")
    color = "table-success" if is_active else "table-secondary" if is_removed else "table-danger"
    owner = getSiteOwner(r.domain)
    status_label = status_labels.get((r.action, r.status), f"{r.action}/{r.status}")
    buttons = ""
    if not is_active:
      buttons += f'''<form action="/mail_domains/retry/" method="POST" class="d-inline">
        <input type="hidden" name="domain" value="{r.domain}">
        <button type="submit" class="btn btn-sm btn-outline-warning" onclick="showLoading()" data-bs-toggle="tooltip" data-bs-placement="top" title="Налаштувати / повторити налаштування">🔁 Повторити</button>
      </form> '''
    if not is_removed and r.cloudflare_account:
      buttons += f'''<form action="/mail_domains/delete/" method="POST" class="d-inline delete-mail-domain-form">
        <input type="hidden" name="domain" value="{r.domain}">
        <button type="submit" class="btn btn-sm btn-outline-danger" onclick="showLoading()" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити з поштового сервера">🗑 Видалити</button>
      </form>'''
    updated = r.updated or r.created
    html += f"""  <tr class="{color}" data-owner="{owner}" data-account="{r.cloudflare_account or ''}">
    <td class="cname-cell">{r.domain}</td>
    <td>{r.cloudflare_account or "-"}</td>
    <td>{owner}</td>
    <td>{status_label}</td>
    <td>{r.message or ""}</td>
    <td>{updated.strftime('%d-%m-%Y %H:%M:%S')}</td>
    <td class="text-nowrap">{buttons}</td>
  </tr>\n"""
  return html
