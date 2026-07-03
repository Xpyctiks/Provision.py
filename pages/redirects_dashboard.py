import glob
import logging
import os
from flask import Blueprint, current_app, jsonify, render_template, flash, redirect
from flask_login import login_required, current_user
from db.database import RedirectsRules, Domain_account, Cloudflare
from functions.site_actions import is_admin, sync_redirects_to_db

redirects_dashboard_bp = Blueprint("redirects_dashboard", __name__)
@redirects_dashboard_bp.route("/redirects_dashboard/", methods=['GET'])
@login_required
def show_redirects_dashboard():
  """GET request: shows a combined dashboard of all 301 redirects (RedirectsRules) grouped by domain, for every domain known in the DB"""
  try:
    rules = RedirectsRules.query.order_by(RedirectsRules.domain).all()
    account_by_domain = {a.domain: a.account for a in Domain_account.query.all()}
    #gathering all list of available Cloudflare accounts to put them into accounts filter list
    cf_accounts_list = ""
    for a in Cloudflare.query.order_by(Cloudflare.account).all():
      cf_accounts_list += f'<option value="{a.account}">{a.account}</option>'
    if not rules:
      rows_html = '<tr><td colspan="6" class="text-center text-muted">Дані відсутні. Зачекайте на синхронізацію редіректів або відкрийте менеджер редіректів для потрібного домену.</td></tr>'
    else:
      rules_by_domain = {}
      for r in rules:
        rules_by_domain.setdefault(r.domain, []).append(r)
      rows_html = ""
      for i, domain in enumerate(sorted(rules_by_domain.keys()), 1):
        domain_rules = rules_by_domain[domain]
        cf_account = account_by_domain.get(domain, "⌛нема інформації")
        items = "".join(f"<li>{r.from_path} → {r.to_path} ({r.redirect_type or '~'})</li>" for r in domain_rules)
        rules_cell = f"""<button class="btn btn-sm btn-outline-secondary" type="button" data-bs-toggle="collapse" data-bs-target="#redir{i}">{len(domain_rules)} шт. ▾</button>
        <div class="collapse mt-2" id="redir{i}"><ul class="mb-0 text-start small">{items}</ul></div>"""
        last_updated = max((r.updated for r in domain_rules if r.updated), default=None)
        updated_cell = last_updated.strftime('%d-%m-%Y %H:%M') if last_updated else ''
        rows_html += f"""
  <tr data-account="{cf_account}">
    <th scope="row">{i}</th>
    <td><a href="https://{domain}" target="_blank">{domain}</a></td>
    <td>{cf_account}</td>
    <td>{rules_cell}</td>
    <td>{updated_cell}</td>
    <td><a class="btn btn-sm btn-secondary" href="/redirects_manager?site={domain}" title="Перегляд та керування редіректами для цього домену.">⚙Керувати</a></td>
  </tr>"""
    return render_template("template-redirects_dashboard.html", rows_html=rows_html, cf_accounts_list=cf_accounts_list, admin_panel=is_admin())
  except Exception as err:
    logging.error(f"show_redirects_dashboard(): general error by {current_user.realname}: {err}")
    flash('Неочікувана помилка при завантаженні дашборду редіректів! Дивіться логи.', 'alert alert-danger')
    return redirect("/",302)

@redirects_dashboard_bp.route("/redirects_dashboard/update_redirects_status", methods=['GET'])
def update_redirects_status():
  """GET request: re-parses every 301-*.conf redirects file on this server and syncs the RedirectsRules DB table. Meant to be triggered periodically by a cron job or manually."""
  try:
    logging.info("update_redirects_status(): -----------------------Starting redirects status update-----------------------")
    conf_dir = current_app.config.get("NGX_ADD_CONF_DIR","")
    if not conf_dir:
      logging.error("update_redirects_status(): ERROR! - NGX_ADD_CONF_DIR variable is empty!")
      return jsonify({"status": "error", "message": "NGX_ADD_CONF_DIR is empty"}), 500
    processed = 0
    errors = 0
    for conf_file in glob.glob(os.path.join(conf_dir, "301-*.conf")):
      filename = os.path.basename(conf_file)
      domain = filename[len("301-"):-len(".conf")]
      try:
        sync_redirects_to_db(domain, "cron job")
        processed += 1
      except Exception as err:
        logging.error(f"update_redirects_status(): Error while processing domain {domain}: {err}")
        errors += 1
    logging.info(f"update_redirects_status(): -----------------------Finished. Domains processed: {processed}, errors: {errors}-----------------------")
    return jsonify({"status": "done", "processed": processed, "errors": errors}), 200
  except Exception as err:
    logging.error(f"update_redirects_status(): Global error: {err}")
    return jsonify({"status": "error", "message": str(err)}), 500
