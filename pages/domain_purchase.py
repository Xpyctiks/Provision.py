import logging
from flask import render_template,request,redirect,flash,Blueprint
from flask_login import login_required,current_user
from db.database import Cloudflare,DomainRegistrator
from functions.site_actions import is_admin,is_mail_admin
from functions.rights_required import rights_required,ADMIN_RIGHTS
from functions.domain_purchase_func import parse_domain_textarea,load_domain_registrators,load_cf_accounts_checkboxes,render_purchase_history,purchase_and_setup_domains

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
    return render_template("template-domain_purchase.html",active1="active",cf_checkboxes=cf_checkboxes,reg_list=reg_list,first_reg=first_reg,admin_panel=is_admin(),mail_admin=is_mail_admin())
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
  """GET request: shows Крок 2 - the purchase history log"""
  try:
    history_rows = render_purchase_history()
    return render_template("template-domain_purchase.html",active2="active",history_rows=history_rows,admin_panel=is_admin(),mail_admin=is_mail_admin())
  except Exception as err:
    logging.error(f"show_domain_purchase_step2(): general render error by {current_user.realname}: {err}")
    flash("Неочікувана помилка на сторінці купівлі доменів, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)
