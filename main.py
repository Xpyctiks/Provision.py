#!/usr/local/bin/python3

from flask import Flask
from flask_login import LoginManager
import os,pathlib
from datetime import timedelta
from functions.cache_func import page_cache

CONFIG_DIR = "/etc/provision/"
DB_FILE = os.path.join(CONFIG_DIR,"provision.db")
application = Flask(__name__)
application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DB_FILE
application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
application.config['PERMANENT_SESSION_LIFETIME'] = 28800
application.config['SESSION_COOKIE_SECURE'] = False
application.config['SESSION_COOKIE_HTTPONLY'] = True
application.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
application.config['SESSION_USE_SIGNER'] = True
application.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
application.config['CACHE_TYPE'] = 'FileSystemCache'
from db.db import db
from db.database import User
db.init_app(application)
application.config['SESSION_SQLALCHEMY'] = db
from functions.load_config import load_config, generate_default_config
generate_default_config(application,CONFIG_DIR,DB_FILE)
load_config(application)
application.secret_key = application.config["SECRET_KEY"]
login_manager = LoginManager()
login_manager.login_view = "main.login.do_login"
login_manager.session_protection = "strong"
login_manager.init_app(application)
with application.app_context():
  db.create_all()
#get name of the parent directory for the whole project
current_file = pathlib.Path(__file__)
directory = current_file.resolve().parent
project_root = directory.parent
application.config['CACHE_DIR'] = os.path.join(project_root,".cache")
page_cache.init_app(application)
from functions.cli_management import show_cli

@login_manager.user_loader
def load_user(user_id):
  return db.session.get(User,int(user_id))
from pages import blueprint as routes_blueprint
application.register_blueprint(routes_blueprint)

if __name__ == "__main__":
  show_cli()

