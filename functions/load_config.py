import os, logging,string,random
from db.db import db
from db.database import Settings

def load_config(application):
    with application.app_context():
        try:
            config = db.session.get(Settings, 1)
            application.config.update({
                "TELEGRAM_TOKEN": f"{config.telegramToken}",
                "TELEGRAM_CHATID": f"{config.telegramChat}",
                "LOG_FILE": f"{config.logFile}",
                "WEB_FOLDER": f"{config.webFolder}",
                "NGX_CRT_PATH": f"{config.nginxCrtPath}",
                "NGX_SITES_PATHAV": f"{config.nginxSitesPathAv}",
                "NGX_SITES_PATHEN": f"{config.nginxSitesPathEn}",
                "WWW_USER": f"{config.wwwUser}",
                "WWW_GROUP": f"{config.wwwGroup}",
                "PHP_POOL": f"{config.phpPool}",
                "PHPFPM_PATH": f"{config.phpFpmPath}",
                "SECRET_KEY": f"{config.sessionKey}"
            })
            logging.basicConfig(filename=config.logFile,level=logging.INFO,format='%(asctime)s - Provision - %(levelname)s - %(message)s',datefmt='%d-%m-%Y %H:%M:%S')
            logging.info("Programm started succesfully. Configuration loaded.")
        except Exception as msg:
            print(f"Load-config error: {msg}")
            quit(1)

def generate_default_config(application,CONFIG_DIR,DB_FILE):
    with application.app_context():
        if not os.path.isfile(DB_FILE):
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
                phpPool = "/etc/php/8.2/fpm/pool.d/",
                phpFpmPath = "/usr/sbin/php-fpm8.2"
                )
            try:
                if not os.path.exists(CONFIG_DIR):
                    os.mkdir(CONFIG_DIR)
                db.create_all()
                db.session.add(default_settings)
                db.session.commit()
                print(f"First launch. Default database created in {DB_FILE}. You need to add telegram ChatID and Token if you want to get notifications")
            except Exception as msg:
                print(f"Generate-default-config error: {msg}")
                quit(1)
