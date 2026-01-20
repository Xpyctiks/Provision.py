#!/usr/local/bin/python3

from flask import Flask
from flask_login import LoginManager
import os,sys
from datetime import timedelta

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
from functions.cli_management import *

@login_manager.user_loader
def load_user(user_id):
  return db.session.get(User,int(user_id))
from pages import blueprint as routes_blueprint
application.register_blueprint(routes_blueprint)

if __name__ == "__main__":
  application.app_context().push()
  if len(sys.argv) > 2:
    if sys.argv[1] == "set" and sys.argv[2] == "chat":
      if (len(sys.argv) == 4):
        set_telegramChat(sys.argv[3].strip())
      else:
        print("Error! Enter ChatID")
    elif sys.argv[1] == "set" and sys.argv[2] == "token":
      if (len(sys.argv) == 4):
        set_telegramToken(sys.argv[3].strip())
      else:
        print("Error! Enter Token")
    elif sys.argv[1] == "set" and sys.argv[2] == "log":
      if (len(sys.argv) == 4):
        set_logpath(sys.argv[3].strip())
      else:
        print("Error! Enter log path")
    elif sys.argv[1] == "user" and sys.argv[2] == "add":
      if (len(sys.argv) == 6):
        register_user(sys.argv[3].strip(),sys.argv[4].strip(),sys.argv[5].strip())
      else:
        print("Error! Enter both username and password")
    elif sys.argv[1] == "user" and sys.argv[2] == "setpwd":
      if (len(sys.argv) == 5):
        update_user(sys.argv[3].strip(),sys.argv[4].strip())
      else:
        print("Error! Enter both username and new password")
    elif sys.argv[1] == "user" and sys.argv[2] == "del":
      if (len(sys.argv) == 4):
        delete_user(sys.argv[3].strip())
      else:
        print("Error! Enter username to delete")
    elif sys.argv[1] == "user" and sys.argv[2] == "setadmin":
      if (len(sys.argv) == 4):
        make_admin_user(sys.argv[3].strip())
      else:
        print("Error! Enter username to make him admin")
    elif sys.argv[1] == "user" and sys.argv[2] == "unsetadmin":
      if (len(sys.argv) == 4):
        remove_admin_user(sys.argv[3].strip())
      else:
        print("Error! Enter username to unset him as admin")
    elif sys.argv[1] == "set" and sys.argv[2] == "webFolder":
      if (len(sys.argv) == 4):
        set_webFolder(sys.argv[3].strip())
      else:
        print("Error! Enter root path to webfolder")
    elif sys.argv[1] == "set" and sys.argv[2] == "nginxCrtPath":
      if (len(sys.argv) == 4):
        set_nginxCrtPath(sys.argv[3].strip())
      else:
        print("Error! Enter path to Nginx SSL certificates folder")
    elif sys.argv[1] == "set" and sys.argv[2] == "wwwUser":
      if (len(sys.argv) == 4):
        set_wwwUser(sys.argv[3].strip())
      else:
        print("Error! Enter name of user for www sites")
    elif sys.argv[1] == "set" and sys.argv[2] == "wwwGroup":
      if (len(sys.argv) == 4):
        set_wwwGroup(sys.argv[3].strip())
      else:
        print("Error! Enter name of group for www sites")
    elif sys.argv[1] == "set" and sys.argv[2] == "nginxSitesPathAv":
      if (len(sys.argv) == 4):
        set_nginxSitesPathAv(sys.argv[3].strip())
      else:
        print("Error! Enter path to Nginx's Sites-Available folder")
    elif sys.argv[1] == "set" and sys.argv[2] == "nginxSitesPathEn":
      if (len(sys.argv) == 4):
        set_nginxSitesPathEn(sys.argv[3].strip())
      else:
        print("Error! Enter path to Nginx's Sites-Enabled folder")
    elif sys.argv[1] == "set" and sys.argv[2] == "nginxPath":
      if (len(sys.argv) == 4):
        set_nginxPath(sys.argv[3].strip())
      else:
        print("Error! Enter path to Nginx's main config. directory")
    elif sys.argv[1] == "set" and sys.argv[2] == "nginxAddConfDir":
      if (len(sys.argv) == 4):
        set_nginxAddConfDir(sys.argv[3].strip())
      else:
        print("Error! Enter path to Nginx's directory with additional configs")
    elif sys.argv[1] == "set" and sys.argv[2] == "phpPool":
      if (len(sys.argv) == 4):
        set_phpPool(sys.argv[3].strip())
      else:
        print("Error! Enter path to Php's Pool.d/ folder")
    elif sys.argv[1] == "set" and sys.argv[2] == "phpFpmPath":
      if (len(sys.argv) == 4):
        set_phpFpmPath(sys.argv[3].strip())
      else:
        print("Error! Enter path to Php-fpm executable")
    elif sys.argv[1] == "show" and sys.argv[2] == "templates":
      show_templates()
    elif sys.argv[1] == "show" and sys.argv[2] == "users":
      show_users()
    elif sys.argv[1] == "show" and sys.argv[2] == "config":
      show_config()
    elif sys.argv[1] == "show" and sys.argv[2] == "cloudflare":
      show_cloudflare()
    elif sys.argv[1] == "show" and sys.argv[2] == "servers":
      show_servers()
    elif sys.argv[1] == "show" and sys.argv[2] == "owners":
      show_owners()
    elif sys.argv[1] == "show" and sys.argv[2] == "accounts":
      show_accounts()
    elif sys.argv[1] == "flush" and sys.argv[2] == "sessions":
      flush_sessions()
    elif sys.argv[1] == "templates" and sys.argv[2] == "add":
      if (len(sys.argv) == 5):
        add_template(sys.argv[3], sys.argv[4])
      else:
        print("Error! Enter Name and Repository address for a new template")
    elif sys.argv[1] == "templates" and sys.argv[2] == "del":
      if (len(sys.argv) == 4):
        del_template(sys.argv[3])
      else:
        print("Error! Enter Name of the template to delete")
    elif sys.argv[1] == "templates" and sys.argv[2] == "upd":
      if (len(sys.argv) == 5):
        upd_template(sys.argv[3], sys.argv[4])
      else:
        print("Error! Enter Name and New repository address for the template")
    elif sys.argv[1] == "templates" and sys.argv[2] == "default":
      if (len(sys.argv) == 4):
        default_template(sys.argv[3])
      else:
        print("Error! Enter Name of the template to set it as default one")
    elif sys.argv[1] == "cloudflare" and sys.argv[2] == "add":
      if (len(sys.argv) == 5):
        add_cloudflare(sys.argv[3], sys.argv[4])
      else:
        print("Error! Enter Account username and token")
    elif sys.argv[1] == "cloudflare" and sys.argv[2] == "del":
      if (len(sys.argv) == 4):
        del_cloudflare(sys.argv[3])
      else:
        print("Error! Enter account name to delete")
    elif sys.argv[1] == "cloudflare" and sys.argv[2] == "upd":
      if (len(sys.argv) == 5):
        upd_cloudflare(sys.argv[3], sys.argv[4])
      else:
        print("Error! Enter account name and new token for it")
    elif sys.argv[1] == "cloudflare" and sys.argv[2] == "default":
      if (len(sys.argv) == 4):
        default_cloudflare(sys.argv[3])
      else:
        print("Error! Enter account name to set it as default one")
    elif sys.argv[1] == "servers" and sys.argv[2] == "add":
      if (len(sys.argv) == 5):
        add_servers(sys.argv[3], sys.argv[4])
      else:
        print("Error! Enter server name and IP")
    elif sys.argv[1] == "servers" and sys.argv[2] == "del":
      if (len(sys.argv) == 4):
        del_servers(sys.argv[3])
      else:
        print("Error! Enter server name to delete")
    elif sys.argv[1] == "servers" and sys.argv[2] == "upd":
      if (len(sys.argv) == 5):
        upd_servers(sys.argv[3], sys.argv[4])
      else:
        print("Error! Enter server name and new IP for it")
    elif sys.argv[1] == "servers" and sys.argv[2] == "default":
      if (len(sys.argv) == 4):
        default_servers(sys.argv[3])
      else:
        print("Error! Enter server name to set it as default one")
    elif sys.argv[1] == "owner" and sys.argv[2] == "add":
      if (len(sys.argv) == 5):
        add_owner(sys.argv[3], int(sys.argv[4]))
      else:
        print("Error! Enter domain name and owner's ID")
    elif sys.argv[1] == "owner" and sys.argv[2] == "del":
      if (len(sys.argv) == 4):
        del_owner(sys.argv[3])
      else:
        print("Error! Enter domain name to delete")
    elif sys.argv[1] == "owner" and sys.argv[2] == "upd":
      if (len(sys.argv) == 5):
        upd_owner(sys.argv[3], int(sys.argv[4]))
      else:
        print("Error! Enter domain name and new owner ID for it")
    elif sys.argv[1] == "account" and sys.argv[2] == "add":
      if (len(sys.argv) == 5):
        add_account(sys.argv[3], sys.argv[4])
      else:
        print("Error! Enter Domain and Email address of the cloudflare account")
    elif sys.argv[1] == "account" and sys.argv[2] == "del":
      if (len(sys.argv) == 4):
        del_account(sys.argv[3])
      else:
        print("Error! Enter Domain to delete")
    elif sys.argv[1] == "account" and sys.argv[2] == "upd":
      if (len(sys.argv) == 5):
        upd_account(sys.argv[3], sys.argv[4])
      else:
        print("Error! Enter Domain and New cloudflare email address")
    elif sys.argv[1] == "account" and sys.argv[2] == "upload":
      if (len(sys.argv) == 4):
        upload_accounts(sys.argv[3])
      else:
        print("Error! Enter Filename of the file, with data in format <domain> <account>, one domain+account per line")
  elif len(sys.argv) == 2 and sys.argv[1] == "account":
    help_account()
  elif len(sys.argv) == 2 and sys.argv[1] == "set":
    help_set()
  elif len(sys.argv) == 2 and sys.argv[1] == "user":
    help_user()
  elif len(sys.argv) == 2 and sys.argv[1] == "show":
    help_show()
  elif len(sys.argv) == 2 and sys.argv[1] == "templates":
    help_templates()
  elif len(sys.argv) == 2 and sys.argv[1] == "servers":
    help_servers()
  elif len(sys.argv) == 2 and sys.argv[1] == "cloudflare":
    help_cloudflare()
  elif len(sys.argv) == 2 and sys.argv[1] == "owner":
    help_owner()
  #else just show help info.
  elif len(sys.argv) <= 2:
    help_show()
  application.run("0.0.0.0",80,debug=True)
  quit(0)
