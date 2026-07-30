import logging
import re
import idna
import requests
from db.db import db
from db.database import Cloudflare, DomainRegistrator, DomainPurchase
from functions.pages_forms import _load_zones_for_account
from functions.site_actions import link_domain_and_account
from functions.provision_func import setSiteOwner
from functions.dynadot_func import dynadot_register_domain, dynadot_set_ns

CF_ACCOUNT_DOMAIN_LIMIT = 50
DOMAIN_RE = re.compile(r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$')

def _clean_domain(raw: str):
  """Normalizes and validates one domain token. Returns the normalized domain or None if invalid."""
  domain = raw.strip().lower().removeprefix("https://").removeprefix("http://").rstrip("/")
  if not domain:
    return None
  try:
    domain = idna.encode(domain).decode()
  except idna.IDNAError:
    return None
  if not DOMAIN_RE.fullmatch(domain):
    return None
  return domain

def parse_domain_textarea(raw: str):
  """Splits a free-form textarea of domains (one per line, or comma/space separated) into a deduplicated, validated list. Returns (valid_domains, invalid_tokens)."""
  valid = []
  invalid = []
  seen = set()
  for token in re.split(r'[\s,;]+', raw or ""):
    token = token.strip()
    if not token:
      continue
    cleaned = _clean_domain(token)
    if cleaned is None:
      invalid.append(token)
      continue
    if cleaned in seen:
      continue
    seen.add(cleaned)
    valid.append(cleaned)
  return valid, invalid

def load_domain_registrators():
  """Loads all registrators from DB for the dropdown on Крок 1. Mirrors loadClodflareAccounts()."""
  try:
    regs = DomainRegistrator.query.order_by(DomainRegistrator.name).all()
    first_reg = reg_list = ""
    if len(regs) == 0:
      reg_list = "Реєстратори відсутні у базі!"
    else:
      for r in regs:
        reg_list += f'<li><a class="dropdown-item registrator" href="#" data-value="{r.name}">{r.name}</a></li>\n\t\t'
      first_reg = regs[0].name
    return reg_list, first_reg
  except Exception as err:
    logging.error(f"load_domain_registrators(): global error {err}")
    return "Error", "Error"

def load_cf_accounts_checkboxes():
  """Builds the checkbox list of all Cloudflare accounts in DB for Крок 1."""
  try:
    accounts = Cloudflare.query.order_by(Cloudflare.account).all()
    if not accounts:
      return '<div class="text-muted text-center py-2">Аккаунти Cloudflare відсутні у базі!</div>'
    html = ""
    for i, acc in enumerate(accounts, 1):
      html += f"""<div class="col-12 col-sm-6 col-md-4 cf-account-item">
  <div class="form-check">
    <input class="form-check-input cf-account-check" type="checkbox" name="cf_accounts" value="{acc.account}" id="cf-acc-{i}">
    <label class="form-check-label" for="cf-acc-{i}">{acc.account}</label>
  </div>
</div>"""
    return html
  except Exception as err:
    logging.error(f"load_cf_accounts_checkboxes(): global error {err}")
    return "Error"

def render_purchase_history():
  """Builds the Крок 2 history table rows from the DomainPurchase log."""
  try:
    rows = DomainPurchase.query.order_by(DomainPurchase.id.desc()).limit(200).all()
    if not rows:
      return '<tr><td colspan="8" class="text-center text-muted">Історія покупок поки що порожня</td></tr>'
    html = ""
    for r in rows:
      color = "table-success" if r.status == "success" else "table-danger"
      html += f"""  <tr class="{color}">
    <td>{r.id}</td>
    <td>{r.domain}</td>
    <td>{r.registrator}</td>
    <td>{r.cloudflare_account or "-"}</td>
    <td>{r.status}</td>
    <td>{r.message or ""}</td>
    <td>{r.purchased_by}</td>
    <td>{r.created.strftime('%d-%m-%Y %H:%M:%S')}</td>
  </tr>\n"""
    return html
  except Exception as err:
    logging.error(f"render_purchase_history(): global error {err}")
    return f'<tr><td colspan="8">Помилка завантаження історії: {err}</td></tr>'

def count_free_slots(cf_accounts: list) -> dict:
  """For every given Cloudflare account, returns how many domain slots are free before hitting the 50-domain limit."""
  slots = {}
  for acc in cf_accounts:
    zones = _load_zones_for_account(acc)
    slots[acc.account] = max(0, CF_ACCOUNT_DOMAIN_LIMIT - len(zones))
  return slots

def _add_domain_to_cf(acc: Cloudflare, domain: str):
  """Creates a new zone for domain on the given Cloudflare account. Returns (True, name_servers_list) or (False, error_message)."""
  try:
    headers = {
      "X-Auth-Email": acc.account,
      "X-Auth-Key": acc.token,
      "Content-Type": "application/json"
    }
    result_id = requests.get("https://api.cloudflare.com/client/v4/accounts", headers=headers, timeout=15).json()
    if not (result_id.get("success") and result_id.get("result")):
      return False, "Не вдалося отримати ID акаунту Cloudflare"
    account_id = result_id["result"][0]["id"]
    data = {"name": domain, "account": {"id": account_id}, "type": "full"}
    result_add = requests.post("https://api.cloudflare.com/client/v4/zones", headers=headers, json=data, timeout=15).json()
    if result_add.get("success"):
      return True, result_add["result"]["name_servers"]
    error_msg = result_add.get("errors", [{}])[0].get("message", "Unknown error")
    return False, error_msg
  except Exception as err:
    return False, str(err)

def _update_purchase_row(domain: str, account, status: str, message: str):
  row = DomainPurchase.query.filter_by(domain=domain).order_by(DomainPurchase.id.desc()).first()
  if row:
    row.cloudflare_account = account
    row.status = status
    row.message = message
    db.session.commit()

def purchase_and_setup_domains(domains: list, cf_accounts: list, registrator: DomainRegistrator, realname: str) -> dict:
  """Main pipeline: pre-flight capacity check, Dynadot purchase, then sequential Cloudflare assignment/NS/DB registration.
  Returns a dict describing the outcome, either {"aborted": True, "reason": str} or
  {"aborted": False, "purchase_log": [...], "cf_setup_log": [...], "purchased_count": int, "total_count": int}."""
  try:
    logging.info(f"-----------------------Starting domain purchase of {len(domains)} domain(s) via registrator {registrator.name} by {realname}-----------------------")
    if not domains:
      return {"aborted": True, "reason": "Список доменів для покупки порожній!"}
    if not cf_accounts:
      return {"aborted": True, "reason": "Не обрано жодного акаунту Cloudflare!"}
    #Pre-flight capacity check (must run before ANY purchase call)
    slots = count_free_slots(cf_accounts)
    total_free = sum(slots.values())
    logging.info(f"purchase_and_setup_domains(): Free CF slots per account: {slots}, total free: {total_free}, requested: {len(domains)}")
    if len(domains) > total_free:
      reason = (f"Недостатньо вільних місць на обраних акаунтах Cloudflare! "
                f"Потрібно місць: {len(domains)}, доступно: {total_free} (на {len(cf_accounts)} обраних акаунтах, ліміт {CF_ACCOUNT_DOMAIN_LIMIT} на акаунт). "
                f"Оберіть більше акаунтів Cloudflare або зменшіть список доменів.")
      logging.error(f"purchase_and_setup_domains(): {reason}")
      return {"aborted": True, "reason": reason}
    #Phase 1: purchase every domain via Dynadot
    purchased = []
    purchase_log = []
    for domain in domains:
      ok, msg = dynadot_register_domain(registrator, domain, duration=1)
      status = "success" if ok else "error"
      message = "Куплено, очікує налаштування Cloudflare" if ok else f"Помилка покупки: {msg}"
      db.session.add(DomainPurchase(domain=domain, registrator=registrator.name, cloudflare_account=None, status=status, message=message, purchased_by=realname))
      db.session.commit()
      if ok:
        purchased.append(domain)
        purchase_log.append((domain, True, "Домен успішно куплено"))
      else:
        purchase_log.append((domain, False, f"Помилка покупки: {msg}"))
    #Phase 2: sequential Cloudflare assignment (fill account 1 to the limit, then move to next)
    cf_setup_log = []
    remaining_slots = dict(slots)
    acc_idx = 0
    for domain in purchased:
      placed = False
      while acc_idx < len(cf_accounts):
        acc = cf_accounts[acc_idx]
        if remaining_slots.get(acc.account, 0) <= 0:
          acc_idx += 1
          continue
        ok, ns_or_err = _add_domain_to_cf(acc, domain)
        if not ok:
          logging.error(f"purchase_and_setup_domains(): Error adding domain {domain} to CF account {acc.account}: {ns_or_err}")
          cf_setup_log.append((domain, False, f"Помилка додавання в Cloudflare ({acc.account}): {ns_or_err}"))
          _update_purchase_row(domain, acc.account, "error", f"Помилка додавання в Cloudflare: {ns_or_err}")
          placed = True
          break
        ns = ns_or_err
        ns_ok, ns_msg = dynadot_set_ns(registrator, domain, ns)
        setSiteOwner(domain)
        link_domain_and_account(domain, acc.account)
        remaining_slots[acc.account] -= 1
        if ns_ok:
          logging.info(f"purchase_and_setup_domains(): Domain {domain} added to CF account {acc.account}, NS set, registered in DB")
          cf_setup_log.append((domain, True, f"Додано в Cloudflare ({acc.account}), NS встановлено, зареєстровано в базі"))
          _update_purchase_row(domain, acc.account, "success", "Додано в Cloudflare, NS встановлено, зареєстровано в базі")
        else:
          logging.error(f"purchase_and_setup_domains(): Domain {domain} added to CF account {acc.account} but NS set failed: {ns_msg}")
          cf_setup_log.append((domain, False, f"Додано в Cloudflare ({acc.account}), але NS НЕ встановлено: {ns_msg}"))
          _update_purchase_row(domain, acc.account, "error", f"Додано в Cloudflare, але NS не встановлено: {ns_msg}")
        placed = True
        break
      if not placed:
        reason = "Немає вільних місць на жодному з обраних акаунтів Cloudflare! Домен куплено, але НЕ додано в Cloudflare."
        logging.error(f"purchase_and_setup_domains(): Domain {domain}: {reason}")
        cf_setup_log.append((domain, False, reason))
        _update_purchase_row(domain, None, "error", reason)
    logging.info(f"-----------------------End of domain purchase job by {realname}: {len(purchased)}/{len(domains)} purchased-----------------------")
    return {"aborted": False, "purchase_log": purchase_log, "cf_setup_log": cf_setup_log, "purchased_count": len(purchased), "total_count": len(domains)}
  except Exception as err:
    logging.error(f"purchase_and_setup_domains(): general error: {err}")
    return {"aborted": True, "reason": f"Загальна неочікувана помилка: {err}"}
