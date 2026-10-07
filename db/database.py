from .db import db
from werkzeug.security import check_password_hash
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
  id = db.Column(db.Integer, primary_key=True)
  username = db.Column(db.String(80), unique=True, nullable=False)
  realname = db.Column(db.String(80), nullable=False)
  password_hash = db.Column(db.String(250), nullable=False)
  rights = db.Column(db.Integer, nullable=False, default=1)
  created = db.Column(db.DateTime, default=datetime.now)
  def check_password(self, password):
    return check_password_hash(self.password_hash, password)
  
class Settings(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  telegramChat = db.Column(db.String(16), nullable=True)
  telegramToken = db.Column(db.String(64), nullable=True)
  logFile = db.Column(db.String(512), nullable=False)
  sessionKey = db.Column(db.String(64), nullable=False)
  webFolder = db.Column(db.String(512), nullable=False)
  nginxCrtPath = db.Column(db.String(512), nullable=False)
  wwwUser = db.Column(db.String(64), nullable=False)
  wwwGroup = db.Column(db.String(64), nullable=False)
  nginxSitesPathAv = db.Column(db.String(512), nullable=False)
  nginxSitesPathEn = db.Column(db.String(512), nullable=False)
  nginxAddConfDir = db.Column(db.String(256), nullable=False)
  nginxPath = db.Column(db.String(256), nullable=False)
  ngxBindIpAddr = db.Column(db.String(45), nullable=True, default="")
  nginxCachePath = db.Column(db.String(512), nullable=True, default="")
  phpPool = db.Column(db.String(512), nullable=False)
  phpFpmPath = db.Column(db.String(512), nullable=False)
  autheliaLogoutUrl = db.Column(db.String(512), nullable=True, default="")
  webArchiveApiUrl = db.Column(db.String(512), nullable=True, default="")
  mailServerApiUrl = db.Column(db.String(512), nullable=True, default="")
  mailServerApiSecret = db.Column(db.String(256), nullable=True, default="")
  sendJobDoneReports = db.Column(db.String(10), nullable=True, default="true")
  provisionServerHostname = db.Column(db.String(256), nullable=True, default="")

class Provision_templates(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(256), nullable=False)
  repository = db.Column(db.String(512), nullable=False)
  isdefault  = db.Column(db.Boolean(), default=False)
  created = db.Column(db.DateTime, default=datetime.now)

class Cloudflare(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  account = db.Column(db.String(256), nullable=False)
  token = db.Column(db.String(512), nullable=False)
  isdefault  = db.Column(db.Boolean(), default=False)
  created = db.Column(db.DateTime, default=datetime.now)
  #comma-separated NS servers Cloudflare assigns to this account's zones (see functions/cloudflare_ns_func.py)
  ns_servers = db.Column(db.String(512), nullable=True, default="")

class Servers(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(256), nullable=False)
  ip = db.Column(db.String(50), nullable=False)
  isdefault  = db.Column(db.Boolean(), default=False)
  created = db.Column(db.DateTime, default=datetime.now)

class Ownership(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  domain = db.Column(db.String(256), nullable=False,unique=True)
  owner = db.Column(db.String(50), nullable=False)
  created = db.Column(db.DateTime, default=datetime.now)
  cloned = db.Column(db.String(150), nullable=True,default="")

class Domain_account(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  domain = db.Column(db.String(256), nullable=False,unique=True)
  account = db.Column(db.String(150), nullable=False)
  created = db.Column(db.DateTime, default=datetime.now)

class Cloudflare_account_ownership(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  account = db.Column(db.String(256), nullable=False)
  owner = db.Column(db.String(150), nullable=False)
  created = db.Column(db.DateTime, default=datetime.now)

class Messages(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  foruserid = db.Column(db.Integer, nullable=False)
  text = db.Column(db.Text, nullable=False)
  created = db.Column(db.DateTime, default=datetime.now)

class SitesShowRestricions(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  domain = db.Column(db.String(256), nullable=False,unique=True)
  showforuser = db.Column(db.String(500), nullable=False)
  created = db.Column(db.DateTime, default=datetime.now)
  createdby = db.Column(db.String(256), nullable=True)
  updated = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
  updatedby = db.Column(db.String(256), nullable=True)

class CloudflareEmailsStatus(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  domain = db.Column(db.String(256), nullable=False,unique=True)
  routing_enabled = db.Column(db.Boolean(), nullable=False)
  enabled = db.Column(db.DateTime, default=datetime.now)
  enabledby = db.Column(db.String(256), nullable=True)
  updated = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
  updatedby = db.Column(db.String(256), nullable=True)

class CloudflareEmailsRules(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  domain = db.Column(db.String(256), nullable=False)
  rule = db.Column(db.String(500), nullable=False)
  created = db.Column(db.DateTime, default=datetime.now)

class RedirectsRules(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  domain = db.Column(db.String(256), nullable=False)
  from_path = db.Column(db.String(500), nullable=False)
  to_path = db.Column(db.String(500), nullable=False)
  redirect_type = db.Column(db.String(10), nullable=True)
  created = db.Column(db.DateTime, default=datetime.now)
  updated = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
  updatedby = db.Column(db.String(256), nullable=True)

class DomainRegistrator(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String(256), nullable=False,unique=True)
  api_production_key = db.Column(db.String(256), nullable=False)
  api_secret_key = db.Column(db.String(256), nullable=False)
  provider = db.Column(db.String(20), nullable=False, default="dynadot")   #"dynadot" | "spaceship"
  contact_id = db.Column(db.String(64), nullable=True, default="")         #Spaceship contact ID, порожньо для Dynadot
  created = db.Column(db.DateTime, default=datetime.now)

class RegistratorDomain(db.Model):
  #local cache of every domain on every registrator account (DomainRegistrator) - the /domain_registrators/ page
  #reads from here instead of the slow registrator APIs. Refreshed by functions/registrator_domains_func.py
  #(GET /domain_registrators/sync_all/ + the page's sync button), and updated right away on purchase / NS change.
  __table_args__ = (db.UniqueConstraint("registrator", "domain", name="uq_registrator_domain"),)
  id = db.Column(db.Integer, primary_key=True)
  registrator = db.Column(db.String(256), nullable=False, index=True)   #DomainRegistrator.name
  domain = db.Column(db.String(256), nullable=False, index=True)
  ns_servers = db.Column(db.String(1024), nullable=True, default="")    #comma-separated
  registered = db.Column(db.DateTime, nullable=True)                    #registration date reported by the registrator
  status = db.Column(db.String(256), nullable=True, default="")
  created = db.Column(db.DateTime, default=datetime.now)
  synced = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)

class DomainPurchase(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  domain = db.Column(db.String(256), nullable=False)
  registrator = db.Column(db.String(256), nullable=False)
  cloudflare_account = db.Column(db.String(256), nullable=True)
  status = db.Column(db.String(20), nullable=False)
  message = db.Column(db.String(1024), nullable=True)
  purchased_by = db.Column(db.String(80), nullable=False)
  created = db.Column(db.DateTime, default=datetime.now)
  stage = db.Column(db.String(20), nullable=False, default="just_bought")

class EmailRoutingDomainStatus(db.Model):
  #fast-lookup cache of Cloudflare Email Routing status per domain, kept in sync separately from
  #CloudflareEmailsStatus/CloudflareEmailsRules - exists so filters (e.g. "domains without a catchall
  #rule" on cloudflare_email_bulk) can query it with plain SQL instead of hitting the Cloudflare API
  #once per domain. Unrelated to MailServerDomainStatus (that one is the Postfix mailbox/DKIM/DMARC/SPF
  #provisioning state machine for a different feature - /mail_domains/).
  id = db.Column(db.Integer, primary_key=True)
  domain = db.Column(db.String(256), nullable=False, unique=True)
  cloudflare_account = db.Column(db.String(256), nullable=True)
  routing_enabled = db.Column(db.Boolean(), nullable=True, default=False)
  has_catchall = db.Column(db.Boolean(), nullable=True, default=False)
  created = db.Column(db.DateTime, default=datetime.now)
  updated = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
  updatedby = db.Column(db.String(256), nullable=True)

class MailServerDomainStatus(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  #exactly one row per domain - every add/retry/delete action updates this same row in place instead of
  #appending a new one, so Крок 2 doubles as both "current status" and "history" for the domain
  domain = db.Column(db.String(256), nullable=False, unique=True)
  cloudflare_account = db.Column(db.String(256), nullable=True)
  mailbox = db.Column(db.String(256), nullable=True)
  #action: "add" (provision on the mail server) or "delete" (deprovision)
  action = db.Column(db.String(20), nullable=False)
  status = db.Column(db.String(20), nullable=False)
  message = db.Column(db.String(1024), nullable=True)
  #the IP that was resolved from mailServerApiUrl and written into the SPF record at add-time - kept so
  #delete can strip out exactly that token later, even if the mail server's IP changes in the meantime
  mail_server_ip = db.Column(db.String(64), nullable=True)
  #True if the SPF record didn't exist and we created it from scratch (so delete removes it entirely),
  #False/None if we only inserted our ip4: token into an already-existing SPF record (so delete only strips that token)
  spf_record_created = db.Column(db.Boolean, nullable=True, default=False)
  actor = db.Column(db.String(80), nullable=False)
  created = db.Column(db.DateTime, default=datetime.now)
  updated = db.Column(db.DateTime, default=datetime.now, onupdate=datetime.now)
