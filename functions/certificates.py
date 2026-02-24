import requests,logging,os
from cryptography import x509
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import current_app
from flask_login import current_user
from db.database import Cloudflare, Servers
from functions.tld import tld

def cloudflare_certificate(domain: str, selected_account: str, selected_server: str, its_not_a_subdomain: bool = False) -> bool:
  """Main function to automatically get and save certificates"""
  try:
    domain = domain.lower()
    orig_domain = domain.lower()
    #preparing account token by the selected account
    logging.info("cloudflare_certificate(): Starting certificates pre-check")
    tkn = Cloudflare.query.filter_by(account=selected_account).first()
    if not tkn:
      logging.error(f"cloudflare_certificate(): Token for CF account {selected_account} is not found during validation procedure")
      return False
    token = tkn.token
    srv = Servers.query.filter_by(name=selected_server).first()
    if not srv:
      logging.error(f"cloudflare_certificate(): IP of the server {selected_server} is not found during validation procedure")
      return False
    ip = srv.ip
    url_check_domain_exists = f"https://api.cloudflare.com/client/v4/zones"
    headers = {
      "X-Auth-Email": selected_account,
      "X-Auth-Key": token,
      "Content-Type": "application/json"
    }
    #check if there is subdomain
    d = tld(domain)
    #check if there is forced parameter this is not a subdomain
    if its_not_a_subdomain:
      logging.info(f"cloudflare_certificate(): Cert. issue procedure: Forced by user usage of domain {domain} as the root domain for issue of {domain}")
      params_check_domain_exists = {
        "name": domain,
        "per_page": 1
      }  
    elif not its_not_a_subdomain and bool(d.subdomain):
      domain2 = domain.strip().lower().rstrip(".")
      d2 = tld(domain2)
      domain = f"{d2.domain}.{d2.suffix}"
      logging.info(f"cloudflare_certificate(): Cert. issue procedure: using domain {d2.domain}.{d2.suffix} as the root domain for issue of {domain}")
      params_check_domain_exists = {
        "name": domain,
        "per_page": 1
      }
    else:
      logging.info(f"cloudflare_certificate(): Cert. issue procedure: {domain} is the root domain. Validating as is.")
      params_check_domain_exists = {
        "name": domain,
        "per_page": 1
      }
    #making request to check the domain's existance on the server
    result_check_domain_exists = requests.get(url_check_domain_exists, headers=headers, params=params_check_domain_exists).json()
    if result_check_domain_exists.get("success") and result_check_domain_exists.get("result"):
      logging.info(f"cloudflare_certificate(): The selected domain {orig_domain} exists on the account {selected_account}")
      if issue_cert(domain,selected_account,token):
        logging.info("cloudflare_certificate(): Starting preparation to DNS records setup...")
        #getting domain's zone id to check its A records futher
        name_to_id = {i.get("name"): i.get("id") for i in result_check_domain_exists.get("result")}
        #get zone ID for the selected domain
        zone_id = name_to_id.get(domain,"")
        #get current DNS records for the domain
        url_dns_records = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?name={orig_domain}&type=A"
        result_dns_records = requests.get(url_dns_records, headers=headers).json()
        #if we successfully got some data and there is no result with A record
        if result_dns_records.get("success") and len(result_dns_records.get("result")) <= 0:
          logging.info(f"cloudflare_certificate(): No result returned while check current DNS records for {orig_domain}.Looks like there are no A record. Creating the new one...")
          if create_dns_records(orig_domain,selected_account,token,zone_id,ip,its_not_a_subdomain):
            logging.info("cloudflare_certificate(): DNS records setup finished sucessfully!")
            return True
          else:
            return False
        #if we successfully got some data and there is the result with some A records in there
        elif result_dns_records.get("success") and len(result_dns_records.get("result")) > 0:
          logging.info(f"cloudflare_certificate(): Some records found, checking futher...")
          #getting all records of type A
          records = {item.get("name"): item.get("content") for item in result_dns_records.get("result")}
          if records:
            for name, content in records.items():
              if content == ip:
                logging.info(f"cloudflare_certificate(): Type A record {content} for {name} is equal to the A record we need for the server {selected_server}:{ip}. Skipping...")
                return True
              else:
                logging.info(f"cloudflare_certificate(): Type A record {content} for {name} is NOT equal to the A record we need for the server {selected_server}:{ip}. Setting up...")
                if upd_dns_records(name,selected_account,token,zone_id,ip,its_not_a_subdomain):
                  logging.info("cloudflare_certificate(): DNS record setup finished sucessfully!")
                else:
                  return False
          return True
        else:
          logging.error(f"cloudflare_certificate(): Unexpected error after get dns records request to Cloudflare!")
          return False
      else:
        return False
    else:
      logging.error(f"cloudflare_certificate(): Domain {domain} is not exists on the CF account {selected_account}!")
      return False
  except Exception as msg:
    logging.error(f"cloudflare_certificate(): global error: {msg}")
    return False

def upd_dns_records(domain: str, selected_account: str, token: str, zone_id: str, ip: str, its_not_a_subdomain: bool = False) -> bool:
  """Updates DNS records via API to the selected one"""
  try:
    if its_not_a_subdomain:
      logging.info(f"upd_dns_records(): Flag Its_not_a_subdomain is set...")
    headers = {
      "X-Auth-Email": selected_account,
      "X-Auth-Key": token,
      "Content-Type": "application/json"
    }
    #staring update of @ record
    logging.info(f"upd_dns_records(): Updating existing DNS record for domain {domain}, account {selected_account}, zone {zone_id} to IP {ip}")
    url_get_record = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name={domain}"
    result_get_record = requests.get(url_get_record, headers=headers).json()
    record_id = result_get_record["result"][0]["id"]
    url_upd_record = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records/{record_id}"
    logging.info(f"upd_dns_records(): Updating A record for {domain} with internal ID {record_id} to IP {ip}")
    data = {
      "type": "A",
      "name": f"{domain}",
      "content": f"{ip}",
      "ttl": 3600,
      "proxied": True,
      "comment": f"Provision auto deploy by {current_user.realname}"
    }
    result_upd_record = requests.put(url_upd_record,json=data,headers=headers).json()
    #check if there is error after the request
    if not result_upd_record.get("success"):
      error_list = ""
      for error in result_upd_record.get("errors", []):
        error_list += error.get('message')
      logging.error(f"upd_dns_records(): Error while API request to update DNS record {domain} to {ip}! {error_list}")
      return False
    logging.info(f"upd_dns_records(): API request to update DNS record {domain} to {ip} successfully completed.")
    #staring update of www.@ record if the original domain is root domain, means not consists of any subdomain
    d = tld(domain)
    if not bool(d.subdomain) or its_not_a_subdomain:
      logging.info(f"upd_dns_records(): Updation A record for www.{domain} to IP {ip}")
      url_get_record = f"https://api.cloudflare.com/client/v4/zones/{zone_id}/dns_records?type=A&name=www.{domain}"
      result_get_record = requests.get(url_get_record, headers=headers).json()
      #check if there is error after the request
      if not result_get_record.get("success"):
        error_list = ""
        for error in result_get_record.get("errors", []):
          error_list += error.get('message')
        logging.error(f"upd_dns_records(): Get DNS records error: {error_list}")
        return False
      #if no errors, proceed with futher actions
      record_id = result_get_record["result"][0]["id"]
      data2 = {
        "type": "A",
        "name": f"www.{domain}",
        "content": f"{ip}",
        "ttl": 3600,
        "proxied": True,
        "comment": f"Provision auto deploy by {current_user.realname}"
      }
      result_upd_record2 = requests.put(url_upd_record,json=data2,headers=headers).json()
      if not result_upd_record2.get("success"):
        error_list = ""
        for error in result_upd_record2.get("errors", []):
          error_list += error.get('message')
        logging.error(f"upd_dns_records(): Error while API request to update DNS record www.{domain} to {ip}! {error_list}")
        return False
      logging.info(f"upd_dns_records(): API request to update DNS record www.{domain} to {ip} successfully completed.")
      return True
    return True
  except Exception as msg:
    logging.error(f"upd_dns_records() global error: {msg}")
    return False

def create_dns_records(domain: str, selected_account: str, token: str, zone_id: str, ip: str, its_not_a_subdomain: bool = False) -> bool:
  """Creates new DNS records via Cloudflare API"""
  try:
    logging.info(f"create_dns_records(): Setting up new DNS record for domain {domain}, account {selected_account}, zone {zone_id}, ip {ip}")
    addr = tld(domain.strip().lower().rstrip("."))
    if its_not_a_subdomain:
      logging.info(f"create_dns_records(): Flag Its_not_a_subdomain is set...")
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
      "comment": f"Provision auto deploy by {current_user.realname}"
    }
    result_add_record = requests.post(url_add_record,json=data,headers=headers).json()
    if result_add_record.get("success"):
      logging.info(f"create_dns_records(): API request to create DNS record {domain} with {ip} successfully completed.")
    else:
      error_list = ""
      for error in result_add_record.get("errors", []):
        error_list += error.get('message')
      logging.error(f"create_dns_records(): Error while API request to create DNS record {domain} with {ip}! {error_list}")
      return False
    #check if we work with root domain - create www record, if subdomain - passthrough
    if domain == root_domain or its_not_a_subdomain:
      logging.info(f"create_dns_records(): Setting up www.{domain} record...")
      data2 = {
        "type": "A",
        "name": f"www.{domain}",
        "content": f"{ip}",
        "ttl": 3600,
        "proxied": True,
        "comment": f"Provision auto deploy by {current_user.realname}"
      }
      result_add_record2 = requests.post(url_add_record,json=data2,headers=headers).json()
      if result_add_record2.get("success"):
        logging.info(f"create_dns_records(): API request to create DNS record www.{domain} with {ip} successfully completed.")
      else:
        error_list2 = ""
        for error2 in result_add_record2.get("errors", []):
          error_list2 += error2.get('message')
        logging.error(f"create_dns_records(): Error while API request to create DNS record www.{domain} with {ip}! {error_list2}")
        return False
    else:
      logging.info("create_dns_records(): Skipping creation of www. subdomain because we think this is a subdomain already.")
    return True
  except Exception as msg:
    logging.error(f"create_dns_records(): global error: {msg}")
    return False

def generate_key_and_csr(domain: str) -> tuple[bool|bytes, bytes|str]:
  """Generates CSR for future certificate issue via Cloudflare API"""
  try:
    logging.info(f"generate_key_and_csr(): Generating CSR for domain {domain}...")
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
    logging.info(f"generate_key_and_csr(): Generating CSR for domain {domain} is done!")
    return private_key_pem, csr_pem
  except Exception as msg:
    logging.error(f"generate_key_and_csr() global error: {msg}")
    return False, ""

def request_cloudflare_cert(csr_pem,domain: str,email: str, token: str) -> tuple[bool, dict|str]:
  """Makes API request to Cloudflare and gets new certificate and key as JSON response"""
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
    response = requests.post(url, headers=headers, json=data).json()
    if not response.get("success"):
      error_list = ""
      for error in response.get("errors", []):
        error_list += error.get('message')
      logging.error(f"request_cloudflare_cert() error: {error_list}")
      return False, ""
    logging.info(f"request_cloudflare_cert(): Request to Cloudflare API to get certificate and key for {domain} done.")
    return True, response
  except Exception as msg:
    logging.error(f"request_cloudflare_cert() global error: {msg}")
    return False, ""

def issue_cert(domain: str,account: str, token: str) -> bool:
  """Main certificate issue function"""
  try:
    certFile = os.path.join(current_app.config.get('NGX_CRT_PATH',''),domain+".crt")
    keyFile = os.path.join(current_app.config.get('NGX_CRT_PATH',''),domain+'.key')
    if not certFile or not keyFile or not current_app.config.get('NGX_CRT_PATH',''):
      logging.error(f"issue_cert(): some variable has empty value: keyFile={keyFile}, certFile={certFile}, NGX_CRT_PATH={current_app.config.get('NGX_CRT_PATH','')}")
      return False
    logging.info(f"issue_cert(): Starting certificate issue for domain {domain} on the account {account}")
    #check if we already have certificates - do nothing
    if os.path.exists(certFile) and os.path.exists(keyFile):
      logging.info(f"issue_cert(): {certFile} and {keyFile} already exist on the server. Skipping certificates issue!")
      return True
    else:
      logging.info(f"issue_cert(): {certFile} and {keyFile} are not exist on the server. Starting issue procedure...")
    key, csr = generate_key_and_csr(domain)
    #check if the func. returned bool value which means there is error, not a result we need
    if isinstance(key,bool) and key == False:
      return False
    result, response = request_cloudflare_cert(csr,domain,account,token)
    #check if the func. returned bool value which means there is error
    if not result:
      return False
    cert = response["result"]["certificate"]
    key = key.decode()
    with open(keyFile, "w") as f:
      f.write(key)
      logging.info(f"issue_cert(): Certificate key {keyFile} saved.")
    crtFile = certFile
    with open(crtFile, "w") as f:
      f.write(cert)
      logging.info(f"issue_cert(): Certificate {crtFile} saved.")
    logging.info("issue_cert(): Certificate issue done successfully!")
    return True
  except Exception as msg:
    logging.error(f"issue_cert() global error: {msg}")
    return False
