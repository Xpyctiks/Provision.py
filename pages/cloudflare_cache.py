import logging
import requests
import json
from flask import render_template,request,redirect,flash,Blueprint,current_app
from flask_login import login_required,current_user
from db.database import Cloudflare
from functions.site_actions import is_admin,is_mail_admin
from functions.pages_forms import loadClodflareAccounts

cloudflare_cache_bp = Blueprint("cloudflare_cache", __name__)

@cloudflare_cache_bp.route("/cloudflare_cache/", methods=['GET'])
@login_required
def show_cloudflareCache():
  """GET request: shows /cloudflare_cache page"""
  try:
    #parsing Cloudflare accounts available
    cf_list, first_cf = loadClodflareAccounts()
    return render_template("template-cloudflare_cache.html",cf_list=cf_list,first_cf=first_cf,admin_panel=is_admin(),mail_admin=is_mail_admin(),version=current_app.config.get("VERSION",""))
  except Exception as err:
    logging.error(f"show_cloudflareCache(): general render error by {current_user.realname}: {err}")
    flash("Неочікувана помилка на сторінці очищення кешу Cloudflare, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

@cloudflare_cache_bp.route("/cloudflare_cache/domains/", methods=['POST'])
@login_required
def show_cacheDomains():
  """POST request processor: lists all domains on the selected Cloudflare account, with per-domain and bulk cache purge controls"""
  try:
    if not request.form.get('selected_account'):
      logging.error("show_cacheDomains(): selected_account parameter has not been received!")
      return json.dumps({"message": "Помилка! Аккаунт Cloudflare не обрано!"})
    account = request.form.get("selected_account","")
    logging.info(f"show_cacheDomains(): Loading domain list for Cloudflare account {account} requested by {current_user.realname}")
    tkn = Cloudflare.query.filter_by(account=account).first()
    if not tkn:
      logging.error(f"show_cacheDomains(): Token for CF account {account} is not found in DB!")
      return json.dumps({"message": f"Токен для аккаунту {account} не знайдено в базі!"})
    token = tkn.token
    headers = {
      "X-Auth-Email": account,
      "X-Auth-Key": token,
      "Content-Type": "application/json"
    }
    message_table = ""
    i = 0
    pages = 1
    r = requests.get(f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={pages}", headers=headers).json()
    if r.get("success") == True:
      total_pages = r["result_info"]["total_pages"]
      while pages <= total_pages:
        url = f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={pages}"
        r = requests.get(url, headers=headers).json()
        for zone in r.get("result"):
          name = zone.get("name")
          plan_name = zone["plan"]["name"]
          status = zone.get("status")
          table_color = "table-success" if status == "active" else "table-warning"
          i = i + 1
          message_table += f"""\t<tr>
          <td class="{table_color} text-center"><input type="checkbox" class="form-check-input cache-domain-check" name="selected_domains" value="{name}" form="bulkPurgeForm"></td>
          <th scope="row" class="{table_color}">{i}&nbsp;<form class="d-inline" method="post" action="/cloudflare_cache/purge/"><button class="btn btn-outline-primary purgeCache-btn" data-bs-toggle="tooltip" data-bs-placement="top" title="Очистити кеш цього домену." name="buttonPurgeDomain" value="{name}" type="submit">🧹</button>
            <input type="hidden" name="selected_account" value="{account}"></form>
          </th>
          <td class="{table_color}">{name}</td>
          <td class="{table_color}">{plan_name}</td>
          <td class="{table_color}">{status}</td>
      </tr>\n"""
        pages = pages + 1
    else:
      logging.error(f"show_cacheDomains(): Failed to load zones for account {account}: {r.get('errors')}")
      return json.dumps({"message": f"Помилка завантаження списку доменів для аккаунту {account}!"})
    message = f"""
<div class="container-fluid px-2">
  <form id="bulkPurgeForm" action="/cloudflare_cache/purge_bulk/" method="POST">
    <input type="hidden" name="selected_account" value="{account}">
  </form>
  <div class="mb-2 d-flex justify-content-center gap-2 flex-wrap">
    <button type="submit" form="bulkPurgeForm" class="btn btn-outline-primary" id="bulkPurgeBtn" disabled>🧹 Очистити все обране (<span id="bulkPurgeCount">0</span>)</button>
  </div>
  <div class="table-responsive">
    <table class="table table-bordered table-hover">
      <thead>
          <tr>
            <th scope="col" style="width: 5%;"><input type="checkbox" class="form-check-input" id="selectAllCacheDomains" data-bs-toggle="tooltip" data-bs-placement="top" title="Обрати всі"></th>
            <th scope="col" style="width: 10%;">#</th>
            <th scope="col" style="width: 45%;">Домен:</th>
            <th scope="col" style="width: 20%;">Тариф:</th>
            <th scope="col" style="width: 15%;">Статус:</th>
          </tr>
      </thead>
      <tbody>
        {message_table if message_table else '<tr><td colspan="5" class="text-center text-muted">Доменів не знайдено на цьому аккаунті</td></tr>'}
      </tbody>
    </table>
  </div>
</div>"""
    logging.info(f"show_cacheDomains(): Domain list for account {account} loaded successfully by {current_user.realname}, {i} domain(s) found")
    response = {"message": message}
    return json.dumps(response)
  except Exception as err:
    logging.error(f"show_cacheDomains(): POST process error by {current_user.realname}: {err}")
    response = {"message": "Помилка завантаження списку доменів! Дивіться логи."}
    return json.dumps(response)

def _purge_zone_cache(account: str, domain: str) -> tuple[bool, str]:
  """Resolves the zone_id for domain on the given Cloudflare account and purges its cache. Returns (success, message)."""
  try:
    tkn = Cloudflare.query.filter_by(account=account).first()
    if not tkn:
      logging.error(f"_purge_zone_cache(): Token for CF account {account} is not found in DB!")
      return False, f"Токен для аккаунту {account} не знайдено в базі!"
    headers = {
      "X-Auth-Email": account,
      "X-Auth-Key": tkn.token,
      "Content-Type": "application/json"
    }
    url_zone_id = f"https://api.cloudflare.com/client/v4/zones?name={domain}"
    result_zone_id = requests.get(url_zone_id, headers=headers).json()
    if not (result_zone_id.get("success") and result_zone_id.get("result")):
      logging.error(f"_purge_zone_cache(): Error retreiving zone_id for domain {domain} on account {account}!")
      return False, "Не вдалося отримати ID зони домену!"
    zone_id = result_zone_id["result"][0]["id"]
    url_purge = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/purge_cache"
    result_purge = requests.post(url_purge, headers=headers, json={"purge_everything": True}).json()
    if result_purge.get("success"):
      logging.info(f"_purge_zone_cache(): Cache for domain {domain} (account {account}) purged successfully by {current_user.realname}")
      return True, "OK"
    error_msg = (result_purge.get("errors", [{}])[0].get("message", "Unknown error"))
    logging.error(f"_purge_zone_cache(): Error purging cache for domain {domain} on account {account}: {result_purge}")
    return False, error_msg
  except Exception as err:
    logging.error(f"_purge_zone_cache(): general error for domain {domain}: {err}")
    return False, str(err)

@cloudflare_cache_bp.route("/cloudflare_cache/purge/", methods=['POST'])
@login_required
def purge_domainCache():
  """POST request processor: purges Cloudflare cache for a single domain"""
  account = request.form.get("selected_account","")
  domain = request.form.get("buttonPurgeDomain","")
  try:
    logging.info(f"-----------------------Starting cache purge for domain {domain} on Cloudflare account {account} by {current_user.realname}-----------------------")
    if not account or not domain:
      flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
      logging.error("purge_domainCache(): some of the important parameters has not been received!")
      return redirect("/cloudflare_cache/",302)
    ok, msg = _purge_zone_cache(account, domain)
    if ok:
      flash(f'Кеш Cloudflare для домену {domain} успішно очищено!','alert alert-success')
    else:
      flash(f'Помилка очищення кешу для домену {domain}: {msg}','alert alert-danger')
    return redirect("/cloudflare_cache/",302)
  except Exception as err:
    logging.error(f"purge_domainCache(): general error by {current_user.realname}: {err}")
    flash('Неочікувана помилка при очищенні кешу, дивіться логи!','alert alert-danger')
    return redirect("/cloudflare_cache/",302)

@cloudflare_cache_bp.route("/cloudflare_cache/purge_bulk/", methods=['POST'])
@login_required
def purge_domainCache_bulk():
  """POST request processor: purges Cloudflare cache for every selected domain on the given account, one by one"""
  try:
    account = request.form.get("selected_account","")
    domains = request.form.getlist("selected_domains")
    logging.info(f"-----------------------Starting bulk cache purge on Cloudflare account {account} by {current_user.realname}: domains={domains}-----------------------")
    if not account or not domains:
      flash('Помилка! Не обрано жодного домену для очищення кешу!','alert alert-danger')
      logging.error("purge_domainCache_bulk(): some of the important parameters has not been received!")
      return redirect("/cloudflare_cache/",302)
    results = []
    success_count = 0
    error_count = 0
    for domain in domains:
      ok, msg = _purge_zone_cache(account, domain)
      if ok:
        results.append(f"✅ {domain}: кеш очищено")
        success_count += 1
      else:
        results.append(f"❌ {domain}: {msg}")
        error_count += 1
    results_html = "<br>".join(results)
    if error_count == 0:
      flash(f"Кеш успішно очищено для {success_count} доменів!<br>{results_html}",'alert alert-success')
    elif success_count == 0:
      flash(f"Помилки при очищенні кешу для всіх {error_count} доменів!<br>{results_html}",'alert alert-danger')
    else:
      flash(f"Очищено: {success_count} успішно, {error_count} з помилками.<br>{results_html}",'alert alert-warning')
    logging.info(f"-----------------------Bulk cache purge finished by {current_user.realname}: {success_count} success, {error_count} errors-----------------------")
    return redirect("/cloudflare_cache/",302)
  except Exception as err:
    logging.error(f"purge_domainCache_bulk(): general error by {current_user.realname}: {err}")
    flash('Неочікувана помилка при масовому очищенні кешу, дивіться логи!','alert alert-danger')
    return redirect("/cloudflare_cache/",302)
