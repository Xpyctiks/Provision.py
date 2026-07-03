import logging
import os
import re
import requests
from flask import Blueprint, current_app, jsonify, render_template, request, flash, redirect
from flask_login import login_required, current_user
from db.database import Cloudflare
from functions.site_actions import is_admin, sync_redirects_to_db

redirects_bulk_bp = Blueprint("redirects_bulk", __name__)
@redirects_bulk_bp.route("/redirects_bulk/", methods=['GET'])
@login_required
def show_redirects_bulk_page():
  accounts = Cloudflare.query.all()
  accounts_options = "".join(
    f'<option value="{acc.account}">{acc.account}</option>' for acc in accounts
  )
  return render_template(
    "template-redirects_bulk.html",
    accounts_options=accounts_options,
    admin_panel=is_admin()
  )

@redirects_bulk_bp.route("/redirects_bulk/account_data", methods=['GET'])
@login_required
def get_account_domains():
  """AJAX: returns all zones (domains) for the selected Cloudflare account"""
  account_email = (request.args.get("account") or "").strip()
  if not account_email:
    return jsonify({"error": "Account not specified"}), 400
  acc = Cloudflare.query.filter_by(account=account_email).first()
  if not acc:
    return jsonify({"error": "Account not found in DB"}), 404
  headers = {
    "X-Auth-Email": acc.account,
    "X-Auth-Key": acc.token,
    "Content-Type": "application/json"
  }
  try:
    zones = []
    page = 1
    while True:
      url = f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={page}"
      r = requests.get(url, headers=headers, timeout=10).json()
      if not r.get("success"):
        logging.error(f"get_account_domains(): Failed to load zones for account {account_email}: {r.get('errors')}")
        return jsonify({"error": "Failed to load zones from Cloudflare API"}), 502
      zones.extend(r.get("result", []))
      if page >= r.get("result_info", {}).get("total_pages", 1):
        break
      page += 1
    return jsonify({
      "zones": sorted([{"id": z["id"], "name": z["name"]} for z in zones], key=lambda x: x["name"])
    })
  except Exception as err:
    logging.error(f"get_account_domains(): Error for account {account_email}: {err}")
    return jsonify({"error": str(err)}), 500

@redirects_bulk_bp.route("/redirects_bulk/", methods=['POST'])
@login_required
def do_redirects_bulk():
  """POST: bulk-create one 301 redirect rule for all selected domains under the chosen Cloudflare account"""
  account_email = (request.form.get("account") or "").strip()
  redirect_from = (request.form.get("RedirectFromField") or "").strip()
  redirect_to   = (request.form.get("RedirectToField") or "").strip()
  redirect_type = (request.form.get("templateField") or "").strip()
  selected_domains = request.form.getlist("domains")
  logging.info(f"do_redirects_bulk(): New bulk redirects task received from {current_user.realname} - account: {account_email}, from: {redirect_from}, to: {redirect_to}, type: {redirect_type}, domains: {selected_domains}")
  if not account_email or not redirect_from or not redirect_to or not redirect_type or not selected_domains:
    flash("Не всі обов'язкові поля заповнені!", "alert alert-warning")
    return redirect("/redirects_bulk/", 302)
  acc = Cloudflare.query.filter_by(account=account_email).first()
  if not acc:
    flash("Акаунт Cloudflare не знайдено в базі даних!", "alert alert-danger")
    logging.error(f"do_redirects_bulk(): Account {account_email} is not found in DB!")
    return redirect("/redirects_bulk/", 302)
  if redirect_type == "strict":
    type_marker = "="
  elif redirect_type == "catch_all":
    type_marker = "~"
  else:
    logging.error(f"do_redirects_bulk(): templateField is empty or contains something strange")
    flash("Помилка! Невідомий тип редіректу!", "alert alert-danger")
    return redirect("/redirects_bulk/", 302)
  conf_dir = current_app.config.get("NGX_ADD_CONF_DIR","")
  if not conf_dir:
    logging.error("do_redirects_bulk(): NGX_ADD_CONF_DIR variable is empty!")
    flash("Помилка конфігурації сервера! Дивіться логи.", "alert alert-danger")
    return redirect("/redirects_bulk/", 302)
  success_count = 0
  error_count = 0
  results = []
  for domain in selected_domains:
    domain = domain.strip()
    if not domain:
      continue
    try:
      if re.match("https?:", redirect_to):
        target = redirect_to
      else:
        target = f"https://{domain}{redirect_to}"
      template = f"""location {type_marker} {redirect_from} {{
  return 301 {target};
}}
"""
      file301 = os.path.join(conf_dir, "301-" + domain + ".conf")
      with open(file301, "a", encoding="utf-8") as f:
        f.write(template)
      sync_redirects_to_db(domain, current_user.realname)
      logging.info(f"do_redirects_bulk(): Redirect {redirect_from} -> {target} added for {domain} by {current_user.realname}")
      results.append(f"✅ {domain}: {redirect_from} → {target}")
      success_count += 1
    except Exception as err:
      logging.error(f"do_redirects_bulk(): Unexpected error for domain {domain}: {err}")
      results.append(f"❌ {domain}: неочікувана помилка: {err}")
      error_count += 1
  if success_count and not os.path.exists("/tmp/provision.marker"):
    with open("/tmp/provision.marker", 'w', encoding='utf8') as file3:
      file3.write("")
    logging.info("do_redirects_bulk(): Marker file for Apply button created")
  results_html = "<br>".join(results)
  if error_count == 0:
    flash(f"Успішно оброблено {success_count} доменів!<br>{results_html}", "alert alert-success")
  elif success_count == 0:
    flash(f"Помилки при обробці всіх {error_count} доменів!<br>{results_html}", "alert alert-danger")
  else:
    flash(f"Оброблено: {success_count} успішно, {error_count} з помилками.<br>{results_html}", "alert alert-warning")
  return redirect("/redirects_bulk/", 302)
