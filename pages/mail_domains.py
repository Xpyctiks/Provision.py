import logging
from flask import render_template,request,redirect,flash,Blueprint,current_app,jsonify
from flask_login import login_required,current_user
from db.database import Cloudflare,User,MailServerDomainStatus
from functions.site_actions import is_admin,is_mail_admin
from functions.rights_required import rights_required,ADMIN_RIGHTS
from functions.mail_domains_func import (
  load_mail_domains_list,render_mail_domains_list,render_mail_domains_history,
  provision_mail_domain,deprovision_mail_domain
)

mail_domains_bp = Blueprint("mail_domains", __name__)

@mail_domains_bp.route("/mail_domains/", methods=['GET'])
@login_required
@rights_required(ADMIN_RIGHTS)
def show_mail_domains():
  """GET request: Крок 1 - list of domains configured (or failed to configure) on the remote mail server"""
  try:
    rows = load_mail_domains_list()
    domains_html = render_mail_domains_list(rows)
    users_list = "".join(f'<option value="{u.realname}">{u.realname}</option>' for u in User.query.order_by(User.username).all())
    cf_accounts_list = "".join(f'<option value="{a.account}">{a.account}</option>' for a in Cloudflare.query.order_by(Cloudflare.account).all())
    return render_template(
      "template-mail_domains.html",active1="active",
      domains_html=domains_html,users_list=users_list,cf_accounts_list=cf_accounts_list,
      admin_panel=is_admin(),mail_admin=is_mail_admin(),version=current_app.config.get("VERSION","")
    )
  except Exception as err:
    logging.error(f"show_mail_domains(): general render error by {current_user.realname}: {err}")
    flash("Неочікувана помилка на сторінці налаштування доменів для розсилок, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

@mail_domains_bp.route("/mail_domains/retry/", methods=['POST'])
@login_required
@rights_required(ADMIN_RIGHTS)
def retry_mail_domain():
  """POST request processor: retries provisioning a domain that previously failed"""
  try:
    domain = (request.form.get("domain") or "").strip()
    if not domain:
      flash("Помилка! Домен не вказано!", 'alert alert-danger')
      return redirect("/mail_domains/",302)
    last = MailServerDomainStatus.query.filter_by(domain=domain).order_by(MailServerDomainStatus.id.desc()).first()
    if not last or not last.mailbox:
      flash(f"Помилка! Немає збереженої поштової скриньки (mailbox) для домену {domain}, повторити неможливо!", 'alert alert-danger')
      return redirect("/mail_domains/",302)
    ok, message = provision_mail_domain(domain, last.mailbox, current_user.realname)
    flash(f"{domain}: {message}", 'alert alert-success' if ok else 'alert alert-danger')
    return redirect("/mail_domains/",302)
  except Exception as err:
    logging.error(f"retry_mail_domain(): general error by {current_user.realname}: {err}")
    flash("Неочікувана помилка при повторному налаштуванні, дивіться логи!", 'alert alert-danger')
    return redirect("/mail_domains/",302)

@mail_domains_bp.route("/mail_domains/delete/", methods=['POST'])
@login_required
@rights_required(ADMIN_RIGHTS)
def delete_mail_domain():
  """POST request processor: deprovisions a domain from the remote mail server and rolls back its DNS records"""
  try:
    domain = (request.form.get("domain") or "").strip()
    if not domain:
      flash("Помилка! Домен не вказано!", 'alert alert-danger')
      return redirect("/mail_domains/",302)
    ok, message = deprovision_mail_domain(domain, current_user.realname)
    flash(f"{domain}: {message}", 'alert alert-success' if ok else 'alert alert-danger')
    return redirect("/mail_domains/",302)
  except Exception as err:
    logging.error(f"delete_mail_domain(): general error by {current_user.realname}: {err}")
    flash("Неочікувана помилка при видаленні, дивіться логи!", 'alert alert-danger')
    return redirect("/mail_domains/",302)

@mail_domains_bp.route("/mail_domains/history/", methods=['GET'])
@login_required
@rights_required(ADMIN_RIGHTS)
def show_mail_domains_history():
  """GET request: Крок 2 - full history log of add/delete attempts"""
  try:
    history_rows = render_mail_domains_history()
    return render_template("template-mail_domains.html",active2="active",history_rows=history_rows,admin_panel=is_admin(),mail_admin=is_mail_admin(),version=current_app.config.get("VERSION",""))
  except Exception as err:
    logging.error(f"show_mail_domains_history(): general render error by {current_user.realname}: {err}")
    flash("Неочікувана помилка на сторінці налаштування доменів для розсилок, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

@mail_domains_bp.route("/api/sender_config/add_new_domain", methods=['POST'])
def api_add_new_domain():
  """Public webhook (no session login) - the remote mail server / automation calls this to have the
  project write DKIM/DMARC/SPF records for a domain it just started serving. Protected by a shared
  secret header instead of a login session, since there's no user session on the calling side.
  NOTE: change the header name/scheme here if your mail server automation needs something different."""
  try:
    expected_secret = current_app.config.get("MAIL_SERVER_API_SECRET","")
    provided_secret = request.headers.get("X-Api-Key","")
    if not expected_secret or provided_secret != expected_secret:
      logging.warning(f"api_add_new_domain(): rejected request from {request.remote_addr} - missing/invalid X-Api-Key")
      return jsonify({"success": False, "error": "Unauthorized"}), 401
    data = request.get_json(silent=True) or request.form
    domain = (data.get("domain") or "").strip() if data else ""
    mailbox = (data.get("mailbox") or "").strip() if data else ""
    if not domain or not mailbox:
      logging.error("api_add_new_domain(): missing domain or mailbox parameter")
      return jsonify({"success": False, "error": "domain and mailbox are required"}), 400
    ok, message = provision_mail_domain(domain, mailbox, actor="API (mail server)")
    return jsonify({"success": ok, "message": message}), (200 if ok else 400)
  except Exception as err:
    logging.error(f"api_add_new_domain(): general error: {err}")
    return jsonify({"success": False, "error": str(err)}), 500
