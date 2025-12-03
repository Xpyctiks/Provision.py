import json,requests,logging,asyncio,os
from cryptography import x509
from functions.send_to_telegram import send_to_telegram
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import current_app,redirect,flash
from db.database import Cloudflare, Servers

def cloudflare_certificate(domain: str, selected_account: str, selected_server: str):
    try:
        #preparing account token by the selected account
        logging.info("Starting certificates pre-check")
        tkn = Cloudflare.query.filter_by(account=selected_account).first()
        if not tkn:
            logging.error(f"Token for CF account {selected_account} is not found during validation procedure")
            return f'{{"message": "Token for CF account {selected_account} is not found during validation procedure"}}'
        token = tkn.token
        srv = Servers.query.filter_by(name=selected_server).first()
        if not srv:
            logging.error(f"IP of the server {selected_server} is not found during validation procedure")
            return f'{{"message": "IP of the server {selected_server} is not found during validation procedure"}}'
        ip = srv.ip
        url = "https://api.cloudflare.com/client/v4/zones"
        headers = {
            "X-Auth-Email": selected_account,
            "X-Auth-Key": token,
            "Content-Type": "application/json"
        }
        #making request to check the domain's existance on the server
        r = requests.get(url, headers=headers).json()
        names = [item["name"] for item in r["result"]]
        if domain in names:
            logging.info(f"The selected domain {domain} exists on the account {selected_account}")
            issue_cert(domain,selected_account,token)
            #getting domain's zone id to check its A records futher
            name_to_id = {i["name"]: i["id"] for i in r["result"]}
            zone_id = name_to_id.get(domain)
            url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
            r = requests.get(url, headers=headers).json()
            #getting all records of type A
            records = {item["name"]: item["content"] for item in r["result"] if item["type"] == "A"}
            for name, content in records.items():
                if content == ip:
                    logging.info(f"A record {content} for {name} is equal to the A record we need for the server {selected_server}:{ip}")
                else:
                    logging.info(f"A record {content} for {name} is NOT equal to the A record we need for the server {selected_server}:{ip}. Setting up...")
                    set_dns_records(domain,selected_account,token,zone_id,ip)
        else:
            logging.error(f"Domain {domain} is not exists on the CF account {selected_account}")
            asyncio.run(send_to_telegram(f"Domain {domain} is not exists on the CF account {selected_account}",f"🚒Provision job error:"))
    except Exception as msg:
        logging.error(f"Cloudflare_certificate global error: {msg}")
        asyncio.run(send_to_telegram(f"Cloudflare_certificate global error:{msg}",f"🚒Provision job error:"))
        return redirect("/provision",301)

def set_dns_records(domain: str, selected_account: str, token: str, zone_id: str, ip: str):
    try:
        url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name={domain}"
        headers = {
            "X-Auth-Email": selected_account,
            "X-Auth-Key": token,
            "Content-Type": "application/json"
        }
        r = requests.get(url, headers=headers).json()
        name_to_content = {i["name"]: i["content"] for i in r["result"]}
        name_to_id = {i["name"]: i["id"] for i in r["result"]}
        #if A record for @ is exists - replace it by the new one
        if name_to_content.get(domain) == domain:
            logging.info(f"A record for {domain} exists and points to {name_to_content.get(domain)}")
            url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{name_to_id.get(domain)}"
            data = {
                "type": "A",
                "name": f"{domain}",
                "content": f"{ip}",
                "comment": "Provision auto deploy."
            }
            r = requests.put(url,data=data,headers=headers).json()
            if r.status_code == 200:
                logging.info(f"API request to update DNS record {domain} to {ip} successfully completed.")
            else:
                logging.error(f"Error while API request to update DNS record {domain} to {ip}! {r.text}")
                asyncio.run(send_to_telegram(f"Error while API request to update DNS record {domain} to {ip}",f"🚒Provision job error:"))
        #if A record for www.@ is exists - replace it by the new one
        elif name_to_content.get(domain) == "www."+domain:
            logging.info(f"A record for www.{domain} exists and points to {name_to_content.get(domain)}")
            url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{name_to_id.get(domain)}"
            data = {
                "type": "A",
                "name": f"www.{domain}",
                "content": f"{ip}",
                "comment": "Provision auto deploy."
            }
            r = requests.put(url,data=data,headers=headers).json()
            if r.status_code == 200:
                logging.info(f"API request to update DNS record www.{domain} to {ip} successfully completed.")
            else:
                logging.error(f"Error while API request to update DNS record www.{domain} to {ip}! {r.text}")
                asyncio.run(send_to_telegram(f"Error while API request to update DNS record www.{domain} to {ip}",f"🚒Provision job error:"))
        else:
            #Else that means there is no records and we need to create them
            logging.info(f"A records for {domain} are not exist. Setting up {domain} record...")
            url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
            data = {
                "type": "A",
                "name": f"{domain}",
                "content": f"{ip}",
                "comment": "Provision auto deploy."
            }
            r = requests.post(url,data=data,headers=headers).json()
            if r.status_code == 200:
                logging.info(f"API request to create DNS record {domain} with {ip} successfully completed.")
            else:
                logging.error(f"Error while API request to create DNS record {domain} with {ip}! {r.text}")
                asyncio.run(send_to_telegram(f"Error while API request to create DNS record {domain} with {ip}",f"🚒Provision job error:"))
            logging.info(f"Setting up www.{domain} record...")
            url = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
            data = {
                "type": "A",
                "name": f"www.{domain}",
                "content": f"{ip}",
                "comment": "Provision auto deploy."
            }
            r = requests.post(url,data=data,headers=headers).json()
            if r.status_code == 200:
                logging.info(f"API request to create DNS record www.{domain} with {ip} successfully completed.")
            else:
                logging.error(f"Error while API request to create DNS record www.{domain} with {ip}! {r.text}")
                asyncio.run(send_to_telegram(f"Error while API request to create DNS record www.{domain} with {ip}",f"🚒Provision job error:"))
    except Exception as msg:
        logging.error(f"Set_dns_records global error: {msg}")
        asyncio.run(send_to_telegram(f"Set_dns_records global error:{msg}",f"🚒Provision job error:"))
        return redirect("/provision",301)

def generate_key_and_csr(domain: str):
    try:
        logging.info(f"Generating CSR for domain {domain}")
        key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        csr_builder = x509.CertificateSigningRequestBuilder()
        csr_builder = csr_builder.subject_name(x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, domain),
        ]))
        csr_builder = csr_builder.add_extension(
            x509.SubjectAlternativeName([
                x509.DNSName(domain),
                x509.DNSName(f"*.{domain}")
            ]),
            critical=False
        )
        csr = csr_builder.sign(key, hashes.SHA256(), default_backend())
        private_key_pem = key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption()
        )
        csr_pem = csr.public_bytes(serialization.Encoding.PEM)
        logging.info(f"Generating CSR for domain {domain} done.")
        return private_key_pem, csr_pem
    except Exception as msg:
        logging.error(f"Generate_key_and_csr global error: {msg}")
        asyncio.run(send_to_telegram(f"Generate_key_and_csr global error:{msg}",f"🚒Provision job error:"))
        return redirect("/provision",301)

def request_cloudflare_cert(csr_pem,domain: str,email: str, token: str):
    try:
        url = "https://api.cloudflare.com/client/v4/certificates"
        headers = {
            "X-Auth-Email": email,
            "X-Auth-Key": token,
            "Content-Type": "application/json"
        }
        data = {
            "csr": csr_pem.decode(),
            "hostnames": [f"{domain}", f"*.{domain}"],
            "request_type": "origin-rsa",
            "requested_validity": 5475
        }
        r = requests.post(url, headers=headers, json=data)
        logging.info(f"Request to Cloudflare API for {domain} done.")
        return r.json()
    except Exception as msg:
        logging.error(f"Request_certificate global error: {msg}")
        asyncio.run(send_to_telegram(f"Request_certificate global error:{msg}",f"🚒Provision job error:"))
        return redirect("/provision",301)

def issue_cert(domain: str,account: str, token: str) -> None:
    try:
        logging.info(f"Starting certificate issue for domain {domain} on the account {account}")
        key, csr = generate_key_and_csr(domain)
        response = request_cloudflare_cert(csr,domain,account,token)
        if not response.get("success"):
            logging.error(f"Issue cert. global error: {json.dumps(response, indent=2)}")
            asyncio.run(send_to_telegram(f"Issue cert. global error!",f"🚒Provision job error:"))
            quit()
        cert = response["result"]["certificate"]
        key = key.decode()
        keyFile = os.path.join(current_app.config['NGX_CRT_PATH'],domain+".key")
        with open(keyFile, "w") as f:
            f.write(key)
            logging.info(f"Certificate key {keyFile} saved.")
        crtFile = os.path.join(current_app.config['NGX_CRT_PATH'],domain+".crt")
        with open(crtFile, "w") as f:
            f.write(cert)
            logging.info(f"Certificate {crtFile} saved.")
    except Exception as msg:
        logging.error(f"Issue_certificate global error: {msg}")
        asyncio.run(send_to_telegram(f"Issue_certificate global error:{msg}",f"🚒Provision job error:"))
        return redirect("/provision",301)