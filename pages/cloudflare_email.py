import logging
import os
import requests
from flask import Blueprint, current_app, jsonify, request, redirect, render_template, flash
from flask_login import login_required, current_user
from db.database import Cloudflare, CloudflareEmailsStatus, CloudflareEmailsRules
from db.db import db
from functions.site_actions import is_admin

cloudflare_email_bp = Blueprint("cloudflare_email", __name__)

def _format_rule(rule: dict) -> str:
  """Builds a short human-readable description of a single Cloudflare Email Routing rule"""
  matchers = ", ".join(str(m.get("value", m.get("type",""))) for m in rule.get("matchers", []))
  actions = []
  for a in rule.get("actions", []):
    value = a.get("value", [])
    if isinstance(value, list):
      value = ",".join(str(v) for v in value)
    actions.append(f"{a.get('type','')}:{value}")
  actions_str = ", ".join(actions)
  status = "enabled" if rule.get("enabled") else "disabled"
  return f"{matchers} -> {actions_str} [{status}]"[:500]

def _find_zone_for_domain(domain: str):
  """Looks up which Cloudflare account hosts the given domain. Returns (account, headers, zone_id) or (None, None, None)"""
  accounts = Cloudflare.query.all()
  for acc in accounts:
    headers = {
      "X-Auth-Email": acc.account,
      "X-Auth-Key": acc.token,
      "Content-Type": "application/json"
    }
    url = f"https://api.cloudflare.com/client/v4/zones?name={domain}"
    r = requests.get(url, headers=headers, timeout=10).json()
    if r.get("success") and r.get("result"):
      return acc, headers, r["result"][0]["id"]
  return None, None, None

def _get_account_id(headers: dict):
  """Returns the Cloudflare account ID (needed for the destination addresses endpoint, which is account-scoped, not zone-scoped)"""
  url = "https://api.cloudflare.com/client/v4/accounts"
  r = requests.get(url, headers=headers, timeout=10).json()
  if r.get("success") and r.get("result"):
    return r["result"][0]["id"]
  return None

def _get_routing_status(zone_id: str, headers: dict) -> bool:
  """Queries the current Email Routing enabled/disabled status for a zone"""
  url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing"
  r = requests.get(url, headers=headers, timeout=10).json()
  if r.get("success"):
    return bool(r.get("result", {}).get("enabled", False))
  logging.error(f"_get_routing_status(): Failed to load Email Routing status for zone {zone_id}: {r.get('errors')}")
  return False

def _get_routing_rules(zone_id: str, headers: dict) -> list:
  """Queries the full list of Email Routing rules for a zone (handles pagination)"""
  rules = []
  page = 1
  while True:
    url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/rules?per_page=50&page={page}"
    r = requests.get(url, headers=headers, timeout=10).json()
    if not r.get("success"):
      logging.error(f"_get_routing_rules(): Failed to load Email Routing rules for zone {zone_id}: {r.get('errors')}")
      break
    rules.extend(r.get("result", []))
    if page >= r.get("result_info", {}).get("total_pages", 1):
      break
    page += 1
  return rules

def _get_destination_addresses(account_id: str, headers: dict) -> list:
  """Queries the full list of Email Routing destination addresses available on the Cloudflare account (handles pagination)"""
  addresses = []
  if not account_id:
    return addresses
  page = 1
  while True:
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/email/routing/addresses?per_page=50&page={page}"
    r = requests.get(url, headers=headers, timeout=10).json()
    if not r.get("success"):
      logging.error(f"_get_destination_addresses(): Failed to load destination addresses for account {account_id}: {r.get('errors')}")
      break
    addresses.extend(r.get("result", []))
    if page >= r.get("result_info", {}).get("total_pages", 1):
      break
    page += 1
  return addresses

def _sync_status_to_db(domain: str, routing_enabled: bool, actor: str) -> None:
  """Keeps CloudflareEmailsStatus in sync with the actual status received from Cloudflare"""
  record = CloudflareEmailsStatus.query.filter_by(domain=domain).first()
  if not record:
    db.session.add(CloudflareEmailsStatus(domain=domain, routing_enabled=routing_enabled, enabledby=actor, updatedby=actor))
    db.session.commit()
    logging.info(f"_sync_status_to_db(): New Email Routing status record created for domain {domain}: {routing_enabled} (by {actor})")
  elif record.routing_enabled != routing_enabled:
    record.routing_enabled = routing_enabled
    record.updatedby = actor
    db.session.commit()
    logging.info(f"_sync_status_to_db(): Email Routing status for domain {domain} changed to {routing_enabled} (by {actor})")

def _sync_rules_to_db(domain: str, rules: list) -> None:
  """Re-writes the whole CloudflareEmailsRules rule set for the domain with the current one received from Cloudflare"""
  CloudflareEmailsRules.query.filter_by(domain=domain).delete()
  for rule in rules:
    db.session.add(CloudflareEmailsRules(domain=domain, rule=_format_rule(rule)))
  db.session.commit()

@cloudflare_email_bp.route("/cloudflare_email/update_emails_status", methods=['GET'])
def update_emails_status():
  """GET request: queries Cloudflare Email Routing status and rules for every domain in every Cloudflare account stored in DB, and syncs CloudflareEmailsStatus/CloudflareEmailsRules tables. Meant to be triggered periodically by a cron job."""
  try:
    logging.info("update_emails_status(): -----------------------Starting Cloudflare Email Routing status update-----------------------")
    web_folder = current_app.config.get("WEB_FOLDER","")
    if web_folder == "":
      logging.error("update_emails_status(): ERROR! - web_folder variable is empty!")
      return jsonify({"status": "error", "message": "web_folder is empty"}), 500
    #only the sites which are actually present on this server should be synced, not the whole Cloudflare account
    sites_list = [
      name for name in os.listdir(web_folder)
      if os.path.isdir(os.path.join(web_folder, name)) and not name.startswith('.')
    ]
    processed = 0
    errors = 0
    accounts = Cloudflare.query.all()
    for acc in accounts:
      headers = {
        "X-Auth-Email": acc.account,
        "X-Auth-Key": acc.token,
        "Content-Type": "application/json"
      }
      page = 1
      while True:
        url = f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={page}"
        r = requests.get(url, headers=headers, timeout=10).json()
        if not r.get("success"):
          logging.error(f"update_emails_status(): Failed to load zones for account {acc.account}: {r.get('errors')}")
          errors += 1
          break
        for zone in r.get("result", []):
          domain = zone["name"]
          #skip domains which are not actually hosted on this server
          if domain not in sites_list:
            continue
          zone_id = zone["id"]
          try:
            routing_enabled = _get_routing_status(zone_id, headers)
            _sync_status_to_db(domain, routing_enabled, "cron job")
            rules = _get_routing_rules(zone_id, headers)
            _sync_rules_to_db(domain, rules)
            processed += 1
          except Exception as err:
            logging.error(f"update_emails_status(): Error while processing domain {domain}: {err}")
            errors += 1
        if page >= r.get("result_info", {}).get("total_pages", 1):
          break
        page += 1
    logging.info(f"update_emails_status(): -----------------------Finished. Domains processed: {processed}, errors: {errors}-----------------------")
    return jsonify({"status": "done", "processed": processed, "errors": errors}), 200
  except Exception as err:
    logging.error(f"update_emails_status(): Global error: {err}")
    return jsonify({"status": "error", "message": str(err)}), 500

@cloudflare_email_bp.route("/cloudflare_email/manage", methods=['GET'])
@login_required
def manage_email():
  """GET request: shows the Email Routing management page for a single domain - current status, rules and available destination addresses, all read live from the Cloudflare API"""
  domain = (request.args.get("domain") or "").strip()
  if not domain:
    flash('Домен не вказано!','alert alert-danger')
    return redirect("/",302)
  try:
    acc, headers, zone_id = _find_zone_for_domain(domain)
    if not acc:
      logging.error(f"manage_email(): Domain {domain} was not found in any of the Cloudflare accounts in DB!")
      flash(f'Домен {domain} не знайдено у жодному з аккаунтів Cloudflare!','alert alert-danger')
      return redirect("/",302)
    routing_enabled = _get_routing_status(zone_id, headers)
    rules = _get_routing_rules(zone_id, headers)
    account_id = _get_account_id(headers)
    addresses = _get_destination_addresses(account_id, headers)
    #keep the DB in sync with what we just saw live on Cloudflare
    _sync_status_to_db(domain, routing_enabled, current_user.realname)
    _sync_rules_to_db(domain, rules)
    #------------------------- status block -------------------------
    if routing_enabled:
      status_html = '<span class="badge bg-success fs-6">✅ Email Routing увімкнено</span>'
      toggle_button = '<button type="submit" class="btn btn-warning" name="buttonDisableRouting" onclick="showLoading()" data-bs-toggle="tooltip" data-bs-placement="top" title="Вимкнути обробку вхідної електронної пошти для цього домену.">🚫Вимкнути Email Routing</button>'
    else:
      status_html = '<span class="badge bg-secondary fs-6">📪 Email Routing вимкнено</span>'
      toggle_button = '<button type="submit" class="btn btn-success" name="buttonEnableRouting" onclick="showLoading()" data-bs-toggle="tooltip" data-bs-placement="top" title="Увімкнути обробку вхідної електронної пошти для цього домену.">✅Увімкнути Email Routing</button>'
    #------------------------- rules table -------------------------
    if not rules:
      rules_html = '<tr><td colspan="6" class="text-center text-muted">Правил поки що немає</td></tr>'
    else:
      rules_html = ""
      for i, rule in enumerate(rules, 1):
        rule_id = rule.get("id", rule.get("tag",""))
        matchers = ", ".join(str(m.get("value", m.get("type",""))) for m in rule.get("matchers", []))
        actions = []
        for a in rule.get("actions", []):
          value = a.get("value", [])
          if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
          actions.append(f"{a.get('type','')}: {value}")
        actions_str = ", ".join(actions)
        enabled_badge = '<span class="badge bg-success">увімкнено</span>' if rule.get("enabled") else '<span class="badge bg-secondary">вимкнено</span>'
        rules_html += f"""
  <tr class="table-success">
    <td class="table-success cname-cell">{i}</td>
    <td class="table-success cname-cell">{rule.get('name','')}</td>
    <td class="table-success cname-cell">{matchers}</td>
    <td class="table-success cname-cell">{actions_str}</td>
    <td class="table-success cname-cell">{enabled_badge}</td>
    <td class="table-success cname-cell">
      <form action="/cloudflare_email/manage" method="POST" id="postform" novalidate>
        <input type="hidden" name="domain" value="{domain}">
        <button type="submit" class="btn btn-outline-warning DeleteRule-btn" name="buttonDeleteRule" onclick="showLoading()" value="{rule_id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити це правило.">❌</button>
      </form>
    </td>
  </tr>"""
    #------------------------- destination addresses table -------------------------
    if not addresses:
      addresses_html = '<tr><td colspan="3" class="text-center text-muted">Адреси призначення відсутні</td></tr>'
      addresses_options = ""
    else:
      addresses_html = ""
      addresses_options = ""
      for i, addr in enumerate(addresses, 1):
        email = addr.get("email","")
        verified = bool(addr.get("verified"))
        verified_badge = '<span class="badge bg-success">верифіковано</span>' if verified else '<span class="badge bg-warning text-dark">не верифіковано</span>'
        addresses_html += f"""
  <tr class="table-success">
    <td class="table-success cname-cell">{i}</td>
    <td class="table-success cname-cell">{email}</td>
    <td class="table-success cname-cell">{verified_badge}</td>
  </tr>"""
        #only verified addresses can actually be used as a forwarding destination on Cloudflare
        if verified:
          addresses_options += f'<option value="{email}">{email}</option>'
    return render_template(
      "template-cloudflare_email.html",
      domain=domain,
      account=acc.account,
      status_html=status_html,
      toggle_button=toggle_button,
      rules_html=rules_html,
      addresses_html=addresses_html,
      addresses_options=addresses_options,
      admin_panel=is_admin()
    )
  except Exception as err:
    logging.error(f"manage_email(): general error by {current_user.realname} for domain {domain}: {err}")
    flash(f'Помилка завантаження інформації Email Routing для домену {domain}! Дивіться логи.','alert alert-danger')
    return redirect("/",302)

@cloudflare_email_bp.route("/cloudflare_email/manage", methods=['POST'])
@login_required
def catch_manage_email():
  """POST request processor: handles enable/disable Email Routing and add/delete routing rule actions for a single domain"""
  domain = (request.form.get("domain") or "").strip()
  if not domain:
    flash('Домен не вказано!','alert alert-danger')
    return redirect("/",302)
  try:
    acc, headers, zone_id = _find_zone_for_domain(domain)
    if not acc:
      logging.error(f"catch_manage_email(): Domain {domain} was not found in any of the Cloudflare accounts in DB!")
      flash(f'Домен {domain} не знайдено у жодному з аккаунтів Cloudflare!','alert alert-danger')
      return redirect("/",302)
    #------------------------- enable/disable Email Routing -------------------------
    if "buttonEnableRouting" in request.form or "buttonDisableRouting" in request.form:
      action = "enable" if "buttonEnableRouting" in request.form else "disable"
      url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/{action}"
      result = requests.post(url, headers=headers, json={}, timeout=10).json()
      if result.get("success"):
        logging.info(f"catch_manage_email(): Email Routing {action}d for domain {domain} by {current_user.realname}")
        flash(f'Email Routing для домену {domain} успішно {"увімкнено" if action == "enable" else "вимкнено"}!','alert alert-success')
      else:
        error_msg = (result.get("errors", [{}])[0].get("message", "Unknown error"))
        logging.error(f"catch_manage_email(): Failed to {action} Email Routing for domain {domain}: {result.get('errors')}")
        flash(f'Помилка при зміні статусу Email Routing для домену {domain}: <strong>{error_msg}</strong>','alert alert-danger')
    #------------------------- add new rule -------------------------
    elif "buttonAddRule" in request.form:
      matcher = request.form.get("new-rule-matcher","").strip()
      destination = request.form.get("new-rule-destination","").strip()
      name = request.form.get("new-rule-name","").strip() or matcher
      enabled = "new-rule-enabled" in request.form
      if not matcher or not destination:
        flash('Один або декілька важливих параметрів для створення правила не були отримані сервером!','alert alert-warning')
        return redirect(f"/cloudflare_email/manage?domain={domain}",302)
      url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/rules"
      data = {
        "name": name,
        "enabled": enabled,
        "matchers": [{"type": "literal", "field": "to", "value": matcher}],
        "actions": [{"type": "forward", "value": [destination]}]
      }
      result = requests.post(url, headers=headers, json=data, timeout=10).json()
      if result.get("success"):
        logging.info(f"catch_manage_email(): New Email Routing rule '{name}' ({matcher} -> {destination}) created for domain {domain} by {current_user.realname}")
        flash(f'Нове правило {matcher} -&gt; {destination} успішно створено для домену {domain}!','alert alert-success')
      else:
        error_msg = (result.get("errors", [{}])[0].get("message", "Unknown error"))
        logging.error(f"catch_manage_email(): Failed to create Email Routing rule for domain {domain}: {result.get('errors')}")
        flash(f'Помилка при створенні правила для домену {domain}: <strong>{error_msg}</strong>','alert alert-danger')
    #------------------------- delete an existing rule -------------------------
    elif "buttonDeleteRule" in request.form:
      rule_id = request.form.get("buttonDeleteRule","").strip()
      if not rule_id:
        flash('ID правила не був отриман сервером!','alert alert-warning')
        return redirect(f"/cloudflare_email/manage?domain={domain}",302)
      url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/rules/{rule_id}"
      result = requests.delete(url, headers=headers, timeout=10).json()
      if result.get("success"):
        logging.info(f"catch_manage_email(): Email Routing rule {rule_id} deleted for domain {domain} by {current_user.realname}")
        flash(f'Правило успішно видалено для домену {domain}!','alert alert-success')
      else:
        error_msg = (result.get("errors", [{}])[0].get("message", "Unknown error"))
        logging.error(f"catch_manage_email(): Failed to delete Email Routing rule {rule_id} for domain {domain}: {result.get('errors')}")
        flash(f'Помилка при видаленні правила для домену {domain}: <strong>{error_msg}</strong>','alert alert-danger')
    else:
      flash('Помилка! Ні один з можливих параметрів не був переданий!','alert alert-danger')
      logging.error(f"catch_manage_email(): Something strange was received via POST request for domain {domain} and we can't process that.")
    #refresh the live status/rules from Cloudflare and keep the DB in sync with whatever just happened
    routing_enabled = _get_routing_status(zone_id, headers)
    _sync_status_to_db(domain, routing_enabled, current_user.realname)
    rules = _get_routing_rules(zone_id, headers)
    _sync_rules_to_db(domain, rules)
    return redirect(f"/cloudflare_email/manage?domain={domain}",302)
  except Exception as err:
    logging.error(f"catch_manage_email(): general error by {current_user.realname} for domain {domain}: {err}")
    flash(f'Неочікувана помилка при обробці запиту Email Routing для домену {domain}! Дивіться логи.','alert alert-danger')
    return redirect(f"/cloudflare_email/manage?domain={domain}",302)
