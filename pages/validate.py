from flask import Blueprint,request
from flask_login import login_required,current_user
import json,requests,logging
from db.database import Cloudflare, Servers

validate_bp = Blueprint("validate", __name__)
@validate_bp.route("/validate", methods=['POST'])
@login_required
def do_validation():
    message = ""
    domain = request.form.get("domain").strip()
    server = request.form.get("selected_server").strip()
    account = request.form.get("selected_account").strip()
    if len(domain) == 0:
        return f'{{"message": "[❌] {current_user.realname}, ти хоча би домен введи що б було що перевіряти."}}'
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
    url = "https://api.cloudflare.com/client/v4/zones"
    headers = {
        "X-Auth-Email": account,
        "X-Auth-Key": token,
        "Content-Type": "application/json"
    }
    #making request to check the domain's existance on the server
    r = requests.get(url, headers=headers).json()
    names = [item["name"] for item in r["result"]]
    if domain in names:
        message += "[✅] Домен існує на цьому сервері<br>"
        #getting domain's zone id to check its A records futher
        name_to_id = {i["name"]: i["id"] for i in r["result"]}
        id = name_to_id.get(domain)
        url = f"https://api.cloudflare.com/client/v4/zones/{id}/dns_records"
        r = requests.get(url, headers=headers).json()
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
