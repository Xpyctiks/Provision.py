from flask import render_template,request,redirect,flash,Blueprint
from flask_login import login_required,current_user
from db.database import Cloudflare
import logging,requests,json
from functions.site_actions import normalize_domain,is_admin
from functions.pages_forms import loadClodflareAccounts

cloudflare_domains_bp = Blueprint("cloudflare_domains", __name__)
@cloudflare_domains_bp.route("/cloudflare_domains/", methods=['GET'])
@login_required
def show_cloudflareDomains():
  """GET request: shows /cloudflare_domains page"""
  try:
    #parsing Cloudflare accounts available
    cf_list, first_cf = loadClodflareAccounts()
    return render_template("template-cloudflare_domains.html",source_site=(request.args.get('source_site') or 'Error').strip(),cf_list=cf_list,first_cf=first_cf,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"Clone page general render error by {current_user.realname}: {err}")
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
      if not request.form['selected_account'] or not request.form['domain']:
        flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
        logging.error(f"add_cloudflareDomain(): some of the important parameters has not been received!")
        return redirect(f"/cloudflare_domains/",302)
      account = request.form.get("selected_account", "")
      domain = normalize_domain(request.form.get("domain", ""))
      #preparing account token by the selected account
      tkn = Cloudflare.query.filter_by(account=account).first()
      if not tkn:
        logging.error(f"Token for CF account {account} is not found while preparation for new domain addition!")
        flash(f'Помилка! Чомусь API токен для аккаунту {account} не був знайден в базі!','alert alert-danger')
        return redirect(f"/cloudflare_domains/",302)
      token = tkn.token
      logging.info(f"Cloudflare token retreived successfully...")
      headers = {
        "X-Auth-Email": account,
        "X-Auth-Key": token,
        "Content-Type": "application/json"
      }
      #getting account ID which is needed for future domain addition
      url_id = "https://api.cloudflare.com/client/v4/accounts"
      result_id = requests.get(url_id, headers=headers).json()
      if result_id["success"] and result_id["result"]:
        account_id = result_id["result"][0]["id"]
        logging.info(f"Cloudflare account ID retreived successfully...")
      else:
        logging.error(f"Error retreiving Cloudflare account ID!")
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
        logging.info(f"New domain {domain} successfully added to Cloudflare account {account}. NS: {ns[0]} and {ns[1]}")
        flash(message,'alert alert-success')
        return redirect(f"/cloudflare_domains/",302)
      else:
        error_msg = (result_add_domain.get("errors", [{}])[0].get("message", "Unknown error"))
        logging.error(f"Add new domain {domain} to account {account} error! Result: {result_add_domain}")
        flash(f'Якась помилка при додаванні нового домену {domain} до аккаунту {account}: <strong>{error_msg}</strong>!','alert alert-danger')
        return redirect(f"/cloudflare_domains/",302)
  except Exception as err:
    logging.error(f"add_cloudflareDomain() POST general error by {current_user.realname}: {err}")
    flash(f"Неочікувана помилка на сторінці, дивіться логи!", 'alert alert-danger')
    return redirect(f"/cloudflare_domains/",302)

@cloudflare_domains_bp.route("/cloudflare_domains/existing_domains/", methods=['POST'])
@login_required
def show_existingDomains():
  """POST request processor: shows all existing domains on the selected Cloudflare account"""
  try:
    #check if we have all necessary data received
    if not request.form['selected_account']:
      flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
      logging.error(f"showExistingDomains(): some of the important parameters has not been received!")
      return redirect(f"/cloudflare_domains/",302)
    #preparing table structure
    message_table = ""
    account = request.form.get("selected_account", "")
    #preparing account token by the selected account
    tkn = Cloudflare.query.filter_by(account=account).first()
    if not tkn:
      logging.error(f"Token for CF account {account} is not found in DB during show domains procedure!")
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
    if r["success"] == True:
      #how much pages we have at all
      total_pages = r["result_info"]["total_pages"]
      logging.info(f"total_pages={total_pages}")
      i = 0
      while pages <= total_pages:
        url = f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={pages}"
        logging.info(f"pages={pages}")
        r = requests.get(url, headers=headers).json()
        for zone in r["result"]:
          name = zone["name"]
          plan_name = zone["plan"]["name"]
          status = zone["status"]
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
    message = f"""
<div class="container-fluid px-2">
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
      if not request.form['buttonDelAccount'] or not request.form['selected_account']:
        flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
        logging.error(f"del_existingDomain(): some of the important parameters has not been received!")
        return redirect(f"/cloudflare_domains/",302)
      account = request.form.get("selected_account", "")
      domain = request.form.get("buttonDelAccount", "")
      #preparing account token by the selected account
      tkn = Cloudflare.query.filter_by(account=account).first()
      if not tkn:
        logging.error(f"Token for CF account {account} is not found in DB during show domains procedure!")
        return f'{{"message": "Token for CF account {account} is not found during validation procedure"}}'
      token = tkn.token
      headers = {
        "X-Auth-Email": account,
        "X-Auth-Key": token,
        "Content-Type": "application/json"
      }
      url_zone_id = f"https://api.cloudflare.com/client/v4/zones?name={domain}"
      result_zone_id = requests.get(url_zone_id, headers=headers).json()
      if result_zone_id["success"] and result_zone_id["result"]:
        zone_id = result_zone_id["result"][0]["id"]
        logging.info("Zone_id retreived successfully...")
      else:
        logging.error(f"Error retreiving zone_id of the domain!")
        flash(f'Помилка! Чомусь ID домену {account} не був отриман! Далі продовжити не можу!','alert alert-danger')
        return redirect(f"/cloudflare_domains/",302)
      url_del_domain = f"https://api.cloudflare.com/client/v4/zones/{zone_id}"
      result_del_domain = requests.delete(url_del_domain, headers=headers).json()
      if result_del_domain["success"] and result_del_domain["result"]:
        logging.info(f"Domain {domain} successfully deleted from Cloudflare account {account}!")
        flash(f'Домен {account} успішно видален з аккаунту {account}!','alert alert-success')
        return redirect(f"/cloudflare_domains/",302)
      else:
        logging.error(f"Error deleting domain {domain} from Cloudflare account {account}!")
        flash(f'Помилка при видаленні домену {account} з аккаунту {account}!','alert alert-danger')
        return redirect(f"/cloudflare_domains/",302)
  except Exception as err:
    logging.error(f"del_existingDomain(): POST process error by {current_user.realname}: {err}")
    flash(f'Домен {account} успішно видален з аккаунту {account}!','alert alert-success')
    return redirect(f"/cloudflare_domains/",302)
