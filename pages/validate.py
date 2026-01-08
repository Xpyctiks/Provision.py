from flask import Blueprint,request,flash,redirect
from flask_login import login_required,current_user
import json,requests,logging,tldextract,asyncio
from db.database import Cloudflare, Servers
from functions.site_actions import normalize_domain
from functions.send_to_telegram import send_to_telegram

validate_bp = Blueprint("validate", __name__)
@validate_bp.route("/validate", methods=['POST'])
@login_required
def do_validation():
    """POST request processor: does validation of the given domain and returns the result"""
    try:
        message = ""
        domain = request.form.get("domain", "")
        if len(domain) == 0:
            return f'{{"message": "🤦 {current_user.realname}, ти хоча би домен введи що б було що перевіряти."}}'
        #taking domain parameter, making it safe
        domain = str(normalize_domain(domain))
        server = request.form.get("selected_server").strip()
        account = request.form.get("selected_account").strip()
        #preparing account token by the selected account
        tkn = Cloudflare.query.filter_by(account=account).first()
        if not tkn:
            logging.error(f"Token for CF account {account} is not found during validation procedure")
            return f'{{"message": "Token for CF account {account} is not found during validation procedure"}}'
        token = tkn.token
        srv = Servers.query.filter_by(name=server).first()
        if not srv:
            logging.error(f"IP of the server {server} is not found during validation procedure")
            return f'{{"message": "IP of the server {server} is not found during validation procedure"}}'
        ip = srv.ip
        url = "https://api.cloudflare.com/client/v4/zones?per_page=50"
        headers = {
            "X-Auth-Email": account,
            "X-Auth-Key": token,
            "Content-Type": "application/json"
        }
        #check if there is subdomain
        d = tldextract.extract(domain)
        if bool(d.subdomain):
            domain2 = domain.strip().lower().rstrip(".")
            d2 = tldextract.extract(domain2)
            print("1")
            print(d2)
            params = {
                "name": f"{d2.domain}.{d2.suffix}",
                "per_page": 1
            }
            logging.info(f"Validation check: using domain {d2.domain}.{d2.suffix} as the root domain for validation of {domain}")
        else:
            logging.info(f"Validation check: {domain} is the root domain. Validating as is.")
            params = {
                "name": domain,
                "per_page": 1
            }
        #making request to check the domain's existance on the server
        r = requests.get(url, headers=headers,params=params).json()
        if r["success"] and r["result"]:
            message += "[✅] Домен існує на цьому сервері<br>"
            #getting domain's zone id to check its A records futher
            name_to_id = {i["name"]: i["id"] for i in r["result"]}
            id = name_to_id.get(domain)
            url = f"https://api.cloudflare.com/client/v4/zones/{id}/dns_records"
            r = requests.get(url, headers=headers).json()
            if not r.get("success") or not r.get("result"):
                message += "[❌] Не вдалося отримати DNS записи<br>"
                return json.dumps({"message": message})
            #getting all records of type A
            records = {item["name"]: item["content"] for item in r["result"] if item["type"] == "A"}
            for name, content in records.items():
                if content == ip:
                    message += f'[✅] {name} A запис відповідає серверу {server}<br>'
                else:
                    message += f'[❌] {name} A запис {content} не відповідає серверу {server}<br>'
            response = {"message": message}
            return json.dumps(response)
        else:
            message += "[❌] Домен НЕ існує на цьому сервері!"
            response = {"message": message}
            return json.dumps(response)
    except Exception as err:
        logging.error(f"do_validation(): general error: {err}")
        asyncio.run(send_to_telegram(f"do_validation(): general error: {err}",f"🚒Provision validation page error:"))
        flash(f"Неочікувана помилка при POST запиту на сторінці /validate! Дивіться логи!", 'alert alert-danger')
        return redirect("/",302)

@validate_bp.route("/validate", methods=['GET'])
@login_required
def show_validation():
    """GET request: nothing should be in here. Just redirect if somebody hit this page accidently."""
    ip = request.remote_addr
    real_ip = request.headers.get('X-Real-IP', '-.-.-.-')
    logging.info(f"Strange GET request to /validate page: user {current_user.realname} IP:{ip}, Real-IP:{real_ip}")
    flash("Ви не повинні потряпляти на сторінку /validate з GET запитом!", "alert alert-warning")
    return redirect("/",302)
