import logging,os,subprocess,asyncio,re,shutil
from flask import current_app,flash,redirect
from functions.send_to_telegram import send_to_telegram
from functions.config_templates import create_nginx_config, create_php_config
from flask_login import current_user

def delete_site(sitename: str) -> None:
    """Site action: full delete selected site. Requires "sitename" as a parameter"""
    error_message = ""
    try:
        logging.info(f"-----------------------Starting site delete: {sitename} by {current_user.realname}-----------------")
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
            logging.error(f"Error while reloading Nginx: {result1.stderr.strip()}")
            error_message += f"Error while reloading Nginx: {result1.stderr.strip()}"
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
            logging.error(f"Error while reloading PHP: {result2.stderr.strip()}")
            error_message += f"Error while reloading PHP: {result2.stderr.strip()}"
            asyncio.run(send_to_telegram(f"Error while reloading PHP",f"🚒Provision site delete error({sitename}):"))
        #--------------Delete of the site folder
        path = os.path.join(current_app.config["WEB_FOLDER"],sitename)
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
        asyncio.run(send_to_telegram(f"Error: {msg}",f"🚒Provision site delete error({sitename}):"))
    if len(error_message) > 0:
        flash(error_message, 'alert alert-danger')
    else:
        flash(f"Site {sitename} deleted successfully", 'alert alert-success')
    logging.info(f"-----------------------Site delete of {sitename} is finished-----------------")

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
                logging.error(f"Error while reloading Nginx: {result1.stderr.strip()}")
                error_message += f"Error while reloading Nginx: {result1.stderr.strip()}"
                asyncio.run(send_to_telegram(f"Error while reloading Nginx",f"🚒Provision site disable error({sitename}):"))
        else:
            logging.error(f"Nginx site disable error - symlink {ngx} is not exist")
            error_message += f"Error while reloading Nginx"
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
                logging.error(f"Error while reloading PHP: {result2.stderr.strip()}")
                error_message += f"Error while reloading PHP: {result2.stderr.strip()}"
                asyncio.run(send_to_telegram(f"Error while reloading PHP",f"🚒Provision site disable error({sitename}):"))
        else:
            logging.error(f"PHP site conf. disable error - symlink {php} is not exist")
            error_message += f"Error while reloading PHP"
    except Exception as msg:
        logging.error(f"Error while site disable. Error: {msg}")
        error_message += f"Error while site disable. Error: {msg}"
        asyncio.run(send_to_telegram(f"Error: {msg}",f"🚒Provision site disable error({sitename}):"))
    if len(error_message) > 0:
        flash(error_message, 'alert alert-danger')
    else:
        flash(f"Site {sitename} disabled successfully", 'alert alert-success')
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
            logging.error(f"Error while reloading Nginx: {result1.stderr.strip()}")
            error_message += f"Error while reloading Nginx: {result1.stderr.strip()}"
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
            logging.error(f"Error while reloading PHP: {result2.stderr.strip()}")
            error_message += f"Error while reloading PHP: {result2.stderr.strip()}"
            asyncio.run(send_to_telegram(f"Error while reloading PHP",f"🚒Provision site disable error({sitename}):"))
    except Exception as msg:
        logging.error(f"Global error while site enable. Error: {msg}")
        error_message += f"Global error while site disable. Error: {msg}"
        asyncio.run(send_to_telegram(f"Error: {msg}",f"🚒Provision site enable global error({sitename}):"))
    if len(error_message) > 0:
        flash(error_message, 'alert alert-danger')
    else:
        flash(f"Site {sitename} enabled successfully", 'alert alert-success')
    logging.info(f"-----------------------Site enable of {sitename} is finished-----------------")

def enable_allredirects(sitename: str) -> None:
    """Site action: Enables global redirect for all pages to the main page,personal redirects become disabled for the site.Applies changes immediately. Requires "sitename" as a parameter"""
    error_message = ""
    try:
        logging.info(f"-----------------------Enabling all redirects to the main page for {sitename} by {current_user.realname}-----------------")
        ngx_av = os.path.join(current_app.config["NGX_SITES_PATHAV"],sitename)
        logging.info(f"File: {ngx_av}")
        #get into the site's config and uncomment one string
        if os.path.exists(ngx_av):
            #the first open - uncomment out redirects catch in root location
            with open(ngx_av, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith("#") and "if ( $request_uri !=" in stripped:
                    uncommented = line.replace("#", "", 1)
                    new_lines.append(uncommented)
                else:
                    new_lines.append(line)
            with open(ngx_av, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            logging.info(f"Redirects in root location of {sitename} Nginx config uncommented out successfully")
            #the second open - uncomment out include of redirect file config to be sure
            with open(ngx_av, "r", encoding="utf-8") as f2:
                lines2 = f2.readlines()
            new_lines2 = []
            hasbeenfound = 0
            for line2 in lines2:
                stripped2 = line2.lstrip()
                if stripped2.startswith("#") and f"include additional-configs/301-{sitename}.conf;" in stripped2:
                    uncommented2 = line2.replace("#", "", 1)
                    new_lines2.append(uncommented2)
                    hasbeenfound = 1
                    logging.info("inlude line found and uncommented")
                else:
                    new_lines2.append(line2)
            #if there is no include at all (old config file)
            if hasbeenfound == 0:
                stripped2 = line2 = lines2 = uncommented2 = ""
                with open(ngx_av, "r", encoding="utf-8") as f2:
                    lines2 = f2.readlines()
                new_lines2 = []
                for line2 in lines2:
                    stripped2 = line2.lstrip()
                    if stripped2.startswith("charset utf8;"):
                        uncommented2 = line2.replace("charset utf8;", f"charset utf8;\n    include additional-configs/301-{sitename}.conf;", 1)
                        new_lines2.append(uncommented2)
                        hasbeenfound = 2
                    else:
                        new_lines2.append(line2)
            #here we log the creating of this line
            if hasbeenfound == 2:
                logging.info(f"There was no Include for additional-configs/301-{sitename}.conf. Created one.")
            #if there was changes - write them down
            if hasbeenfound != 0:
                with open(ngx_av, "w", encoding="utf-8") as f:
                    f.writelines(new_lines2)
                logging.info(f"Redirects in root location of {sitename} Nginx config uncommented out successfully")
            #start of checks - nginx
            result1 = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
            if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
                result2 = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
                if  re.search(r".*started.*",result2.stderr):
                    logging.info(f"Nginx reloaded successfully. Result: {result2.stderr.strip()}")
            else:
                logging.error(f"Error reloading Nginx: {result1.stderr.strip()}")
                error_message += f"Error reloading Nginx:  {result1.stderr.strip()}"
                asyncio.run(send_to_telegram(f"Error reloading Nginx",f"🚒Provision Error"))
        else:
            logging.error(f"Error enabling all redirects to the main page of {sitename}: {ngx_av} is not exists!")
            error_message += f"Error enabling all redirects to the main page of {sitename}: {ngx_av} is not exists!"
            asyncio.run(send_to_telegram(f"{ngx_av} is not exists!",f"🚒Error enabling all redirects to the main page of {sitename}:"))
    except Exception as msg:
        logging.error(f"Global Error enabling all redirects to the main page of {sitename}: {msg}")
        error_message += f"Global Error enabling all redirects to the main page of {sitename}: {msg}"
        asyncio.run(send_to_telegram(f"Error: {msg}",f"🚒Provision Error enabling all redirects to the main page of {sitename}:"))
    if len(error_message) > 0:
        flash(error_message, 'alert alert-danger')
    else:
        flash(f"Redirects for {sitename} enabled successfully", 'alert alert-success')
    logging.info(f"-----------------------Finished enabling all redirects to the main page for {sitename}-----------------")

def disable_allredirects(sitename: str) -> None:
    """Site action: Disables global redirect for all pages to the main page,personal redirects become available for the site.Applies changes immediately. Requires "sitename" as a parameter"""
    error_message = ""
    try:
        logging.info(f"-----------------------Disabling all redirects to the main page for {sitename} by {current_user.realname}-----------------")
        ngx_av = os.path.join(current_app.config["NGX_SITES_PATHAV"],sitename)
        logging.info(f"File: {ngx_av}")
        #get into the site's config and uncomment one string
        if os.path.exists(ngx_av):
            #the first open - comment out redirects catch in root location
            with open(ngx_av, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                stripped = line.lstrip()
                if stripped.startswith("if ( $request_uri !="):
                    uncommented = line.replace("if ( $request_uri !=", "#if ( $request_uri !=", 1)
                    new_lines.append(uncommented)
                else:
                    new_lines.append(line)
            with open(ngx_av, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            logging.info(f"Redirects in root location of {sitename} Nginx config commented out successfully")
            #the second open - comment out include of redirect file config to be sure
            with open(ngx_av, "r", encoding="utf-8") as f2:
                lines2 = f2.readlines()
            new_lines2 = []
            for line2 in lines2:
                stripped2 = line2.lstrip()
                if stripped2.startswith(f"include additional-configs/301-{sitename}.conf;"):
                    uncommented2 = line2.replace(f"include additional-configs/301-{sitename}.conf;", f"#include additional-configs/301-{sitename}.conf;", 1)
                    new_lines2.append(uncommented2)
                else:
                    new_lines2.append(line2)
            with open(ngx_av, "w", encoding="utf-8") as f:
                f.writelines(new_lines2)
            logging.info(f"Include of redirects file of {sitename} Nginx config commented out successfully")
            #start of checks - nginx
            result1 = subprocess.run(["sudo","nginx","-t"], capture_output=True, text=True)
            if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
                result2 = subprocess.run(["sudo","nginx","-s", "reload"], text=True, capture_output=True)
                if  re.search(r".*started.*",result2.stderr):
                    logging.info(f"Nginx reloaded successfully. Result: {result2.stderr.strip()}")
            else:
                logging.error(f"Error reloading Nginx: {result1.stderr.strip()}")
                error_message += f"Error reloading Nginx:  {result1.stderr.strip()}"
                asyncio.run(send_to_telegram(f"Error reloading Nginx",f"🚒Provision Error"))
        else:
            logging.error(f"Error disabling all redirects to the main page of {sitename}: {ngx_av} is not exists!")
            error_message += f"Error disabling all redirects to the main page of {sitename}: {ngx_av} is not exists!"
            asyncio.run(send_to_telegram(f"{ngx_av} is not exists!",f"🚒Error disabling all redirects to the main page of {sitename}:"))
    except Exception as msg:
        logging.error(f"Global Error disabling all redirects to the main page of {sitename}: {msg}")
        error_message += f"Global Error disabling all redirects to the main page of {sitename}: {msg}"
        asyncio.run(send_to_telegram(f"Error: {msg}",f"🚒Provision Error disabling all redirects to the main page of {sitename}:"))
    if len(error_message) > 0:
        flash(error_message, 'alert alert-danger')
    else:
        flash(f"Redirects for {sitename} disabled successfully", 'alert alert-success')
    logging.info(f"-----------------------Finished disabling all redirects to the main page for {sitename}-----------------")

def del_redirect(location: str,sitename:str):
    """Redirect-manager page: deletes one redirect,selected by Delete button on it.Don't applies changes immediately. Requires redirect "from location" and "sitename" as a parameter"""
    try:
        logging.info(f"-----------------------Delete single redirect for {sitename} by {current_user.realname}-----------------")
        file301 = os.path.join("/etc/nginx/additional-configs","301-" + sitename + ".conf")
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
            else:
                with open(file301, "w", encoding="utf-8") as f:
                    f.write(new_content)
                logging.info(f"Redirect path {location} of {sitename} was deleted successfully")
        else:
            logging.error(f"Error delete redirects of {sitename}: {file301} is not exists,but it is not possible because you are deleting from it!")
            flash(f"Error delete redirects of {sitename}: {file301} is not exists!", 'alert alert-danger')
            asyncio.run(send_to_telegram(f"{file301} is not exists,but it is not possible because you are deleting from it!",f"🚒Provision redirects delete error:"))
    except Exception as msg:
        logging.error(f"Privision Global Error:", "{msg}")
        asyncio.run(send_to_telegram(f"{file301} is not exists, but it is not possible because you are deleting from it.",f"🚒Provision Global Error:"))
    #here we create a marker file which makes "Apply changes" button to glow yellow
    if not os.path.exists("/tmp/provision.marker"):
        with open("/tmp/provision.marker", 'w',encoding='utf8') as file3:
            file3.write("")
            logging.info("Marker file for Apply button created")
    logging.info(f"-----------------------single redirect deleted---------------------------")
    return redirect(f"/redirects_manager?site={sitename}",301)

def del_selected_redirects(array: str,sitename:str):
    """Redirect-manager page: deletes array of selected by checkboxes redirects.Don't applies changes immediately. Requires redirect locations array and "sitename" as a parameter"""
    try:
        logging.info(f"-----------------------Delete selected bulk redirects for {sitename} by {current_user.realname}-----------------")
        file301 = os.path.join("/etc/nginx/additional-configs","301-" + sitename + ".conf")
        #get into the site's config and uncomment one string
        if os.path.exists(file301):
            #start of parsing array() and remove selected routes
            for location in array:
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
                else:
                    with open(file301, "w", encoding="utf-8") as f:
                        f.write(new_content)
                    logging.info(f"Redirect path {location} of {sitename} was deleted successfully")
        else:
            logging.error(f"Error delete redirects of {sitename}: {file301} is not exists,but it is not possible because you are deleting from it!")
            flash(f"Error delete redirects of {sitename}: {file301} is not exists!", 'alert alert-danger')
            asyncio.run(send_to_telegram(f"🚒Provision redirects delete error:",f"{file301} is not exists,but it is not possible because you are deleting from it!"))
    except Exception as msg:
        logging.error(f"Privision Global Error:", "{msg}")
        asyncio.run(send_to_telegram(f"{file301} is not exists, but it is not possible because you are deleting from it.",f"🚒Provision Global Error:"))
    #here we create a marker file which makes "Apply changes" button to glow yellow
    if not os.path.exists("/tmp/provision.marker"):
        with open("/tmp/provision.marker", 'w',encoding='utf8') as file3:
            file3.write("")
            logging.info("Marker file for Apply button created")
    logging.info(f"-----------------------Selected bulk redirects deleted---------------------------")
    return redirect(f"/redirects_manager?site={sitename}",301)

def applyChanges(sitename: str):
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
            return redirect(f"/redirects_manager?site={sitename}",301)
    else:
        logging.error(f"Error reloading Nginx: {result1.stderr.strip()}")
        asyncio.run(send_to_telegram(f"Changes apply error: Nginx has bad configuration",f"🚒Provision Error"))
        flash(f"Error reloading Nginx! Some error in configuration, see logs:\n{result1.stderr.strip()}",'alert alert-danger')
        logging.info(f"-----------------------Applying changes in Nginx finished-----------------")
        return redirect(f"/redirects_manager?site={sitename}",301)

def count_redirects(site: str) -> str:
    try:
        with open(os.path.join("/etc/nginx/additional-configs","301-"+site+".conf"), "r", encoding="utf-8") as f:
            count = (sum(1 for _ in f) / 3)
            return str(count)
    except Exception:
        return "0"