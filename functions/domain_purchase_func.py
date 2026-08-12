import logging
import re
import time
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

def recheck_domain_statuses():
  """Re-checks every domain still in just_bought/ns_set stage against the live Cloudflare zone status and
  advances it to ready_to_setup once Cloudflare reports the zone as active (NS propagated, domain served by CF)."""
  try:
    rows = DomainPurchase.query.filter(DomainPurchase.stage.in_(["just_bought", "ns_set"])).all()
    #group by cloudflare_account to minimize API calls - one zones listing per account instead of per domain
    by_account = {}
    for row in rows:
      if not row.cloudflare_account:
        continue
      by_account.setdefault(row.cloudflare_account, []).append(row)
    for account_email, account_rows in by_account.items():
      acc = Cloudflare.query.filter_by(account=account_email).first()
      if not acc:
        continue
      zones = _load_zones_for_account(acc)
      for row in account_rows:
        is_ready = zones.get(row.domain) == "active"
        new_stage = "ready_to_setup" if is_ready else "ns_set"
        if row.stage != new_stage:
          logging.info(f"recheck_domain_statuses(): Domain {row.domain} stage {row.stage} -> {new_stage} (CF zone status: {zones.get(row.domain)})")
          row.stage = new_stage
    db.session.commit()
  except Exception as err:
    logging.error(f"recheck_domain_statuses(): global error: {err}")

def load_actionable_domains():
  """Returns all DomainPurchase rows still awaiting setup (not yet ready_to_email/done), grouped implicitly by account via ordering."""
  return DomainPurchase.query.filter(DomainPurchase.stage.in_(["just_bought", "ns_set", "ready_to_setup"])).order_by(DomainPurchase.cloudflare_account, DomainPurchase.domain).all()

def distinct_actionable_accounts(rows: list) -> list:
  """Returns the distinct Cloudflare accounts present among the given rows, in first-seen order."""
  seen = []
  for row in rows:
    if row.cloudflare_account and row.cloudflare_account not in seen:
      seen.append(row.cloudflare_account)
  return seen

def render_actionable_domains(rows: list) -> str:
  """Builds the Крок 2 checkbox list: one entry per domain, only ready_to_setup domains get an enabled checkbox."""
  if not rows:
    return '<div class="text-muted text-center py-2">Немає доменів, що очікують налаштування</div>'
  stage_labels = {
    "just_bought": '<span class="badge bg-warning text-dark">Щойно куплено</span>',
    "ns_set": '<span class="badge bg-info text-dark">NS встановлено</span>',
    "ready_to_setup": '<span class="badge bg-success">Готовий до розгортання</span>'
  }
  html = ""
  for i, row in enumerate(rows, 1):
    label = stage_labels.get(row.stage, '<span class="badge bg-secondary">?</span>')
    account = row.cloudflare_account or ""
    if row.stage == "ready_to_setup":
      checkbox = f'<input class="form-check-input setup-domain-check" type="checkbox" name="setup_domains" value="{row.domain}" id="setup-dom-{i}">'
    else:
      checkbox = '<input class="form-check-input" type="checkbox" disabled>'
    html += f"""<div class="col-12 col-md-6 col-lg-4 setup-domain-item" data-account="{account}">
  <div class="form-check d-flex align-items-center gap-2 py-1">
    {checkbox}
    <label class="form-check-label flex-grow-1" for="setup-dom-{i}">{row.domain}</label>
    {label}
  </div>
  <div class="text-muted small ms-4">{account or '—'}</div>
</div>\n"""
  return html

def render_purchase_history():
  """Builds the 'Історія покупок' table rows from the full DomainPurchase log."""
  try:
    rows = DomainPurchase.query.order_by(DomainPurchase.id.desc()).limit(200).all()
    if not rows:
      return '<tr><td colspan="9" class="text-center text-muted">Історія покупок поки що порожня</td></tr>'
    html = ""
    for r in rows:
      color = "table-success" if r.status == "success" else "table-danger"
      html += f"""  <tr class="{color}">
    <td>{r.id}</td>
    <td>{r.domain}</td>
    <td>{r.registrator}</td>
    <td>{r.cloudflare_account or "-"}</td>
    <td>{r.status}</td>
    <td>{r.stage}</td>
    <td>{r.message or ""}</td>
    <td>{r.purchased_by}</td>
    <td>{r.created.strftime('%d-%m-%Y %H:%M:%S')}</td>
  </tr>\n"""
    return html
  except Exception as err:
    logging.error(f"render_purchase_history(): global error {err}")
    return f'<tr><td colspan="9">Помилка завантаження історії: {err}</td></tr>'

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

def _update_purchase_row(domain: str, account, status: str, message: str, stage: str = None):
  row = DomainPurchase.query.filter_by(domain=domain).order_by(DomainPurchase.id.desc()).first()
  if row:
    row.cloudflare_account = account
    row.status = status
    row.message = message
    if stage is not None:
      row.stage = stage
    db.session.commit()

def get_purchase_row(domain: str):
  """Returns the most recent DomainPurchase row for the given domain, or None."""
  return DomainPurchase.query.filter_by(domain=domain).order_by(DomainPurchase.id.desc()).first()

def append_purchase_message(row: DomainPurchase, text: str, stage: str = None):
  """Appends one more step's note to the domain's running message log (Крок 2 keeps extending it
  through deploy -> email routing instead of overwriting the earlier purchase/NS message)."""
  row.message = f"{row.message}; {text}" if row.message else text
  if stage is not None:
    row.stage = stage
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
      if ok:
        #only a successful purchase gets a DB record - a failed attempt leaves no trace of the domain at all
        db.session.add(DomainPurchase(domain=domain, registrator=registrator.name, cloudflare_account=None, status="success", message="Куплено, очікує налаштування Cloudflare", purchased_by=realname, stage="just_bought"))
        db.session.commit()
        purchased.append(domain)
        purchase_log.append((domain, True, "Домен успішно куплено"))
      else:
        logging.error(f"purchase_and_setup_domains(): Purchase failed for domain {domain}, skipping any DB records for it: {msg}")
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
          _update_purchase_row(domain, acc.account, "success", "Додано в Cloudflare, NS встановлено, зареєстровано в базі", stage="ns_set")
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
