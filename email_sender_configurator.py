#!/usr/bin/env python3
"""
email_sender_configurator.py

Standalone Flask application meant to run on the REMOTE MAIL SERVER itself (Postfix + PostfixAdmin's
MySQL schema + Dovecot + rspamd) - it is the counterpart the main Provision.py project's "Налаштування
доменів для розсилок" feature (pages/mail_domains.py / functions/mail_domains_func.py) talks to.

It is intentionally fully self-contained: no imports from the rest of the Provision.py codebase (it
does not even live on the same machine), no external config files besides its own .env.

Exposes two endpoints, both POST, both requiring header "X-Api-Key" to match API_KEY from .env. The
mailbox login is NOT a request parameter - it's always the hardcoded MAILBOX_LOGIN below, exactly like
the mailbox password is already hardcoded, since every domain in this project gets exactly one fixed
"order@domain" mailbox:

  POST /api/add_new_domain     {"domain": "example.com"}
    -> adds the domain + mailbox "order@example.com" (hardcoded login and password) to the PostfixAdmin
       MySQL database, generates a DKIM key via rspamadm, registers it in rspamd's dkim_signing.conf,
       restarts rspamd, sends a welcome email to physically create the Dovecot Maildir, and returns the
       DKIM DNS TXT value to the caller: {"success": true, "dkim": "v=DKIM1; k=rsa; p=..."}

  POST /api/delete_domain      {"domain": "example.com"}
    -> removes the domain (and every mailbox/alias under it) from the database, removes its DKIM key
       and its dkim_signing.conf entry, restarts rspamd. Returns {"success": true}

Deployment
----------
Requires (pip): flask, gunicorn, pymysql, python-dotenv
Run under gunicorn, e.g.:
    gunicorn -w 2 -b 127.0.0.1:8686 email_sender_configurator:application

This process needs root privileges (or equivalent) to: write DKIM keys under /etc/rspamd/dkim/, chown
them to _rspamd:_rspamd, edit /etc/rspamd/local.d/dkim_signing.conf, and restart the rspamd service -
the simplest option is to run the gunicorn service itself as root (e.g. via a dedicated systemd unit),
rather than granting a limited user passwordless sudo for each of these commands individually.

.env (place next to this file) must define:
    API_KEY=some-long-random-shared-secret          # must match Settings.mailServerApiSecret on the Provision.py side
    DB_HOST=127.0.0.1
    DB_PORT=3306
    DB_NAME=postfixadmin
    DB_USER=postfixadmin
    DB_PASSWORD=...
    MAILBOX_LOGIN=mailbox                            # optional, defaults shown
    MAILBOX_PASSWORD=123456                          # optional, defaults shown
    LOG_FILE=./email_sender_configurator.log         # optional, defaults shown

See .env.example alongside this file.
"""
import os
import re
import logging
import subprocess
import smtplib
from email.mime.text import MIMEText
from pathlib import Path
import pymysql
from flask import Flask, request, jsonify
from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")

API_KEY = os.environ.get("API_KEY", "")
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_NAME = os.environ.get("DB_NAME", "postfixadmin")
DB_USER = os.environ.get("DB_USER", "postfixadmin")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
LOG_FILE = os.environ.get("LOG_FILE", "/var/log/email_sender_configurator.log")
MAILBOX_LOGIN = os.environ.get("MAILBOX_LOGIN", "")
MAILBOX_PASSWORD = os.environ.get("MAILBOX_PASSWORD", "")
DKIM_DIR = "/etc/rspamd/dkim"
DKIM_SIGNING_CONF = "/etc/rspamd/local.d/dkim_signing.conf"
DKIM_SELECTOR = "default"

logging.basicConfig(
  filename=LOG_FILE,
  level=logging.INFO,
  format='%(asctime)s - EmailSenderConfigurator - %(levelname)s - %(message)s',
  datefmt='%d-%m-%Y %H:%M:%S'
)
logging.getLogger('werkzeug').setLevel(logging.WARNING)
application = Flask(__name__)
app = application

# ── MySQL (PostfixAdmin schema: domain / mailbox / alias tables) ─────────────
def _get_db_connection():
  return pymysql.connect(
    host=DB_HOST, port=DB_PORT, user=DB_USER, password=DB_PASSWORD, database=DB_NAME,
    charset="utf8mb4", autocommit=False
  )

def db_domain_exists(domain: str) -> bool:
  conn = _get_db_connection()
  try:
    with conn.cursor() as cur:
      cur.execute("SELECT 1 FROM domain WHERE domain=%s", (domain,))
      return cur.fetchone() is not None
  finally:
    conn.close()

def db_add_domain_and_mailbox(domain: str, local_part: str, password_hash: str):
  """Creates the domain row, the mailbox row (local_part@domain) and its self-referencing alias row -
  the same three inserts PostfixAdmin itself does when an admin adds a new domain + first mailbox."""
  username = f"{local_part}@{domain}"
  maildir = f"{domain}/{local_part}/"
  logging.info(f"db_add_domain_and_mailbox(): inserting domain={domain}, mailbox={username}, maildir={maildir}")
  conn = _get_db_connection()
  try:
    with conn.cursor() as cur:
      cur.execute(
        "INSERT INTO domain (domain, description, transport, created, modified, active) "
        "VALUES (%s, %s, %s, NOW(), NOW(), 1)",
        (domain, "", "dovecot")
      )
      cur.execute(
        "INSERT INTO mailbox (username, password, name, maildir, quota, local_part, domain, created, modified, active) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), 1)",
        (username, password_hash, local_part, maildir, 0, local_part, domain)
      )
      cur.execute(
        "INSERT INTO alias (address, goto, domain, created, modified, active) VALUES (%s, %s, %s, NOW(), NOW(), 1)",
        (username, username, domain)
      )
    conn.commit()
    logging.info(f"db_add_domain_and_mailbox(): domain/mailbox/alias rows for {domain} committed successfully")
  except Exception as err:
    conn.rollback()
    logging.error(f"db_add_domain_and_mailbox(): failed for domain {domain}, rolled back: {err}")
    raise
  finally:
    conn.close()

def db_delete_domain(domain: str):
  """Removes every alias/mailbox under the domain, then the domain row itself. Does NOT touch the
  physical Maildir on disk (mail data removal is left as a deliberate manual/separate step)."""
  logging.info(f"db_delete_domain(): removing alias/mailbox/domain rows for {domain}")
  conn = _get_db_connection()
  try:
    with conn.cursor() as cur:
      cur.execute("DELETE FROM alias WHERE domain=%s", (domain,))
      aliases_deleted = cur.rowcount
      cur.execute("DELETE FROM mailbox WHERE domain=%s", (domain,))
      mailboxes_deleted = cur.rowcount
      cur.execute("DELETE FROM domain WHERE domain=%s", (domain,))
      domains_deleted = cur.rowcount
    conn.commit()
    logging.info(f"db_delete_domain(): removed for {domain} - {aliases_deleted} alias(es), {mailboxes_deleted} mailbox(es), {domains_deleted} domain row(s)")
  except Exception as err:
    conn.rollback()
    logging.error(f"db_delete_domain(): failed for domain {domain}, rolled back: {err}")
    raise
  finally:
    conn.close()

# ── Dovecot password hashing ──────────────────────────────────────────────────

def hash_password(password: str) -> str:
  """Produces a {SHA512-CRYPT}$6$... hash via doveadm, matching exactly what PostfixAdmin itself
  stores in mailbox.password."""
  result = subprocess.run(["doveadm", "pw", "-s", "SHA512-CRYPT", "-p", password], capture_output=True, text=True, timeout=15)
  if result.returncode != 0 or not result.stdout.strip():
    logging.error(f"hash_password(): doveadm pw failed: {result.stderr.strip() or 'no output'}")
    raise RuntimeError(f"doveadm pw failed: {result.stderr.strip() or 'no output'}")
  logging.info("hash_password(): mailbox password hash generated via doveadm")
  return result.stdout.strip()

# ── DKIM key generation (rspamadm) ────────────────────────────────────────────

def _dkim_key_path(domain: str) -> str:
  return os.path.join(DKIM_DIR, f"{domain}.{DKIM_SELECTOR}.key")

def _parse_dkim_output(raw_output: str) -> str:
  """rspamadm dkim_keygen prints the public key as a zonefile-style TXT record, its value wrapped and
  split across multiple quoted/parenthesized segments, e.g.:
    default._domainkey  IN  TXT ( "v=DKIM1; k=rsa; " "p=MIIBIjANBgkq..." )  ; ----- DKIM key default for example.com
  This reassembles just the actual record value (concatenating every quoted segment), stripped of the
  surrounding quotes/parentheses/comment noise, ready to be written as-is into a DNS TXT record."""
  segments = re.findall(r'"([^"]*)"', raw_output)
  return "".join(segments).strip()

def generate_dkim_key(domain: str) -> str:
  """Generates a new 2048-bit DKIM key for the domain, saves the private key under /etc/rspamd/dkim/,
  fixes its ownership for the rspamd daemon, and returns the cleaned-up public DKIM TXT value."""
  os.makedirs(DKIM_DIR, exist_ok=True)
  key_path = _dkim_key_path(domain)
  logging.info(f"generate_dkim_key(): running rspamadm dkim_keygen for {domain} -> {key_path}")
  result = subprocess.run(
    ["rspamadm", "dkim_keygen", "-b", "2048", "-s", DKIM_SELECTOR, "-d", domain, "-k", key_path],
    capture_output=True, text=True, timeout=30
  )
  if result.returncode != 0 or not os.path.exists(key_path):
    logging.error(f"generate_dkim_key(): rspamadm dkim_keygen failed for {domain}: {result.stderr.strip() or result.stdout.strip()}")
    raise RuntimeError(f"rspamadm dkim_keygen failed: {result.stderr.strip() or result.stdout.strip()}")
  logging.info(f"generate_dkim_key(): DKIM key file created at {key_path}")
  chown_result = subprocess.run(["chown", "_rspamd:_rspamd", key_path], capture_output=True, text=True, timeout=10)
  if chown_result.returncode != 0:
    logging.error(f"generate_dkim_key(): chown _rspamd:_rspamd failed for {key_path}: {chown_result.stderr.strip()}")
  else:
    logging.info(f"generate_dkim_key(): ownership of {key_path} set to _rspamd:_rspamd")
  dkim_value = _parse_dkim_output(result.stdout)
  logging.info(f"generate_dkim_key(): DKIM TXT value for {domain} parsed successfully ({len(dkim_value)} chars)")
  return dkim_value

def remove_dkim_key(domain: str):
  key_path = _dkim_key_path(domain)
  if os.path.exists(key_path):
    os.remove(key_path)
    logging.info(f"remove_dkim_key(): removed DKIM key file {key_path}")
  else:
    logging.warning(f"remove_dkim_key(): DKIM key file {key_path} not found, nothing to remove")

# ── rspamd dkim_signing.conf domain{} block management ───────────────────────

def _dkim_signing_block(domain: str) -> str:
  key_path = _dkim_key_path(domain)
  return (
    f"    {domain} {{\n"
    f"      selectors [\n"
    f"        {{\n"
    f'          path = "{key_path}";\n'
    f'          selector = "{DKIM_SELECTOR}";\n'
    f"        }},\n"
    f"      ]\n"
    f"    }},\n"
  )

def add_domain_to_dkim_signing_conf(domain: str):
  """Inserts a new per-domain selectors block right before the final closing brace of the file (the
  domain {...} block is the last thing in dkim_signing.conf, per the deployed template)."""
  content = Path(DKIM_SIGNING_CONF).read_text(encoding="utf-8")
  block = _dkim_signing_block(domain)
  if block in content:
    logging.info(f"add_domain_to_dkim_signing_conf(): block for {domain} already present in {DKIM_SIGNING_CONF}, nothing to do")
    return  # already present (e.g. a retried request) - nothing to do
  last_brace = content.rfind("}")
  if last_brace == -1:
    logging.error(f"add_domain_to_dkim_signing_conf(): no closing brace found in {DKIM_SIGNING_CONF}")
    raise RuntimeError(f"{DKIM_SIGNING_CONF}: не знайдено закриваючої дужки блоку domain {{ }}")
  new_content = content[:last_brace] + block + content[last_brace:]
  _write_text_file(DKIM_SIGNING_CONF, new_content)
  logging.info(f"add_domain_to_dkim_signing_conf(): added selectors block for {domain} to {DKIM_SIGNING_CONF}")

def remove_domain_from_dkim_signing_conf(domain: str):
  content = Path(DKIM_SIGNING_CONF).read_text(encoding="utf-8")
  block = _dkim_signing_block(domain)
  if block not in content:
    logging.warning(f"remove_domain_from_dkim_signing_conf(): block for {domain} not found in {DKIM_SIGNING_CONF}, nothing to remove")
    return
  new_content = content.replace(block, "", 1)
  _write_text_file(DKIM_SIGNING_CONF, new_content)
  logging.info(f"remove_domain_from_dkim_signing_conf(): removed selectors block for {domain} from {DKIM_SIGNING_CONF}")

def _write_text_file(path: str, content: str):
  try:
    Path(path).write_text(content, encoding="utf-8")
  except PermissionError as err:
    raise RuntimeError(f"Немає прав на запис {path} - переконайтесь, що процес запущений з правами root: {err}")

def restart_rspamd():
  result = subprocess.run(["systemctl", "restart", "rspamd"], capture_output=True, text=True, timeout=30)
  if result.returncode != 0:
    logging.error(f"restart_rspamd(): systemctl restart rspamd failed: {result.stderr.strip()}")
    raise RuntimeError(f"Не вдалося перезапустити rspamd: {result.stderr.strip()}")
  logging.info("restart_rspamd(): rspamd restarted successfully")

# ── Welcome email (physically creates the Dovecot Maildir on first delivery) ─

def send_welcome_email(domain: str, local_part: str):
  """Relays a short welcome email through the local Postfix instance to the freshly created mailbox.
  Postfix hands it to Dovecot's LMTP delivery (virtual_transport=dovecot), which creates the Maildir
  directory tree on disk on first delivery - the same trick PostfixAdmin itself relies on.
  Best-effort only: the domain/mailbox is already fully created in the database either way."""
  try:
    to_addr = f"{local_part}@{domain}"
    from_addr = f"welcome@{domain}"
    msg = MIMEText("Вашу поштову скриньку успішно створено.", _charset="utf-8")
    msg["Subject"] = "Mailbox created"
    msg["From"] = from_addr
    msg["To"] = to_addr
    with smtplib.SMTP("127.0.0.1", 25, timeout=20) as smtp:
      smtp.sendmail(from_addr, [to_addr], msg.as_string())
    logging.info(f"send_welcome_email(): welcome email sent to {to_addr} (Maildir should now be created)")
  except Exception as err:
    logging.error(f"send_welcome_email(): failed to send welcome email to {local_part}@{domain}: {err}")

# ── API ────────────────────────────────────────────────────────────────────

def _fingerprint(secret: str) -> str:
  """Returns a short, safe-to-log fingerprint of a secret (never the full value)."""
  return f"{secret[:4]}...({len(secret)} chars)" if secret else "(empty)"

def _check_api_key() -> bool:
  provided = request.headers.get("X-Api-Key", "")
  if not API_KEY:
    logging.error("_check_api_key(): API_KEY is empty/not set in this script's .env - rejecting every request until it's configured and the process is restarted")
    return False
  if not provided:
    logging.warning("_check_api_key(): request has no X-Api-Key header at all")
    return False
  if provided != API_KEY:
    logging.warning(f"_check_api_key(): X-Api-Key mismatch - got {_fingerprint(provided)}, expected {_fingerprint(API_KEY)}")
    return False
  return True

@application.route("/api/add_new_domain", methods=["POST"])
def add_new_domain():
  if not _check_api_key():
    logging.warning(f"add_new_domain(): rejected request from {request.remote_addr} - missing/invalid X-Api-Key")
    return jsonify({"success": False, "error": "Unauthorized"}), 401
  data = request.get_json(silent=True) or {}
  domain = (data.get("domain") or "").strip().lower()
  if not domain:
    return jsonify({"success": False, "error": "domain is required"}), 400
  logging.info(f"-----------------------Adding domain {domain} with mailbox {MAILBOX_LOGIN} (requested from {request.remote_addr})-----------------------")
  try:
    if db_domain_exists(domain):
      logging.error(f"add_new_domain(): domain {domain} already exists in the database")
      return jsonify({"success": False, "error": f"Domain {domain} already exists"}), 409
    logging.info(f"add_new_domain(): [1/5] domain {domain} not yet in database, proceeding")
    password_hash = hash_password(MAILBOX_PASSWORD)
    logging.info(f"add_new_domain(): [2/5] password hash ready for {domain}")
    db_add_domain_and_mailbox(domain, MAILBOX_LOGIN, password_hash)
    logging.info(f"add_new_domain(): [3/5] database rows created for {domain}")
    dkim_value = generate_dkim_key(domain)
    add_domain_to_dkim_signing_conf(domain)
    restart_rspamd()
    logging.info(f"add_new_domain(): [4/5] DKIM key generated and rspamd reconfigured for {domain}")
    send_welcome_email(domain, MAILBOX_LOGIN)
    logging.info(f"add_new_domain(): [5/5] domain {domain} fully configured, DKIM: {dkim_value[:40]}...")
    return jsonify({"success": True, "dkim": dkim_value}), 200
  except Exception as err:
    logging.error(f"add_new_domain(): error configuring domain {domain}: {err}")
    return jsonify({"success": False, "error": str(err)}), 500

@application.route("/api/delete_domain", methods=["POST"])
def delete_domain():
  if not _check_api_key():
    logging.warning(f"delete_domain(): rejected request from {request.remote_addr} - missing/invalid X-Api-Key")
    return jsonify({"success": False, "error": "Unauthorized"}), 401
  data = request.get_json(silent=True) or {}
  domain = (data.get("domain") or "").strip().lower()
  if not domain:
    return jsonify({"success": False, "error": "domain is required"}), 400
  logging.info(f"-----------------------Deleting domain {domain} (mailbox {MAILBOX_LOGIN}, requested from {request.remote_addr})-----------------------")
  try:
    db_delete_domain(domain)
    logging.info(f"delete_domain(): [1/3] database rows removed for {domain}")
    remove_domain_from_dkim_signing_conf(domain)
    remove_dkim_key(domain)
    logging.info(f"delete_domain(): [2/3] DKIM key and dkim_signing.conf entry removed for {domain}")
    restart_rspamd()
    logging.info(f"delete_domain(): [3/3] domain {domain} fully removed")
    return jsonify({"success": True}), 200
  except Exception as err:
    logging.error(f"delete_domain(): error deleting domain {domain}: {err}")
    return jsonify({"success": False, "error": str(err)}), 500

if __name__ == "__main__":
  application.run(host="127.0.0.1", port=8686)
