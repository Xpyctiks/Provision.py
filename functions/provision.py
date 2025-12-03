
import os,subprocess,shutil,glob,zipfile,random,string,re,asyncio,logging
from functions.config_templates import create_nginx_config, create_php_config
from functions.send_to_telegram import send_to_telegram
from functions.certificates import cloudflare_certificate
from flask import current_app,flash
import functions.variables

def genJobID() -> None:
    length = 16
    characters = string.ascii_letters + string.digits
    functions.variables.JOB_ID = ''.join(random.choice(characters) for _ in range(length)).lower()

def finishJob(file: str) -> None:
    try:
        filename = os.path.join(os.path.abspath(os.path.dirname(__name__)),os.path.basename(file))
        #if this is zip file, not autoprovision, and the file exists - delete it
        if os.path.exists(filename):
            os.remove(filename)
            logging.info(f"Archive #{functions.variables.JOB_COUNTER} of {functions.variables.JOB_TOTAL} - {filename} removed")
        if functions.variables.JOB_COUNTER == functions.variables.JOB_TOTAL:
            asyncio.run(send_to_telegram(f"Provision jobs are finished. Total {functions.variables.JOB_TOTAL} done.",f"🏁Provision job finish ({functions.variables.JOB_ID}):"))
            logging.info(f"----------------------------------------End of JOB ID:{functions.variables.JOB_ID}--------------------------------------------")
            #quit only if we use zip files. if web provision - no to interrupt flow
            if functions.variables.JOB_ID != f"Autoprovision":
                quit()
        else:
            logging.info(f">>>End of JOB #{functions.variables.JOB_COUNTER}")
            asyncio.run(send_to_telegram(f"JOB #{functions.variables.JOB_COUNTER} of {functions.variables.JOB_TOTAL} finished successfully",f"Provision job {functions.variables.JOB_ID}:"))
            functions.variables.JOB_COUNTER += 1
            findZip_1()
    except Exception as msg:
        logging.error(msg)

def start_autoprovision(domain: str, selected_account: str, selected_server: str, template: str, realname: str):
    logging.info(f"---------------------------Starting automatic deploy for site {domain}  by {realname}----------------------------")
    logging.info(f"Cloudflare account: {selected_account}, IP of the server: {selected_server}, Template: {template}")
    finalPath = os.path.join(current_app.config["WEB_FOLDER"],domain)
    functions.variables.JOB_ID = f"Autoprovision"
    #First of all starting DNS and certificates check and setup procedure
    if cloudflare_certificate(domain,selected_account,selected_server):
        try:
            if os.path.exists(finalPath):
                logging.error(f"Site {domain} already exists! Remove it before new deploy!")
                flash(f"Сайт вже існує! Спочатку видаліть його і потім можна буде розгорнути знову!", 'alert alert-danger')
                logging.info(f"--------------------Automatic deploy for site {domain} from template {template} by {realname} finshed with error-----------------------")
                quit()
            os.makedirs(finalPath)
            logging.info(f"New directory {finalPath} created")
            os.chdir(finalPath)
            logging.info(f"We are in {finalPath}")
            result = subprocess.run(["sudo","git","clone",f"{template}","."], capture_output=True, text=True)
            if result.returncode != 0:
                logging.error(f"Error while git clone command: {result.stderr}")
                asyncio.run(send_to_telegram(f"Error while git clone command!",f"🚒Provision job error({functions.variables.JOB_ID}):"))
                flash('Помилка при клонуванні із гіт репозиторію!','alert alert-danger')
                quit()
            logging.info("Git clone done successfully!")
            #we add .zip to domain for backward compatibility with another functions of the system
            setupNginx(domain+".zip")
            return True
        except Exception as msg:
            logging.error(f"Autoprovision Error: {msg}")
            asyncio.run(send_to_telegram(f"Autoprovision function error: {msg}",f"🚒Provision job error({functions.variables.JOB_ID}):"))
            return False
    else:
        return False

def setupPHP(file: str) -> None:
    logging.info(f"Configuring PHP...")
    filename = os.path.basename(file)[:-4]
    config = create_php_config(filename)
    try:
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
                logging.info(f"PHP reloaded successfully.")
                finishJob(file)
            else:
                logging.error(f"PHP reload failed!. {result.stderr}")
                asyncio.run(send_to_telegram(f"Error while reloading PHP",f"🚒Provision job error({functions.variables.JOB_ID}):"))
                finishJob(file)
        else:
            logging.error(f"Error while reloading PHP: {result.stdout.strip()} {result.stderr.strip()}")
            asyncio.run(send_to_telegram(f"Error while reloading PHP",f"🚒Provision job error({functions.variables.JOB_ID}):"))
            finishJob(file)
    except Exception as msg:
        logging.error(f"Error while configuring PHP. Error: {msg}")
        asyncio.run(send_to_telegram(f"Error: {msg}",f"🚒Provision job error({functions.variables.JOB_ID}):"))
        finishJob(file)

def setupNginx(file: str) -> None:
    logging.info(f"Configuring Nginx...Preparing certificates")
    filename = os.path.basename(file)[:-4]
    try:
        #preparing certificates
        #Check if we are using provision from zip file or autoprovision. If auto - skip copying the certificates, they are already in ssl folder
        if functions.variables.JOB_ID != f"Autoprovision":
            crtPath = os.path.join(current_app.config["WEB_FOLDER"],filename,filename+".crt")
            keyPath = os.path.join(current_app.config["WEB_FOLDER"],filename,filename+".key")
            shutil.copy(crtPath,current_app.config["NGX_CRT_PATH"])
            os.remove(crtPath)
            shutil.copy(keyPath,current_app.config["NGX_CRT_PATH"])
            os.remove(keyPath)
            logging.info(f"Certificate {crtPath} and key {keyPath} moved successfully to {current_app.config['NGX_CRT_PATH']}")
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
            setupPHP(file)
        else:
            logging.error(f"Error while reloading Nginx: {result.stderr.strip()}")
            asyncio.run(send_to_telegram(f"Error while reloading Nginx",f"🚒Provision job error({functions.variables.JOB_ID}):"))
            finishJob(file)
    except Exception as msg:
        logging.error(f"Error while configuring Nginx. Error: {msg}")
        asyncio.run(send_to_telegram(f"Error: {msg}",f"🚒Provision job error({functions.variables.JOB_ID}):"))
        finishJob(file)

def unZip_3(file: str) -> None:
    #Getting the site name from the archive name
    filename = os.path.basename(file)[:-4]
    #Getting the full path to the folder
    finalPath = os.path.join(current_app.config["WEB_FOLDER"],filename)
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
        asyncio.run(send_to_telegram(f"Error: {msg}",f"🚒Provision job error({functions.variables.JOB_ID}):"))
        finishJob(file)

def checkZip_2(file: str) -> None:
    logging.info(f">>>Start processing of archive #{functions.variables.JOB_COUNTER} of {functions.variables.JOB_TOTAL} total - {file}")
    asyncio.run(send_to_telegram(f"Archive #{functions.variables.JOB_COUNTER} of {functions.variables.JOB_TOTAL}: {file}",f"🎢Provisoin job start({functions.variables.JOB_ID}):"))
    #Getting site name from archive name
    fileName = os.path.basename(file)[:-4]
    #Preparing full path - path to general web folder + site name
    finalPath = os.path.join(current_app.config["WEB_FOLDER"],fileName)
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
        if found < 3:
            print(f"Either {fileName}.crt or {fileName}.key or public/ is absent in {file}")
            logging.error(f"Either {fileName}.crt or {fileName}.key or public/ is absent in {file}")
            asyncio.run(send_to_telegram(f"Job #{functions.variables.JOB_COUNTER} error: Either {fileName}.crt or {fileName}.key or public/ is absent in {file}",f"🚒Provision job error:"))
            logging.info(f">>>End of JOB #{functions.variables.JOB_COUNTER}")
            finishJob(file)
        else:
            logging.info(f"Minimum reqired {fileName}.crt, {fileName}.key, public/ are present in {file}")
            unZip_3(file)
    except Exception as msg:
        logging.error(f"Error while checking {file}. Error: {msg}")
        asyncio.run(send_to_telegram(f"Error: {msg}",f"🚒Provision job error({functions.variables.JOB_ID}):"))
        finishJob(file)

def findZip_1() -> None:
    path = os.path.abspath(os.path.dirname(__name__))
    extension = "*.zip"
    files = glob.glob(os.path.join(path, extension))
    for file in files:
        checkZip_2(file)

def preStart_0() -> None:
    genJobID()
    path = os.path.abspath(os.path.dirname(__file__))
    extension = "*.zip"
    files = glob.glob(os.path.join(path, extension))
    functions.variables.JOB_TOTAL = len(files)
    logging.info(f"-----------------------Starting pre-check(JOB ID:{functions.variables.JOB_ID}). Total {functions.variables.JOB_TOTAL} archive(s) found-----------------")
    findZip_1()
