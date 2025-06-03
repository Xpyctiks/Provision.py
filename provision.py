#!/usr/local/bin/python3

from flask import Flask,render_template,request,redirect,flash
from flask_login import LoginManager, login_required
from werkzeug.security import generate_password_hash
import os,sys,subprocess,shutil,logging,glob,zipfile,random,string,re,asyncio
from pages import blueprint as routes_blueprint
from db.db import db
from db.database import User, Settings
from functions.config_templates import create_nginx_config, create_php_config
from functions.load_config import load_config, generate_default_config, show_config
from functions.send_to_telegram import send_to_telegram

CONFIG_DIR = os.path.join("/etc/",os.path.basename(__file__).split(".py")[0])
DB_FILE = os.path.join(CONFIG_DIR,os.path.basename(__file__).split(".py")[0]+".db")
JOB_COUNTER = JOB_TOTAL = 1
application = Flask(__name__)
application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DB_FILE
application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
application.config['PERMANENT_SESSION_LIFETIME'] = 28800
application.register_blueprint(routes_blueprint)
db.init_app(application)
login_manager = LoginManager(application)
login_manager.login_view = "/login"
login_manager.login_message = "You must log in before proceed."
login_manager.session_protection = "strong"

#Global loading of config and all main initializations
generate_default_config(application,CONFIG_DIR,DB_FILE)
load_config(application)
application.secret_key = application.config["SECRET_KEY"]
try:
    logging.basicConfig(filename=application.config["LOG_FILE"],level=logging.INFO,format='%(asctime)s - Provision - %(levelname)s - %(message)s',datefmt='%d-%m-%Y %H:%M:%S')
except Exception as msg:
    logging.error(msg)
    print(f"Logger activation error: {msg}")

def set_telegramChat(tgChat):
    t = Settings(id=1,telegramChat=tgChat.strip())
    db.session.merge(t)
    db.session.commit()
    load_config(application)
    print("Telegram ChatID added successfully")
    try:
        logging.info(f"Telegram ChatID updated successfully!")
    except Exception as err:
        pass

def set_telegramToken(tgToken):
    t = Settings(id=1,telegramToken=tgToken)
    db.session.merge(t)
    db.session.commit()
    load_config(application)
    print("Telegram Token added successfully")
    try:
        logging.info(f"Telegram Token updated successfully!")
    except Exception as err:
        pass

def set_logpath(logpath):
    t = Settings(id=1,logFile=logpath)
    db.session.merge(t)
    db.session.commit()
    load_config(application)
    updated = db.session.get(Settings, 1)
    print(f"logPath updated successfully. New log path: \"{updated.logFile}\"")
    try:
        logging.info(f"logPath updated to \"{updated.logFile}\"")
    except Exception as err:
        pass

def register_user(username,password,realname):
    try:
        if User.query.filter_by(username=username).first():
            print(f"User \"{username}\" creation error - already exists!")
            logging.error(f"User \"{username}\" creation error - already exists!")
        else:
            new_user = User(
                username=username,
                password_hash=generate_password_hash(password),
                realname=realname,
            )
            db.session.add(new_user)
            db.session.commit()
            load_config(application)
            print(f"New user \"{username}\" - \"{realname}\" created successfully!")
            logging.info(f"New user \"{username}\" - \"{realname}\" created successfully!")
    except Exception as err:
        logging.error(f"User \"{username}\" - \"{realname}\" creation error: {err}")
        print(f"User \"{username}\" - \"{realname}\" creation error: {err}")

def update_user(username,password):
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            d = User(id=user.id,password_hash=generate_password_hash(password))
            db.session.merge(d)
            db.session.commit()
            print(f"Password for user \"{user.username}\" updated successfully!")
            logging.info(f"Password for user \"{user.username}\" updated successfully!")
        else:
            print(f"User \"{username}\" set password error - no such user!")
            logging.error(f"User \"{username}\" set password error - no such user!")
            quit(1)
    except Exception as err:
        logging.error(f"User \"{username}\" set password error: {err}")
        print(f"User \"{username}\" set password error: {err}")

def delete_user(username):
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            load_config(application)
            print(f"User \"{user.username}\" deleted successfully!")
            logging.info(f"User \"{user.username}\" deleted successfully!")
        else:
            print(f"User \"{username}\" delete error - no such user!")
            logging.error(f"User \"{username}\" delete error - no such user!")
            quit(1)
    except Exception as err:
        logging.error(f"User \"{username}\" delete error: {err}")
        print(f"User \"{username}\" delete error: {err}")

def set_webFolder(data):
    try:
        t = Settings(id=1,webFolder=data)
        db.session.merge(t)
        db.session.commit()
        load_config(application)
        updated = db.session.get(Settings, 1)
        print(f"Root web folder updated successfully. New path: \"{updated.webFolder}\"")
        logging.info(f"Root web folder updated to \"{updated.webFolder}\"")
    except Exception as err:
        logging.error(f"Root web folder \"{data}\" set error: {err}")
        print(f"Root web folder \"{data}\" set error: {err}")

def set_nginxCrtPath(data):
    try:
        t = Settings(id=1,nginxCrtPath=data)
        db.session.merge(t)
        db.session.commit()
        load_config(application)
        updated = db.session.get(Settings, 1)
        print(f"Nginx SSL folder updated successfully. New path: \"{updated.nginxCrtPath}\"")
        logging.info(f"Nginx SSL folder updated to \"{updated.nginxCrtPath}\"")
    except Exception as err:
        logging.error(f"Nginx SSL folder \"{data}\" set error: {err}")
        print(f"Nginx SSL folder \"{data}\" set error: {err}")

def set_wwwUser(data):
    try:
        t = Settings(id=1,wwwUser=data)
        db.session.merge(t)
        db.session.commit()
        load_config(application)
        updated = db.session.get(Settings, 1)
        print(f"User for web folders updated successfully to: \"{updated.wwwUser}\"")
        logging.info(f"User for web folders updated to \"{updated.wwwUser}\"")
    except Exception as err:
        logging.error(f"User for web folders \"{data}\" set error: {err}")
        print(f"User for web folders \"{data}\" set error: {err}")

def set_wwwGroup(data):
    try:
        t = Settings(id=1,wwwGroup=data)
        db.session.merge(t)
        db.session.commit()
        load_config(application)
        updated = db.session.get(Settings, 1)
        print(f"Group for web folders updated successfully to: \"{updated.wwwGroup}\"")
        logging.info(f"Group for web folders updated to \"{updated.wwwGroup}\"")
    except Exception as err:
        logging.error(f"Group for web folders \"{data}\" set error: {err}")
        print(f"Group for web folders \"{data}\" set error: {err}")

def set_nginxSitesPathAv(data):
    try:
        t = Settings(id=1,nginxSitesPathAv=data)
        db.session.merge(t)
        db.session.commit()
        load_config(application)
        updated = db.session.get(Settings, 1)
        print(f"Nginx Sites-available folder updated successfully to: \"{updated.nginxSitesPathAv}\"")
        logging.info(f"Nginx Sites-available folder updated to \"{updated.nginxSitesPathAv}\"")
    except Exception as err:
        logging.error(f"Nginx Sites-available folder \"{data}\" set error: {err}")
        print(f"Nginx Sites-available folder \"{data}\" set error: {err}")

def set_nginxSitesPathEn(data):
    try:
        t = Settings(id=1,nginxSitesPathEn=data)
        db.session.merge(t)
        db.session.commit()
        load_config(application)
        updated = db.session.get(Settings, 1)
        print(f"Nginx Sites-enabled folder updated successfully to: \"{updated.nginxSitesPathEn}\"")
        logging.info(f"Nginx Sites-enabled folder updated to \"{updated.nginxSitesPathEn}\"")
    except Exception as err:
        logging.error(f"Nginx Sites-enabled folder \"{data}\" set error: {err}")
        print(f"Nginx Sites-enabled folder \"{data}\" set error: {err}")

def set_phpPool(data):
    try:
        t = Settings(id=1,nginxSitesPathEn=data)
        db.session.merge(t)
        db.session.commit()
        load_config(application)
        updated = db.session.get(Settings, 1)
        print(f"PHP Pool.d/ folder updated successfully to: \"{updated.phpPool}\"")
        logging.info(f"PHP Pool.d/ folder updated to \"{updated.phpPool}\"")
    except Exception as err:
        logging.error(f"PHP Pool.d/ folder \"{data}\" set error: {err}")
        print(f"PHP Pool.d/ folder \"{data}\" set error: {err}")

def set_phpFpmPath(data):
    try:
        t = Settings(id=1,nginxSitesPathEn=data)
        db.session.merge(t)
        db.session.commit()
        load_config(application)
        updated = db.session.get(Settings, 1)
        print(f"Php-fpm executable path updated successfully to: \"{updated.phpFpmPath}\"")
        logging.info(f"Php-fpm executable path updated to \"{updated.phpFpmPath}\"")
    except Exception as err:
        logging.error(f"Php-fpm executable path \"{data}\" set error: {err}")
        print(f"Php-fpm executable path \"{data}\" set error: {err}")

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
        if not os.path.exists(os.path.join(application.config["NGX_SITES_PATHAEN"],filename)):
            os.symlink(os.path.join(application.config["NGX_SITES_PATHAV"],filename),os.path.join(application.config["NGX_SITES_PATHEN"],filename))
        logging.info(f"Nginx config {os.path.join(application.config['NGX_SITES_PATHAVEN'],filename)} symlink created")
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
    #load_config()
    genJobID()
    path = os.path.abspath(os.path.dirname(__file__))
    extension = "*.zip"
    files = glob.glob(os.path.join(path, extension))
    JOB_TOTAL = len(files)
    logging.info(f"-----------------------Starting pre-check(JOB ID:{JOB_ID}). Total {JOB_TOTAL} archive(s) found-----------------")
    findZip_1()

def delete_site(sitename):
    error_message = ""
    try:
        logging.info(f"-----------------------Starting site delete: {sitename}-----------------")
        #-------------------------Delete Nginx site config
        ngx_en = os.path.join(application.config["NGX_SITES_PATHEN"],sitename)
        ngx_av = os.path.join(application.config["NGX_SITES_PATHAV"],sitename)
        #delete in nginx/sites-enabled
        if os.path.islink(ngx_en):
            os.unlink(ngx_en)
            logging.info(f"Nginx {ngx_en} deleted successfully")
        else:
            logging.info(f"Nginx {ngx_en} is already deleted")
        #delete in nginx/sites-available
        if os.path.isfile(ngx_av):
            os.unlink(ngx_av)
            logging.info(f"Nginx {ngx_av} deleted successfully")
        else:
            logging.info(f"Nginx {ngx_av} is already deleted")
        result1 = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
            result2 = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
            if  re.search(r".*started.*",result2.stderr):
                logging.info(f"Nginx reloaded successfully. Result: {result2.stderr.strip()}")
        else:
            logging.error(f"Error while reloading Nginx: {result1.stderr.strip()}")
            error_message += f"Error while reloading Nginx: {result1.stderr.strip()}"
            asyncio.run(send_to_telegram(f"🚒Provision site delete error({sitename}):",f"Error while reloading Nginx"))
        #------------------------Delete in php pool.d/
        php = os.path.join(application.config["PHP_POOL"],sitename+".conf")
        php_dis = os.path.join(application.config["PHP_POOL"],sitename+".conf.disabled")
        if os.path.isfile(php):
            os.unlink(php)
            logging.info(f"PHP config {php} deleted successfully")
        elif os.path.isfile(php_dis):
            os.unlink(php_dis)
            logging.info(f"PHP config {php_dis} deleted successfully")
        else:
            logging.info(f"PHP config {php} already deleted")
        result2 = subprocess.run(["sudo",application.config["PHPFPM_PATH"],"-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result2.stderr):
        #gettings digits of PHP version from the path to the PHP-FPM
            phpVer = re.search(r"(.*)(\d\.\d)",application.config["PHPFPM_PATH"]).group(2)
            logging.info(f"PHP config test passed successfully: {result2.stderr.strip()}. Reloading PHP, version {phpVer}...")
            result3 = subprocess.run(["sudo","systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
            if  result3.returncode == 0:
                logging.info(f"PHP reloaded successfully.")
        else:
            logging.error(f"Error while reloading PHP: {result2.stderr.strip()}")
            error_message += f"Error while reloading PHP: {result2.stderr.strip()}"
            asyncio.run(send_to_telegram(f"🚒Provision site delete error({sitename}):",f"Error while reloading PHP"))
        #--------------Delete of the site folder
        path = os.path.join(application.config["WEB_FOLDER"],sitename)
        if not os.path.isdir(path):
            logging.error(f"Site folder delete error - {path} - is not a directory!")
            error_message += f"Site folder delete error - {path} - is not a directory!"
        directory_path = os.path.abspath(path)
        if directory_path in ('/', '/home', '/root', '/etc', '/var', '/tmp', os.path.expanduser("~")):
            logging.error(f"Site folder delete error: {path} - too dangerous directory is selected!")
            error_message += f"Site folder delete error: {path} - too dangerous directory is selected!"
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        os.rmdir(path)
        logging.info(f"Site folder {path} deleted successfully")
    except Exception as msg:
        logging.error(f"Error while site delete. Error: {msg}")
        error_message += f"Error while site delete. Error: {msg}"
        asyncio.run(send_to_telegram(f"🚒Provision site delete error({JOB_ID}):",f"Error: {msg}"))
        if len(error_message) > 0:
            flash(error_message, 'alert alert-danger')
        else:
            flash(f"Site {sitename} deleted successfully", 'alert alert-success')
    if len(error_message) > 0:
        flash(error_message, 'alert alert-danger')
    else:
        flash(f"Site {sitename} deleted successfully", 'alert alert-success')
    logging.info(f"-----------------------Site delete of {sitename} is finished-----------------")

def disable_site(sitename):
    error_message = ""
    try:
        logging.info(f"-----------------------Starting site disable: {sitename}-----------------")
        #disable Nginx site
        ngx = os.path.join(application.config["NGX_SITES_PATHEN"],sitename)
        if os.path.isfile(ngx) or os.path.islink(ngx):
            os.unlink(ngx)
            logging.info(f"Nginx symlink {ngx} removed")
            result1 = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
            if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
                result2 = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
                if  re.search(r".*started.*",result2.stderr):
                    logging.info(f"Nginx reloaded successfully. Result: {result2.stderr.strip()}")
            else:
                logging.error(f"Error while reloading Nginx: {result1.stderr.strip()}")
                error_message += f"Error while reloading Nginx: {result1.stderr.strip()}"
                asyncio.run(send_to_telegram(f"🚒Provision site disable error({sitename}):",f"Error while reloading Nginx"))
        else:
            logging.error(f"Nginx site disable error - symlink {ngx} is not exist")
            error_message += f"Error while reloading Nginx"
        #php disable
        php = os.path.join(application.config["PHP_POOL"],sitename+".conf")
        if os.path.isfile(php) or os.path.islink(php):
            os.rename(php,php+".disabled")
            result2 = subprocess.run(["sudo",application.config["PHPFPM_PATH"],"-t"], capture_output=True, text=True)
            if  re.search(r".*test is successful.*",result2.stderr):
            #gettings digits of PHP version from the path to the PHP-FPM
                phpVer = re.search(r"(.*)(\d\.\d)",application.config["PHPFPM_PATH"]).group(2)
                logging.info(f"PHP config test passed successfully: {result2.stderr.strip()}. Reloading PHP, version {phpVer}...")
                result3 = subprocess.run(["sudo","systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
                if  result3.returncode == 0:
                    logging.info(f"PHP reloaded successfully.")
            else:
                logging.error(f"Error while reloading PHP: {result2.stderr.strip()}")
                error_message += f"Error while reloading PHP: {result2.stderr.strip()}"
                asyncio.run(send_to_telegram(f"🚒Provision site disable error({sitename}):",f"Error while reloading PHP"))
        else:
            logging.error(f"PHP site conf. disable error - symlink {php} is not exist")
            error_message += f"Error while reloading PHP"
    except Exception as msg:
        logging.error(f"Error while site disable. Error: {msg}")
        error_message += f"Error while site disable. Error: {msg}"
        asyncio.run(send_to_telegram(f"🚒Provision site disable error({sitename}):",f"Error: {msg}"))
        if len(error_message) > 0:
            flash(error_message, 'alert alert-danger')
        else:
            flash(f"Site {sitename} disabled sucessfully", 'alert alert-success')
    if len(error_message) > 0:
        flash(error_message, 'alert alert-danger')
    else:
        flash(f"Site {sitename} disabled successfully", 'alert alert-success')
    logging.info(f"-----------------------Site disable of {sitename} is finished-----------------")

def enable_site(sitename):
    error_message = ""
    try:
        logging.info(f"-----------------------Starting site enable: {sitename}-----------------")
        #enable Nginx site
        ngx_en = os.path.join(application.config["NGX_SITES_PATHEN"],sitename)
        ngx_av = os.path.join(application.config["NGX_SITES_PATHAV"],sitename)
        php_cnf = os.path.join(application.config["PHP_POOL"],sitename+".conf")
        php_cnf_dis = os.path.join(application.config["PHP_POOL"],sitename+".conf.disabled")
        #--------------------check if there is no active symlink to the site
        #in sites-enabled is not exists, but in sites-available it is
        if not os.path.islink(ngx_en) and os.path.isfile(ngx_av):
            os.symlink(ngx_av,ngx_en)
            logging.info(f"Symlink {ngx_av} -> {ngx_en} created.")
        #exists everywhere
        elif os.path.islink(ngx_en) and os.path.isfile(ngx_av):
            logging.info(f"Symlink {ngx_av} -> {ngx_en} already exists. Skipping this step.")
        #exists nowhere
        elif not os.path.islink(ngx_en) and not os.path.isfile(ngx_av):
            config = create_nginx_config(sitename)
            with open(os.path.join(ngx_av), 'w',encoding='utf8') as fileC:
                fileC.write(config)
                logging.info(f"Nginx config create for {sitename} because there was none of it")
                os.symlink(ngx_av,ngx_en)
                logging.info(f"Symlink {ngx_av} -> {ngx_en} created.")
        #--------------------check if there is no active php config
        #site.com.conf.disabled exists and site.com.conf is not
        if not os.path.isfile(php_cnf) and os.path.isfile(php_cnf_dis):
            os.rename(php_cnf_dis,php_cnf)
            logging.info(f"Php config renamed from {php_cnf_dis} -> {php_cnf}.")
        elif os.path.isfile(php_cnf) and not os.path.isfile(php_cnf_dis):
            logging.info(f"Php config already exists and is active. Skipping this step.")
        elif not os.path.isfile(php_cnf) and not os.path.isfile(php_cnf_dis):
            config = create_php_config(sitename)
            with open(php_cnf, 'w',encoding='utf8') as fileC:
                fileC.write(config)
            logging.info(f"PHP config {os.path.join(application.config['PHP_POOL'],sitename)} created because it wasn't exist")
        #start of checks - nginx
        result1 = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
            result2 = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
            if  re.search(r".*started.*",result2.stderr):
                logging.info(f"Nginx reloaded successfully. Result: {result2.stderr.strip()}")
        else:
            logging.error(f"Error while reloading Nginx: {result1.stderr.strip()}")
            error_message += f"Error while reloading Nginx: {result1.stderr.strip()}"
            asyncio.run(send_to_telegram(f"🚒Provision site disable error({sitename}):",f"Error while reloading Nginx"))
        #start of checks - php
        result2 = subprocess.run(["sudo",application.config['PHPFPM_PATH'],"-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result2.stderr):
        #gettings digits of PHP version from the path to the PHP-FPM
            phpVer = re.search(r"(.*)(\d\.\d)",application.config['PHPFPM_PATH']).group(2)
            logging.info(f"PHP config test passed successfully: {result2.stderr.strip()}. Reloading PHP, version {phpVer}...")
            result3 = subprocess.run(["sudo","systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
            if  result3.returncode == 0:
                logging.info(f"PHP reloaded successfully.")
        else:
            logging.error(f"Error while reloading PHP: {result2.stderr.strip()}")
            error_message += f"Error while reloading PHP: {result2.stderr.strip()}"
            asyncio.run(send_to_telegram(f"🚒Provision site disable error({sitename}):",f"Error while reloading PHP"))
    except Exception as msg:
        logging.error(f"Global error while site enable. Error: {msg}")
        error_message += f"Global error while site disable. Error: {msg}"
        asyncio.run(send_to_telegram(f"🚒Provision site enable global error({sitename}):",f"Error: {msg}"))
        if len(error_message) > 0:
            flash(error_message, 'alert alert-danger')
        else:
            flash(f"Site {sitename} enabled successfull", 'alert alert-success')
    if len(error_message) > 0:
        flash(error_message, 'alert alert-danger')
    else:
        flash(f"Site {sitename} enabled successfully", 'alert alert-success')

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User,int(user_id))

#catch upload form. Save files to the current folder. Redirect to /
@application.route("/action", methods=['POST'])
@login_required
def do_action():
    delete_form = request.form.get('delete')
    if delete_form:
        delete_site(request.form['delete'].strip())
    disable_form = request.form.get('disable')
    if disable_form:
        disable_site(request.form['disable'].strip())
    enable_form = request.form.get('enable')
    if enable_form:
        enable_site(request.form['enable'].strip())
    return redirect("/",301)

@application.route("/", methods=['GET'])
@login_required
def index():
    try:
        table = ""
        sites_list = []
        sites_list = [
            name for name in os.listdir(application.config["WEB_FOLDER"])
            if os.path.isdir(os.path.join(application.config["WEB_FOLDER"], name))
        ]
        for i, s in enumerate(sites_list, 1):
            #general check all Nginx sites-available, sites-enabled folder + php pool.d/ are available
            #variable with full path to nginx sites-enabled symlink to the site
            ngx_site = os.path.join(application.config["NGX_SITES_PATHEN"],s)
            #variable with full path to php pool config of the site
            php_site = os.path.join(application.config["PHP_POOL"],s+".conf")
            #check of nginx and php have active links and configs of the site
            if os.path.islink(ngx_site) and os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-success">{i}</th>
                <td class="table-success"><form method="post" action="/action">
                    <button type="submit" value="{s}" name="delete" onclick="showLoading()" class="btn btn-danger">Delete site</button>
                    <button type="submit" value="{s}" name="disable" onclick="showLoading()" class="btn btn-warning">Disable site</button>
                    <button type="submit" value="asdf" name="manager" onclick="" class="btn btn-info">Redirects manager</button>
                    <div class="form-check form-switch">
                        <input class="form-check-input" type="checkbox" name="redirect" checked>Redirect all to the main page
                    </div></form>
                <td class="table-success">{s}</td>
                <td class="table-success">{os.path.join(application.config["WEB_FOLDER"],s)}</td>
                <td class="table-success">OK</td>
                \n</tr>"""
            #if nginx is ok but php is not
            elif os.path.islink(ngx_site) and not os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-danger">{i}</th>
                <td class="table-danger"><form method="post" action="/action">
                    <button type="submit" value="{s}" name="delete" onclick="showLoading()" class="btn btn-danger">Delete site</button>
                    <button type="submit" value="{s}" name="enable" onclick="showLoading()" class="btn btn-warning">Re-enable site</button></form>
                <td class="table-danger">{s}</td>
                <td class="table-danger">{os.path.join(application.config["WEB_FOLDER"],s)}</td>
                <td class="table-danger">PHP config error</td>
                \n</tr>"""
            #if php is ok but nginx is not
            elif not os.path.islink(ngx_site) and os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-danger">{i}</th>
                <td class="table-danger"><form method="post" action="/action">
                    <button type="submit" value="{s}" name="delete" onclick="showLoading()" class="btn btn-danger">Delete site</button>
                    <button type="submit" value="{s}" name="enable" onclick="showLoading()" class="btn btn-warning">Re-enable site</button></form>
                <td class="table-danger">{s}</td>
                <td class="table-danger">{os.path.join(application.config["WEB_FOLDER"],s)}</td>
                <td class="table-danger">Nginx config error</td>
                \n</tr>"""
            #if really disabled
            elif not os.path.islink(ngx_site) and not os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-warning">{i}</th>
                <td class="table-warning"><form method="post" action="/action">
                    <button type="submit" value="{s}" name="delete" onclick="showLoading()" class="btn btn-danger">Delete site</button>
                    <button type="submit" value="{s}" name="enable" onclick="showLoading()" class="btn btn-success">Enable site</button></form>
                <td class="table-warning">{s}</td>
                <td class="table-warning">{os.path.join(application.config["WEB_FOLDER"],s)}</td>
                <td class="table-warning">Site is disabled</td>
                \n</tr>"""
            else:
                table += f"""\n<tr>\n<th scope="row" class="table-danger">{i}</th>
                <td class="table-danger">General</td>
                <td class="table-danger">Error</td>
                <td class="table-danger">Important folders are not available or not exist</td>
                \n</tr>"""
        return render_template("template-main.html",table=table)
    except Exception as msg:
        logging.error(f"Error in index(/): {msg}")

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
                set_phpPool(sys.argv[3].strip())
            else:
                print("Error! Enter path to Php-fpm executable")
        elif sys.argv[1] == "show" and sys.argv[2] == "config":
            if (len(sys.argv) == 3):
                show_config(application)
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
