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
  phpPool = db.Column(db.String(512), nullable=False)
  phpFpmPath = db.Column(db.String(512), nullable=False)
  autheliaLogoutUrl = db.Column(db.String(512), nullable=True, default="")
  webArchiveApiUrl = db.Column(db.String(512), nullable=True, default="")

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
  created = db.Column(db.DateTime, default=datetime.now)

class DomainPurchase(db.Model):
  id = db.Column(db.Integer, primary_key=True)
  domain = db.Column(db.String(256), nullable=False)
  registrator = db.Column(db.String(256), nullable=False)
  cloudflare_account = db.Column(db.String(256), nullable=True)
  status = db.Column(db.String(20), nullable=False)
  message = db.Column(db.String(512), nullable=True)
  purchased_by = db.Column(db.String(80), nullable=False)
  created = db.Column(db.DateTime, default=datetime.now)
  stage = db.Column(db.String(20), nullable=False, default="just_bought")
