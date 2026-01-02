from .db import db
from werkzeug.security import check_password_hash
from flask_login import UserMixin
from datetime import datetime

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    realname = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created = db.Column(db.DateTime,default=datetime.now)
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

class Provision_templates(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    repository = db.Column(db.String(512), nullable=False)
    isdefault  = db.Column(db.Boolean(), default=False)
    created = db.Column(db.DateTime,default=datetime.now)

class Cloudflare(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    account = db.Column(db.String(256), nullable=False)
    token = db.Column(db.String(512), nullable=False)
    isdefault  = db.Column(db.Boolean(), default=False)
    created = db.Column(db.DateTime,default=datetime.now)

class Servers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(256), nullable=False)
    ip = db.Column(db.String(50), nullable=False)
    isdefault  = db.Column(db.Boolean(), default=False)
    created = db.Column(db.DateTime,default=datetime.now)

class Ownership(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(256), nullable=False,unique=True)
    owner = db.Column(db.String(50), nullable=False)
    created = db.Column(db.DateTime,default=datetime.now)
    cloned = db.Column(db.String(150), nullable=True,default="")

class Domain_account(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    domain = db.Column(db.String(256), nullable=False,unique=True)
    account = db.Column(db.String(150), nullable=False)
    created = db.Column(db.DateTime,default=datetime.now)
