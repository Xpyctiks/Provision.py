from flask import render_template,request,redirect,flash,Blueprint
from flask_login import login_required,current_user
import logging,requests
from db.database import Domain_account, Cloudflare
from functions.send_to_telegram import send_to_telegram
from functions.site_actions import normalize_domain,is_admin

dns_validation_bp = Blueprint("dns_validation", __name__)
@dns_validation_bp.route("/dns_validation/", methods=['GET'])
@login_required
def dns_validation():
  """GET request: shows /dns_validation page where you can see,remove and add CNAME records"""
  try:
    if not request.args.get('domain'):
      logging.error(f"dns_validation(): Important GET parameter domain was not received! By {current_user.realname}")
      flash(f"Не передано обов'язкового параметру для сторінки ДНС валідації. Мабуть ви опинилсь там в результаті помилки.", 'alert alert-danger')
      return redirect("/",302)
    #variable for full data for template render
    html_data = []
    #variable for account of the domain
    account = ""
    token = ""
    #taking domain parameter, making it safe
    domain = request.args.get("domain", "")
    domain = normalize_domain(domain)
    #getting cloudflare account by the given domain name
    res = Domain_account.query.filter_by(domain=domain).first()
    if res:
      account = res.account
    else:
      logging.error(f"dns_validation(): Account for domain {domain} is not found in DB! Dunno how did you get into this page...")
      send_to_telegram(f"Account for domain {domain} is not found in DB! Dunno how did you get into this page...",f"🚒Provision error by {current_user.realname}:")
      flash(f"Аккаунт для домена {domain} не знайден в базі! Як ви взагалі опинилсь на цій сторінці...", 'alert alert-danger')
      return redirect("/",302)
    tkn = Cloudflare.query.filter_by(account=account).first()
    if tkn:
      token = tkn.token
    else:
      logging.error(f"dns_validation(): Token for account {account} is not found in DB! Strange error...")
      send_to_telegram(f"Token for account {account} is not found in DB! Strange error...",f"🚒Provision error by {current_user.realname}:")
      flash(f"API токен для аккаунту {account} не знайден в базі! Фігня якась...", 'alert alert-danger')
      return redirect("/",302)
    #Getting zoneID for the given domain
    url_check_domain = "https://api.cloudflare.com/client/v4/zones?per_page=50"
    headers = {
      "X-Auth-Email": account,
      "X-Auth-Key": token,
      "Content-Type": "application/json"
    }
    params_check_domain = {
      "name": domain,
      "per_page": 1
    }
    result_check_domain = requests.get(url_check_domain, headers=headers, params=params_check_domain).json()
    if result_check_domain.get("success") and result_check_domain.get("result"):
      name_to_id = {i.get("name"): i.get("id") for i in result_check_domain.get("result")}
      zone_id = name_to_id.get(domain)
    url_get_records = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
    params_get_records = {
      "type": "CNAME",
      "per_page": 100,
      "direction": "asc"
    }
    result_get_records = requests.get(url_get_records,headers=headers,params=params_get_records).json()
    if result_get_records.get("success") and result_get_records.get("result"):
      records = result_get_records.get("result", [])
      for record in records:
        record_name = record.get("name")
        record_content = record.get("content")
        record_id = record.get("id")
        html_data.append({
          "record_name": record_name,
          "record_conent": record_content,
          "record_id": record_id
        })
    return render_template("template-dns_validation.html",html_data=html_data,domain=domain,account=account,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"dns_validation(): general render error: {err}")
    flash(f"Неочікувана помилка на сторінці ДНС валідації, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

@dns_validation_bp.route("/dns_validation/", methods=['POST'])
@login_required
def dns_del_cname():
  """POST request processor: deletes the given CNAME records from DNS records via API to Cloudflare"""
  try:
    #Check if we received DelCname request. If not - passthrough to AddCname function
    if not request.form.get('buttonDelCname'):
      return dns_add_cname()
    #If this is DelCname request - basic checks
    logging.info(f"-----------------------Starting delete of CNAME {request.form.get('cname')}, id {request.form.get('buttonDelCname')}, account {request.form.get('account')} by {current_user.realname}-----------------")
    #if not request.form['domain'] or not request.form['account'] or not request.form['cname'] or (request.form['buttonDelCname'] == ""):
    if not 'domain' or not 'account' or not 'cname' in request.form or (request.form.get('buttonDelCname') == ""):
      logging.error(f"-----------------------dns_del_cname(): Important POST parameter domain or account or buttonDelCname or cname was not received! By {current_user.realname}-----------------------")
      flash(f"Не передано обов'язкового параметру для сторінки видалення ДНС запису. Мабуть ви опинилсь там в результаті помилки.", 'alert alert-danger')
      return redirect("/",302)
    #variable for account of the domain
    account = ""
    token = ""
    #taking domain parameter, making it safe
    domain = request.form.get("domain")
    domain = normalize_domain(domain)
    #cloudflare account
    account = request.form["account"]
    #getting token for API
    tkn = Cloudflare.query.filter_by(account=account).first()
    if tkn:
      token = tkn.token
    else:
      logging.error(f"-----------------------dns_del_cname(): Token for account {account} is not found in DB! Strange error...-----------------------")
      send_to_telegram(f"Token for account {account} is not found in DB! Strange error...",f"🚒Provision error by {current_user.realname}:")
      flash(f"API токен для аккаунту {account} не знайден в базі! Фігня якась...", 'alert alert-danger')
      return redirect("/",301)
    #Getting zoneID for the given domain
    url_check_domain = "https://api.cloudflare.com/client/v4/zones?per_page=50"
    headers = {
      "X-Auth-Email": account,
      "X-Auth-Key": token,
      "Content-Type": "application/json"
    }
    params_check_domain = {
      "name": domain,
      "per_page": 1
    }
    result_check_domain = requests.get(url_check_domain, headers=headers, params=params_check_domain).json()
    if result_check_domain.get("success") and result_check_domain.get("result"):
      name_to_id = {i.get("name"): i.get("id") for i in result_check_domain.get("result")}
      zone_id = name_to_id.get(domain)
    url_del_cname = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{request.form.get('buttonDelCname')}"
    result_del_cname = requests.delete(url_del_cname,headers=headers)
    if result_del_cname.status_code != 200:
      logging.error(f"-----------------------dns_del_cname(): API returned an error: {result_del_cname.text}-----------------------")
      flash(f"API повернуло помилку при спробі видалення запису {request.form.get('cname')}. Дивіться логи!", 'alert alert-danger')
      return redirect("/",302)
    else:
      logging.info(f"-----------------------CNAME запис з ID {request.form.get('buttonDelCname')} видалено успішно!-----------------------")
      return redirect(f"/dns_validation?domain={request.form.get('domain')}",302)
  except Exception as err:
    logging.error(f"dns_del_cname(): general error: {err}")
    flash(f"Неочікувана помилка при спробі видалення ДНС запису, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

def dns_add_cname():
  try:
    """POST request processor: adds the given CNAME records to DNS records via API to Cloudflare"""
    #Check if we received AddCname request. If not - error
    if not request.form.get('buttonAddCname'):
      logging.error(f"-----------------------dns_add_cname(): POST parameter buttonAddCname is not received! This can't be add_cname function. By {current_user.realname}-----------------------")
      flash(f"Не передано обов'язкового параметру Додати чи Видалити запис для сторінки додавання ДНС запису. Мабуть ви опинилсь там в результаті помилки.", 'alert alert-danger')
      return redirect("/",302)
    #If this is AddCname request - basic checks
    logging.info(f"-----------------------Starting addition of CNAME {request.form.get('cname')}, value {request.form.get('cname_value')}, account {request.form.get('account')} by {current_user.realname}-----------------")
    required = ('domain', 'account', 'cname', 'cname_value')
    for key in required:
      value = request.form.get(key)
      if not value or not value.strip():
        logging.error(f"-----------------------dns_add_cname(): Important POST parameter domain or account or cname_value or cname was not received! By {current_user.realname}-----------------------")
        flash(f"Не передано обов'язкового параметру для сторінки додавання ДНС запису. Мабуть ви опинилсь там в результаті помилки.", 'alert alert-danger')
        return redirect("/",302)
    #variable for account of the domain
    account = ""
    token = ""
    #taking domain parameter, making it safe
    domain = request.form.get("domain")
    domain = normalize_domain(domain)
    #cloudflare account
    account = request.form.get("account")
    #getting token for API
    tkn = Cloudflare.query.filter_by(account=account).first()
    if tkn:
      token = tkn.token
    else:
      logging.error(f"-----------------------dns_add_cname(): Token for account {account} is not found in DB! Strange error...-----------------------")
      send_to_telegram(f"Token for account {account} is not found in DB! Strange error...",f"🚒Provision error by {current_user.realname}:")
      flash(f"API токен для аккаунту {account} не знайден в базі! Фігня якась...", 'alert alert-danger')
      return redirect("/",302)
    #Getting zoneID for the given domain
    url_check_domain = "https://api.cloudflare.com/client/v4/zones?per_page=50"
    headers = {
      "X-Auth-Email": account,
      "X-Auth-Key": token,
      "Content-Type": "application/json"
    }
    params_check_domain = {
      "name": domain,
      "per_page": 1
    }
    result_check_domain = requests.get(url_check_domain, headers=headers, params=params_check_domain).json()
    if result_check_domain.get("success") and result_check_domain.get("result"):
      name_to_id = {i.get("name"): i.get("id") for i in result_check_domain.get("result")}
      zone_id = name_to_id.get(domain)
    url_add_cname = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/"
    data = {
      "type": "CNAME",
      "name": f"{request.form.get('cname')}",
      "content": f"{request.form.get('cname_value')}",
      "ttl": 3600,
      "proxied": False,
      "comment": "Provision auto deploy."
    }
    result_add_cname = requests.post(url_add_cname,headers=headers,json=data)
    if result_add_cname.status_code != 200:
      logging.error(f"-----------------------dns_add_cname(): API returned an error: {result_add_cname.text}-----------------------")
      flash(f"API повернуло помилку при спробі додавання запису {request.form.get('cname')}. Дивіться логи!", 'alert alert-danger')
      return redirect("/",302)
    else:
      logging.info(f"-----------------------CNAME record {request.form.get('cname')} with value {request.form.get('cname_value')} added sucessfully!-----------------------")
      flash(f"CNAME запис {request.form.get('cname')} із значенням {request.form.get('cname_value')} додано успішно!", 'alert alert-success')
      return redirect(f"/",302)
  except Exception as err:
    logging.error(f"dns_add_cname(): general error: {err}")
    flash(f"Неочікувана помилка при спробі додавання ДНС запису, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)
