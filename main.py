#!/usr/local/bin/python3

from flask import Flask
from flask_login import LoginManager
import os,sys,subprocess,shutil,glob,zipfile,random,string,re,asyncio,logging

CONFIG_DIR = "/etc/provision/"
DB_FILE = os.path.join(CONFIG_DIR,"provision.db")
JOB_COUNTER = JOB_TOTAL = 1
application = Flask(__name__)
application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DB_FILE
application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
application.config['PERMANENT_SESSION_LIFETIME'] = 28800
application.config['SESSION_COOKIE_SECURE'] = True
application.config['SESSION_COOKIE_HTTPONLY'] = True
application.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
from db.db import db
from db.database import User
db.init_app(application)
from functions.load_config import load_config, generate_default_config
generate_default_config(application,CONFIG_DIR,DB_FILE)
load_config(application)
application.secret_key = application.config["SECRET_KEY"]
login_manager = LoginManager()
login_manager.login_view = "main.login.login"
login_manager.session_protection = "strong"
login_manager.init_app(application)
from pages import blueprint as routes_blueprint
application.register_blueprint(routes_blueprint)
from functions.config_templates import create_nginx_config, create_php_config
from functions.send_to_telegram import send_to_telegram
from functions.upd_config import delete_user,register_user,update_user,set_wwwUser,set_webFolder,set_wwwGroup,set_logpath,set_nginxCrtPath,set_nginxSitesPathAv,set_nginxSitesPathEn,set_phpFpmPath,set_phpPool,set_telegramChat,set_telegramToken

def genJobID():  
    global JOB_ID
    length = 16
    characters = string.ascii_letters + string.digits
    JOB_ID = ''.join(random.choice(characters) for _ in range(length)).lower()

def finishJob(file):
    global JOB_COUNTER
    filename = os.path.join(os.path.abspath(os.path.dirname(__file__)),os.path.basename(file))
    os.remove(filename)
    logging.info(f"Archive #{JOB_COUNTER} of {JOB_TOTAL} - {filename} removed")
    if JOB_COUNTER == JOB_TOTAL:
        asyncio.run(send_to_telegram(f"🏁Provision job finish ({JOB_ID}):",f"Provision jobs are finished. Total {JOB_TOTAL} done."))
        logging.info(f"----------------------------------------End of JOB ID:{JOB_ID}--------------------------------------------")
        quit()
    else:
        logging.info(f">>>End of JOB #{JOB_COUNTER}")
        asyncio.run(send_to_telegram(f"Provision job {JOB_ID}:",f"JOB #{JOB_COUNTER} of {JOB_TOTAL} finished successfully"))
        JOB_COUNTER += 1
        findZip_1()

def setupPHP(file):
    logging.info(f"Configuring PHP...")
    filename = os.path.basename(file)[:-4]
    config = create_php_config(filename)
    try:
        with open(os.path.join(application.config["PHP_POOL"],filename)+".conf", 'w',encoding='utf8') as fileC:
            fileC.write(config)
        logging.info(f"PHP config {os.path.join(application.config['PHP_POOL'],filename)} created")
        result = subprocess.run(["sudo",application.config["PHPFPM_PATH"],"-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result.stderr):
            #gettings digits of PHP version from the path to the PHP-FPM
            phpVer = re.search(r"(.*)(\d\.\d)",application.config["PHPFPM_PATH"]).group(2)
            logging.info(f"PHP config test passed successfully: {result.stderr.strip()}. Reloading PHP, version {phpVer}...")
            result = subprocess.run(["sudo","systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
            if  result.returncode == 0:
                logging.info(f"PHP reloaded successfully.")
                finishJob(file)
        else:
            logging.error(f"Error while reloading PHP: {result.stdout.strip()} {result.stderr.strip()}")
            asyncio.run(send_to_telegram(f"🚒Provision job error({JOB_ID}):",f"Error while reloading PHP"))
            finishJob(file)
    except Exception as msg:
        logging.error(f"Error while configuring PHP. Error: {msg}")
        asyncio.run(send_to_telegram(f"🚒Provision job error({JOB_ID}):",f"Error: {msg}"))
        finishJob(file)

def setupNginx(file):
    logging.info(f"Configuring Nginx...Preparing certificates")
    filename = os.path.basename(file)[:-4]
    crtPath = os.path.join(application.config["WEB_FOLDER"],filename,filename+".crt")
    keyPath = os.path.join(application.config["WEB_FOLDER"],filename,filename+".key")
    try:
        #preparing certificates
        shutil.copy(crtPath,application.config["NGX_CRT_PATH"])
        os.remove(crtPath)
        shutil.copy(keyPath,application.config["NGX_CRT_PATH"])
        os.remove(keyPath)
        os.chmod(application.config["NGX_CRT_PATH"]+filename+".crt", 0o600)
        os.chmod(application.config["NGX_CRT_PATH"]+filename+".key", 0o600)
        logging.info(f"Certificate {crtPath} and key {keyPath} moved successfully to {application.config['NGX_CRT_PATH']}")
        #preparing folder
        os.system(f"sudo chown -R {application.config['WWW_USER']}:{application.config['WWW_GROUP']} {os.path.join(application.config['WEB_FOLDER'],filename)}")
        logging.info(f"Folders and files ownership of {os.path.join(application.config['WEB_FOLDER'],filename)} changed to {application.config['WWW_USER']}:{application.config['WWW_GROUP']}")
        #preparing redirects config
        if os.path.exists("/etc/nginx/additional-configs/"):
            redirect_file = os.path.join("/etc/nginx/additional-configs/","301-" + filename + ".conf")
            with open(redirect_file, 'w',encoding='utf8') as fileRedir:
                fileRedir.write("")
            logging.info(f"File for redirects {redirect_file} created successfully!")
        else:
            logging.error(f"Folder /etc/nginx/additional-configs is not exists!")
            asyncio.run(send_to_telegram(f"🚒Provision job warning({JOB_ID}):",f"Folder /etc/nginx/additional-configs is not exists!"))
        config = create_nginx_config(filename)
        with open(os.path.join(application.config["NGX_SITES_PATHAV"],filename), 'w',encoding='utf8') as fileC:
            fileC.write(config)
        logging.info(f"Nginx config {os.path.join(application.config['NGX_SITES_PATHAV'],filename)} created")
        if not os.path.exists(os.path.join(application.config["NGX_SITES_PATHEN"],filename)):
            os.symlink(os.path.join(application.config["NGX_SITES_PATHAV"],filename),os.path.join(application.config["NGX_SITES_PATHEN"],filename))
        logging.info(f"Nginx config {os.path.join(application.config['NGX_SITES_PATHEN'],filename)} symlink created")
        result = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result.stderr) and re.search(r".*syntax is ok.*",result.stderr):
            logging.info(f"Nginx config test passed successfully: {result.stderr.strip()}. Reloading Nginx...")
            result = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
            if  re.search(r".*started.*",result.stderr):
                logging.info(f"Nginx reloaded successfully. Result: {result.stderr.strip()}")
            setupPHP(file)
        else:
            logging.error(f"Error while reloading Nginx: {result.stderr.strip()}")
            asyncio.run(send_to_telegram(f"🚒Provision job error({JOB_ID}):",f"Error while reloading Nginx"))
            finishJob(file)
    except Exception as msg:
        logging.error(f"Error while configuring Nginx. Error: {msg}")
        asyncio.run(send_to_telegram(f"🚒Provision job error({JOB_ID}):",f"Error: {msg}"))
        finishJob(file)

def unZip_3(file):
    "Getting the site name from the archive name"
    filename = os.path.basename(file)[:-4]
    "Getting the full path to the folder"
    finalPath = os.path.join(application.config["WEB_FOLDER"],filename)
    logging.info(f"Unpacking {file} to {finalPath}")
    try:
        if not os.path.exists(finalPath):
            os.makedirs(finalPath)
        with zipfile.ZipFile(file, 'r') as zip_ref:
            for member in zip_ref.namelist():
                extracted_path = os.path.join(finalPath, member)
                if os.path.exists(extracted_path):
                    if os.path.isfile(extracted_path):
                        os.remove(extracted_path)
                    if os.path.isdir(extracted_path):
                        shutil.rmtree(extracted_path)
            zip_ref.extractall(finalPath)
            setupNginx(file)
    except Exception as msg:
        logging.error(f"Error while unpacking {file}. Error: {msg}")
        asyncio.run(send_to_telegram(f"🚒Provision job error({JOB_ID}):",f"Error: {msg}"))
        finishJob(file)

def checkZip_2(file):
    logging.info(f">>>Start processing of archive #{JOB_COUNTER} of {JOB_TOTAL} total - {file}")
    asyncio.run(send_to_telegram(f"🎢Provisoin job start({JOB_ID}):",f"Archive #{JOB_COUNTER} of {JOB_TOTAL}: {file}"))
    #Getting site name from archive name
    fileName = os.path.basename(file)[:-4]
    #Preparing full path - path to general web folder + site name
    finalPath = os.path.join(application.config["WEB_FOLDER"],fileName)
    #Preparing full path + "public" folder
    test = os.path.join(finalPath,"public")
    #test if already exists site folder + public folder inside
    if os.path.exists(test):
        #Set counter to 4 to pass all checks. We don't need to check the archive now - just unpack whatever is inside
        found = 4
    else:
        found = 0
    try:
        with zipfile.ZipFile(file, 'r') as zip_ref:
            file_list = zip_ref.namelist()
        for files in file_list:
            if files == f"{fileName}.crt":
                found += 1
                logging.info(f"{fileName}.crt found!")
            if files == f"{fileName}.key":
                found += 1
                logging.info(f"{fileName}.key found!")
            if files == f"public/":
                found += 1
                logging.info("public/ found!")
            if files == f"htpasswd":
                found += 1
                logging.info("htpasswd found!")
        if found < 4:
            print(f"Either {fileName}.crt or {fileName}.key or htpasswd or public/ is absent in {file}")
            logging.error(f"Either {fileName}.crt or {fileName}.key or htpasswd or public/ is absent in {file}")
            asyncio.run(send_to_telegram(f"🚒Provision job error:",f"Job #{JOB_COUNTER} error: Either {fileName}.crt or {fileName}.key or htpasswd or public/ is absent in {file}"))
            logging.info(f">>>End of JOB #{JOB_COUNTER}")
            finishJob(file)
        else:
            logging.info(f"Minimum reqired {fileName}.crt, {fileName}.key, htpasswd, public/ are present in {file}")
            unZip_3(file)
    except Exception as msg:
        logging.error(f"Error while checking {file}. Error: {msg}")
        asyncio.run(send_to_telegram(f"🚒Provision job error({JOB_ID}):",f"Error: {msg}"))
        finishJob(file)

def findZip_1():
    path = os.path.abspath(os.path.dirname(__file__))
    extension = "*.zip"
    files = glob.glob(os.path.join(path, extension))
    for file in files:
        checkZip_2(file)

def main():
    global JOB_TOTAL
    load_config(application)
    genJobID()
    path = os.path.abspath(os.path.dirname(__file__))
    extension = "*.zip"
    files = glob.glob(os.path.join(path, extension))
    JOB_TOTAL = len(files)
    logging.info(f"-----------------------Starting pre-check(JOB ID:{JOB_ID}). Total {JOB_TOTAL} archive(s) found-----------------")
    findZip_1()

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User,int(user_id))

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
                print("Error! Enter both username and new password")
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
        elif sys.argv[1] == "show" and sys.argv[2] == "config":
            if (len(sys.argv) == 3):
                print (f"""
    Telegram ChatID:       {application.config["TELEGRAM_TOKEN"]}
    Telegram Token:        {application.config["TELEGRAM_CHATID"]}
    Log file:              {application.config["LOG_FILE"]}
    SessionKey:            {application.config["SECRET_KEY"]}
    Web root folder:       {application.config["WEB_FOLDER"]}
    Nginx SSL folder:      {application.config["NGX_CRT_PATH"]}
    WWW folders user:      {application.config["WWW_USER"]}
    WWW folders group:     {application.config["WWW_GROUP"]}
    Nginx Sites-Available: {application.config["NGX_SITES_PATHAV"]}
    Nginx Sites-Enabled:   {application.config["NGX_SITES_PATHEN"]}
    Php Pool.d folder:     {application.config["PHP_POOL"]}
    Php-fpm executable:    {application.config["PHPFPM_PATH"]}
    key: {application.secret_key}
                """)
    #if we call the script from console with argument "main" to start provision process
    elif len(sys.argv) == 2 and sys.argv[1] == "main":
        main()
    #else just show help info.
    elif len(sys.argv) <= 2:
        print(f"""Usage: \n{sys.argv[0]} set chat <chatID>
\tAdd Telegram ChatID for notifications.
{sys.argv[0]} set token <Token>
\tAdd Telegram Token for notifications.
{sys.argv[0]} set logpath <new log file path>
\tAdd Telegram Token for notifications.
{sys.argv[0]} user add <login> <password> <realname>
\tAdd new user with its password and default permissions for all cache pathes.
{sys.argv[0]} user setpwd <user> <new password>
\tSet new password for existing user.
{sys.argv[0]} user del <user>
\tDelete existing user by its login
{sys.argv[0]} cfaccount add <name> <token>
\tAdd new CF account and its token
{sys.argv[0]} cfaccount import <path to file>
\tImport CF account records from file
{sys.argv[0]} cfaccount del <name>
\tDelete CF account entry\n
Info: full script should be launched via UWSGI server. In CLI mode use can only use commands above.
""")
    quit(0)
else:
    application.app_context().push()
