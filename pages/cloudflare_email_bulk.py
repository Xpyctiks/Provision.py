import logging
import requests
from flask import Blueprint, jsonify, render_template, request, flash, redirect
from flask_login import login_required, current_user
from db.database import Cloudflare
from functions.site_actions import is_admin
from pages.cloudflare_email import (
  _get_account_id, _get_routing_status, _get_routing_rules,
  _get_destination_addresses, _sync_status_to_db, _sync_rules_to_db
)

cloudflare_email_bulk_bp = Blueprint("cloudflare_email_bulk", __name__)


@cloudflare_email_bulk_bp.route("/cloudflare_email_bulk/", methods=['GET'])
@login_required
def show_bulk_email_page():
  accounts = Cloudflare.query.all()
  accounts_options = "".join(
    f'<option value="{acc.account}">{acc.account}</option>' for acc in accounts
  )
  return render_template(
    "template-cloudflare_email_bulk.html",
    accounts_options=accounts_options,
    admin_panel=is_admin()
  )


@cloudflare_email_bulk_bp.route("/cloudflare_email_bulk/account_data", methods=['GET'])
@login_required
def get_account_data():
  """AJAX: returns all zones and verified destination addresses for the selected Cloudflare account"""
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
    account_id = _get_account_id(headers)
    zones = []
    page = 1
    while True:
      url = f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={page}"
      r = requests.get(url, headers=headers, timeout=10).json()
      if not r.get("success"):
        logging.error(f"get_account_data(): Failed to load zones for account {account_email}: {r.get('errors')}")
        return jsonify({"error": "Failed to load zones from Cloudflare API"}), 502
      zones.extend(r.get("result", []))
      if page >= r.get("result_info", {}).get("total_pages", 1):
        break
      page += 1
    addresses = _get_destination_addresses(account_id, headers)
    verified = [a for a in addresses if a.get("verified")]
    return jsonify({
      "zones": sorted([{"id": z["id"], "name": z["name"]} for z in zones], key=lambda x: x["name"]),
      "addresses": [{"email": a["email"]} for a in verified]
    })
  except Exception as err:
    logging.error(f"get_account_data(): Error for account {account_email}: {err}")
    return jsonify({"error": str(err)}), 500


@cloudflare_email_bulk_bp.route("/cloudflare_email_bulk/", methods=['POST'])
@login_required
def do_bulk_email():
  """POST: bulk-create Email Routing rules for all selected domains in the chosen Cloudflare account"""
  account_email = (request.form.get("account") or "").strip()
  destination   = (request.form.get("destination") or "").strip()
  login         = (request.form.get("login") or "").strip()
  selected_domains = request.form.getlist("domains")

  if not account_email or not destination or not login or not selected_domains:
    flash("Не всі обов'язкові поля заповнені!", "alert alert-warning")
    return redirect("/cloudflare_email_bulk/", 302)

  acc = Cloudflare.query.filter_by(account=account_email).first()
  if not acc:
    flash("Акаунт Cloudflare не знайдено в базі даних!", "alert alert-danger")
    return redirect("/cloudflare_email_bulk/", 302)

  headers = {
    "X-Auth-Email": acc.account,
    "X-Auth-Key": acc.token,
    "Content-Type": "application/json"
  }

  success_count = 0
  error_count   = 0
  results       = []

  for domain in selected_domains:
    domain = domain.strip()
    if not domain:
      continue
    matcher = f"{login}@{domain}"
    try:
      # Locate the zone for this domain within the selected account
      url = f"https://api.cloudflare.com/client/v4/zones?name={domain}"
      r = requests.get(url, headers=headers, timeout=10).json()
      if not r.get("success") or not r.get("result"):
        logging.error(f"do_bulk_email(): Zone not found for domain {domain} in account {account_email}")
        results.append(f"❌ {domain}: зону не знайдено в акаунті")
        error_count += 1
        continue
      zone_id = r["result"][0]["id"]

      # Enable Email Routing if it is currently off
      routing_enabled = _get_routing_status(zone_id, headers)
      if not routing_enabled:
        enable_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/enable"
        enable_result = requests.post(enable_url, headers=headers, json={}, timeout=10).json()
        if enable_result.get("success"):
          logging.info(f"do_bulk_email(): Email Routing enabled for {domain} by {current_user.realname}")
          routing_enabled = True
        else:
          err_msg = (enable_result.get("errors") or [{}])[0].get("message", "Unknown error")
          logging.error(f"do_bulk_email(): Failed to enable Email Routing for {domain}: {enable_result.get('errors')}")
          results.append(f"❌ {domain}: помилка активації Email Routing: {err_msg}")
          error_count += 1
          continue

      # Create the forwarding rule  login@domain → destination
      rule_url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/email/routing/rules"
      rule_data = {
        "name": matcher,
        "enabled": True,
        "matchers": [{"type": "literal", "field": "to", "value": matcher}],
        "actions":  [{"type": "forward", "value": [destination]}]
      }
      rule_result = requests.post(rule_url, headers=headers, json=rule_data, timeout=10).json()
      if rule_result.get("success"):
        logging.info(f"do_bulk_email(): Rule {matcher} -> {destination} created for {domain} by {current_user.realname}")
        results.append(f"✅ {domain}: правило {matcher} → {destination} створено")
        success_count += 1
      else:
        err_msg = (rule_result.get("errors") or [{}])[0].get("message", "Unknown error")
        logging.error(f"do_bulk_email(): Failed to create rule for {domain}: {rule_result.get('errors')}")
        results.append(f"❌ {domain}: помилка створення правила: {err_msg}")
        error_count += 1
        _sync_status_to_db(domain, routing_enabled, current_user.realname)
        continue

      # Keep DB in sync after successful rule creation
      _sync_status_to_db(domain, routing_enabled, current_user.realname)
      rules = _get_routing_rules(zone_id, headers)
      _sync_rules_to_db(domain, rules)

    except Exception as err:
      logging.error(f"do_bulk_email(): Unexpected error for domain {domain}: {err}")
      results.append(f"❌ {domain}: неочікувана помилка: {err}")
      error_count += 1

  results_html = "<br>".join(results)
  if error_count == 0:
    flash(f"Успішно оброблено {success_count} доменів!<br>{results_html}", "alert alert-success")
  elif success_count == 0:
    flash(f"Помилки при обробці всіх {error_count} доменів!<br>{results_html}", "alert alert-danger")
  else:
    flash(f"Оброблено: {success_count} успішно, {error_count} з помилками.<br>{results_html}", "alert alert-warning")

  return redirect("/cloudflare_email_bulk/", 302)
