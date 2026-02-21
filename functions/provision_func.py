
import os,subprocess,shutil,glob,zipfile,random,string,re,logging
from functions.config_templates import create_nginx_config, create_php_config
from functions.send_to_telegram import send_to_telegram
from functions.certificates import cloudflare_certificate
from flask import current_app,flash
from flask_login import current_user
import functions.variables
from db.database import Ownership,User
from db.db import db
from functions.site_actions import link_domain_and_account
from pathlib import Path
from functions.tld import tld

def setSiteOwner(domain: str) -> bool:
  """Sets a site owner to the user, who did the provision job"""
  try:
    #Get all users and find the ID for the our current user
    users = User.query.filter_by(realname=current_user.realname).first()
    if users:
      owner = users.id
    else:
      logging.error(f"setSiteOwner(): can not find info in DB about user {current_app.realname}!")
      send_to_telegram(f"setSiteOwner(): can not find info in DB about user {current_app.realname}",f"🚒Provision job error({functions.variables.JOB_ID}):")
      return False
    logging.info(f"setSiteOwner(): Setting site {domain} owner to user {current_user.realname} with ID {owner}")
    #check if the current user is already an owner of the given domain
    check = Ownership.query.filter_by(domain=domain).first()
    if check:
      if check.id == owner:
        logging.info(f"setSiteOwner(): User {current_user.realname} with ID {owner} already is the owner of {domain}!")
        return True
    #else set it as the new one
    else:
      #check the global variable if this is cloned site
      if functions.variables.CLONED_FROM != "":
        logging.info(f"setSiteOwner(): The CLONED_FROM variable is set to {functions.variables.CLONED_FROM}. Setting this value as DB value Cloned")
        new_owner = Ownership(domain=domain, owner=owner, cloned = functions.variables.CLONED_FROM)
      else:
        logging.info(f"setSiteOwner(): The CLONED_FROM variable is empty.No records to DB value Cloned")
        new_owner = Ownership(domain=domain, owner=owner)
      db.session.add(new_owner)
      db.session.commit()
      logging.info(f"setSiteOwner(): User {current_user.realname} with ID {owner} successfully set as the owner of the {domain}")
    return True
  except Exception as msg:
    logging.error(f"setSiteOwner(): Error setting owner {owner} for domain {domain}: {msg}")
    return False

def genJobID() -> bool:
  """Smal function to generate random string as the uniq JOBID"""
  try:
    length = 16
    characters = string.ascii_letters + string.digits
    functions.variables.JOB_ID = ''.join(random.choice(characters) for _ in range(length)).lower()
    return True
  except Exception as msg:
    logging.error(f"genJobID(): global error {msg}")
    return False

def finishJob(file: str = "", domain: str = "", selected_account: str = "", selected_server: str = "", realname: str = "",emerg_shutdown: bool = False) -> bool:
  """The final function. Accepts either filename or domain name as the variable to properly finish all jobs."""
  try:
    if file != "" and domain == "" and emerg_shutdown == False:
      filename = os.path.join(os.path.abspath(os.path.dirname(__name__)),os.path.basename(file))
      #if this is zip file, not autoprovision, and the file exists - delete it
      if os.path.exists(filename):
        os.remove(filename)
        logging.info(f"finishJob(): Archive #{functions.variables.JOB_COUNTER} of {functions.variables.JOB_TOTAL} - {filename} removed")
      if functions.variables.JOB_COUNTER == functions.variables.JOB_TOTAL:
        #writing site owner info to the database
        if not setSiteOwner(os.path.basename(file)[:-4]):
          return False
        #writing link of domain and its account to the database
        if not link_domain_and_account(os.path.basename(file)[:-4],selected_account):
          return False
        send_to_telegram(f"Provision jobs are finished. Total {functions.variables.JOB_TOTAL} done by {current_user.realname}.",f"🏁Provision job finish ({functions.variables.JOB_ID}):")
        logging.info(f"----------------------------------------End of JOB ID:{functions.variables.JOB_ID}--------------------------------------------")
        #quit only if we use zip files. if web provision - not to interrupt flow
        if functions.variables.JOB_ID != f"Autoprovision":
          return True
      else:
        logging.info(f">>>End of JOB #{functions.variables.JOB_COUNTER}")
        send_to_telegram(f"JOB #{functions.variables.JOB_COUNTER} of {functions.variables.JOB_TOTAL} finished successfully",f"Provision job {functions.variables.JOB_ID}:")
        functions.variables.JOB_COUNTER += 1
        #writing site owner info to the database
        if not setSiteOwner(os.path.basename(file)[:-4]):
          return False
        #writing link of domain and its account to the database
        if not link_domain_and_account(os.path.basename(file)[:-4],selected_account):
          return False
        findZip_1(selected_account,selected_server,realname)
    elif file == "" and domain != "" and emerg_shutdown == False:
      #writing site owner info to the database
      setSiteOwner(os.path.basename(domain))
      #writing link of domain and its account to the database
      link_domain_and_account(domain,selected_account)
      send_to_telegram(f"Autoprovision job by {current_user.realname} is finished! ",f"🏁AutoProvision job for {domain}:")
      logging.info(f"----------------------------------------End of Autorpovison JOB--------------------------------------------")
      return True
    #the function was called after emergency exit from some other place
    elif file != "" and domain == "" and emerg_shutdown == True:
      logging.error("Starting emergency shutdown after finish_job signal received with emergency=true flag...")
      filename = os.path.join(os.path.abspath(os.path.dirname(__name__)),os.path.basename(file))
      #if this is zip file, not autoprovision, and the file exists - delete it
      if os.path.exists(filename):
        os.remove(filename)
      logging.error(f"finishJob(): Archive #{functions.variables.JOB_COUNTER} of {functions.variables.JOB_TOTAL} - {filename} removed")
      send_to_telegram(f"Provision jobs are interrupted due to errors! Total {functions.variables.JOB_TOTAL} done by {current_user.realname}.",f"🚒🏁Provision job finish ({functions.variables.JOB_ID}):")
      logging.error(f"----------------------------------------End of JOB ID:{functions.variables.JOB_ID}--------------------------------------------")
      return True
    elif file == "" and domain != "" and emerg_shutdown == True:
      logging.error("Starting emergency shutdown after finish_job signal received with emergency=true flag...")
      logging.error(f"----------------------------------------End of Autorpovison JOB--------------------------------------------")
      return True
  except Exception as msg:
    logging.error(f"finishJob(): global error {msg}")
    return False

def setupPHP(file: str) -> bool:
  """Setups PHP config from the template and reloads the daemon"""
  try:
    logging.info(f"setupPHP(): Configuring PHP...")
    php_pool = current_app.config.get("PHP_POOL","")
    php_path = current_app.config.get("PHPFPM_PATH","")
    if not php_path or not php_pool:
      logging.error("setupPHP(): Some important variable to start the function is empty!")
      send_to_telegram("setupPHP(): Some important variable to start the function is empty!",f"🚒Provision job error({functions.variables.JOB_ID}):")
      return False
    filename = os.path.basename(file)[:-4]
    config = create_php_config(filename)
    with open(os.path.join(php_pool,filename)+".conf", 'w',encoding='utf8') as fileC:
      fileC.write(config)
    logging.info(f"setupPHP(): PHP config {os.path.join(php_pool,filename)} created")
    result = subprocess.run(["sudo", php_path, "-t"], capture_output=True, text=True)
    if  re.search(r".*test is successful.*",result.stderr):
      #gettings digits of PHP version from the path to the PHP-FPM
      phpVer = re.search(r"(.*)(\d\.\d)", php_path).group(2)
      logging.info(f"setupPHP(): PHP config test passed successfully: {result.stderr.strip()}. Reloading PHP, version {phpVer}...")
      result = subprocess.run(["sudo","systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
      if  result.returncode == 0:
        logging.info(f"setupPHP(): PHP reloaded successfully.")
        return True
      else:
        logging.error(f"setupPHP(): PHP reload failed!. {result.stderr}")
        return False
    else:
      logging.error(f"setupPHP(): Error while reloading PHP: {result.stdout.strip()} {result.stderr.strip()}")
      return False
  except Exception as msg:
    logging.error(f"setupPHP(): Error while configuring PHP. Error: {msg}")
    return False

def setupNginx(file: str,has_subdomain: str = "---") -> bool:
  """Setups Nginx config from the template and reloads the daemon"""
  try:
    logging.info(f"setupNginx(): Configuring Nginx...Preparing certificates")
    crt_path = current_app.config.get("NGX_CRT_PATH","")
    www_user = current_app.config.get("WWW_USER","")
    www_group = current_app.config.get("WWW_GROUP","")
    web_folder = current_app.config.get("WEB_FOLDER","")
    path_av = current_app.config.get("NGX_SITES_PATHAV","")
    path_en = current_app.config.get("NGX_SITES_PATHEN","")
    if not crt_path or not www_user or not www_group or not web_folder or not path_av or not path_en:
      logging.error("setupNginx(): Some important variable to start the function is empty!")
      send_to_telegram("setupNginx(): Some important variable to start the function is empty!",f"🚒Provision job error({functions.variables.JOB_ID}):")
      return False
    #if we get a TLD - use standart file name
    if has_subdomain == "---":
      filename = os.path.basename(file)[:-4]
      crt_filename = filename
    else:
      filename = os.path.basename(file)[:-4]
      crt_filename = has_subdomain
      logging.info(f"setupNginx(): We have a subdomain there...")
    #setting correct rights to our newly created certificates
    os.chmod(crt_path+crt_filename+".crt", 0o600)
    os.chmod(crt_path+crt_filename+".key", 0o600)
    #preparing folder
    os.system(f"sudo chown -R {www_user}:{www_group} {os.path.join(web_folder,filename)}")
    logging.info(f"setupNginx(): Folders and files ownership of {os.path.join(web_folder,filename)} changed to {www_user}:{www_group}")
    #preparing redirects config
    if os.path.exists("/etc/nginx/additional-configs/"):
      redirect_file = os.path.join("/etc/nginx/additional-configs/","301-" + filename + ".conf")
      with open(redirect_file, 'w',encoding='utf8') as fileRedir:
        fileRedir.write("")
      logging.info(f"setupNginx(): File for redirects {redirect_file} created successfully!")
    else:
      logging.error(f"setupNginx(): Folder /etc/nginx/additional-configs is not exists!")
      send_to_telegram(f"Folder /etc/nginx/additional-configs is not exists!",f"🚒Provision job warning({functions.variables.JOB_ID}):")
    #running template config according to our domain or its subdomain for crtificates
    if has_subdomain == "---":
      config = create_nginx_config(filename,"---")
    else:
      config = create_nginx_config(filename,crt_filename)
    with open(os.path.join(path_av,filename), 'w',encoding='utf8') as fileC:
      fileC.write(config)
    logging.info(f"setupNginx(): Nginx config {os.path.join(path_av,filename)} created")
    if not os.path.exists(os.path.join(path_en,filename)):
      os.symlink(os.path.join(path_av,filename),os.path.join(path_en,filename))
    logging.info(f"setupNginx(): Nginx config {os.path.join(path_en,filename)} symlink created")
    result = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
    if  re.search(r".*test is successful.*",result.stderr) and re.search(r".*syntax is ok.*",result.stderr):
      logging.info(f"setupNginx(): Nginx config test passed successfully: {result.stderr.strip()}. Reloading Nginx...")
      result = subprocess.run(["sudo","systemctl","restart","nginx"], text=True, capture_output=True)
      if  re.search(r".*started.*",result.stderr):
        logging.info(f"setupNginx(): Nginx restarted successfully. Result: {result.stderr.strip()}")
      if not setupPHP(file):
        logging.error("setupNginx(): setupPHP() function returned an error!")
        return False
    else:
      logging.error(f"setupNginx(): Error while restarting Nginx: {result.stderr.strip()}")
      return False
    return True
  except Exception as msg:
    logging.error(f"setupNginx(): Error while configuring Nginx: {msg}")
    return False

def unZip_3(file: str, selected_account: str, selected_server: str, realname: str) -> bool:
  """Step3: unzips the given archive to its new folder"""
  try:
    #Getting the site name from the archive name
    filename = os.path.basename(file)[:-4]
    #Getting the full path to the folder
    finalPath = os.path.join(current_app.config.get("WEB_FOLDER"),filename)
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
  send_to_telegram(f"Archive #{functions.variables.JOB_COUNTER} of {functions.variables.JOB_TOTAL}: {file}",f"🎢Provisoin job start({functions.variables.JOB_ID}):")
  try:
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
      send_to_telegram(f"Job #{functions.variables.JOB_COUNTER} error: Looks like public/ folder is absent in {file}",f"🚒Provision job error:")
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
    path = Path(__file__).resolve().parents[1]
    files = glob.glob(os.path.join(path, "*.zip"))
    for file in files:
      if not checkZip_2(file,selected_account,selected_server,realname):
        logging.error("findZip_1(): checkZip_2() function returned an error!")
        return False
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
    path = Path(__file__).resolve().parents[1]
    files = glob.glob(os.path.join(path,"*.zip"))
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

def start_autoprovision(domain: str, selected_account: str, selected_server: str, template: str, realname: str, its_not_a_subdomain: bool = False):
  """Starts main autoprovision process to deploy site from a git repo,DNS records and certificates automatically"""
  try:
    logging.info(f"---------------------------Starting automatic deploy for site {domain}  by {realname}----------------------------")
    logging.info(f"Cloudflare account: {selected_account}, Server: {selected_server}")
    finalPath = os.path.join(current_app.config.get("WEB_FOLDER"),domain)
    functions.variables.JOB_ID = f"Autoprovision"
    #First of all starting DNS and certificates check and setup procedure
    if cloudflare_certificate(domain,selected_account,selected_server,its_not_a_subdomain):
      os.makedirs(finalPath)
      logging.info(f"New directory {finalPath} created")
      os.chdir(finalPath)
      logging.info(f"We are in {finalPath}")
      result = subprocess.run(["sudo","git","clone",f"{template}","."], capture_output=True, text=True)
      if result.returncode != 0:
        logging.error(f"Error while git clone command: {result.stderr}")
        finishJob("",domain,selected_account,selected_server,emerg_shutdown=True)
        flash('Помилка при клонуванні із гіт репозиторію!','alert alert-danger')
        return False
      logging.info("Git clone done successfully!")
      result2 = subprocess.run(["sudo","git","config","--global", "--add", "safe.directory", f"{finalPath}"], capture_output=True, text=True)
      if result2.returncode != 0:
        logging.error(f"Error while git add safe.directory: {result.stderr}")
      logging.info("Git add safe directory done successfully!")
      #prepare subdomain functions
      if its_not_a_subdomain:
        has_subdomain = "---"
        logging.info("start_autoprovision(): we have forced parameter not_a_subdomain - passing it to setupNginx()")
      else:
        d = tld(domain)
        if bool(d.subdomain):
          has_subdomain = f"{d.domain}.{d.suffix}"
          logging.info("start_autoprovision(): we have detected a subdomain - passing it to setupNginx()")
        else:
          has_subdomain = "---"
          logging.info("start_autoprovision(): we have not detected a subdomain - passing it to setupNginx()")
      #we add .zip to domain for backward compatibility with another functions of the system
      if not setupNginx(domain+".zip",has_subdomain):
        logging.error("start_autoprovision(): setupNginx() function returned an error!")
        finishJob("",domain,selected_account,selected_server,emerg_shutdown=True)
        return False
      finishJob("",domain,selected_account,selected_server)
      return True
  except Exception as msg:
    logging.error(f"start_autoprovision() error: {msg}")
    return False
