import glob
import logging
import os
import re
import subprocess
from flask import Blueprint,current_app,jsonify,render_template,flash,redirect
from flask_login import login_required,current_user
from db.database import RedirectsRules,Domain_account,Cloudflare
from functions.site_actions import is_admin,sync_redirects_to_db,is_mail_admin,clear_nginx_cache
from functions.rights_required import block_mail_admin,rights_required,ADMIN_RIGHTS

redirects_dashboard_bp = Blueprint("redirects_dashboard", __name__)
@redirects_dashboard_bp.route("/redirects_dashboard/", methods=['GET'])
@login_required
@block_mail_admin
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
    return render_template("template-redirects_dashboard.html", rows_html=rows_html, cf_accounts_list=cf_accounts_list, admin_panel=is_admin(),mail_admin=is_mail_admin(),version=current_app.config.get("VERSION",""))
  except Exception as err:
    logging.error(f"show_redirects_dashboard(): general error by {current_user.realname}: {err}")
    flash('Неочікувана помилка при завантаженні дашборду редіректів! Дивіться логи.', 'alert alert-danger')
    return redirect("/",302)

def _nginx_service_state() -> dict:
  """Reads the nginx systemd unit state (no sudo needed for 'systemctl show')."""
  result = subprocess.run(["systemctl","show","nginx","--property=ActiveState,SubState,MainPID"], capture_output=True, text=True, timeout=10)
  state = {}
  for line in result.stdout.splitlines():
    key, _, value = line.partition("=")
    state[key.strip()] = value.strip()
  return {"active_state": state.get("ActiveState",""), "sub_state": state.get("SubState",""), "pid": state.get("MainPID","0")}

@redirects_dashboard_bp.route("/redirects_dashboard/nginx_restart/", methods=['POST'])
@login_required
@rights_required(ADMIN_RIGHTS)
def nginx_restart():
  """POST request (AJAX): full restart (not reload) of Nginx. The restart itself runs in a detached process with a short
  delay, so this answer gets delivered even when the panel itself is served through the very same Nginx. The page then
  polls /redirects_dashboard/nginx_status/ until Nginx is back with a new master PID."""
  try:
    logging.info(f"-----------------------Nginx full restart requested by {current_user.realname}-----------------------")
    #never restart into a broken config - nginx wouldn't start back and all sites would stay down
    test = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True, timeout=30)
    if not (re.search(r".*test is successful.*",test.stderr) and re.search(r".*syntax is ok.*",test.stderr)):
      logging.error(f"nginx_restart(): Nginx config test failed, restart cancelled: {test.stderr.strip()}")
      return jsonify({"error": f"Перевірка конфігурації Nginx не пройдена, перезапуск скасовано:\n{test.stderr.strip()}"}), 400
    #the delayed restart can't report errors back, so check the sudo permission upfront
    check = subprocess.run(["sudo","-n","-l","systemctl","restart","nginx"], capture_output=True, text=True, timeout=10)
    if check.returncode != 0:
      logging.error(f"nginx_restart(): no sudo permission for 'systemctl restart nginx': {check.stderr.strip()}")
      return jsonify({"error": "Немає прав sudo на 'systemctl restart nginx' для користувача, від якого працює програма. Додайте правило в sudoers."}), 403
    old_state = _nginx_service_state()
    subprocess.Popen(["sh","-c","sleep 2; sudo systemctl restart nginx"], start_new_session=True,
                     stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    clear_nginx_cache()
    logging.info(f"nginx_restart(): Nginx restart scheduled by {current_user.realname}, old master PID {old_state['pid']}")
    return jsonify({"status": "scheduled", "old_pid": old_state["pid"]}), 202
  except Exception as err:
    logging.error(f"nginx_restart(): general error by {current_user.realname}: {err}")
    return jsonify({"error": str(err)}), 500

@redirects_dashboard_bp.route("/redirects_dashboard/nginx_status/", methods=['GET'])
@login_required
@rights_required(ADMIN_RIGHTS)
def nginx_status():
  """GET request (AJAX): current Nginx systemd state - polled by the page while the restart is in progress"""
  try:
    return jsonify(_nginx_service_state())
  except Exception as err:
    logging.error(f"nginx_status(): general error: {err}")
    return jsonify({"error": str(err)}), 500

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
