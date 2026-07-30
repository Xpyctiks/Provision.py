import logging
import requests
import json
import html
from flask import render_template,request,redirect,flash,Blueprint,jsonify,current_app
from flask_login import login_required,current_user
from db.database import Cloudflare
from functions.site_actions import normalize_domain,is_admin, is_mail_admin
from functions.pages_forms import loadClodflareAccounts,_load_zones_for_account

cloudflare_domains_bp = Blueprint("cloudflare_domains", __name__)
@cloudflare_domains_bp.route("/cloudflare_domains/", methods=['GET'])
@login_required
def show_cloudflareDomains():
  """GET request: shows /cloudflare_domains page"""
  try:
    #parsing Cloudflare accounts available
    cf_list, first_cf = loadClodflareAccounts()
    return render_template("template-cloudflare_domains.html",source_site=(request.args.get('source_site') or 'Error').strip(),cf_list=cf_list,first_cf=first_cf,admin_panel=is_admin(),mail_admin=is_mail_admin(),version=current_app.config.get("VERSION",""))
  except Exception as err:
    logging.error(f"show_cloudflareDomains(): general render error by {current_user.realname}: {err}")
    flash(f"Неочікувана помилка на сторінці колнування, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

@cloudflare_domains_bp.route("/cloudflare_domains/", methods=['POST'])
@login_required
def add_cloudflareDomain():
  """POST request processor: adds new domain to the selected Cloudflare account"""
  try:
    #Handle buttonAddZone action
    if 'buttonAddZone' in request.form:
      logging.info(f"-----------------------Starting new domain addition to Cloudflare account {request.form.get('selected_account', '')} by {current_user.realname}")
      #check if we have all necessary data received
      if not request.form.get('selected_account') or not request.form.get('domain'):
        flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
        logging.error(f"add_cloudflareDomain(): some of the important parameters has not been received!")
        return redirect(f"/cloudflare_domains/",302)
      account = request.form.get("selected_account", "")
      domain = normalize_domain(request.form.get("domain", ""))
      #preparing account token by the selected account
      tkn = Cloudflare.query.filter_by(account=account).first()
      if not tkn:
        logging.error(f"add_cloudflareDomain(): Token for CF account {account} is not found while preparation for new domain addition!")
        flash(f'Помилка! Чомусь API токен для аккаунту {account} не був знайден в базі!','alert alert-danger')
        return redirect(f"/cloudflare_domains/",302)
      token = tkn.token
      logging.info(f"add_cloudflareDomain(): Cloudflare token retreived successfully...")
      headers = {
        "X-Auth-Email": account,
        "X-Auth-Key": token,
        "Content-Type": "application/json"
      }
      #getting account ID which is needed for future domain addition
      url_id = "https://api.cloudflare.com/client/v4/accounts"
      result_id = requests.get(url_id, headers=headers).json()
      if result_id.get("success") and result_id.get("result"):
        account_id = result_id["result"][0]["id"]
        logging.info(f"add_cloudflareDomain(): Cloudflare account ID retreived successfully...")
      else:
        logging.error(f"add_cloudflareDomain(): Error retreiving Cloudflare account ID!")
        flash(f'Помилка! Чомусь ID аккаунту {account} не був отриман! Далі продовжити не можу!','alert alert-danger')
        return redirect(f"/cloudflare_domains/",302)
      url_add_zone = "https://api.cloudflare.com/client/v4/zones"
      data = {
        "name": f"{domain}",
        "account": {
          "id": f"{account_id}"
          },
        "type": "full"
      }
      result_add_domain = requests.post(url_add_zone, headers=headers, json=data).json()
      if result_add_domain.get("success"):
        ns = result_add_domain["result"]["name_servers"]
        message = f"""Новий домен {domain} успішно додано до аккаунту {account}!
        <strong>Встановіть наступні NS сервери в регістраторі домену:</strong>
        <div>
          <code id="ns1">{ns[0]}</code>
          <button class="btn btn-outline-warning" data-bs-toggle="tooltip" data-bs-placement="top" title="Скопіювати в буфер" onclick="copyText('ns1')">📋</button>
        </div>
        <div>
          <code  id="ns2">{ns[1]}</code>
          <button class="btn btn-outline-warning" data-bs-toggle="tooltip" data-bs-placement="top" title="Скопіювати в буфер" onclick="copyText('ns2')">📋</button>
        </div>"""
        logging.info(f"add_cloudflareDomain(): New domain {domain} successfully added to Cloudflare account {account}. NS: {ns[0]} and {ns[1]}")
        flash(message,'alert alert-success')
        return redirect(f"/cloudflare_domains/",302)
      else:
        error_msg = (result_add_domain.get("errors", [{}])[0].get("message", "Unknown error"))
        logging.error(f"add_cloudflareDomain(): Add new domain {domain} to account {account} error! Result: {result_add_domain}")
        flash(f'Якась помилка при додаванні нового домену {domain} до аккаунту {account}: <strong>{error_msg}</strong>!','alert alert-danger')
        return redirect(f"/cloudflare_domains/",302)
  except Exception as err:
    logging.error(f"add_cloudflareDomain(): POST general error by {current_user.realname}: {err}")
    flash(f"Неочікувана помилка на сторінці, дивіться логи!", 'alert alert-danger')
    return redirect(f"/cloudflare_domains/",302)

@cloudflare_domains_bp.route("/cloudflare_domains/existing_domains/", methods=['POST'])
@login_required
def show_existingDomains():
  """POST request processor: shows all existing domains on the selected Cloudflare account"""
  try:
    #check if we have all necessary data received
    if not request.form.get('selected_account'):
      flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
      logging.error(f"showExistingDomains(): some of the important parameters has not been received!")
      return redirect(f"/cloudflare_domains/",302)
    #preparing table structure
    message_table = ""
    domain_list = []
    account = request.form.get("selected_account", "")
    #preparing account token by the selected account
    tkn = Cloudflare.query.filter_by(account=account).first()
    if not tkn:
      logging.error(f"show_existingDomains(): Token for CF account {account} is not found in DB during show domains procedure!")
      return f'{{"message": "Token for CF account {account} is not found during validation procedure"}}'
    token = tkn.token
    pages = 1
    url = f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={pages}"
    headers = {
      "X-Auth-Email": account,
      "X-Auth-Key": token,
      "Content-Type": "application/json"
    }
    #requesting first page with limit 50 zones per page, then checks how much pages are there at all
    r = requests.get(url, headers=headers).json()
    if r.get("success") == True:
      #how much pages we have at all
      total_pages = r["result_info"]["total_pages"]
      i = 0
      while pages <= total_pages:
        url = f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={pages}"
        r = requests.get(url, headers=headers).json()
        for zone in r.get("result"):
          name = zone.get("name")
          domain_list.append(name)
          plan_name = zone["plan"]["name"]
          status = zone.get("status")
          if status == "active":
            table_color = "table-success"
          else:
            table_color = "table-warning"
          message_table += f"""\t<tr>
          <th scope="row" class="{table_color}">{i}&nbsp;<form class="d-inline" method="post" action="/cloudflare_domains/delete_domain/"><button class="btn btn-outline-danger delDomain-btn" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити цей домен з аккаунту." name="buttonDelAccount" value="{name}" type="submit">❌</button>
            <input type="hidden" name="selected_account" value="{account}"></form>
          </th>
          <td class="{table_color}">{name}</td>
          <td class="{table_color}">{plan_name}</td>
          <td class="{table_color}">{status}</td>
      </tr>\n"""
          i = i + 1
        pages = pages + 1
    domains_str = html.escape(", ".join(domain_list), quote=True)
    message = f"""
<div class="container-fluid px-2">
  <div class="mb-2 d-flex justify-content-center">
    <button type="button" class="btn btn-outline-primary" id="copyAllDomainsBtn" data-domains="{domains_str}" onclick="copyAllDomains()">📋 Скопіювати список доменів аккаунта {account}</button>
  </div>
  <div class="table-responsive">
    <table class="table table-bordered table-hover">
      <thead>
          <tr>
            <th scope="col" style="width: 15%;">#</th>
            <th scope="col" style="width: 50%;">Домен:</th>
            <th scope="col" style="width: 20%;">Тариф:</th>
            <th scope="col" style="width: 15%;">Статус:</th>
          </tr>
      </thead>
      <tbody>
        {message_table}
      </tbody>
    </table>
  </div>
</div>"""
    response = {"message": message}
    return json.dumps(response)
  except Exception as err:
    logging.error(f"show_existingDomains(): POST process error by {current_user.realname}: {err}")
    response = {"message": "Error!"}
    return json.dumps(response)

@cloudflare_domains_bp.route("/cloudflare_domains/delete_domain/", methods=['POST'])
@login_required
def del_existingDomain():
  """POST request processor: deletes a domain from the selected Cloudflare account"""
  try:
    logging.info(f"-----------------------Starting domain {request.form.get('buttonDelAccount', '')} deletion from Cloudflare account {request.form.get('selected_account', '')} by {current_user.realname}")
    #Handle buttonDelAccount action
    if 'buttonDelAccount' in request.form:
      #check if we have all necessary data received
      if not request.form.get('buttonDelAccount') or not request.form.get('selected_account'):
        flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
        logging.error(f"del_existingDomain(): some of the important parameters has not been received!")
        return redirect(f"/cloudflare_domains/",302)
      account = request.form.get("selected_account", "")
      domain = request.form.get("buttonDelAccount", "")
      #preparing account token by the selected account
      tkn = Cloudflare.query.filter_by(account=account).first()
      if not tkn:
        logging.error(f"del_existingDomain(): Token for CF account {account} is not found in DB during show domains procedure!")
        return f'{{"message": "Token for CF account {account} is not found during validation procedure"}}'
      token = tkn.token
      headers = {
        "X-Auth-Email": account,
        "X-Auth-Key": token,
        "Content-Type": "application/json"
      }
      url_zone_id = f"https://api.cloudflare.com/client/v4/zones?name={domain}"
      result_zone_id = requests.get(url_zone_id, headers=headers).json()
      if result_zone_id.get("success") and result_zone_id.get("result"):
        zone_id = result_zone_id["result"][0]["id"]
        logging.info("del_existingDomain(): Zone_id retreived successfully...")
      else:
        logging.error(f"del_existingDomain(): Error retreiving zone_id of the domain!")
        flash(f'Помилка! Чомусь ID домену {account} не був отриман! Далі продовжити не можу!','alert alert-danger')
        return redirect(f"/cloudflare_domains/",302)
      url_del_domain = f"https://api.cloudflare.com/client/v4/zones/{zone_id}"
      result_del_domain = requests.delete(url_del_domain, headers=headers).json()
      if result_del_domain.get("success") and result_del_domain.get("result"):
        logging.info(f"del_existingDomain(): Domain {domain} successfully deleted from Cloudflare account {account}!")
        flash(f'Домен {domain} успішно видален з аккаунту {account}!','alert alert-success')
        return redirect(f"/cloudflare_domains/",302)
      else:
        logging.error(f"del_existingDomain(): Error deleting domain {domain} from Cloudflare account {account}!")
        flash(f'Помилка при видаленні домену {domain} з аккаунту {account}!','alert alert-danger')
        return redirect(f"/cloudflare_domains/",302)
  except Exception as err:
    logging.error(f"del_existingDomain(): POST process error by {current_user.realname}: {err}")
    flash(f'Домен {domain} успішно видален з аккаунту {account}!','alert alert-success')
    return redirect(f"/cloudflare_domains/",302)

@cloudflare_domains_bp.route("/cloudflare_domains/zones/", methods=['GET'])
@login_required
def get_cloudflareZones():
  """AJAX: returns all domain names for the selected Cloudflare account, used to populate the DNS record form"""
  account = (request.args.get("account") or "").strip()
  if not account:
    return jsonify({"error": "Аккаунт не вказано"}), 400
  acc = Cloudflare.query.filter_by(account=account).first()
  if not acc:
    return jsonify({"error": "Аккаунт не знайдено в базі"}), 404
  zones = _load_zones_for_account(acc)
  return jsonify({"zones": sorted(zones.keys())})

def _cf_zone_context(account: str, domain: str):
  """Looks up the API headers and zone_id for the given CF account/domain pair. Returns (headers, zone_id, error) where error is None on success."""
  tkn = Cloudflare.query.filter_by(account=account).first()
  if not tkn:
    return None, None, f"API токен для аккаунту {account} не знайдено в базі!"
  headers = {
    "X-Auth-Email": account,
    "X-Auth-Key": tkn.token,
    "Content-Type": "application/json"
  }
  url_zone_id = f"https://api.cloudflare.com/client/v4/zones?name={domain}"
  result_zone_id = requests.get(url_zone_id, headers=headers).json()
  if not (result_zone_id.get("success") and result_zone_id.get("result")):
    return headers, None, f"Не вдалося отримати ID домену {domain}!"
  return headers, result_zone_id["result"][0]["id"], None

@cloudflare_domains_bp.route("/cloudflare_domains/add_dns_record/", methods=['POST'])
@login_required
def add_dns_record():
  """POST request processor: adds one DNS record to all selected domains on the selected Cloudflare account"""
  try:
    account = (request.form.get("dns_account") or "").strip()
    domains = [d.strip() for d in request.form.getlist("dns_domains") if d.strip()]
    record_type = (request.form.get("record_type") or "").strip().upper()
    record_name = (request.form.get("record_name") or "").strip()
    record_content = (request.form.get("record_content") or "").strip()
    ttl = (request.form.get("record_ttl") or "1").strip()
    priority = (request.form.get("record_priority") or "").strip()
    proxied = request.form.get("record_proxied") == "on"
    logging.info(f"-----------------------New DNS record addition requested by {current_user.realname}: account={account}, domains={domains}, type={record_type}, name={record_name}, content={record_content}-----------------")
    if not account or not domains or not record_type or not record_name or not record_content:
      flash("Помилка! Не всі обов'язкові поля заповнені для додавання DNS запису!", "alert alert-danger")
      return redirect("/cloudflare_domains/", 302)
    data_base = {
      "type": record_type,
      "name": record_name,
      "content": record_content,
      "ttl": int(ttl) if ttl.isdigit() else 1,
      "comment": "Provision manual DNS record."
    }
    if record_type in ("A", "AAAA", "CNAME"):
      data_base["proxied"] = proxied
    if record_type == "MX":
      data_base["priority"] = int(priority) if priority.isdigit() else 10
    results = []
    success_count = 0
    error_count = 0
    for domain in domains:
      headers, zone_id, error = _cf_zone_context(account, domain)
      if error:
        logging.error(f"add_dns_record(): {domain}: {error}")
        results.append(f"❌ {domain}: {error}")
        error_count += 1
        continue
      url_add_record = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
      result_add_record = requests.post(url_add_record, headers=headers, json=data_base).json()
      if result_add_record.get("success"):
        logging.info(f"add_dns_record(): DNS record {record_type} {record_name} -> {record_content} added successfully for {domain} by {current_user.realname}")
        results.append(f"✅ {domain}: {record_type} {record_name} → {record_content}")
        success_count += 1
      else:
        error_msg = (result_add_record.get("errors", [{}])[0].get("message", "Unknown error"))
        logging.error(f"add_dns_record(): Error adding DNS record for {domain}: {result_add_record}")
        results.append(f"❌ {domain}: {error_msg}")
        error_count += 1
    results_html = "<br>".join(results)
    if error_count == 0:
      flash(f"DNS запис успішно додано для {success_count} доменів!<br>{results_html}", "alert alert-success")
    elif success_count == 0:
      flash(f"Помилки при додаванні DNS запису для всіх {error_count} доменів!<br>{results_html}", "alert alert-danger")
    else:
      flash(f"Додано: {success_count} успішно, {error_count} з помилками.<br>{results_html}", "alert alert-warning")
    return redirect("/cloudflare_domains/", 302)
  except Exception as err:
    logging.error(f"add_dns_record(): general error by {current_user.realname}: {err}")
    flash("Неочікувана помилка при додаванні DNS запису, дивіться логи!", "alert alert-danger")
    return redirect("/cloudflare_domains/", 302)

@cloudflare_domains_bp.route("/cloudflare_domains/dns_records/", methods=['GET'])
@login_required
def get_dns_records():
  """AJAX: returns existing DNS records for the selected domain, used to populate the editable records list"""
  account = (request.args.get("account") or "").strip()
  domain = (request.args.get("domain") or "").strip()
  if not account or not domain:
    return jsonify({"error": "Аккаунт або домен не вказано"}), 400
  headers, zone_id, error = _cf_zone_context(account, domain)
  if error:
    logging.error(f"get_dns_records(): {error}")
    return jsonify({"error": error}), 400
  try:
    records = []
    page = 1
    while True:
      url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?per_page=100&page={page}"
      r = requests.get(url, headers=headers, timeout=10).json()
      if not r.get("success"):
        logging.error(f"get_dns_records(): Failed to load DNS records for {domain}: {r.get('errors')}")
        return jsonify({"error": "Не вдалося завантажити DNS записи"}), 502
      for rec in r.get("result", []):
        records.append({
          "id": rec.get("id"),
          "type": rec.get("type"),
          "name": rec.get("name"),
          "content": rec.get("content"),
          "ttl": rec.get("ttl"),
          "proxied": rec.get("proxied", False),
          "priority": rec.get("priority"),
          "locked": rec.get("locked", False)
        })
      if page >= r.get("result_info", {}).get("total_pages", 1):
        break
      page += 1
    records.sort(key=lambda x: (x["type"], x["name"]))
    return jsonify({"records": records})
  except Exception as err:
    logging.error(f"get_dns_records(): Error for domain {domain}: {err}")
    return jsonify({"error": str(err)}), 500

@cloudflare_domains_bp.route("/cloudflare_domains/dns_records/update/", methods=['POST'])
@login_required
def update_dns_record():
  """AJAX: updates an existing DNS record of the selected domain"""
  try:
    account = (request.form.get("dns_account") or "").strip()
    domain = (request.form.get("dns_domain") or "").strip()
    record_id = (request.form.get("record_id") or "").strip()
    record_type = (request.form.get("record_type") or "").strip().upper()
    record_name = (request.form.get("record_name") or "").strip()
    record_content = (request.form.get("record_content") or "").strip()
    ttl = (request.form.get("record_ttl") or "1").strip()
    priority = (request.form.get("record_priority") or "").strip()
    proxied = request.form.get("record_proxied") == "true"
    logging.info(f"-----------------------DNS record {record_id} update requested by {current_user.realname}: account={account}, domain={domain}, type={record_type}, name={record_name}, content={record_content}-----------------")
    if not account or not domain or not record_id or not record_type or not record_name or not record_content:
      return jsonify({"success": False, "error": "Не всі обов'язкові поля заповнені"}), 400
    headers, zone_id, error = _cf_zone_context(account, domain)
    if error:
      logging.error(f"update_dns_record(): {error}")
      return jsonify({"success": False, "error": error}), 400
    data = {
      "type": record_type,
      "name": record_name,
      "content": record_content,
      "ttl": int(ttl) if ttl.isdigit() else 1
    }
    if record_type in ("A", "AAAA", "CNAME"):
      data["proxied"] = proxied
    if record_type == "MX":
      data["priority"] = int(priority) if priority.isdigit() else 10
    url_upd_record = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    result = requests.put(url_upd_record, headers=headers, json=data).json()
    if result.get("success"):
      logging.info(f"update_dns_record(): DNS record {record_id} updated successfully for {domain} by {current_user.realname}")
      return jsonify({"success": True})
    error_msg = (result.get("errors", [{}])[0].get("message", "Unknown error"))
    logging.error(f"update_dns_record(): Error updating DNS record {record_id} for {domain}: {result}")
    return jsonify({"success": False, "error": error_msg}), 400
  except Exception as err:
    logging.error(f"update_dns_record(): general error by {current_user.realname}: {err}")
    return jsonify({"success": False, "error": str(err)}), 500

@cloudflare_domains_bp.route("/cloudflare_domains/dns_records/delete/", methods=['POST'])
@login_required
def delete_dns_record():
  """AJAX: deletes an existing DNS record of the selected domain"""
  try:
    account = (request.form.get("dns_account") or "").strip()
    domain = (request.form.get("dns_domain") or "").strip()
    record_id = (request.form.get("record_id") or "").strip()
    logging.info(f"-----------------------DNS record {record_id} deletion requested by {current_user.realname}: account={account}, domain={domain}-----------------")
    if not account or not domain or not record_id:
      return jsonify({"success": False, "error": "Не всі обов'язкові поля заповнені"}), 400
    headers, zone_id, error = _cf_zone_context(account, domain)
    if error:
      logging.error(f"delete_dns_record(): {error}")
      return jsonify({"success": False, "error": error}), 400
    url_del_record = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    result = requests.delete(url_del_record, headers=headers).json()
    if result.get("success"):
      logging.info(f"delete_dns_record(): DNS record {record_id} deleted successfully for {domain} by {current_user.realname}")
      return jsonify({"success": True})
    error_msg = (result.get("errors", [{}])[0].get("message", "Unknown error"))
    logging.error(f"delete_dns_record(): Error deleting DNS record {record_id} for {domain}: {result}")
    return jsonify({"success": False, "error": error_msg}), 400
  except Exception as err:
    logging.error(f"delete_dns_record(): general error by {current_user.realname}: {err}")
    return jsonify({"success": False, "error": str(err)}), 500
