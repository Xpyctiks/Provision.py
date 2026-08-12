import logging
import os
import json
import requests
from flask import render_template,request,redirect,flash,Blueprint,current_app
from flask_login import login_required,current_user
from db.database import Cloudflare,DomainRegistrator,Provision_templates
from functions.site_actions import is_admin,is_mail_admin,clearCache
from functions.rights_required import rights_required,ADMIN_RIGHTS
from functions.pages_forms import loadTemplatesList,loadServersList
from functions.clone_func import start_clone
from functions.provision_func import start_autoprovision,finishJob
from functions.domain_purchase_func import (
  parse_domain_textarea,load_domain_registrators,load_cf_accounts_checkboxes,render_purchase_history,
  purchase_and_setup_domains,recheck_domain_statuses,load_actionable_domains,distinct_actionable_accounts,
  render_actionable_domains,get_purchase_row,append_purchase_message
)
from pages.cloudflare_email import (
  _get_account_id,_get_destination_addresses,_get_routing_status,_get_routing_rules,
  _sync_status_to_db,_sync_rules_to_db
)

domain_purchase_bp = Blueprint("domain_purchase", __name__)

def _build_flash(result: dict):
  """Builds one aggregated flash message (message, category) out of the pipeline result."""
  if result.get("aborted"):
    return result["reason"], 'alert alert-danger'
  purchase_log = result["purchase_log"]
  cf_setup_log = result["cf_setup_log"]
  purchased_count = result["purchased_count"]
  total_count = result["total_count"]
  cf_ok = sum(1 for _, ok, _ in cf_setup_log if ok)
  cf_total = len(cf_setup_log)
  lines = [f"<strong>Куплено доменів: {purchased_count} з {total_count}</strong>"]
  for domain, ok, msg in purchase_log:
    lines.append(f"{'✅' if ok else '❌'} {domain}: {msg}")
  if cf_setup_log:
    lines.append(f"<hr><strong>Налаштування Cloudflare: {cf_ok} з {cf_total} успішно</strong>")
    for domain, ok, msg in cf_setup_log:
      lines.append(f"{'✅' if ok else '❌'} {domain}: {msg}")
  message = "<br>".join(lines)
  if purchased_count == total_count and cf_ok == cf_total and total_count > 0:
    category = 'alert alert-success'
  elif purchased_count == 0 and cf_ok == 0:
    category = 'alert alert-danger'
  else:
    category = 'alert alert-warning'
  return message, category

@domain_purchase_bp.route("/domain_purchase/", methods=['GET'])
@login_required
@rights_required(ADMIN_RIGHTS)
def show_domain_purchase():
  """GET request: redirects the bare page to Крок 1"""
  return redirect("/domain_purchase/step1/",302)

@domain_purchase_bp.route("/domain_purchase/step1/", methods=['GET'])
@login_required
@rights_required(ADMIN_RIGHTS)
def show_domain_purchase_step1():
  """GET request: shows Крок 1 - the purchase form"""
  try:
    cf_checkboxes = load_cf_accounts_checkboxes()
    reg_list, first_reg = load_domain_registrators()
    return render_template("template-domain_purchase.html",active1="active",cf_checkboxes=cf_checkboxes,reg_list=reg_list,first_reg=first_reg,admin_panel=is_admin(),mail_admin=is_mail_admin(),version=current_app.config.get("VERSION",""))
  except Exception as err:
    logging.error(f"show_domain_purchase_step1(): general render error by {current_user.realname}: {err}")
    flash("Неочікувана помилка на сторінці купівлі доменів, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

@domain_purchase_bp.route("/domain_purchase/step1/", methods=['POST'])
@login_required
@rights_required(ADMIN_RIGHTS)
def do_domain_purchase():
  """POST request processor: runs the whole purchase -> Cloudflare assignment -> DB registration pipeline"""
  try:
    domains_raw = request.form.get("domains", "")
    selected_cf_accounts = request.form.getlist("cf_accounts")
    selected_registrator = (request.form.get("selected_registrator") or "").strip()
    logging.info(f"-----------------------Domain purchase form submitted by {current_user.realname}: registrator={selected_registrator}, cf_accounts={selected_cf_accounts}-----------------------")
    if not domains_raw.strip() or not selected_cf_accounts or not selected_registrator:
      flash("Помилка! Не всі обов'язкові поля заповнені (список доменів, акаунти Cloudflare, реєстратор)!", 'alert alert-danger')
      logging.error("do_domain_purchase(): some of the important parameters has not been received!")
      return redirect("/domain_purchase/step1/",302)
    registrator = DomainRegistrator.query.filter_by(name=selected_registrator).first()
    if not registrator:
      flash(f"Помилка! Реєстратор {selected_registrator} не знайден в базі!", 'alert alert-danger')
      logging.error(f"do_domain_purchase(): registrator {selected_registrator} not found in DB!")
      return redirect("/domain_purchase/step1/",302)
    cf_accounts = [Cloudflare.query.filter_by(account=acc).first() for acc in selected_cf_accounts]
    cf_accounts = [acc for acc in cf_accounts if acc is not None]
    if not cf_accounts:
      flash("Помилка! Жоден з обраних акаунтів Cloudflare не знайден в базі!", 'alert alert-danger')
      logging.error("do_domain_purchase(): none of the selected Cloudflare accounts were found in DB!")
      return redirect("/domain_purchase/step1/",302)
    domains, invalid_tokens = parse_domain_textarea(domains_raw)
    if invalid_tokens:
      flash(f"Увага! Наступні записи не є коректними доменами і були проігноровані: {', '.join(invalid_tokens)}", 'alert alert-warning')
    if not domains:
      flash("Помилка! У списку немає жодного коректного домену!", 'alert alert-danger')
      logging.error("do_domain_purchase(): no valid domains found in the submitted list!")
      return redirect("/domain_purchase/step1/",302)
    result = purchase_and_setup_domains(domains,cf_accounts,registrator,current_user.realname)
    message, category = _build_flash(result)
    flash(message, category)
    return redirect("/domain_purchase/step2/",302)
  except Exception as err:
    logging.error(f"do_domain_purchase(): general error by {current_user.realname}: {err}")
    flash("Неочікувана помилка при обробці купівлі доменів, дивіться логи!", 'alert alert-danger')
    return redirect("/domain_purchase/step1/",302)

@domain_purchase_bp.route("/domain_purchase/step2/", methods=['GET'])
@login_required
@rights_required(ADMIN_RIGHTS)
def show_domain_purchase_step2():
  """GET request: shows Крок 2 - re-checks live Cloudflare status for pending domains, then shows the
  actionable list (just_bought/ns_set/ready_to_setup) plus the deploy+email setup form"""
  try:
    recheck_domain_statuses()
    rows = load_actionable_domains()
    domains_html = render_actionable_domains(rows)
    accounts = distinct_actionable_accounts(rows)
    accounts_options = "".join(f'<option value="{a}">{a}</option>' for a in accounts)
    #pre-fetch verified destination addresses per distinct account (avoids an extra AJAX round trip client-side)
    addresses_by_account = {}
    for account_email in accounts:
      acc = Cloudflare.query.filter_by(account=account_email).first()
      if not acc:
        continue
      headers = {"X-Auth-Email": acc.account, "X-Auth-Key": acc.token, "Content-Type": "application/json"}
      account_id = _get_account_id(headers)
      addresses_by_account[account_email] = [a["email"] for a in _get_destination_addresses(account_id, headers) if a.get("verified")]
    web_folder = current_app.config.get("WEB_FOLDER","")
    sites_list = sorted([name for name in os.listdir(web_folder) if os.path.isdir(os.path.join(web_folder,name)) and not name.startswith('.')]) if web_folder and os.path.isdir(web_folder) else []
    sites_options = "".join(f'<option value="{s}">{s}</option>' for s in sites_list)
    templates_list, first_template = loadTemplatesList()
    server_list, first_server = loadServersList()
    return render_template(
      "template-domain_purchase.html",active2="active",
      domains_html=domains_html,accounts_options=accounts_options,
      addresses_by_account_json=json.dumps(addresses_by_account),
      sites_options=sites_options,templates=templates_list,first_template=first_template,
      server_list=server_list,first_server=first_server,
      admin_panel=is_admin(),mail_admin=is_mail_admin(),
      version=current_app.config.get("VERSION","")
    )
  except Exception as err:
    logging.error(f"show_domain_purchase_step2(): general render error by {current_user.realname}: {err}")
    flash("Неочікувана помилка на сторінці купівлі доменів, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

def _setup_email_for_domain(domain: str, account_email: str, destination: str, alias: str, realname: str):
  """Enables Email Routing (if needed) and creates a forwarding rule alias@domain -> destination for one domain.
  Mirrors the per-domain logic in pages/cloudflare_email.py / pages/cloudflare_email_bulk.py."""
  try:
    acc = Cloudflare.query.filter_by(account=account_email).first()
    if not acc:
      return False, "Cloudflare акаунт не знайдено в базі"
    headers = {"X-Auth-Email": acc.account, "X-Auth-Key": acc.token, "Content-Type": "application/json"}
    r = requests.get(f"https://api.cloudflare.com/client/v4/zones?name={domain}", headers=headers, timeout=10).json()
    if not (r.get("success") and r.get("result")):
      return False, "Зону домену не знайдено на Cloudflare"
    zone_id = r["result"][0]["id"]
    routing_enabled = _get_routing_status(zone_id, headers)
    if not routing_enabled:
      enable_result = requests.post(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/enable", headers=headers, json={}, timeout=10).json()
      if not enable_result.get("success"):
        return False, (enable_result.get("errors") or [{}])[0].get("message","Помилка активації Email Routing")
      routing_enabled = True
      logging.info(f"_setup_email_for_domain(): Email Routing enabled for {domain} by {realname}")
    matcher = f"{alias}@{domain}"
    rule_data = {
      "name": matcher,
      "enabled": True,
      "matchers": [{"type": "literal", "field": "to", "value": matcher}],
      "actions": [{"type": "forward", "value": [destination]}]
    }
    rule_result = requests.post(f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/rules", headers=headers, json=rule_data, timeout=10).json()
    _sync_status_to_db(domain, routing_enabled, realname)
    if not rule_result.get("success"):
      error_msg = (rule_result.get("errors") or [{}])[0].get("message", "Помилка створення правила")
      logging.error(f"_setup_email_for_domain(): Failed to create rule for {domain}: {rule_result.get('errors')}")
      return False, error_msg
    rules = _get_routing_rules(zone_id, headers)
    _sync_rules_to_db(domain, rules)
    logging.info(f"_setup_email_for_domain(): Rule {matcher} -> {destination} created for {domain} by {realname}")
    return True, "OK"
  except Exception as err:
    logging.error(f"_setup_email_for_domain(): error for domain {domain}: {err}")
    return False, str(err)

def _deploy_and_setup_email(domains: list, selected_server: str, selected_template: str, selected_clone_source: str, destination_email: str, email_alias: str, realname: str):
  """For each selected (ready_to_setup) domain: deploys it (clone an existing site, or provision from a template -
  reusing functions/clone_func.start_clone / functions/provision_func.start_autoprovision exactly like
  pages/clone.py and pages/provision.py do), then activates Email Routing + a forwarding rule. Every step
  appends its own note to the domain's DomainPurchase.message running log instead of overwriting it."""
  web_folder = current_app.config.get("WEB_FOLDER","")
  results = []
  for domain in domains:
    row = get_purchase_row(domain)
    if not row or row.stage != "ready_to_setup":
      results.append((domain, False, "Домен не має статусу 'готовий до розгортання', пропущено"))
      continue
    cf_account = row.cloudflare_account
    if not cf_account:
      results.append((domain, False, "У домену не вказано аккаунт Cloudflare, пропущено"))
      continue
    finalPath = os.path.join(web_folder, domain)
    if os.path.exists(finalPath):
      results.append((domain, False, "Сайт з такою назвою вже існує на сервері, розгортання пропущено"))
      continue
    logging.info(f"-----------------------Starting deploy for domain {domain} (account {cf_account}, server {selected_server}) by {realname}-----------------------")
    if selected_clone_source:
      deployed = start_clone(domain, selected_clone_source, cf_account, selected_server, realname, web_folder, its_not_a_subdomain=True)
      #start_clone() does not register the DB records itself - the caller (like pages/clone.py) must call finishJob()
      if deployed:
        finishJob("",domain,cf_account,selected_server)
      else:
        finishJob("",domain,cf_account,selected_server,emerg_shutdown=True)
    else:
      repo = Provision_templates.query.filter_by(name=selected_template).first()
      if not repo:
        results.append((domain, False, "Шаблон не знайдено в базі"))
        continue
      #start_autoprovision() already calls finishJob() internally on both success and failure
      deployed = start_autoprovision(domain, cf_account, selected_server, repo.repository, realname, its_not_a_subdomain=True)
    if not deployed:
      logging.error(f"_deploy_and_setup_email(): Deploy failed for domain {domain}")
      results.append((domain, False, "Помилка розгортання сайту, дивіться логи"))
      continue
    clearCache()
    #the running message log only ever gets a note on SUCCESS of a step - failures are logged and shown
    #in the flash summary for this request, but never written to DomainPurchase.message
    append_purchase_message(row, "Сайт розгорнуто", stage="ready_to_email")
    ok, msg = _setup_email_for_domain(domain, cf_account, destination_email, email_alias, realname)
    if not ok:
      results.append((domain, False, f"Сайт розгорнуто, але помилка Email Routing: {msg}"))
      continue
    append_purchase_message(row, "Email Routing активовано", stage="done")
    results.append((domain, True, "Сайт розгорнуто, Email Routing активовано"))
  return results

@domain_purchase_bp.route("/domain_purchase/step2/", methods=['POST'])
@login_required
@rights_required(ADMIN_RIGHTS)
def do_domain_purchase_step2():
  """POST request processor: deploys every selected ready_to_setup domain and sets up its Email Routing"""
  try:
    selected_domains = request.form.getlist("setup_domains")
    selected_server = (request.form.get("selected_server") or "").strip()
    selected_template = (request.form.get("selected_template") or "").strip()
    selected_clone_source = (request.form.get("selected_clone_source") or "").strip()
    destination_email = (request.form.get("destination_email") or "").strip()
    email_alias = (request.form.get("email_alias") or "support").strip() or "support"
    logging.info(f"-----------------------Domain setup form submitted by {current_user.realname}: domains={selected_domains}, server={selected_server}, template={selected_template}, clone_source={selected_clone_source}, destination={destination_email}, alias={email_alias}-----------------------")
    if not selected_domains or not selected_server or not destination_email:
      flash("Помилка! Оберіть хоча б один домен зі статусом 'готовий до розгортання', сервер та адресу призначення для пошти!", 'alert alert-danger')
      return redirect("/domain_purchase/step2/",302)
    if not selected_clone_source and not selected_template:
      flash("Помилка! Оберіть шаблон для розгортання, або сайт для клонування!", 'alert alert-danger')
      return redirect("/domain_purchase/step2/",302)
    results = _deploy_and_setup_email(selected_domains,selected_server,selected_template,selected_clone_source,destination_email,email_alias,current_user.realname)
    lines = []
    ok_count = 0
    for domain, ok, msg in results:
      lines.append(f"{'✅' if ok else '❌'} {domain}: {msg}")
      if ok:
        ok_count += 1
    message = "<br>".join(lines) if lines else "Жодного домену не оброблено."
    if results and ok_count == len(results):
      category = 'alert alert-success'
    elif ok_count == 0:
      category = 'alert alert-danger'
    else:
      category = 'alert alert-warning'
    flash(message, category)
    return redirect("/domain_purchase/step2/",302)
  except Exception as err:
    logging.error(f"do_domain_purchase_step2(): general error by {current_user.realname}: {err}")
    flash("Неочікувана помилка при розгортанні доменів, дивіться логи!", 'alert alert-danger')
    return redirect("/domain_purchase/step2/",302)

@domain_purchase_bp.route("/domain_purchase/history/", methods=['GET'])
@login_required
@rights_required(ADMIN_RIGHTS)
def show_domain_purchase_history():
  """GET request: shows the full purchase history log"""
  try:
    history_rows = render_purchase_history()
    return render_template("template-domain_purchase.html",active3="active",history_rows=history_rows,admin_panel=is_admin(),mail_admin=is_mail_admin(),version=current_app.config.get("VERSION",""))
  except Exception as err:
    logging.error(f"show_domain_purchase_hisory(): general render error by {current_user.realname}: {err}")
    flash("Неочікувана помилка на сторінці купівлі доменів, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)
