import logging,os,subprocess,asyncio,re,shutil
from flask import current_app,flash,redirect
from functions.send_to_telegram import send_to_telegram
from functions.config_templates import create_nginx_config, create_php_config
from flask_login import current_user
import functions.variables
from db.db import db
from db.database import *

def delete_site(sitename: str) -> bool:
    """Site action: full delete selected site. Requires "sitename" as a parameter"""
    error_message = ""
    try:
        logging.info(f"-----------------------Starting single site delete: {sitename} by {current_user.realname}-----------------")
        #-------------------------Delete Nginx site config
        ngx_en = os.path.join(current_app.config["NGX_SITES_PATHEN"],sitename)
        ngx_av = os.path.join(current_app.config["NGX_SITES_PATHAV"],sitename)
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
                logging.error(f"Nginx reload failed!. {result2.stderr}")
                asyncio.run(send_to_telegram(f"Error while reloading Nginx",f"🚒Provision job error({functions.variables.JOB_ID}):"))
        else:
            logging.error(f"Error while reloading Nginx: {result1.stderr.strip()}")
            error_message += f"Error while reloading Nginx: {result1.stderr.strip()}\n"
            asyncio.run(send_to_telegram(f"Error while reloading Nginx",f"🚒Provision site delete error({sitename}):"))
        #------------------------Delete in php pool.d/
        php = os.path.join(current_app.config["PHP_POOL"],sitename+".conf")
        php_dis = os.path.join(current_app.config["PHP_POOL"],sitename+".conf.disabled")
        if os.path.isfile(php):
            os.unlink(php)
            logging.info(f"PHP config {php} deleted successfully")
        elif os.path.isfile(php_dis):
            os.unlink(php_dis)
            logging.info(f"PHP config {php_dis} deleted successfully")
        else:
            logging.info(f"PHP config {php} already deleted")
        result2 = subprocess.run(["sudo",current_app.config["PHPFPM_PATH"],"-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result2.stderr):
        #gettings digits of PHP version from the path to the PHP-FPM
            phpVer = re.search(r"(.*)(\d\.\d)",current_app.config["PHPFPM_PATH"]).group(2)
            logging.info(f"PHP config test passed successfully: {result2.stderr.strip()}. Reloading PHP, version {phpVer}...")
            result3 = subprocess.run(["sudo","systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
            if  result3.returncode == 0:
                logging.info(f"PHP reloaded successfully.")
            else:
                logging.error(f"PHP reload failed!. {result3.stderr}")
                asyncio.run(send_to_telegram(f"Error while reloading PHP",f"🚒Provision job error({functions.variables.JOB_ID}):"))
        else:
            logging.error(f"Error while reloading PHP: {result2.stderr.strip()}")
            error_message += f"Помилка при перезавантаженні PHP: {result2.stderr.strip()}\n"
            asyncio.run(send_to_telegram(f"Error while reloading PHP",f"🚒Provision site delete error({sitename}):"))
        #--------------Delete of the site folder
        path = os.path.join(current_app.config["WEB_FOLDER"],sitename)
        if not os.path.isdir(path):
            logging.error(f"Site folder delete error - {path} - is not a directory!")
            error_message += f"Помилка видалення папки сайту - {path} - це не є папка!\n"
        directory_path = os.path.abspath(path)
        if directory_path in ('/', '/home', '/root', '/etc', '/var', '/tmp', os.path.expanduser("~")):
            logging.error(f"Site folder delete error: {path} - too dangerous directory is selected!")
            error_message += f"Помилка видалення папки сайту: {path} - обрана занадто опасна папка!\n"
        for filename in os.listdir(path):
            file_path = os.path.join(path, filename)
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        os.rmdir(path)
        logging.info(f"Site folder {path} deleted successfully")
        owner = Ownership.query.filter_by(domain=sitename).first()
        if owner:
            db.session.delete(owner)
            db.session.commit()
            print(f"Ownership for domain \"{sitename}\" deleted successfully!")
            logging.info(f"Ownership for domain \"{sitename}\" deleted successfully!")
        else:
            print(f"Ownership for domain \"{sitename}\" deletion error - no such domain!")
            logging.error(f"Ownership for domain \"{sitename}\" deletion error - no such domain!")
            error_message += f"Помилка видалення власника сайту з бази!\n"
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
        logging.error(f"Error while site delete. Error: {msg}")
        error_message += f"Глобальна помилка видалення сайту: {msg}"
        asyncio.run(send_to_telegram(f"Error: {msg}",f"🚒Provision site delete error({sitename}):"))
        return False

def del_selected_sites(sitename: str,delArray: list) -> bool:
    logging.info(f"-----------------------Bunch sites deletion by {current_user.realname}-----------------")
    logging.info(delArray)
    message = ""
    #starting deletion procedure one by one
    for i, curr_site in enumerate(delArray,1):
        if delete_site(curr_site):
            message += f"[✅] Cайт {curr_site} успішно видалено!\n"
            logging.info(f"Site {curr_site} deleted successfully!")
        else:
            message += f"[❌] Помилка при видаленні {curr_site} - дивіться логи.\n"
            logging.error(f"Site {curr_site} deletion error!")
    flash(message,'alert alert-info')
    logging.info(f"-----------------------Bunch sites deletion by {current_user.realname} is done!-----------------")
    return True

def disable_site(sitename: str) -> None:
    """Site action: disables the selected site and applies changes immediately. Requires "sitename" as a parameter"""
    error_message = ""
    try:
        logging.info(f"-----------------------Starting site disable: {sitename} by {current_user.realname}-----------------")
        #disable Nginx site
        ngx = os.path.join(current_app.config["NGX_SITES_PATHEN"],sitename)
        if os.path.isfile(ngx) or os.path.islink(ngx):
            os.unlink(ngx)
            logging.info(f"Nginx symlink {ngx} removed")
            result1 = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
            if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
                result2 = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
                if  re.search(r".*started.*",result2.stderr):
                    logging.info(f"Nginx reloaded successfully. Result: {result2.stderr.strip()}")
                else:
                    logging.error(f"Nginx reload failed!. {result2.stderr}")
                    asyncio.run(send_to_telegram(f"Error while reloading Nginx",f"🚒Provision job error({functions.variables.JOB_ID}):"))
            else:
                logging.error(f"Error while reloading Nginx: {result1.stderr.strip()}")
                error_message += f"Помилка при перезавантаженні веб сервера Nginx: {result1.stderr.strip()}"
                asyncio.run(send_to_telegram(f"Error while reloading Nginx",f"🚒Provision site disable error({sitename}):"))
        else:
            logging.error(f"Nginx site disable error - symlink {ngx} is not exist")
            error_message += f"Помилка при перезавантаженні веб сервера Nginx"
        #php disable
        php = os.path.join(current_app.config["PHP_POOL"],sitename+".conf")
        if os.path.isfile(php) or os.path.islink(php):
            os.rename(php,php+".disabled")
            result2 = subprocess.run(["sudo",current_app.config["PHPFPM_PATH"],"-t"], capture_output=True, text=True)
            if  re.search(r".*test is successful.*",result2.stderr):
            #gettings digits of PHP version from the path to the PHP-FPM
                phpVer = re.search(r"(.*)(\d\.\d)",current_app.config["PHPFPM_PATH"]).group(2)
                logging.info(f"PHP config test passed successfully: {result2.stderr.strip()}. Reloading PHP, version {phpVer}...")
                result3 = subprocess.run(["sudo","systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
                if  result3.returncode == 0:
                    logging.info(f"PHP reloaded successfully.")
                else:
                    logging.error(f"PHP reload failed!. {result3.stderr}")
                    asyncio.run(send_to_telegram(f"Error while reloading PHP",f"🚒Provision job error({functions.variables.JOB_ID}):"))
            else:
                logging.error(f"Error while reloading PHP: {result2.stderr.strip()}")
                error_message += f"Помилка при перезавантаженні PHP: {result2.stderr.strip()}"
                asyncio.run(send_to_telegram(f"Error while reloading PHP",f"🚒Provision site disable error({sitename}):"))
        else:
            logging.error(f"PHP site conf. disable error - symlink {php} is not exist")
            error_message += f"Помилка при перезавантаженні PHP"
    except Exception as msg:
        logging.error(f"Error while site disable. Error: {msg}")
        error_message += f"Глобальна помилка про спробі деактивації сайту: {msg}"
        asyncio.run(send_to_telegram(f"Error: {msg}",f"🚒Provision site disable error({sitename}):"))
    if len(error_message) > 0:
        flash(error_message, 'alert alert-danger')
    else:
        flash(f"Сайт {sitename} успішно деактивовано.", 'alert alert-success')
    logging.info(f"-----------------------Site disable of {sitename} is finished-----------------")

def enable_site(sitename: str) -> None:
    """Site action: enables the selected site and applies changes immediately. Requires "sitename" as a parameter"""
    error_message = ""
    try:
        logging.info(f"-----------------------Starting site enable: {sitename} by {current_user.realname}-----------------")
        #enable Nginx site
        ngx_en = os.path.join(current_app.config["NGX_SITES_PATHEN"],sitename)
        ngx_av = os.path.join(current_app.config["NGX_SITES_PATHAV"],sitename)
        php_cnf = os.path.join(current_app.config["PHP_POOL"],sitename+".conf")
        php_cnf_dis = os.path.join(current_app.config["PHP_POOL"],sitename+".conf.disabled")
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
            logging.info(f"PHP config {os.path.join(current_app.config['PHP_POOL'],sitename)} created because it wasn't exist")
        #start of checks - nginx
        result1 = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
            result2 = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
            if  re.search(r".*started.*",result2.stderr):
                logging.info(f"Nginx reloaded successfully. Result: {result2.stderr.strip()}")
            else:
                logging.error(f"Nginx reload failed!. {result2.stderr}")
                asyncio.run(send_to_telegram(f"Error while reloading Nginx",f"🚒Provision job error({functions.variables.JOB_ID}):"))
        else:
            logging.error(f"Error while reloading Nginx: {result1.stderr.strip()}")
            error_message += f"Помилка при перезавантаженні веб сервера Nginx: {result1.stderr.strip()}"
            asyncio.run(send_to_telegram(f"Error while reloading Nginx",f"🚒Provision site disable error({sitename}):"))
        #start of checks - php
        result2 = subprocess.run(["sudo",current_app.config['PHPFPM_PATH'],"-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result2.stderr):
        #gettings digits of PHP version from the path to the PHP-FPM
            phpVer = re.search(r"(.*)(\d\.\d)",current_app.config['PHPFPM_PATH']).group(2)
            logging.info(f"PHP config test passed successfully: {result2.stderr.strip()}. Reloading PHP, version {phpVer}...")
            result3 = subprocess.run(["sudo","systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
            if  result3.returncode == 0:
                logging.info(f"PHP reloaded successfully.")
            else:
                logging.error(f"PHP reload failed!. {result3.stderr}")
                asyncio.run(send_to_telegram(f"Error while reloading PHP",f"🚒Provision job error({functions.variables.JOB_ID}):"))
        else:
            logging.error(f"Error while reloading PHP: {result2.stderr.strip()}")
            error_message += f"Помилка при перезавантаженні PHP: {result2.stderr.strip()}"
            asyncio.run(send_to_telegram(f"Error while reloading PHP",f"🚒Provision site disable error({sitename}):"))
    except Exception as msg:
        logging.error(f"Global error while site enable. Error: {msg}")
        error_message += f"Глобальна помилка при спробі активації сайту: {msg}"
        asyncio.run(send_to_telegram(f"Error: {msg}",f"🚒Provision site enable global error({sitename}):"))
    if len(error_message) > 0:
        flash(error_message, 'alert alert-danger')
    else:
        flash(f"Сайт {sitename} успішно активовано", 'alert alert-success')
    logging.info(f"-----------------------Site enable of {sitename} is finished-----------------")

def del_redirect(location: str,sitename: str, callable: int = 0) -> bool:
    """Redirect-manager page: deletes one redirect,selected by Delete button on it.Don't applies changes immediately. Requires redirect "from location" and "sitename" as a parameter"""
    try:
        if callable == 0:
            logging.info(f"-----------------------Delete single redirect for {sitename} by {current_user.realname}-----------------")
        else:
            #creating counter to count how much redirects were processed from the general count
            counter = 1
        file301 = os.path.join(current_app.config["NGX_ADD_CONF_DIR"],"301-" + sitename + ".conf")
        #get into the site's config and uncomment one string
        if os.path.exists(file301):
            logging.info(f"Starting delete operation for {location}...")
            with open(file301, "r", encoding="utf-8") as f:
                content = f.read()
            escaped_path = re.escape(location.strip())
            pattern = re.compile(
                rf'location\s+.\s+{escaped_path}\s*{{.*?}}[\r\n]*',
                re.DOTALL
            )
            new_content, count = pattern.subn('', content)
            if count == 0:
                logging.error(f"Path {location} was not found in {file301} for site {sitename}")
                flash(f"Path {location} was not found in {file301} for site {sitename}",'alert alert-danger')
                return False
            else:
                with open(file301, "w", encoding="utf-8") as f:
                    f.write(new_content)
                logging.info(f"Redirect path {location} of {sitename} was deleted successfully")
                #if callable=0 that means there is single deletion.Creating a marker file after we have done.
                if callable == 0:
                    #here we create a marker file which makes "Apply changes" button to glow yellow
                    if not os.path.exists("/tmp/provision.marker"):
                        with open("/tmp/provision.marker", 'w',encoding='utf8') as file3:
                            file3.write("")
                    logging.info("Marker file for Apply button created")
                    logging.info(f"-----------------------single redirect deleted---------------------------")
                    return True
                if callable >= counter:
                    #here we create a marker file which makes "Apply changes" button to glow yellow
                    if not os.path.exists("/tmp/provision.marker"):
                        with open("/tmp/provision.marker", 'w',encoding='utf8') as file3:
                            file3.write("")
                    logging.info("Marker file for Apply button created")
                    counter = counter + 1
                    return True
        else:
            logging.error(f"Error delete redirects of {sitename}: {file301} is not exists,but it is not possible because you are deleting from it!")
            flash(f"Error delete redirects of {sitename}: {file301} is not exists!", 'alert alert-danger')
            asyncio.run(send_to_telegram(f"{file301} is not exists,but it is not possible because you are deleting from it!",f"🚒Provision redirects delete error:"))
            return False
    except Exception as msg:
        logging.error(f"Privision Global Error:", f"{msg}")
        asyncio.run(send_to_telegram(f"{file301} is not exists, but it is not possible because you are deleting from it.",f"🚒Provision Global Error:"))
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
                logging.info(f"Redirect path {curr_redir} of {sitename} was deleted successfully")
                message += f"Редирект {curr_redir} успішно видалено!\n"
            else:
                message += f"Помилка видалення редиректу {curr_redir}!\n"
                logging.info(f"Redirect path {curr_redir} of {sitename} deletion error!")
                #here we create a marker file which makes "Apply changes" button to glow yellow
                if not os.path.exists("/tmp/provision.marker"):
                    with open("/tmp/provision.marker", 'w',encoding='utf8') as file3:
                        file3.write("")
                logging.info("Marker file for Apply button created")
        logging.info(f"-----------------------Selected bulk redirects deleted---------------------------")
        return True
    except Exception as msg:
        logging.error(f"del_selected_redirects() Global Error: {msg}")
        asyncio.run(send_to_telegram(f"del_selected_redirects() Global Error: {msg}",f"🚒Provision Global Error:"))
        return False

def applyChanges(sitename: str) -> bool:
    """Redirect-manager page: applies all changes, made to redirect config files"""
    logging.info(f"-----------------------Applying changes in Nginx by {current_user.realname}-----------------")
    result1 = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
    if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
        result2 = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
        if  re.search(r".*started.*",result2.stderr):
            logging.info(f"Nginx reloaded successfully. Result: {result2.stderr.strip()}")
            flash(f"Changes applied succesfully. Nginx reloaded.",'alert alert-success')
            logging.info(f"-----------------------Applying changes in Nginx finished-----------------")
            if os.path.exists("/tmp/provision.marker"):
                os.unlink("/tmp/provision.marker")
            return True
        else:
            logging.info(f"Nginx reload error!. Result: {result2.stderr.strip()}")
            flash(f"Помилка застосування нової конфігурації веб сервером!.",'alert alert-danger')
            logging.info(f"-----------------------Applying changes in Nginx finished with error!-----------------")
            asyncio.run(send_to_telegram(f"Changes apply error: Nginx has bad configuration",f"🚒Provision Error"))
            return False
    else:
        logging.error(f"Error reloading Nginx: {result1.stderr.strip()}")
        asyncio.run(send_to_telegram(f"Changes apply error: Nginx has bad configuration",f"🚒Provision Error"))
        flash(f"Error reloading Nginx! Some error in configuration, see logs:\n{result1.stderr.strip()}",'alert alert-danger')
        logging.info(f"-----------------------Applying changes in Nginx finished-----------------")
        return False

def count_redirects(site: str) -> str:
    """This function is counts current available redirects for every site while general site list is loading"""
    try:
        with open(os.path.join(current_app.config["NGX_ADD_CONF_DIR"],"301-"+site+".conf"), "r", encoding="utf-8") as f:
            count = int(sum(1 for _ in f) / 3)
            return str(count)
    except Exception:
        return "0"

def makePull(domain: str, pullArray: list = []) -> bool:
    """Root page: makes git pull to update the site code. Can receive single domain name or a list of."""
    try:
        #When a single site pull
        if len(pullArray) == 0:
            logging.info(f"-----------------------Single git pull for {domain} by {current_user.realname}-----------------")
            path = os.path.join(current_app.config["WEB_FOLDER"],domain)
            if os.path.exists(path):
                os.chdir(path)
                logging.info(f"Successfully got into {path}")
                result = subprocess.run(["sudo","git","pull"], capture_output=True, text=True)
                if result.returncode != 0:
                    logging.error(f"Git pull for {domain} returned error: {result.stderr}")
                    asyncio.run(send_to_telegram(f"Git pull error for site {domain}: {result.stderr}",f"🚒Provision pull error:"))
                    flash(f"Помилка оновлення коду із репозиторію {path}: {result.stderr}.",'alert alert-danger')
                    logging.info(f"-----------------------Single git pull for {domain} by {current_user.realname} finished---------------------------")
                    return False
                else:
                    flash(f"Код для сайту {domain} успішно оновлено із репозиторію!.",'alert alert-success')
                    logging.info(f"Git pull for {domain} done successfully!")
                    logging.info(f"-----------------------Single git pull for {domain} by {current_user.realname} finished---------------------------")
                    return True
            else:
                logging.error(f"Git pull for {domain} returned error: site folder {path} not exists!")
                asyncio.run(send_to_telegram(f"Git pull for {domain} returned error: site folder {path} not exists!",f"🚒Provision pull error:"))
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
                path = os.path.join(current_app.config["WEB_FOLDER"],curr_domain)
                if os.path.exists(path):
                    os.chdir(path)
                    logging.info(f"Successfully got into {path}")
                    result = subprocess.run(["sudo","git","pull"], capture_output=True, text=True)
                    if result.returncode != 0:
                        logging.error(f"Git pull for {domain} returned error: {result.stderr}")
                        asyncio.run(send_to_telegram(f"Git pull error for site {domain}: {result.stderr}",f"🚒Provision pull error:"))
                        message += f"[❌] Помилка оновлення коду для {curr_domain}\n"
                    else:
                        message += f"[✅] Код {curr_domain} успішно оновлено!\n"
                        logging.info(f"Git pull for {domain} done successfully!")
            flash(message,'alert alert-info')
            logging.info(f"-----------------------Bunch git pull by {current_user.realname} is done!-----------------")
            return True
    except Exception as msg:
        logging.error(f"Makepull() Global Error:", "{msg}")
        asyncio.run(send_to_telegram(f"makePull() global error: {msg}",f"🚒Provision pull error:"))
        logging.info(f"-----------------------Single git pull for {domain} by {current_user.realname} finished---------------------------")
        return False
