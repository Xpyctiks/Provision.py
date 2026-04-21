import logging
import os
import subprocess
import re
import shutil
import idna
from flask import current_app,flash,redirect
from functions.send_to_telegram import send_to_telegram
from functions.config_templates import create_nginx_config
from flask_login import current_user
from db.db import db
from db.database import *
from functions.cli_management import del_account,del_owner
from functions.cache_func import page_cache

def delete_site(sitename: str) -> bool:
  """Site action: full delete selected site. Requires "sitename" as a parameter"""
  error_message = ""
  try:
    logging.info(f"-----------------------Starting single site delete: {sitename} by {current_user.realname}-----------------")
    path_en = current_app.config.get("NGX_SITES_PATHEN","")
    path_av = current_app.config.get("NGX_SITES_PATHAV","")
    # php_pool = current_app.config.get("PHP_POOL","")
    # php_path = current_app.config.get("PHPFPM_PATH","")
    web_folder = current_app.config.get("WEB_FOLDER","")
    if not path_en or not path_av  or not web_folder: #or not php_pool or not php_path:
      logging.error(f"delete_site(): Some important variable is empty!")
      return False
    #-------------------------Delete Nginx site config
    ngx_en = os.path.join(path_en,sitename)
    ngx_av = os.path.join(path_av,sitename)
    #delete in nginx/sites-enabled
    if os.path.islink(ngx_en):
      os.unlink(ngx_en)
      logging.info(f"delete_site(): Nginx {ngx_en} deleted successfully")
    else:
      logging.info(f"delete_site(): Nginx {ngx_en} is already deleted")
    #delete in nginx/sites-available
    if os.path.isfile(ngx_av):
      os.unlink(ngx_av)
      logging.info(f"delete_site(): Nginx {ngx_av} deleted successfully")
    else:
      logging.info(f"delete_site(): Nginx {ngx_av} is already deleted")
    result1 = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
    if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
      result2 = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
      if  re.search(r".*started.*",result2.stderr):
        logging.info(f"delete_site(): Nginx reloaded successfully. Result: {result2.stderr.strip()}")
      else:
        logging.error(f"delete_site(): Nginx reload failed!. {result2.stderr}")
        error_message += f"Error while reloading Nginx: {result1.stderr.strip()}\n"
    else:
      logging.error(f"delete_site(): Error while Nginx config test: {result1.stderr.strip()}")
      error_message += f"Помилка тестування конфігурації Nginx: {result1.stderr.strip()}\n"
    # #------------------------Delete in php pool.d/
    # php = os.path.join(php_pool,sitename+".conf")
    # php_dis = os.path.join(php_pool,sitename+".conf.disabled")
    # if os.path.isfile(php):
    #   os.unlink(php)
    #   logging.info(f"delete_site(): PHP config {php} deleted successfully")
    # elif os.path.isfile(php_dis):
    #   os.unlink(php_dis)
    #   logging.info(f"delete_site(): PHP config {php_dis} deleted successfully")
    # else:
    #   logging.info(f"delete_site(): PHP config {php} already deleted")
    # result2 = subprocess.run(["sudo", php_path, "-t"], capture_output=True, text=True)
    # if  re.search(r".*test is successful.*",result2.stderr):
    # #gettings digits of PHP version from the path to the PHP-FPM
    #   phpVer = re.search(r"(.*)(\d\.\d)",php_path).group(2)
    #   logging.info(f"delete_site(): PHP config test passed successfully: {result2.stderr.strip()}. Reloading PHP, version {phpVer}...")
    #   result3 = subprocess.run(["sudo","systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
    #   if  result3.returncode == 0:
    #     logging.info(f"delete_site(): PHP reloaded successfully.")
    #   else:
    #     logging.error(f"delete_site(): PHP reload failed!. {result3.stderr}")
    #     error_message += f"Помилка при перезавантаженні PHP: {result2.stderr.strip()}\n"
    # else:
    #   logging.error(f"delete_site(): Error while PHP config. test: {result2.stderr.strip()}")
    #   error_message += f"Помилка тестування конфігурації PHP: {result2.stderr.strip()}\n"
    #--------------Delete of the site folder
    path = os.path.join(web_folder,sitename)
    if not os.path.isdir(path):
      logging.error(f"delete_site(): Site folder delete error - {path} - is not a directory!")
      error_message += f"Помилка видалення папки сайту - {path} - це не є папка!\n"
    directory_path = os.path.abspath(path)
    if directory_path in ('/', '/home', '/root', '/etc', '/var', '/tmp', os.path.expanduser("~")):
      logging.error(f"delete_site(): Site folder delete error: {path} - too dangerous directory is selected!")
      error_message += f"Помилка видалення папки сайту: {path} - обрана занадто опасна папка!\n"
      return False
    status = 0
    for filename in os.listdir(path):
      file_path = os.path.join(path, filename)
      try:
        if os.path.isfile(file_path) or os.path.islink(file_path):
          os.unlink(file_path)
        elif os.path.isdir(file_path):
          shutil.rmtree(file_path)
      except Exception as msg:
        logging.error(f"delete_site(): File of folder {file_path}: {msg}")
        status = 1
    #if we have errors during delete procedure - send an alert
    if status > 0:
      logging.error(f"delete_site(): Root folder {path} is not deleted because some files or folders are still inside.")
      error_message += f"Root folder {path} is not deleted because some files or folders are still inside!"
    else:
      os.rmdir(path)
      logging.info(f"delete_site(): Root folder {path} deleted successfully!")
    #deleting site from the owner table in the database
    del_owner(sitename,False)
    #deleting link between domain and its Cloudflare account from the database
    del_account(sitename,False)
    #final check of the results
    if len(error_message) > 0:
      error_message += f"Сайт {sitename} видалено, але з помилками!\n"
      flash(error_message, 'alert alert-danger')
      return False
    else:
      flash(f"Сайт {sitename} успішно видалено", 'alert alert-success')
      logging.info(f"-----------------------Site deletion of {sitename} is finished-----------------")
      return True
  except Exception as msg:
    logging.error(f"delete_site(): Error while site delete. Error: {msg}")
    return False

def del_selected_sites(sitename: str,delArray: list) -> bool:
  """Function to bunch process of sites deletion. Requires "delArray" as a parameter"""
  try:
    logging.info(f"-----------------------Bunch sites deletion by {current_user.realname}-----------------")
    logging.info(delArray)
    message = ""
    #starting deletion procedure one by one
    for i, curr_site in enumerate(delArray,1):
      if delete_site(curr_site):
        message += f"[✅] Cайт {curr_site} успішно видалено!\n"
        logging.info(f"del_selected_sites(): Site {curr_site} deleted successfully!")
      else:
        message += f"[❌] Помилка при видаленні {curr_site} - дивіться логи.\n"
        logging.error(f"del_selected_sites(): Site {curr_site} deletion error!")
    flash(message,'alert alert-info')
    logging.info(f"-----------------------Bunch sites deletion by {current_user.realname} is done!-----------------")
    return True
  except Exception as msg:
    logging.error(f"del_selected_sites(): Error while site disable. Error: {msg}")
    return False

def disable_site(sitename: str) -> bool:
  """Site action: disables the selected site and applies changes immediately. Requires "sitename" as a parameter"""
  error_message = ""
  try:
    logging.info(f"-----------------------Starting site disable: {sitename} by {current_user.realname}-----------------")
    # php_pool = current_app.config.get("PHP_POOL","")
    php_path = current_app.config.get("PHPFPM_PATH","")
    path_en = current_app.config.get("NGX_SITES_PATHEN","")
    if not php_path or not path_en: # or not php_pool:
      logging.error(f"disable_site(): Some important variable is empty!")
      return False
    #disable Nginx site
    ngx = os.path.join(path_en,sitename)
    if os.path.isfile(ngx) or os.path.islink(ngx):
      os.unlink(ngx)
      logging.info(f"disable_site(): Nginx symlink {ngx} removed")
      result1 = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
      if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
        result2 = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
        if  re.search(r".*started.*",result2.stderr):
          logging.info(f"disable_site(): Nginx reloaded successfully. Result: {result2.stderr.strip()}")
        else:
          logging.error(f"disable_site(): Nginx reload failed!. {result2.stderr}")
          error_message += f"Помилка при перезавантаженні веб сервера Nginx: {result1.stderr.strip()}"
      else:
        logging.error(f"disable_site(): Error while Nginx config test: {result1.stderr.strip()}")
        error_message += f"Помилка при тестуванні конфігурації веб сервера Nginx: {result1.stderr.strip()}"
    else:
      logging.error(f"disable_site(): Nginx site disable error - symlink {ngx} is not exist")
      error_message += f"Помилка при перезавантаженні веб сервера Nginx"
    # #php disable
    # php = os.path.join(php_pool,sitename+".conf")
    # if os.path.isfile(php) or os.path.islink(php):
    #   os.rename(php,php+".disabled")
    #   result2 = subprocess.run(["sudo", php_path, "-t"], capture_output=True, text=True)
    #   if  re.search(r".*test is successful.*",result2.stderr):
    #   #gettings digits of PHP version from the path to the PHP-FPM
    #     phpVer = re.search(r"(.*)(\d\.\d)",php_path).group(2)
    #     logging.info(f"disable_site(): PHP config test passed successfully: {result2.stderr.strip()}. Reloading PHP, version {phpVer}...")
    #     result3 = subprocess.run(["sudo","systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
    #     if  result3.returncode == 0:
    #       logging.info(f"disable_site(): PHP reloaded successfully.")
    #     else:
    #       logging.error(f"disable_site(): PHP reload failed!. {result3.stderr}")
    #       error_message += f"Помилка при перезавантаженні PHP: {result2.stderr.strip()}"
    #   else:
    #     logging.error(f"disable_site(): Error while test PHP config: {result2.stderr.strip()}")
    #     error_message += f"Помилка при тестуванні конфігурації PHP: {result2.stderr.strip()}"
    # else:
    #   logging.error(f"disable_site(): PHP site conf. disable error - symlink {php} is not exist")
    #   error_message += f"Помилка при перезавантаженні PHP"
    logging.info(f"-----------------------Site disable of {sitename} is finished-----------------")
    if len(error_message) > 0:
      flash(error_message, 'alert alert-danger')
      return False
    else:
      flash(f"Сайт {sitename} успішно деактивовано.", 'alert alert-success')
      return True
  except Exception as msg:
    logging.error(f"disable_site(): global error: {msg}")
    return False

def enable_site(sitename: str) -> bool:
  """Site action: enables the selected site and applies changes immediately. Requires "sitename" as a parameter"""
  error_message = ""
  try:
    logging.info(f"-----------------------Starting site enable: {sitename} by {current_user.realname}-----------------")
    #enable Nginx site
    path_en = current_app.config.get("NGX_SITES_PATHEN","")
    path_av = current_app.config.get("NGX_SITES_PATHAV","")
    # php_pool = current_app.config.get("PHP_POOL","")
    # php_path = current_app.config.get("PHPFPM_PATH","")
    web_folder = current_app.config.get("WEB_FOLDER","")
    if not path_en or not path_av or not web_folder: #or not php_pool or not php_path :
      logging.error(f"enable_site(): Some important variable is empty!")
      return False
    ngx_en = os.path.join(path_en,sitename)
    ngx_av = os.path.join(path_av,sitename)
    # php_cnf = os.path.join(php_pool,sitename+".conf")
    # php_cnf_dis = os.path.join(php_pool,sitename+".conf.disabled")
    #First of all, check does the important folders exist
    if not os.path.exists(path_en):
      logging.error(f"enable_site(): root folder {path_en} does not exists!")
      error_message += f"Важлива папка {path_en} не існує! не можу продовжувати..."
    elif not os.path.exists(path_av):
      logging.error(f"enable_site(): root folder {path_av} does not exists!")
      error_message += f"Важлива папка {path_av} не існує! не можу продовжувати..."
    # elif not os.path.exists(php_pool):
    #   logging.error(f"enable_site(): root folder {php_pool} does not exists!")
    #   error_message += f"Важлива папка {php_pool} не існує! не можу продовжувати..."
    if error_message != "":
      flash(error_message, 'alert alert-danger')
      return False
    #--------------------check if there is no active symlink to the site
    if not os.path.exists(ngx_av):
      config = create_nginx_config(sitename)
      with open(ngx_av, 'x',encoding='utf8') as fileC:
        fileC.write(config)
        logging.info(f"enable_site(): Nginx config recreated for {sitename} because there was none of it")
        os.symlink(ngx_av,ngx_en)
        logging.info(f"enable_site(): Symlink {ngx_av} -> {ngx_en} created.")
    #in sites-enabled is not exists, but in sites-available it is
    if not os.path.islink(ngx_en) and os.path.isfile(ngx_av):
      os.symlink(ngx_av,ngx_en)
      logging.info(f"enable_site(): Symlink {ngx_av} -> {ngx_en} created.")
    #exists everywhere
    elif os.path.islink(ngx_en) and os.path.isfile(ngx_av):
      logging.info(f"enable_site(): Symlink {ngx_av} -> {ngx_en} already exists. Skipping this step.")
    # #--------------------check if there is no active php config
    # if not os.path.exists(php_cnf) and not os.path.exists(php_cnf_dis):
    #   config = create_php_config(sitename)
    #   with open(php_cnf, 'w',encoding='utf8') as fileC:
    #     fileC.write(config)
    #   logging.info(f"enable_site(): PHP config {os.path.join(php_pool,sitename)} recreated because it wasn't exist")
    # #site.com.conf.disabled exists and site.com.conf is not
    # if not os.path.isfile(php_cnf) and os.path.isfile(php_cnf_dis):
    #   os.rename(php_cnf_dis,php_cnf)
    #   logging.info(f"enable_site(): Php config renamed from {php_cnf_dis} -> {php_cnf}.")
    # elif os.path.isfile(php_cnf) and not os.path.isfile(php_cnf_dis):
    #   logging.info(f"enable_site(): Php config already exists and is active. Skipping this step.")
    #start of checks - nginx
    result1 = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
    if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
      result2 = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
      if  re.search(r".*started.*",result2.stderr):
        logging.info(f"enable_site(): Nginx reloaded successfully. Result: {result2.stderr.strip()}")
      else:
        logging.error(f"enable_site(): Nginx reload failed!. {result2.stderr}")
        error_message += f"Помилка перезавантаження Nginx: {result2.stderr}"
    else:
      logging.error(f"enable_site(): Error while Nginx config. test: {result1.stderr.strip()}")
      error_message += f"Помилка при тестуванні конфігурації веб сервера Nginx: {result1.stderr.strip()}"
    # #start of checks - php
    # result2 = subprocess.run(["sudo", php_path, "-t"], capture_output=True, text=True)
    # if  re.search(r".*test is successful.*",result2.stderr):
    # #gettings digits of PHP version from the path to the PHP-FPM
    #   phpVer = re.search(r"(.*)(\d\.\d)",php_path).group(2)
    #   logging.info(f"enable_site(): PHP config test passed successfully: {result2.stderr.strip()}. Reloading PHP, version {phpVer}...")
    #   result3 = subprocess.run(["sudo","systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
    #   if  result3.returncode == 0:
    #     logging.info(f"enable_site(): PHP reloaded successfully.")
    #   else:
    #     logging.error(f"enable_site(): PHP reload failed!. {result3.stderr}")
    #     error_message += f"Помилка при перезавантаженні PHP: {result2.stderr.strip()}"
    # else:
    #   logging.error(f"Error testing configuration of PHP: {result2.stderr.strip()}")
    #   error_message += f"Помилка тесту конфігурації PHP: {result2.stderr.strip()}"
    logging.info(f"-----------------------Site enable of {sitename} is finished-----------------")
    if len(error_message) > 0:
      flash(error_message, 'alert alert-danger')
      return False
    else:
      flash(f"Сайт {sitename} успішно активовано", 'alert alert-success')
      return True
  except Exception as msg:
    logging.error(f"enable_site(): global error {msg}")
    return False
  
def del_redirect(location: str,sitename: str, callable: int = 0) -> bool:
  """Redirect-manager page: deletes one redirect,selected by Delete button on it.Don't applies changes immediately. Requires redirect "from location" and "sitename" as a parameter"""
  try:
    conf_dir = current_app.config.get("NGX_ADD_CONF_DIR","")
    if not conf_dir:
      logging.error(f"del_redirect(): conf_dir variable is empty!")
      return False
    if callable == 0:
      logging.info(f"-----------------------Delete single redirect for {sitename} by {current_user.realname}-----------------")
    else:
      #creating counter to count how much redirects were processed from the general count
      counter = 1
    file301 = os.path.join(conf_dir,"301-" + sitename + ".conf")
    #get into the site's config and uncomment one string
    if os.path.exists(file301):
      logging.info(f"del_redirect(): Starting delete operation for {location}...")
      with open(file301, "r", encoding="utf-8") as f:
        content = f.read()
      escaped_path = re.escape(location.strip())
      pattern = re.compile(
        rf'location\s+.\s+{escaped_path}\s*{{.*?}}[\r\n]*',
        re.DOTALL
      )
      new_content, count = pattern.subn('', content)
      if count == 0:
        logging.error(f"del_redirect(): Path {location} was not found in {file301} for site {sitename}")
        flash(f"Path {location} was not found in {file301} for site {sitename}",'alert alert-danger')
        return False
      else:
        with open(file301, "w", encoding="utf-8") as f:
          f.write(new_content)
        logging.info(f"del_redirect(): Redirect path {location} of {sitename} was deleted successfully")
        #if callable=0 that means there is single deletion.Creating a marker file after we have done.
        if callable == 0:
          #here we create a marker file which makes "Apply changes" button to glow yellow
          if not os.path.exists("/tmp/provision.marker"):
            with open("/tmp/provision.marker", 'w',encoding='utf8') as file3:
              file3.write("")
          logging.info("del_redirect(): Marker file for Apply button created")
          logging.info(f"-----------------------single redirect deleted---------------------------")
          return True
        if callable >= counter:
          #here we create a marker file which makes "Apply changes" button to glow yellow
          if not os.path.exists("/tmp/provision.marker"):
            with open("/tmp/provision.marker", 'w',encoding='utf8') as file3:
              file3.write("")
          logging.info("del_redirect(): Marker file for Apply button created")
          counter = counter + 1
        return True
    else:
      logging.error(f"del_redirect(): Error delete redirects of {sitename}: {file301} is not exists,but it is not possible because you are deleting from it!")
      flash(f"Error delete redirects of {sitename}: {file301} is not exists!", 'alert alert-danger')
      return False
  except Exception as msg:
    logging.error(f"del_redirect(): global error {msg}")
    return False

def del_selected_redirects(array: list,sitename: str) -> bool:
  """Redirect-manager page: deletes array of selected by checkboxes redirects.Don't applies changes immediately. Requires redirect locations array and "sitename" as a parameter"""
  try:
    logging.info(f"-----------------------Delete selected bulk redirects for {sitename} by {current_user.realname}-----------------")
    logging.info(array)
    message = ""
    counter = len(array)
    for i, curr_redir in enumerate(array,1):
      if del_redirect(curr_redir,sitename,counter):
        logging.info(f"del_selected_redirects(): Redirect path {curr_redir} of {sitename} was deleted successfully")
        message += f"Редирект {curr_redir} успішно видалено!\n"
      else:
        message += f"Помилка видалення редиректу {curr_redir}!\n"
        logging.info(f"Redirect path {curr_redir} of {sitename} deletion error!")
        #here we create a marker file which makes "Apply changes" button to glow yellow
        if not os.path.exists("/tmp/provision.marker"):
          with open("/tmp/provision.marker", 'w',encoding='utf8') as file3:
            file3.write("")
        logging.info("del_selected_redirects(): Marker file for Apply button created")
    logging.info(f"-----------------------Selected bulk redirects deleted---------------------------")
    return True
  except Exception as msg:
    logging.error(f"del_selected_redirects(): Global Error: {msg}")
    return False

def applyChanges(sitename: str) -> bool:
  """Redirect-manager page: applies all changes, made to redirect config files"""
  logging.info(f"-----------------------Applying changes in Nginx by {current_user.realname}-----------------")
  result1 = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
  if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
    result2 = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
    if  re.search(r".*started.*",result2.stderr):
      logging.info(f"applyChanges(): Nginx reloaded successfully. Result: {result2.stderr.strip()}")
      flash(f"Нові зміни застосовані. Веб сервер Nginx перезавантажений.",'alert alert-success')
      logging.info(f"-----------------------Applying changes in Nginx finished-----------------")
      if os.path.exists("/tmp/provision.marker"):
        os.unlink("/tmp/provision.marker")
      return True
    else:
      logging.info(f"applyChanges(): Nginx reload error!. Result: {result2.stderr.strip()}")
      flash(f"Помилка застосування нової конфігурації веб сервером!.",'alert alert-danger')
      logging.info(f"-----------------------Applying changes in Nginx finished with error!-----------------")
      return False
  else:
    logging.error(f"applyChanges(): Error reloading Nginx: {result1.stderr.strip()}")
    flash(f"Помилка застосування нової конфігурації веб сервером! {result1.stderr.strip()}",'alert alert-danger')
    logging.info(f"-----------------------Applying changes in Nginx finished-----------------")
    return False

def count_redirects(site: str) -> str:
  """This function is counts current available redirects for every site while general site list is loading"""
  try:
    with open(os.path.join(current_app.config.get("NGX_ADD_CONF_DIR",""),"301-"+site+".conf"), "r", encoding="utf-8") as f:
      count = int(sum(1 for _ in f) / 3)
      return str(count)
  except Exception:
    return "0"

def makePull(domain: str, pullArray: list = []) -> bool:
  """Root page: makes git pull to update the site code. Can receive single domain name or a list of."""
  try:
    web_folder = current_app.config.get("WEB_FOLDER","")
    www_user = current_app.config.get("WWW_USER","")
    www_group = current_app.config.get("WWW_GROUP","")
    message = ""
    if not web_folder or not www_group or not www_user:
      logging.error(f"makePull(): web_folder/www_user/www_group variable is empty!")
      return False
    #When a single site pull
    if len(pullArray) == 0:
      logging.info(f"-----------------------Single git pull for {domain} by {current_user.realname}-----------------")
      path = os.path.join(web_folder,domain)
      if os.path.exists(path):
        os.chdir(path)
        logging.info(f"Successfully got into {path}")
        result_pre = subprocess.run(["sudo","git","stash"], capture_output=True, text=True)
        if result_pre.returncode != 0:
          logging.error(f"makePull(): Git stash for {domain} returned error: {result_pre.stderr}")
          message += f"[❌] Помилка stash перед оновленням коду для {domain}\n"
        else:
          logging.info(f"makePull(): Git stash done...")
        result = subprocess.run(["sudo","git","pull"], capture_output=True, text=True)
        if result.returncode != 0:
          logging.error(f"Git pull for {domain} returned error: {result.stderr}")
          flash(f"Помилка оновлення коду із репозиторію {path}: {result.stderr}.",'alert alert-danger')
          logging.info(f"-----------------------Single git pull for {domain} by {current_user.realname} finished---------------------------")
          return False
        else:
          #setting correct rights again after pull to all files and folders
          os.system(f"sudo chown -R {www_user}:{www_group} {path}")
          logging.info(f"makePull(): Rights after pull set again to {www_user}:{www_group} inside {path}")
          #after pull is completed do migration db tasks
          if os.path.exists("bin/"):
            result3 = subprocess.run(["php", "bin/migrate.php"], capture_output=True, text=True)
            if  result3.returncode == 0:
              logging.info(f"DB migration done successfully!")
            else:
              logging.error(f"DB migration error for {domain}: {result3.stderr}")
              flash(f"Помилка оновлення бази для {domain} після пулу!.",'alert alert-warning')
              return False
          else:
            logging.error(f"DB migration error for {domain}: bin/ folder not found. we are in {os.curdir}")
            flash(f"Помилка оновлення бази для {domain} після пулу!.",'alert alert-warning')
            return False
          flash(f"Код для сайту {domain} успішно оновлено із репозиторію!.",'alert alert-success')
          logging.info(f"Git pull for {domain} done successfully!")
          logging.info(f"-----------------------Single git pull for {domain} by {current_user.realname} finished---------------------------")
          return True
      else:
        logging.error(f"Git pull for {domain} returned error: site folder {path} not exists!")
        flash(f"Помилка оновлення коду із репозиторію: папка {domain} чомусь не існує!",'alert alert-danger')
        logging.info(f"-----------------------Single git pull for {domain} by {current_user.realname} finished---------------------------")
        return False
    #When a list of sites to pull received
    else:
      logging.info(f"-----------------------Bunch git pull by {current_user.realname}-----------------")
      logging.info(pullArray)
      message = ""
      #starting pull procedure one by one
      for i, curr_domain in enumerate(pullArray,1):
        path = os.path.join(web_folder,curr_domain)
        if os.path.exists(path):
          os.chdir(path)
          logging.info(f"makePull(): Successfully got into {path}")
          result_pre = subprocess.run(["sudo","git","stash"], capture_output=True, text=True)
          if result_pre.returncode != 0:
            logging.error(f"makePull(): Git stash for {domain} returned error: {result.stderr}")
            message += f"[❌] Помилка stash перед оновленням коду для {curr_domain}\n"
          else:
            logging.info(f"makePull(): Git stash done...")
          result = subprocess.run(["sudo","git","pull"], capture_output=True, text=True)
          if result.returncode != 0:
            logging.error(f"makePull(): Git pull for {domain} returned error: {result.stderr}")
            send_to_telegram(f"Git pull error for site {curr_domain}: {result.stderr}",f"🚒Provision pull by {current_user.realname}:")
            message += f"[❌] Помилка оновлення коду для {curr_domain}\n"
          else:
            message += f"[✅] Код {curr_domain} успішно оновлено!\n"
            logging.info(f"makePull(): Git pull for {curr_domain} done successfully!")
            #setting correct rights again after pull to all files and folders
            os.system(f"sudo chown -R {www_user}:{www_group} {path}")
            logging.info(f"makePull(): Rights after pull set again to {www_user}:{www_group} inside {path}")
            #after pull is completed do migration db tasks
            if os.path.exists("bin/"):
              result3 = subprocess.run(["php", "bin/migrate.php"], capture_output=True, text=True)
              if  result3.returncode == 0:
                logging.info(f"makePull(): DB migration for {curr_domain} done successfully!")
              else:
                logging.error(f"makePull(): DB migration error: {result3.stderr}")
                send_to_telegram(f"DB migration for {curr_domain} error,check logs!",f"🚒Provision pull by {current_user.realname}:")
            else:
              logging.error(f"makePull(): DB migration error for {curr_domain}: bin/ folder not found. we are in {os.curdir}")
              send_to_telegram(f"DB migration error for {curr_domain}: bin/ folder not found. we are in {os.curdir}",f"🚒Provision pull by {current_user.realname}:")
      flash(message,'alert alert-info')
      logging.info(f"-----------------------Bunch git pull by {current_user.realname} is done!-----------------")
      return True
  except Exception as msg:
    logging.error(f"Makepull(): global Error: {msg}")
    logging.info(f"-----------------------Single git pull for {domain} by {current_user.realname} finished---------------------------")
    return False

def normalize_domain(domain: str):
  """Function to check and filter a domain, which is got as GET parameter"""
  DOMAIN_RE = re.compile(r'^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$')
  domain = domain.strip().lower().removeprefix("https://").removeprefix("http://").rstrip("/")
  try:
    domain = idna.encode(domain).decode()
  except idna.IDNAError:
    logging.error(f"Invalid IDNA domain {domain}!")
    flash(f"Помилка перевірки змінної домена для ДНС валідації, дивіться логи!", 'alert alert-danger')
    return redirect("/",301)
  if not DOMAIN_RE.fullmatch(domain):
    logging.error(f"Invalid domain format {domain}!")
    flash(f"Помилка перевірки змінної домена для ДНС валідації, дивіться логи!", 'alert alert-danger')
    return redirect("/",301)
  return domain

def link_domain_and_account(domain: str, account: str) -> bool:
  """Adds an account info for the given domain to DB for future simple actions with"""
  logging.info(f"Linking domain {domain} with account {account} in DB...")
  try:
    #Check if the account with given email exists
    acc = Cloudflare.query.filter_by(account=account).first()
    if not acc:
      logging.error(f"link_domain_and_account(): Error! Cloudflare account with the given email {account} is not exists in our database! But this is not possible!")
      send_to_telegram(f"link_domain_and_account(): Cloudflare account with the given email {account} is not exists in our database! But this is not possible!",f"🚒Provision error by {current_user.realname}:")
      return False
    #Check if the given account is already linked with the given domain
    check = Domain_account.query.filter_by(domain=domain).all()
    for i, c in enumerate(check,1):
      if c.account == account:
        logging.info(f"link_domain_and_account(): Domain {domain} is already linked with account {account}!")
        return True
    #Else start addition procedure
    new_account = Domain_account(domain=domain,account=account)
    db.session.add(new_account)
    db.session.commit()
    logging.info(f"link_domain_and_account(): Domain domain now is linked to account {account}!")
    return True
  except Exception as err:
    logging.error(f"link_domain_and_account() general error: {err}")
    return False

def is_admin():
  """Adds Admin panel option to the main menu if user is admin"""
  user = User.query.filter_by(realname=current_user.realname).first()
  if user:
    rights = user.rights
    if rights == 255:
      return '<li><a class="dropdown-item" href="/admin_panel" class="btn btn-secondary">🎮Панель адміністрування</a></li>'
    else:
      return ""
  else:
    return ""

def clearCache() -> bool:
  """GET request: clears web page cache"""
  try:
    CACHE_KEY = f"user:{current_user.realname}"
    page_cache.delete(CACHE_KEY)
    return True
  except Exception as err:
    logging.error(f"clearCache(): general error by {current_user.realname}: {err}")
    return False
