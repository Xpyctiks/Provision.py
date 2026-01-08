
import os,subprocess,shutil,glob,zipfile,random,string,re,asyncio,logging
from functions.config_templates import create_nginx_config, create_php_config
from functions.send_to_telegram import send_to_telegram
from functions.certificates import cloudflare_certificate
from flask import current_app,flash
from flask_login import current_user
import functions.variables
from db.database import Ownership,User
from db.db import db
from functions.site_actions import link_domain_and_account

def setSiteOwner(domain: str) -> bool:
    """Sets a site owner to the user, who did the provision job"""
    try:
        #Get all users and find the ID for the our current user
        users = User.query.filter_by(realname=current_user.realname).first()
        if users:
            owner = users.id
        else:
            logging.error(f"setSiteOwner() can not find info in Db about user {current_app.realname}!")
            asyncio.run(send_to_telegram(f"setSiteOwner() can not find info in Db about user {current_app.realname}",f"🚒Provision job error({functions.variables.JOB_ID}):"))
            return False
        logging.info(f"Setting site {domain} owner to user {current_user.realname} with ID {owner}")
        #check if the current user is already an owner of the given domain
        check = Ownership.query.filter_by(domain=domain).first()
        if check:
            if check.id == owner:
                logging.info(f"User {current_user.realname} with ID {owner} already is the owner of {domain}!")
                return True
        #else set it as the new one
        else:
            #check the global variable if this is cloned site
            if functions.variables.CLONED_FROM != "":
                new_owner = Ownership(
                    domain=domain,
                    owner=owner,
                    cloned = functions.variables.CLONED_FROM
                )
            else:
                new_owner = Ownership(
                    domain=domain,
                    owner=owner,
                )
            db.session.add(new_owner)
            db.session.commit()
            logging.info(f"User {current_user.realname} with ID {owner} successfully set as the owner of the {domain}")
        return True
    except Exception as msg:
        logging.error(f"Error setting owner {owner} for domain {domain}: {msg}")
        asyncio.run(send_to_telegram(f"Error setting owner {owner} for domain {domain}: {msg}",f"🚒Provision job error({functions.variables.JOB_ID}):"))
        return False

def genJobID() -> None:
    """Smal function to generate random string as the uniq JOBID"""
    length = 16
    characters = string.ascii_letters + string.digits
    functions.variables.JOB_ID = ''.join(random.choice(characters) for _ in range(length)).lower()

def finishJob(file: str = "", domain: str = "", selected_account: str = "", selected_server: str = "", realname: str = "",emerg_shutdown: bool = False) -> bool:
    """The final function. Accepts either filename or domain name as the variable to properly finish all jobs."""
    try:
        if file != "" and domain == "" and emerg_shutdown == False:
            filename = os.path.join(os.path.abspath(os.path.dirname(__name__)),os.path.basename(file))
            #if this is zip file, not autoprovision, and the file exists - delete it
            if os.path.exists(filename):
                os.remove(filename)
                logging.info(f"Archive #{functions.variables.JOB_COUNTER} of {functions.variables.JOB_TOTAL} - {filename} removed")
            if functions.variables.JOB_COUNTER == functions.variables.JOB_TOTAL:
                #writing site owner info to the database
                setSiteOwner(os.path.basename(file)[:-4])
                #writing link of domain and its account to the database
                link_domain_and_account(os.path.basename(file)[:-4],selected_account)
                asyncio.run(send_to_telegram(f"Provision jobs are finished. Total {functions.variables.JOB_TOTAL} done by {current_user.realname}.",f"🏁Provision job finish ({functions.variables.JOB_ID}):"))
                logging.info(f"----------------------------------------End of JOB ID:{functions.variables.JOB_ID}--------------------------------------------")
                #quit only if we use zip files. if web provision - not to interrupt flow
                if functions.variables.JOB_ID != f"Autoprovision":
                    quit()
            else:
                logging.info(f">>>End of JOB #{functions.variables.JOB_COUNTER}")
                asyncio.run(send_to_telegram(f"JOB #{functions.variables.JOB_COUNTER} of {functions.variables.JOB_TOTAL} finished successfully",f"Provision job {functions.variables.JOB_ID}:"))
                functions.variables.JOB_COUNTER += 1
                #writing site owner info to the database
                setSiteOwner(os.path.basename(file)[:-4])
                #writing link of domain and its account to the database
                link_domain_and_account(os.path.basename(file)[:-4],selected_account)
                findZip_1(selected_account,selected_server,realname)
        elif file == "" and domain != "" and emerg_shutdown == False:
            #writing site owner info to the database
            setSiteOwner(os.path.basename(domain))
            #writing link of domain and its account to the database
            link_domain_and_account(domain,selected_account)
            asyncio.run(send_to_telegram(f"Autoprovision job by {current_user.realname} is finished! ",f"🏁AutoProvision job for {domain}:"))
            logging.info(f"----------------------------------------End of Autorpovison JOB--------------------------------------------")
            return True
        #the function was called after emergency exit from some other place
        elif file != "" and domain == "" and emerg_shutdown == True:
            logging.error("Starting emergency shutdown after finish_job signal received with emergency=true flag...")
            filename = os.path.join(os.path.abspath(os.path.dirname(__name__)),os.path.basename(file))
            #if this is zip file, not autoprovision, and the file exists - delete it
            if os.path.exists(filename):
                os.remove(filename)
            logging.error(f"Archive #{functions.variables.JOB_COUNTER} of {functions.variables.JOB_TOTAL} - {filename} removed")
            asyncio.run(send_to_telegram(f"Provision jobs are interrupted due to errors! Total {functions.variables.JOB_TOTAL} done by {current_user.realname}.",f"🚒🏁Provision job finish ({functions.variables.JOB_ID}):"))
            logging.error(f"----------------------------------------End of JOB ID:{functions.variables.JOB_ID}--------------------------------------------")
            return False
        elif file == "" and domain != "" and emerg_shutdown == True:
            logging.error("Starting emergency shutdown after finish_job signal received with emergency=true flag...")
            asyncio.run(send_to_telegram(f"Autoprovision job by {current_user.realname} is interrupted due to errors! ",f"🚒🏁AutoProvision job finish for {domain}:"))
            logging.error(f"----------------------------------------End of Autorpovison JOB--------------------------------------------")
            return False
    except Exception as msg:
        logging.error(msg)
        return False

def start_autoprovision(domain: str, selected_account: str, selected_server: str, template: str, realname: str):
    """Starts main autoprovision process to deploy site from a git repo,DNS records and certificates automatically"""
    try:
        logging.info(f"---------------------------Starting automatic deploy for site {domain}  by {realname}----------------------------")
        logging.info(f"Cloudflare account: {selected_account}, Server: {selected_server}")
        finalPath = os.path.join(current_app.config["WEB_FOLDER"],domain)
        functions.variables.JOB_ID = f"Autoprovision"
        #First of all starting DNS and certificates check and setup procedure
        if cloudflare_certificate(domain,selected_account,selected_server):
            os.makedirs(finalPath)
            logging.info(f"New directory {finalPath} created")
            os.chdir(finalPath)
            logging.info(f"We are in {finalPath}")
            result = subprocess.run(["sudo","git","clone",f"{template}","."], capture_output=True, text=True)
            if result.returncode != 0:
                logging.error(f"Error while git clone command: {result.stderr}")
                asyncio.run(send_to_telegram(f"Error while git clone command!",f"🚒Provision job error({functions.variables.JOB_ID}):"))
                flash('Помилка при клонуванні із гіт репозиторію!','alert alert-danger')
                return False
            logging.info("Git clone done successfully!")
            result2 = subprocess.run(["sudo","git","config","--global", "--add", "safe.directory", f"{finalPath}"], capture_output=True, text=True)
            if result2.returncode != 0:
                logging.error(f"Error while git add safe.directory: {result.stderr}")
                asyncio.run(send_to_telegram(f"Error while git add safe directory!",f"🚒Provision job error({functions.variables.JOB_ID}):"))
            logging.info("Git add safe directory done successfully!")
            #we add .zip to domain for backward compatibility with another functions of the system
            if not setupNginx(domain+".zip"):
                logging.error("start_autoprovision(): setupNginx() function returned an error!")
                finishJob("",domain,selected_account,selected_server,emerg_shutdown=True)
                return False
            finishJob("",domain,selected_account,selected_server)
            return True
    except Exception as msg:
        logging.error(f"start_autoprovision() error: {msg}")
        asyncio.run(send_to_telegram(f"Autoprovision function error: {msg}",f"🚒Provision job error({functions.variables.JOB_ID}):"))
        return False

def setupPHP(file: str) -> bool:
    """Setups PHP config from the template and reloads the daemon"""
    try:
        logging.info(f"Configuring PHP...")
        filename = os.path.basename(file)[:-4]
        config = create_php_config(filename)
        with open(os.path.join(current_app.config["PHP_POOL"],filename)+".conf", 'w',encoding='utf8') as fileC:
            fileC.write(config)
        logging.info(f"PHP config {os.path.join(current_app.config['PHP_POOL'],filename)} created")
        result = subprocess.run(["sudo",current_app.config["PHPFPM_PATH"],"-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result.stderr):
            #gettings digits of PHP version from the path to the PHP-FPM
            phpVer = re.search(r"(.*)(\d\.\d)",current_app.config["PHPFPM_PATH"]).group(2)
            logging.info(f"PHP config test passed successfully: {result.stderr.strip()}. Reloading PHP, version {phpVer}...")
            result = subprocess.run(["sudo","systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
            if  result.returncode == 0:
                logging.info(f"setupPHP(): PHP reloaded successfully.")
                return True
            else:
                logging.error(f"setupPHP(): PHP reload failed!. {result.stderr}")
                asyncio.run(send_to_telegram(f"setupPHP(): {result.stderr}",f"🚒Provision job error({functions.variables.JOB_ID}):"))
                return False
        else:
            logging.error(f"Error while reloading PHP: {result.stdout.strip()} {result.stderr.strip()}")
            asyncio.run(send_to_telegram(f"Error while reloading PHP",f"🚒Provision job error({functions.variables.JOB_ID}):"))
            return False
    except Exception as msg:
        logging.error(f"Error while configuring PHP. Error: {msg}")
        asyncio.run(send_to_telegram(f"Error: {msg}",f"🚒Provision job error({functions.variables.JOB_ID}):"))
        return False

def setupNginx(file: str) -> bool:
    """Setups Nginx config from the template and reloads the daemon"""
    try:
        logging.info(f"Configuring Nginx...Preparing certificates")
        filename = os.path.basename(file)[:-4]
        #setting correct rights to our newly created certificates
        os.chmod(current_app.config["NGX_CRT_PATH"]+filename+".crt", 0o600)
        os.chmod(current_app.config["NGX_CRT_PATH"]+filename+".key", 0o600)
        #preparing folder
        os.system(f"sudo chown -R {current_app.config['WWW_USER']}:{current_app.config['WWW_GROUP']} {os.path.join(current_app.config['WEB_FOLDER'],filename)}")
        logging.info(f"Folders and files ownership of {os.path.join(current_app.config['WEB_FOLDER'],filename)} changed to {current_app.config['WWW_USER']}:{current_app.config['WWW_GROUP']}")
        #preparing redirects config
        if os.path.exists("/etc/nginx/additional-configs/"):
            redirect_file = os.path.join("/etc/nginx/additional-configs/","301-" + filename + ".conf")
            with open(redirect_file, 'w',encoding='utf8') as fileRedir:
                fileRedir.write("")
            logging.info(f"File for redirects {redirect_file} created successfully!")
        else:
            logging.error(f"Folder /etc/nginx/additional-configs is not exists!")
            asyncio.run(send_to_telegram(f"Folder /etc/nginx/additional-configs is not exists!",f"🚒Provision job warning({functions.variables.JOB_ID}):"))
        config = create_nginx_config(filename)
        with open(os.path.join(current_app.config["NGX_SITES_PATHAV"],filename), 'w',encoding='utf8') as fileC:
            fileC.write(config)
        logging.info(f"Nginx config {os.path.join(current_app.config['NGX_SITES_PATHAV'],filename)} created")
        if not os.path.exists(os.path.join(current_app.config["NGX_SITES_PATHEN"],filename)):
            os.symlink(os.path.join(current_app.config["NGX_SITES_PATHAV"],filename),os.path.join(current_app.config["NGX_SITES_PATHEN"],filename))
        logging.info(f"Nginx config {os.path.join(current_app.config['NGX_SITES_PATHEN'],filename)} symlink created")
        result = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result.stderr) and re.search(r".*syntax is ok.*",result.stderr):
            logging.info(f"Nginx config test passed successfully: {result.stderr.strip()}. Reloading Nginx...")
            result = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
            if  re.search(r".*started.*",result.stderr):
                logging.info(f"Nginx reloaded successfully. Result: {result.stderr.strip()}")
            if not setupPHP(file):
                logging.error("setupNginx(): setupPHP() function returned an error!")
                return False
        else:
            logging.error(f"Error while reloading Nginx: {result.stderr.strip()}")
            asyncio.run(send_to_telegram(f"Error while reloading Nginx",f"🚒Provision job error({functions.variables.JOB_ID}):"))
            return False
        return True
    except Exception as msg:
        logging.error(f"setupNginx(): Error while configuring Nginx: {msg}")
        asyncio.run(send_to_telegram(f"setupNginx(): {msg}",f"🚒Provision job error({functions.variables.JOB_ID}):"))
        return False

def unZip_3(file: str, selected_account: str, selected_server: str, realname: str) -> bool:
    """Step3: unzips the given archive to its new folder"""
    try:
        #Getting the site name from the archive name
        filename = os.path.basename(file)[:-4]
        #Getting the full path to the folder
        finalPath = os.path.join(current_app.config["WEB_FOLDER"],filename)
        logging.info(f"Unpacking {file} to {finalPath}")
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
            if cloudflare_certificate(filename,selected_account,selected_server):
                if not setupNginx(file):
                    logging.error("unZip_3(): setupNginx() function returned an error!")
                    return False
            else:
                logging.error("unZip_3(): cloudflare_certificate() function returned an error!")
                return False
        return True
    except Exception as msg:
        logging.error(f"unZip_3(): general error while processing {file}. Error: {msg}")
        return False

def checkZip_2(file: str, selected_account: str, selected_server: str, realname: str) -> bool:
    """Step2: Checks zip file for it content"""
    logging.info(f">>>Start processing of archive #{functions.variables.JOB_COUNTER} of {functions.variables.JOB_TOTAL} total - {file}")
    asyncio.run(send_to_telegram(f"Archive #{functions.variables.JOB_COUNTER} of {functions.variables.JOB_TOTAL}: {file}",f"🎢Provisoin job start({functions.variables.JOB_ID}):"))
    try:
        #Getting site name from archive name
        fileName = os.path.basename(file)[:-4]
        #Preparing full path - path to general web folder + site name
        finalPath = os.path.join(current_app.config["WEB_FOLDER"],fileName)
        #Preparing full path + "public" folder
        found = 0
        with zipfile.ZipFile(file, 'r') as zip_ref:
            file_list = zip_ref.namelist()
        for files in file_list:
            if files == f"public/":
                found += 1
                logging.info("checkZip_2(): public/ folder found!")
        if found < 1:
            logging.error(f"Looks like public/ folder is absent in {file}!")
            asyncio.run(send_to_telegram(f"Job #{functions.variables.JOB_COUNTER} error: Looks like public/ folder is absent in {file}",f"🚒Provision job error:"))
            logging.info(f">>>End of JOB #{functions.variables.JOB_COUNTER}")
            return False
        else:
            logging.info(f"Minimum reqired public/ folder is present in {file}.Processing futher...")
            if not unZip_3(file,selected_account,selected_server,realname):
                logging.error("checkZip_2: unZip_3() function returned an error!")
                return False
            return True
    except Exception as msg:
        logging.error(f"checkZip_2(): general error! {msg}")
        return False

def findZip_1(selected_account: str, selected_server: str, realname: str) -> bool:
    """Step1: Listing the given dir for zip. files and passes them to the step2 one-by-one"""
    try:
        #check if we have all necessary variables
        if not selected_account or not selected_account or not realname:
            logging.error(f"findZip_1(): some of the important variables has not been received!")
            return False
        path = os.path.abspath(os.path.dirname(__name__))
        extension = "*.zip"
        files = glob.glob(os.path.join(path, extension))
        for file in files:
            if not checkZip_2(file,selected_account,selected_server,realname):
                logging.error("findZip_1(): checkZip_2() function returned an error!")
        return True
    except Exception as msg:
        logging.error(f"findZip_1(): general error! {msg}")
        return False

def preStart_0(selected_account: str, selected_server: str, realname: str) -> bool:
    """Pre-check procedure. Starts the Step1."""
    try:
        #check if we have all necessary variables
        if not selected_account or not selected_account or not realname:
            logging.error(f"start_provision(): some of the important variables has not been received!")
            return False
        genJobID()
        path = os.path.abspath(os.path.dirname(__file__))
        extension = "*.zip"
        files = glob.glob(os.path.join(path, extension))
        functions.variables.JOB_TOTAL = len(files)
        logging.info(f"preStart_0(): Starting pre-check(JOB ID:{functions.variables.JOB_ID}). Total {functions.variables.JOB_TOTAL} archive(s) found")
        #check the return result of the called function
        if not findZip_1(selected_account,selected_server,realname):
            logging.error("preStart_0(): findZip_1() function returned an error!")
            return False
        #normal exit
        return True
    except Exception as msg:
        logging.error(f"preStart_0(): general error! {msg}")
        return False

def start_provision(selected_account: str, selected_server: str, realname: str) -> bool:
    """Callable from Upload page main function"""
    logging.info(f"Cloudflare account: {selected_account}, IP of the server: {selected_server}")
    try:
        #check if we have all necessary variables
        if not selected_account or not selected_account or not realname:
            logging.error(f"start_provision(): some of the important variables has not been received!")
            return False
        #check the return result of the called function
        if not preStart_0(selected_account,selected_server,realname):
            logging.error(f"start_provision(): preStart_0() functions returned an error!")
            return False
        #normal exit
        return True
    except Exception as msg:
        logging.error(f"Autoprovision Error: {msg}")
        return False
