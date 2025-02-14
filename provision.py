#!/usr/bin/env python3

from flask import Flask,render_template,request,make_response,redirect
from werkzeug.utils import secure_filename
import os
import sys
import subprocess
import shutil
import json
import logging
import logging.handlers
import requests
import glob
import zipfile
import random
import string
import bcrypt
import signal
import re

CONFIG_FILE = os.path.abspath(os.path.dirname(__file__))+"/provision.conf"
PASSWORD_FILE = os.path.abspath(os.path.dirname(__file__))+"/user-pass.conf"
TELEGRAM_TOKEN = TELEGRAM_CHATID = WEB_FOLDER = JOB_ID = NGX_CRT_PATH = WWW_USER = WWW_GROUP = NGX_SITES_PATH = NGX_SITES_PATH2 = PHP_POOL = NGINX_PATH = PHPFPM_PATH = ""
JOB_COUNTER = JOB_TOTAL = 1
PWD_LIST = []
COOKIE_SALT="55c5834073242d20dd19c94a058198cf"

def load_config():
    global TELEGRAM_TOKEN, TELEGRAM_CHATID, WEB_FOLDER, NGX_CRT_PATH, WWW_USER, WWW_GROUP, NGX_SITES_PATH, NGX_SITES_PATH2, PHP_POOL,PWD_LIST, NGINX_PATH, PHPFPM_PATH
    error = 0
    "Check if config file exists. If not - generate the new one."
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, 'r',encoding='utf8') as file:
            config = json.load(file)
        "Check if all parameters are set. If not - shows the error message"
        for id,key in enumerate(config.keys()):
            if not config.get(key):
                print(f"Parameter {key} is not defined!")
                error+=1
        if error != 0:
            print(f"Some variables are not set in config file. Please fix it then run the program again.")
            quit()
        WEB_FOLDER = config.get('webFolder')
        TELEGRAM_TOKEN = config.get('telegramToken')
        TELEGRAM_CHATID = config.get('telegramChat')
        LOG_FILE = config.get('logFile')
        NGX_CRT_PATH = config.get('nginxCrtPath')
        NGX_SITES_PATH = config.get('nginxSitesPathAv')
        NGX_SITES_PATH2 = config.get('nginxSitesPathEn')
        WWW_USER = config.get('wwwUser')
        WWW_GROUP = config.get('wwwGroup')
        PHP_POOL = config.get('phpPool')
        NGINX_PATH = config.get('nginxPath')
        PHPFPM_PATH = config.get('phpFpmPath')
        logging.basicConfig(filename=LOG_FILE,level=logging.INFO,format='%(asctime)s - Provision - %(levelname)s - %(message)s',datefmt='%d-%m-%Y %H:%M:%S')
        if os.path.exists(PASSWORD_FILE):
            with open(PASSWORD_FILE, 'r',encoding='utf8') as file2:
                PWD_LIST = json.load(file2)
        else:
            print(f"Config file {PASSWORD_FILE} is not found. Please check it.")
            logging.error(f"Config file {PASSWORD_FILE} is not found. Please check it.")
    else:
        generate_default_config()

def generate_default_config():
    config = {
        "telegramToken": "",
        "telegramChat": "",
        "webFolder": "/var/www",
        "logFile": "provision.log",
        "nginxCrtPath": "/etc/nginx/ssl/",
        "phpFpmPath": "/usr/sbin/php-fpm8.2",
        "nginxPath": "/usr/sbin/nginx",
        "wwwUser": "www-data",
        "wwwGroup": "www-data",
        "nginxSitesPathAv": "/etc/nginx/sites-available/",
        "nginxSitesPathEn": "/etc/nginx/sites-enabled/"
    }
    with open(CONFIG_FILE, 'w',encoding='utf8') as file:
        json.dump(config, file, indent=4)
    os.chmod(CONFIG_FILE, 0o600)
    print(f"First launch. New config file {CONFIG_FILE} generated and needs to be configured.")
    quit()

def send_to_telegram(subject,message):
    headers = {
        'Content-Type': 'application/json',
    }
    data = {
        "chat_id": f"{TELEGRAM_CHATID}",
        "text": f"{subject}\n{message}",
    }
    response = requests.post(f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",headers=headers,json=data)
    if response.status_code != 200:
        err = response.json()
        logging.error(f"Error while sending message to Telegram: {err}")

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
        send_to_telegram(f"🏁Provision job finish ({JOB_ID}):",f"Provision jobs are finished. Total {JOB_TOTAL} done.")
        logging.info(f"----------------------------------------End of JOB ID:{JOB_ID}--------------------------------------------")
        quit()
    else:
        logging.info(f">>>End of JOB #{JOB_COUNTER}")
        send_to_telegram(f"Provision job {JOB_ID}:",f"JOB #{JOB_COUNTER} of {JOB_TOTAL} finished successfully")
        JOB_COUNTER += 1
        findZip_1()

def setupPHP(file):
    logging.info(f"Configuring Nginx...Preparing certificates")
    filename = os.path.basename(file)[:-4]
    config = f"""[{filename}]
user = {WWW_USER}
group = {WWW_GROUP}
listen = /run/php/{filename}.sock
listen.owner = {WWW_USER}
listen.group = {WWW_GROUP}
listen.mode = 0660
listen.allowed_clients = 127.0.0.1
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
chdir = {os.path.join(WEB_FOLDER,filename)}
env[HOSTNAME] = {filename}
env[PATH] = /usr/local/bin:/usr/bin:/bin
env[TMP] = /tmp
env[TMPDIR] = /tmp
env[TEMP] = /tmp
php_admin_value[error_log] = /var/log/nginx/php-fpm_{filename}.log
php_admin_flag[log_errors] = on
php_admin_value[open_basedir] = {os.path.join(WEB_FOLDER,filename)}:/tmp
php_admin_value[disable_functions] = apache_child_terminate,apache_get_modules,apache_get_version,apache_getenv,apache_lookup_uri,apache_note,apache_request_headers,apache_reset_timeout,apache_response_headers,apache_setenv,getallheaders,virtual,chdir,chroot,exec,passthru,proc_close,proc_get_status,proc_nice,proc_open,proc_terminate,shell_exec,system,chgrp,chown,disk_free_space,disk_total_space,diskfreespace,filegroup,fileinode,fileowner,lchgrp,lchown,link,linkinfo,lstat,pclose,popen,readlink,symlink,umask,cli_get_process_title,cli_set_process_title,dl,gc_collect_cycles,gc_disable,gc_enable,get_current_user,getmygid,getmyinode,getmypid,getmyuid,php_ini_loaded_file,php_ini_scanned_files,php_logo_guid,php_uname,zend_logo_guid,zend_thread_id,highlight_file,php_check_syntax,show_source,sys_getloadavg,closelog,define_syslog_variables,openlog,pfsockopen,syslog,nsapi_request_headers,nsapi_response_headers,nsapi_virtual,pcntl_alarm,pcntl_errno,pcntl_exec,pcntl_fork,pcntl_get_last_error,pcntl_getpriority,pcntl_setpriority,pcntl_signal_dispatch,pcntl_signal,pcntl_sigprocmask,pcntl_sigtimedwait,pcntl_sigwaitinfo,pcntl_strerror,pcntl_wait,pcntl_waitpid,pcntl_wexitstatus,pcntl_wifexited,pcntl_wifsignaled,pcntl_wifstopped,pcntl_wstopsig,pcntl_wtermsig,posix_access,posix_ctermid,posix_errno,posix_get_last_error,posix_getcwd,posix_getegid,posix_geteuid,posix_getgid,posix_getgrgid,posix_getgrnam,posix_getgroups,posix_getlogin,posix_getpgid,posix_getpgrp,posix_getpid,posix_getppid,posix_getpwnam,posix_getpwuid,posix_getrlimit,posix_getsid,posix_getuid,posix_initgroups,posix_isatty,posix_kill,posix_mkfifo,posix_mknod,posix_setegid,posix_seteuid,posix_setgid,posix_setpgid,posix_setsid,posix_setuid,posix_strerror,posix_times,posix_ttyname,posix_uname,setproctitle,setthreadtitle,shmop_close,shmop_delete,shmop_open,shmop_read,shmop_size,shmop_write,opcache_compile_file,opcache_get_configuration,opcache_get_status,opcache_invalidate,opcache_is_script_cached,opcache_reset,putenv
"""
    try:
        with open(os.path.join(PHP_POOL,filename)+".conf", 'w',encoding='utf8') as fileC:
            fileC.write(config)
        logging.info(f"PHP config {os.path.join(PHP_POOL,filename)} created")
        result = subprocess.run([PHPFPM_PATH,"-t"], capture_output=True, shell=True)
        if  re.search(r".*test is successful.*",result.stderr):
            #gettings digits of PHP version from the path to the PHP-FPM
            phpVer = re.search(r"(.*)(\d\.\d)",PHPFPM_PATH).group(2)
            logging.info(f"PHP config test passed successfully: {result.stdout}. Reloading PHP, version {phpVer}...")
            result = subprocess.run(["systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, shell=True)
            if  result.returncode == 0:
                logging.info(f"PHP reloaded successfully.")
                finishJob(file)
        else:
            logging.error(f"Error while reloading PHP: {result.stdout} {result.stderr}")
            send_to_telegram(f"🚒Provision job error({JOB_ID}):",f"Error while reloading PHP")
            finishJob(file)
    except Exception as msg:
        logging.error(f"Error while configuring PHP. Error: {msg}")
        send_to_telegram(f"🚒Provision job error({JOB_ID}):",f"Error: {msg}")
        finishJob(file)

def setupNginx(file):
    logging.info(f"Configuring Nginx...Preparing certificates")
    filename = os.path.basename(file)[:-4]
    crtPath = os.path.join(WEB_FOLDER,filename,filename+".crt")
    keyPath = os.path.join(WEB_FOLDER,filename,filename+".key")
    try:
        shutil.copy(crtPath,NGX_CRT_PATH)
        os.remove(crtPath)
        shutil.copy(keyPath,NGX_CRT_PATH)
        os.remove(keyPath)
        os.chmod(NGX_CRT_PATH+filename+".crt", 0o600)
        os.chmod(NGX_CRT_PATH+filename+".key", 0o600)
        logging.info(f"Certificate {crtPath} and key {keyPath} moved successfully to {NGX_CRT_PATH}")
        os.system(f"chown -R {WWW_USER}:{WWW_GROUP} {os.path.join(WEB_FOLDER,filename)}")
        logging.info(f"Folders and files ownership of {os.path.join(WEB_FOLDER,filename)} changed to {WWW_USER}:{WWW_GROUP}")
        config = f"""server {{
    listen 203.161.35.70:80;
    server_name {filename} www.{filename};
    access_log /var/log/nginx/access_{filename}.log postdata;
    error_log /var/log/nginx/error_{filename}.log;

    location ~ / {{
      return 301 https://{filename};
    }}
}}

server {{
    listen 203.161.35.70:443 ssl http2;
    server_name www.{filename};
    ssl_certificate /etc/nginx/ssl/{filename}.crt;
    ssl_certificate_key /etc/nginx/ssl/{filename}.key;
    access_log /var/log/nginx/access_{filename}.log postdata;
    error_log /var/log/nginx/error_{filename}.log;

    location / {{
      return 301 https://{filename};
    }}
}}

server {{
    listen 203.161.35.70:443 ssl http2;
    server_name {filename};
    ssl_certificate /etc/nginx/ssl/{filename}.crt;
    ssl_certificate_key /etc/nginx/ssl/{filename}.key;
    include mime.types;
    access_log /var/log/nginx/access_{filename}.log postdata;
    error_log /var/log/nginx/error_{filename}.log;
    root {os.path.join(WEB_FOLDER,filename)}/public;
    charset utf8;
    index index.php index.html index.htm;

    if ($request_method !~ ^(GET|POST|HEAD)$ ) {{
      return 403 "Forbidden!";
    }}

    location ~ /.git/ {{
      deny all;
    }}

    location /admin/ {{
      auth_basic "Prove you are who you are";
      auth_basic_user_file {os.path.join(WEB_FOLDER,filename)}/htpasswd;
      location ~* ^/admin/.+\.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/{filename}.sock;
      }}
    }}

    location ~* ^/(?:robots.txt) {{
      allow all;
      root {os.path.join(WEB_FOLDER,filename)}/public;
      try_files $uri $uri/ /index.php?$args;
    }}

        location ~* ".+\.(?:svg|svgz|eot|otf|webmanifest|woff|woff2|ttf|rss|css|swf|js|atom|jpe?g|gif|png|ico|html)$" {{
        allow all;
        root {os.path.join(WEB_FOLDER,filename)}/public;
        try_files $uri $uri/;
    }}

    location / {{
      if ( $request_uri != "/") {{ return 301 https://{filename}/; }}
      index index.php index.html index.htm;
    }}

    location @home {{
      return 301 https://{filename}/;
    }}

    location ~ \.php$ {{
      include snippets/fastcgi-php.conf;
      add_header X-XSS-Protection "1; mode=block";
      add_header X-Content-Type-Options nosniff;
      add_header X-Frame-Options SAMEORIGIN;
      fastcgi_pass unix:/var/run/php/{filename}.sock;
    }}
}}"""
        with open(os.path.join(NGX_SITES_PATH,filename), 'w',encoding='utf8') as fileC:
            fileC.write(config)
        logging.info(f"Nginx config {os.path.join(NGX_SITES_PATH,filename)} created")
        if not os.path.exists(os.path.join(NGX_SITES_PATH2,filename)):
            os.symlink(os.path.join(NGX_SITES_PATH,filename),os.path.join(NGX_SITES_PATH2,filename))
        logging.info(f"Nginx config {os.path.join(NGX_SITES_PATH2,filename)} symlink created")
        result = subprocess.run(["/usr/sbin/nginx","-t"], capture_output=True, shell=True)
        if  re.search(r".*test is successful.*",result.stderr) and re.search(r".*syntax is ok.*",result.stderr):
            logging.info(f"Nginx config test passed successfully: {result.stderr}. Reloading Nginx...")
            result = subprocess.run(["/usr/sbin/nginx","-s", "reload"], text=True, capture_output=True, shell=True)
            if  re.search(r".*started.*",result.stderr):
                logging.info(f"Nginx reloaded successfully. Result: {result.stderr}")
            setupPHP(file)
        else:
            logging.error(f"Error while reloading Nginx: {result.stderr}")
            send_to_telegram(f"🚒Provision job error({JOB_ID}):",f"Error while reloading Nginx")
            finishJob(file)
    except Exception as msg:
        logging.error(f"Error while configuring Nginx. Error: {msg}")
        send_to_telegram(f"🚒Provision job error({JOB_ID}):",f"Error: {msg}")
        finishJob(file)

def unZip_3(file):
    "Getting the site name from the archive name"
    filename = os.path.basename(file)[:-4]
    "Getting the full path to the folder"
    finalPath = os.path.join(WEB_FOLDER,filename)
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
        send_to_telegram(f"🚒Provision job error({JOB_ID}):",f"Error: {msg}")
        finishJob(file)

def checkZip_2(file):
    logging.info(f">>>Start processing of archive #{JOB_COUNTER} of {JOB_TOTAL} total - {file}")
    send_to_telegram(f"🎢Provisoin job start({JOB_ID}):",f"Archive #{JOB_COUNTER} of {JOB_TOTAL}: {file}")
    #Getting site name from archive name
    fileName = os.path.basename(file)[:-4]
    #Preparing full path - path to general web folder + site name
    finalPath = os.path.join(WEB_FOLDER,fileName)
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
            send_to_telegram(f"🚒Provision job error:",f"Job #{JOB_COUNTER} error: Either {fileName}.crt or {fileName}.key or htpasswd or public/ is absent in {file}")
            logging.info(f">>>End of JOB #{JOB_COUNTER}")
            finishJob(file)
        else:
            logging.info(f"Minimum reqired {fileName}.crt, {fileName}.key, htpasswd, public/ are present in {file}")
            unZip_3(file)
    except Exception as msg:
        logging.error(f"Error while checking {file}. Error: {msg}")
        send_to_telegram(f"🚒Provision job error({JOB_ID}):",f"Error: {msg}")
        finishJob(file)

def findZip_1():
    path = os.path.abspath(os.path.dirname(__file__))
    extension = "*.zip"
    files = glob.glob(os.path.join(path, extension))
    for file in files:
        checkZip_2(file)

def main():
    global JOB_TOTAL
    load_config()
    genJobID()
    path = os.path.abspath(os.path.dirname(__file__))
    extension = "*.zip"
    files = glob.glob(os.path.join(path, extension))
    JOB_TOTAL = len(files)
    logging.info(f"-----------------------Starting pre-check(JOB ID:{JOB_ID}). Total {JOB_TOTAL} archive(s) found-----------------")
    findZip_1()

def reload_config(signum, frame):
    logging.info("SIGHUP received. Reloading configuration...")

load_config()
signal.signal(signal.SIGHUP, reload_config)
application = Flask(__name__)

#catch logout form. Deleting cookies and redirect to /
@application.route("/logout", methods=['POST'])
def logout():
    logging.info(f"Logout: User {request.cookies.get('username')} logged out")
    response = make_response(redirect("/"),301)
    response.delete_cookie("realname")
    response.delete_cookie("username")
    response.delete_cookie("SESSID")
    return response

#catch upload form. Save files to the current folder. Redirect to /
@application.route("/upload", methods=['GET','POST'])
def upload_file():
    if request.method == 'POST':
        #check if fileUpload[] is in the request
        if 'fileUpload[]' not in request.files:
            logging.error(f"Upload: No <fileUpload> name in the request fields")
            response = make_response(redirect("/"),301)
            return response
        else:
            #get the list of files. saving them to the current folder. Redirect to /
            files = request.files.getlist("fileUpload[]")
            nameList = ""
            for file in files:
                if file.filename:
                    filename = os.path.join(os.path.abspath(os.path.dirname(__file__)),secure_filename(file.filename))
                    file.save(f"{filename}")
                    nameList += filename+","
            response = make_response(redirect("/"),301)
            response.set_cookie("result", f"File(s) uploaded successfully!", max_age=5)
            logging.info(f"Upload by {request.cookies.get('realname')}: Files {nameList} uploaded successfully")
            send_to_telegram(f"⬆Provision\nUpload by {request.cookies.get('realname')}:",f"Files {nameList} uploaded successfully")
            #now call this script from shell to start deploy procedure
            subprocess.run([__file__, 'main'])
            return response
    #if this is GET request - redirect to /
    if request.method == 'GET':
        response = make_response(redirect("/"),301)
        return response

#catch login form. Check if user exists in the list and password is correct. If yes - set cookies and redirect to /
@application.route("/login", methods=['GET','POST'])
def index2():
    #is this is POST request so we are trying to login
    if request.method == 'POST':
        check = 0
        #searching for the given user in the list.break when found
        for id,user in enumerate(PWD_LIST.keys()):
            if request.form['username'] == user:
                check = 1
                break
        if check == 1:
            if bcrypt.checkpw(request.form['password'].encode('utf-8'), PWD_LIST[user]['password'].encode('utf-8')):
                response = make_response(redirect("/"),301)
                response.set_cookie("realname", PWD_LIST[user]['realname'], max_age=60*60*8)
                response.set_cookie("username", user, max_age=60*60*8)
                #creating encrypted cookie data
                data = f"{COOKIE_SALT}{request.form['username']}".encode('utf-8')
                response.set_cookie(f"SESSID", bcrypt.hashpw(data,bcrypt.gensalt()).decode('utf-8'), max_age=60*60*8)
                logging.info(f"Login: User {request.form['username']} logged in")
                return response
            else:
                #if password is incorrect - show error message.Adding error message to the login form
                loginError = f"""<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\" style=\"margin-top: 15px;\">
                Wrong username or password!"
                <button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"alert\" aria-label=\"Close\"></button>
                </div>"""
                logging.error(f"Login: Wrong password \"{request.form['password']}\" for user \"{request.form['username']}\"")
                return render_template("template-login.html",loginError=loginError)
        #if user is not found - show error message.Adding error message to the login form
        else:
            loginError = f"""<div class=\"alert alert-danger alert-dismissible fade show\" role=\"alert\" style=\"margin-top: 15px;\">
            Wrong username or password!"
            <button type=\"button\" class=\"btn-close\" data-bs-dismiss=\"alert\" aria-label=\"Close\"></button>
            </div>"""
            logging.error(f"Login: Unknown user \"{request.form['username']}\", password \"{request.form['password']}\"")
            return render_template("template-login.html",loginError=loginError)

    #if this is GET request - just show login form
    if request.method == 'GET':
        return render_template("template-login.html")

#main route. If cookies are set - show main page. If not - redirect to login page
@application.route("/", methods=['GET'])
def index():
    if request.cookies.get("SESSID") and request.cookies.get("realname") and request.cookies.get("username"):
        #searching for the given user in the list
        for id,user in enumerate(PWD_LIST.keys()):
            dataLocal = f"{COOKIE_SALT}{request.cookies.get('username')}".encode('utf-8')
            dataReceived = request.cookies.get("SESSID").encode('utf-8')
            #checking if user is found and encrypted cookie he sent is correct
            if bcrypt.checkpw(dataLocal,dataReceived):
                res = request.cookies.get("result")
                if res == None:
                    return render_template("template-main.html", realName=request.cookies.get("realname"))
                else:
                    result = f"<script>alert('{res}')</script>"
                    return render_template("template-main.html", realName=request.cookies.get("realname"), result=result)
            else:
                return render_template("template-login.html")
    else:
        response = make_response(redirect("/login"),301)
        return response

def genpwd():
    if len(sys.argv) < 3:
        print(f"Password not provided. Usage: {sys.argv[0]} genpwd <password>")
        quit()
    password = sys.argv[2]
    hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
    print(f"Password: {password}\nHash: {hashed}")
    quit()

if __name__ == "__main__":
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help" or sys.argv[1] == "-h" or sys.argv[1] == "help":
            print(f"""Usage: {sys.argv[0]} genpwd <password>
            You will get the hash of the password. Add block to the user-pass.conf file in JSON format:
            {{
                "<username>": {{
                    "realname": "<Real Name>",
                    "password": "<hash you've generated>"
                }}
            }}""")
            quit()
        #if we are generating the password hash
        elif sys.argv[1] == "genpwd":
            genpwd()
        #if we are running the main function
        elif sys.argv[1] == "main":
            main()
        else:
            print(f"Something went wrong. Please check the parameters.")
            quit()
    load_config()
    application.run()
