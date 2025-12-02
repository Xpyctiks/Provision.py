import json,requests,logging,asyncio,os
from cryptography import x509
from functions.send_to_telegram import send_to_telegram
from cryptography.x509.oid import NameOID
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import serialization, hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from flask import current_app

def generate_key_and_csr(domain: str):
    try:
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
        return private_key_pem, csr_pem
    except Exception as msg:
        logging.error(f"Generate_key_and_csr global error: {msg}")
        asyncio.run(send_to_telegram(f"Generate_key_and_csr global error:{msg}",f"🚒Provision job error:"))
        quit()

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
        return r.json()
    except Exception as msg:
        logging.error(f"Request_certificate global error: {msg}")
        asyncio.run(send_to_telegram(f"Request_certificate global error:{msg}",f"🚒Provision job error:"))
        quit()

def issue_cert(domain: str,account: str, token: str) -> None:
    try:
        key, csr = generate_key_and_csr(domain)
        response = request_cloudflare_cert(csr,domain,account,token)
        print()
        if not response.get("success"):
            logging.error(f"Issue cert. global error: {json.dumps(response, indent=2)}")
            asyncio.run(send_to_telegram(f"Issue cert. global error!",f"🚒Provision job error:"))
            quit()
        cert = response["result"]["certificate"]
        key = key.decode()
        keyFile = os.path.join(current_app.config['NGX_CRT_PATH'],domain+".key")
        with open(keyFile, "w") as f:
            f.write(key)
        crtFile = os.path.join(current_app.config['NGX_CRT_PATH'],domain+".crt")
        with open(crtFile, "w") as f:
            f.write(cert)
    except Exception as msg:
        logging.error(f"Issue_certificate global error: {msg}")
        asyncio.run(send_to_telegram(f"Issue_certificate global error:{msg}",f"🚒Provision job error:"))
        quit()