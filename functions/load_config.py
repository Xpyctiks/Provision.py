import logging
import string
import random
from db.db import db
from db.database import Settings

def load_config(application):
  """Important function - loads all configuration values from Sqlite3 database when an application starts"""
  with application.app_context():
    try:
      config = db.session.get(Settings, 1)
      application.config.update({
        "TELEGRAM_TOKEN": f"{config.telegramToken or ''}",
        "TELEGRAM_CHATID": f"{config.telegramChat or ''}",
        "LOG_FILE": f"{config.logFile or ''}",
        "WEB_FOLDER": f"{config.webFolder or ''}",
        "NGX_CRT_PATH": f"{config.nginxCrtPath or ''}",
        "NGX_SITES_PATHAV": f"{config.nginxSitesPathAv or ''}",
        "NGX_SITES_PATHEN": f"{config.nginxSitesPathEn or ''}",
        "NGX_ADD_CONF_DIR": f"{config.nginxAddConfDir or ''}",
        "NGX_PATH": f"{config.nginxPath or ''}",
        "NGX_BIND_IP_ADDR": f"{config.ngxBindIpAddr or ''}",
        "NGX_CACHE_PATH": f"{config.nginxCachePath or ''}",
        "WWW_USER": f"{config.wwwUser or ''}",
        "WWW_GROUP": f"{config.wwwGroup or ''}",
        "PHP_POOL": f"{config.phpPool or ''}",
        "PHPFPM_PATH": f"{config.phpFpmPath or ''}",
        "SECRET_KEY": f"{config.sessionKey or ''}",
        "AUTHELIA_LOGOUT_URL": f"{config.autheliaLogoutUrl or ''}",
        "WEB_ARCHIVE_API_URL": f"{config.webArchiveApiUrl or ''}",
        "MAIL_SERVER_API_URL": f"{config.mailServerApiUrl or ''}",
        "MAIL_SERVER_API_SECRET": f"{config.mailServerApiSecret or ''}",
        "SEND_JOB_DONE_REPORTS": (config.sendJobDoneReports or "true").strip().lower() != "false",
        "PROVISION_SERVER_HOSTNAME": f"{config.provisionServerHostname or ''}"
      })
      logging.basicConfig(filename=config.logFile,level=logging.INFO,format='%(asctime)s - Provision - %(levelname)s - %(message)s',datefmt='%d-%m-%Y %H:%M:%S')
      logging.getLogger('werkzeug').setLevel(logging.WARNING)
      logging.getLogger("httpx").setLevel(logging.WARNING)
    except Exception as msg:
      print(f"Load-config error: {msg}")
      quit(1)

def generate_default_config(application):
  """Checks every application loads if the app's configuration exists (a Settings row with id=1). If not -
  creates the tables (idempotent, safe on an already-populated database) and inserts default values."""
  with application.app_context():
    db.create_all()
    if db.session.get(Settings, 1) is None:
      length = 32
      characters = string.ascii_letters + string.digits
      session_key = ''.join(random.choice(characters) for _ in range(length))
      default_settings = Settings(id=1, 
        telegramChat = "",
        telegramToken = "",
        logFile = "/var/log/provision.log",
        sessionKey = session_key,
        webFolder = "/var/www/drops-sites/",
        nginxCrtPath = "/etc/nginx/ssl/",
        wwwUser = "www-data",
        wwwGroup = "www-data",
        nginxSitesPathAv = "/etc/nginx/sites-available-drops/",
        nginxSitesPathEn = "/etc/nginx/sites-enabled-drops/",
        nginxAddConfDir = "/etc/nginx/additional-configs",
        nginxPath = "/etc/nginx/",
        ngxBindIpAddr = "0.0.0.0",
        nginxCachePath = "",
        phpPool = "/etc/php/8.2/fpm/pool.d/",
        phpFpmPath = "/usr/sbin/php-fpm8.2",
        autheliaLogoutUrl = "",
        webArchiveApiUrl = "",
        mailServerApiUrl = "",
        mailServerApiSecret = "",
        sendJobDoneReports = "true",
        provisionServerHostname = ""
        )
      try:
        db.session.add(default_settings)
        db.session.commit()
        print("First launch. Default settings created in the database. You need to add telegram ChatID and Token if you want to get notifications")
      except Exception as msg:
        print(f"Generate-default-config error: {msg}")
        quit(1)
