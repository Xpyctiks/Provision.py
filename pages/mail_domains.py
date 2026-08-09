import logging
from flask import render_template,request,redirect,flash,Blueprint,current_app
from flask_login import login_required,current_user
from db.database import Cloudflare,User,MailServerDomainStatus
from functions.site_actions import is_admin,is_mail_admin
from functions.rights_required import rights_required,ADMIN_RIGHTS
from functions.mail_domains_func import (
  load_mail_domains_list,render_mail_domains_list,provision_mail_domain,deprovision_mail_domain
)

mail_domains_bp = Blueprint("mail_domains", __name__)

@mail_domains_bp.route("/mail_domains/", methods=['GET'])
@login_required
@rights_required(ADMIN_RIGHTS)
def show_mail_domains():
  """GET request: Крок 1 - pick a Cloudflare account, then a domain hosted on it, to provision for mail sending"""
  try:
    cf_accounts_options = "".join(f'<option value="{a.account}">{a.account}</option>' for a in Cloudflare.query.order_by(Cloudflare.account).all())
    return render_template(
      "template-mail_domains.html",active1="active",
      cf_accounts_options=cf_accounts_options,
      admin_panel=is_admin(),mail_admin=is_mail_admin(),version=current_app.config.get("VERSION","")
    )
  except Exception as err:
    logging.error(f"show_mail_domains(): general render error by {current_user.realname}: {err}")
    flash("Неочікувана помилка на сторінці налаштування доменів для розсилок, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

@mail_domains_bp.route("/mail_domains/", methods=['POST'])
@login_required
@rights_required(ADMIN_RIGHTS)
def do_add_mail_domain():
  """POST request processor: provisions the selected domain (from the selected Cloudflare account) for mail sending.
  Mailbox login is always "order", per the project-wide convention (see functions/provision_func.py:finishJob())."""
  try:
    domain = (request.form.get("mail_domain") or "").strip()
    cf_account = (request.form.get("mail_cf_account") or "").strip()
    if not domain or not cf_account:
      flash("Помилка! Оберіть аккаунт Cloudflare та домен!", 'alert alert-danger')
      return redirect("/mail_domains/",302)
    ok, message = provision_mail_domain(domain, "order", cf_account, current_user.realname)
    flash(f"{domain}: {message}", 'alert alert-success' if ok else 'alert alert-danger')
    return redirect("/mail_domains/list/",302)
  except Exception as err:
    logging.error(f"do_add_mail_domain(): general error by {current_user.realname}: {err}")
    flash("Неочікувана помилка при налаштуванні домену, дивіться логи!", 'alert alert-danger')
    return redirect("/mail_domains/",302)

@mail_domains_bp.route("/mail_domains/list/", methods=['GET'])
@login_required
@rights_required(ADMIN_RIGHTS)
def show_mail_domains_list():
  """GET request: Крок 2 - unified current-status + history list, one row per domain"""
  try:
    rows = load_mail_domains_list()
    domains_html = render_mail_domains_list(rows)
    users_list = "".join(f'<option value="{u.realname}">{u.realname}</option>' for u in User.query.order_by(User.username).all())
    cf_accounts_list = "".join(f'<option value="{a.account}">{a.account}</option>' for a in Cloudflare.query.order_by(Cloudflare.account).all())
    return render_template(
      "template-mail_domains.html",active2="active",
      domains_html=domains_html,users_list=users_list,cf_accounts_list=cf_accounts_list,
      admin_panel=is_admin(),mail_admin=is_mail_admin(),version=current_app.config.get("VERSION","")
    )
  except Exception as err:
    logging.error(f"show_mail_domains_list(): general render error by {current_user.realname}: {err}")
    flash("Неочікувана помилка на сторінці налаштування доменів для розсилок, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

@mail_domains_bp.route("/mail_domains/retry/", methods=['POST'])
@login_required
@rights_required(ADMIN_RIGHTS)
def retry_mail_domain():
  """POST request processor: (re)provisions a domain, reusing the mailbox/Cloudflare account already on record for it"""
  try:
    domain = (request.form.get("domain") or "").strip()
    if not domain:
      flash("Помилка! Домен не вказано!", 'alert alert-danger')
      return redirect("/mail_domains/list/",302)
    row = MailServerDomainStatus.query.filter_by(domain=domain).first()
    mailbox = row.mailbox if row and row.mailbox else "order"
    cf_account = row.cloudflare_account if row else None
    if not cf_account:
      flash(f"Помилка! Невідомий аккаунт Cloudflare для домену {domain}, повторити неможливо!", 'alert alert-danger')
      return redirect("/mail_domains/list/",302)
    ok, message = provision_mail_domain(domain, mailbox, cf_account, current_user.realname)
    flash(f"{domain}: {message}", 'alert alert-success' if ok else 'alert alert-danger')
    return redirect("/mail_domains/list/",302)
  except Exception as err:
    logging.error(f"retry_mail_domain(): general error by {current_user.realname}: {err}")
    flash("Неочікувана помилка при повторному налаштуванні, дивіться логи!", 'alert alert-danger')
    return redirect("/mail_domains/list/",302)

@mail_domains_bp.route("/mail_domains/delete/", methods=['POST'])
@login_required
@rights_required(ADMIN_RIGHTS)
def delete_mail_domain():
  """POST request processor: deprovisions a domain from the remote mail server and rolls back its DNS records"""
  try:
    domain = (request.form.get("domain") or "").strip()
    if not domain:
      flash("Помилка! Домен не вказано!", 'alert alert-danger')
      return redirect("/mail_domains/list/",302)
    ok, message = deprovision_mail_domain(domain, current_user.realname)
    flash(f"{domain}: {message}", 'alert alert-success' if ok else 'alert alert-danger')
    return redirect("/mail_domains/list/",302)
  except Exception as err:
    logging.error(f"delete_mail_domain(): general error by {current_user.realname}: {err}")
    flash("Неочікувана помилка при видаленні, дивіться логи!", 'alert alert-danger')
    return redirect("/mail_domains/list/",302)
