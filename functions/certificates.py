import json,requests,logging,asyncio,os
from cryptography import x509
from functions.send_to_telegram import send_to_telegram
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from flask_login import current_user
from flask import current_app
from db.database import Cloudflare, Servers
from functions.tld import tld

def cloudflare_certificate(domain: str, selected_account: str, selected_server: str):
    """Main function to automatically get and save certificates"""
    try:
        domain = domain.lower()
        orig_domain = domain.lower()
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
        url_check_domain_exists = "https://api.cloudflare.com/client/v4/zones?per_page=50"
        headers = {
            "X-Auth-Email": selected_account,
            "X-Auth-Key": token,
            "Content-Type": "application/json"
        }
        #check if there is subdomain
        d = tld(domain)
        if bool(d.subdomain):
            domain2 = domain.strip().lower().rstrip(".")
            d2 = tld(domain2)
            domain = f"{d2.domain}.{d2.suffix}"
            logging.info(f"Cert. issue procedure: using domain {d2.domain}.{d2.suffix} as the root domain for issue of {domain}")
        else:
            logging.info(f"Cert. issue procedure: {domain} is the root domain. Validating as is.")
        params_check_domain_exists = {
            "name": domain,
            "per_page": 1
        }
        #making request to check the domain's existance on the server
        result_check_domain_exists = requests.get(url_check_domain_exists, headers=headers, params=params_check_domain_exists).json()
        if result_check_domain_exists["success"] and result_check_domain_exists["result"]:
            logging.info(f"The selected domain {orig_domain} exists on the account {selected_account}")
            if issue_cert(domain,selected_account,token):
                logging.info("Starting preparation to DNS records setup...")
                #getting domain's zone id to check its A records futher
                name_to_id = {i["name"]: i["id"] for i in result_check_domain_exists["result"]}
                #get zone ID for the selected domain
                zone_id = name_to_id.get(domain)
                #get current DNS records for the domain
                url_dns_records = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={orig_domain}"
                result_dns_records = requests.get(url_dns_records, headers=headers).json()
                #if we successfully got some data and there is no result with A record
                if result_dns_records.get("success") and len(result_dns_records.get("result")) <= 0:
                    logging.info(f"No result returned while check current DNS records for {orig_domain}.Looks like there are no A record. Creating the new one...")
                    if create_dns_records(orig_domain,selected_account,token,zone_id,ip):
                        logging.info("DNS record setup finished sucessfully!")
                        return True
                    else:
                        logging.error("DNS records setup error!")
                        return False
                #if we successfully got some data and there is the result with some A records in there
                elif result_dns_records.get("success") and len(result_dns_records.get("result")) > 0:
                    #getting all records of type A
                    records = {item["name"]: item["content"] for item in result_dns_records["result"] if item["type"] == "A"}
                    if records:
                        for name, content in records.items():
                            if content == ip:
                                logging.info(f"A record {content} for {name} is equal to the A record we need for the server {selected_server}:{ip}")
                            else:
                                logging.info(f"A record {content} for {name} is NOT equal to the A record we need for the server {selected_server}:{ip}. Setting up...")
                                if upd_dns_records(name,selected_account,token,zone_id,ip):
                                    logging.info("DNS record setup finished sucessfully!")
                                else:
                                    logging.error("DNS records setup error!")
                                    return False
                        return True
                else:
                    logging.error(f"cloudflare_certificate(): Unexpected error after get-dns-records request to Cloudflare!")
                    asyncio.run(send_to_telegram(f"Unexpected error after get-dns-records request to Cloudflare!",f"🚒Provision job error by {current_user.realname}:"))
                    return False
            else:
                logging.error("Issue_cert returned an error!")
                asyncio.run(send_to_telegram(f"cloudflare_certificate(): Issue_cert returned an error!",f"🚒Provision job error by {current_user.realname}:"))
                return False
        else:
            logging.error(f"Domain {domain} is not exists on the CF account {selected_account}")
            asyncio.run(send_to_telegram(f"Domain {domain} is not exists on the CF account {selected_account}",f"🚒Provision job :"))
            return False
    except Exception as msg:
        logging.error(f"Cloudflare_certificate global error: {msg}")
        asyncio.run(send_to_telegram(f"Cloudflare_certificate global error: {msg}",f"🚒Provision job by {current_user.realname}:"))
        return False

def upd_dns_records(domain: str, selected_account: str, token: str, zone_id: str, ip: str):
    """Updates DNS records via API to the selected one"""
    try:
        headers = {
            "X-Auth-Email": selected_account,
            "X-Auth-Key": token,
            "Content-Type": "application/json"
        }
        #staring update of @ record
        logging.info(f"Updating existing DNS record for domain {domain}, account {selected_account}, zone {zone_id} to IP {ip}")
        url_get_record = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name={domain}"
        result_get_record = requests.get(url_get_record, headers=headers).json()
        record_id = result_get_record["result"][0]["id"]
        url_upd_record = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
        logging.info(f"Updating A record for {domain} with internal ID {record_id} to IP {ip}")
        data = {
            "type": "A",
            "name": f"{domain}",
            "content": f"{ip}",
            "ttl": 3600,
            "proxied": True,
            "comment": "Provision auto deploy."
        }
        result_upd_record = requests.put(url_upd_record,json=data,headers=headers)
        if result_upd_record.status_code == 200:
            logging.info(f"API request to update DNS record {domain} to {ip} successfully completed.")
        else:
            logging.error(f"Error while API request to update DNS record {domain} to {ip}! {result_upd_record.text}")
            asyncio.run(send_to_telegram(f"Error while API request to update DNS record {domain} to {ip} By {current_user.realname}",f"🚒Provision job error:"))
            return False
        #staring update of www.@ record if the original domain is root domain, means not consists of any subdomain
        d = tld(domain)
        if not bool(d.subdomain):
            logging.info(f"Updation A record for www.{domain} to IP {ip}")
            url_get_record = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name=www.{domain}"
            result_get_record = requests.get(url_get_record, headers=headers).json()
            record_id = result_get_record["result"][0]["id"]
            data2 = {
                "type": "A",
                "name": f"www.{domain}",
                "content": f"{ip}",
                "ttl": 3600,
                "proxied": True,
                "comment": "Provision auto deploy."
            }
            result_upd_record = requests.put(url_upd_record,json=data2,headers=headers)
            if result_upd_record.status_code == 200:
                logging.info(f"API request to update DNS record www.{domain} to {ip} successfully completed.")
            else:
                logging.error(f"Error while API request to update DNS record www.{domain} to {ip}! {result_upd_record.text}")
                asyncio.run(send_to_telegram(f"Error while API request to update DNS record www.{domain} to {ip}",f"🚒Provision job error by {current_user.realname}:"))
                return False
        return True
    except Exception as msg:
        logging.error(f"upd_dns_records() global error: {msg}")
        asyncio.run(send_to_telegram(f"upd_dns_records() global error: {msg}",f"🚒Provision job error by {current_user.realname}:"))
        return False

def create_dns_records(domain: str, selected_account: str, token: str, zone_id: str, ip: str):
    """Creates new DNS records via Cloudflare API"""
    try:
        logging.info(f"Setting up new DNS record for domain {domain}, account {selected_account}, zone {zone_id}, ip {ip}")
        addr = tld(domain.strip().lower().rstrip("."))
        #here we keep the root domain. Will check it futher and see if there is a subdomain or not
        root_domain = f"{addr.domain}.{addr.suffix}"
        url_add_record = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records"
        headers = {
            "X-Auth-Email": selected_account,
            "X-Auth-Key": token,
            "Content-Type": "application/json"
        }
        data = {
            "type": "A",
            "name": f"{domain}",
            "content": f"{ip}",
            "ttl": 3600,
            "proxied": True,
            "comment": "Provision auto deploy."
        }
        result_add_record = requests.post(url_add_record,json=data,headers=headers)
        if result_add_record.status_code == 200:
            logging.info(f"create_dns_records(): API request to create DNS record {domain} with {ip} successfully completed.")
        else:
            logging.error(f"create_dns_records(): Error while API request to create DNS record {domain} with {ip}! {result_add_record.text}")
            asyncio.run(send_to_telegram(f"Error while API request to create DNS record {domain} with {ip}",f"🚒Provision job error by {current_user.realname}:"))
        #check if we work with root domain - create www record, if subdomain - passthrough
        if domain == root_domain:
            logging.info(f"Setting up www.{domain} record...")
            data2 = {
                "type": "A",
                "name": f"www.{domain}",
                "content": f"{ip}",
                "ttl": 3600,
                "proxied": True,
                "comment": "Provision auto deploy."
            }
            result_add_record2 = requests.post(url_add_record,json=data2,headers=headers)
            if result_add_record2.status_code == 200:
                logging.info(f"API request to create DNS record www.{domain} with {ip} successfully completed.")
            else:
                logging.error(f"Error while API request to create DNS record www.{domain} with {ip}! {result_add_record2.text}")
                asyncio.run(send_to_telegram(f"Error while API request to create DNS record www.{domain} with {ip}",f"🚒Provision job error by {current_user.realname}:"))
        return True
    except Exception as msg:
        logging.error(f"create_dns_records(): global error: {msg}")
        asyncio.run(send_to_telegram(f"create_dns_records(): global error: {msg}",f"🚒Provision job error by {current_user.realname}:"))
        return False

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
        asyncio.run(send_to_telegram(f"Generate_key_and_csr global error by {current_user.realname}: {msg}",f"🚒Provision job error:"))
        return False

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
        asyncio.run(send_to_telegram(f"Request_certificate global error by {current_user.realname}: {msg}",f"🚒Provision job error:"))
        return False

def issue_cert(domain: str,account: str, token: str):
    """Main certificate issue function"""
    try:
        logging.info(f"Starting certificate issue for domain {domain} on the account {account}")
        #check if we already have certificates - do nothing
        if os.path.exists(os.path.join(current_app.config['NGX_CRT_PATH'],domain+".crt")) and os.path.exists(os.path.join(current_app.config['NGX_CRT_PATH'],domain+".key")):
            logging.info(f"{os.path.join(current_app.config['NGX_CRT_PATH'],domain+'.crt')} and {os.path.join(current_app.config['NGX_CRT_PATH'],domain+'.key')} already exist on the server. Skipping certificates issue!")
            return True
        else:
            logging.info(f"{os.path.join(current_app.config['NGX_CRT_PATH'],domain+'.crt')} and {os.path.join(current_app.config['NGX_CRT_PATH'],domain+'.key')} are not exist on the server. Starting issue procedure...")
        key, csr = generate_key_and_csr(domain)
        response = request_cloudflare_cert(csr,domain,account,token)
        if not response.get("success"):
            logging.error(f"Issue cert. global error: {json.dumps(response, indent=2)}")
            asyncio.run(send_to_telegram(f"Issue cert. global error! By {current_user.realname}",f"🚒Provision job error:"))
            return False
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
        logging.info("Issue_cert done successfully!")
        return True
    except Exception as msg:
        logging.error(f"Issue_certificate global error: {msg}")
        asyncio.run(send_to_telegram(f"Issue_certificate global error by {current_user.realname}: {msg}",f"🚒Provision job error:"))
        return False
