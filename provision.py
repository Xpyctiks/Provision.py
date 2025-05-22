#!/usr/local/bin/python3

from flask import Flask,render_template,request,redirect,url_for,flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.utils import secure_filename
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
import os,sys,subprocess,shutil,logging,glob,zipfile,random,string,re,httpx,asyncio

CONFIG_DIR = os.path.join("/etc/",os.path.basename(__file__).split(".py")[0])
DB_FILE = os.path.join(CONFIG_DIR,os.path.basename(__file__).split(".py")[0]+".db")
TELEGRAM_TOKEN = TELEGRAM_CHATID = WEB_FOLDER = JOB_ID = NGX_CRT_PATH = WWW_USER = WWW_GROUP = NGX_SITES_PATH = NGX_SITES_PATH2 = PHP_POOL = PHPFPM_PATH = ""
JOB_COUNTER = JOB_TOTAL = 1
application = Flask(__name__)
application.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + DB_FILE
application.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
application.config['PERMANENT_SESSION_LIFETIME'] = 28800
db = SQLAlchemy(application)
login_manager = LoginManager(application)
login_manager.login_view = "login"

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    realname = db.Column(db.String(80), nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    created = db.Column(db.DateTime,default=datetime.now)
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
class Settings(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    telegramChat = db.Column(db.String(16), nullable=True)
    telegramToken = db.Column(db.String(64), nullable=True)
    logFile = db.Column(db.String(512), nullable=False)
    sessionKey = db.Column(db.String(64), nullable=False)
    webFolder = db.Column(db.String(512), nullable=False)
    nginxCrtPath = db.Column(db.String(512), nullable=False)
    wwwUser = db.Column(db.String(64), nullable=False)
    wwwGroup = db.Column(db.String(64), nullable=False)
    nginxSitesPathAv = db.Column(db.String(512), nullable=False)
    nginxSitesPathEn = db.Column(db.String(512), nullable=False)
    phpPool = db.Column(db.String(512), nullable=False)
    phpFpmPath = db.Column(db.String(512), nullable=False)

def generate_default_config():
    if not os.path.isfile(DB_FILE):
        length = 64
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

def set_telegramChat(tgChat):
    t = Settings(id=1,telegramChat=tgChat.strip())
    db.session.merge(t)
    db.session.commit()
    load_config()
    print("Telegram ChatID added successfully")
    try:
        logging.info(f"Telegram ChatID updated successfully!")
    except Exception as err:
        pass

def set_telegramToken(tgToken):
    t = Settings(id=1,telegramToken=tgToken)
    db.session.merge(t)
    db.session.commit()
    load_config()
    print("Telegram Token added successfully")
    try:
        logging.info(f"Telegram Token updated successfully!")
    except Exception as err:
        pass

def set_logpath(logpath):
    t = Settings(id=1,logFile=logpath)
    db.session.merge(t)
    db.session.commit()
    load_config()
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
            load_config()
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
            load_config()
            print(f"Password for user \"{user.username}\" updated successfully!")
            logging.info(f"Password for user \"{user.username}\" updated successfully!")
        else:
            print(f"User \"{user.username}\" set password error - no such user!")
            logging.error(f"User \"{user.username}\" set password error - no such user!")
            quit(1)
    except Exception as err:
        logging.error(f"User \"{user.username}\" set password error: {err}")
        print(f"User \"{user.username}\" set password error: {err}")

def delete_user(username):
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            load_config()
            print(f"User \"{user.username}\" deleted successfully!")
            logging.info(f"User \"{user.username}\" deleted successfully!")
        else:
            print(f"User \"{user.username}\" delete error - no such user!")
            logging.error(f"User \"{user.username}\" delete error - no such user!")
            quit(1)
    except Exception as err:
        logging.error(f"User \"{user.username}\" delete error: {err}")
        print(f"User \"{user.username}\" delete error: {err}")

def set_webFolder(data):
    try:
        t = Settings(id=1,webFolder=data)
        db.session.merge(t)
        db.session.commit()
        load_config()
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
        load_config()
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
        load_config()
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
        load_config()
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
        load_config()
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
        load_config()
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
        load_config()
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
        load_config()
        updated = db.session.get(Settings, 1)
        print(f"Php-fpm executable path updated successfully to: \"{updated.phpFpmPath}\"")
        logging.info(f"Php-fpm executable path updated to \"{updated.phpFpmPath}\"")
    except Exception as err:
        logging.error(f"Php-fpm executable path \"{data}\" set error: {err}")
        print(f"Php-fpm executable path \"{data}\" set error: {err}")

def show_config():
    try:
        load_config()
        data = db.session.get(Settings, 1)
        print(f"""
            Telegram ChatID:       {data.telegramChat}
            Telegram Token:        {data.telegramToken}
            Log file:              {data.logFile}
            SessionKey:            {data.sessionKey}
            Web root folder:       {data.webFolder}
            Nginx SSL folder:      {data.nginxCrtPath}
            WWW folders user:      {data.wwwUser}
            WWW folders group:     {data.wwwGroup}
            Nginx Sites-Available: {data.nginxSitesPathAv}
            Nginx Sites-Enabled:   {data.nginxSitesPathEn}
            Php Pool.d folder:     {data.phpPool}
            Php-fpm executable:    {data.phpFpmPath}
              """)
    except Exception as err:
        logging.error(f"Show config error: {err}")
        print(f"Show config error: {err}")

async def send_to_telegram(subject,message):
    if TELEGRAM_CHATID and TELEGRAM_TOKEN:
        headers = {
            'Content-Type': 'application/json',
        }
        data = {
            "chat_id": f"{TELEGRAM_CHATID}",
            "text": f"{subject}\n{message}",
        }
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                response = await client.post(
                    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                    headers=headers,
                    json=data
                )
            print(response.status_code)
            if response.status_code != 200:
                logging.error("error", f"Telegram bot error! Status: {response.status_code} Body: {response.text}")
        except Exception as err:
            logging.error(f"Error while sending message to Telegram: {err}")

def load_config():
    #main initialization phase starts here
    global TELEGRAM_TOKEN, TELEGRAM_CHATID, WEB_FOLDER, NGX_CRT_PATH, WWW_USER, WWW_GROUP, NGX_SITES_PATH, NGX_SITES_PATH2, PHP_POOL, PHPFPM_PATH
    try:
        config = db.session.get(Settings, 1)
        TELEGRAM_TOKEN = config.telegramToken
        TELEGRAM_CHATID = config.telegramChat
        LOG_FILE = config.logFile
        WEB_FOLDER = config.webFolder
        NGX_CRT_PATH = config.nginxCrtPath
        NGX_SITES_PATH = config.nginxSitesPathAv
        NGX_SITES_PATH2 = config.nginxSitesPathEn
        WWW_USER = config.wwwUser
        WWW_GROUP = config.wwwGroup
        PHP_POOL = config.phpPool
        PHPFPM_PATH = config.phpFpmPath
        application.secret_key = config.sessionKey
        try:
            logging.basicConfig(filename=LOG_FILE,level=logging.INFO,format='%(asctime)s - Provision - %(levelname)s - %(message)s',datefmt='%d-%m-%Y %H:%M:%S')
        except Exception as msg:
            logging.error(msg)
            print(f"Load-config error: {msg}")
            quit(1)
    except Exception as msg:
        print(f"Load-config error: {msg}")
        quit(1)

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

def create_php_config(filename):
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
    return config

def create_nginx_config(filename):
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
    return config

def setupPHP(file):
    logging.info(f"Configuring PHP...")
    filename = os.path.basename(file)[:-4]
    config = create_php_config(filename)
    try:
        with open(os.path.join(PHP_POOL,filename)+".conf", 'w',encoding='utf8') as fileC:
            fileC.write(config)
        logging.info(f"PHP config {os.path.join(PHP_POOL,filename)} created")
        result = subprocess.run([PHPFPM_PATH,"-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result.stderr):
            #gettings digits of PHP version from the path to the PHP-FPM
            phpVer = re.search(r"(.*)(\d\.\d)",PHPFPM_PATH).group(2)
            logging.info(f"PHP config test passed successfully: {result.stderr.strip()}. Reloading PHP, version {phpVer}...")
            result = subprocess.run(["systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
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
        config = create_nginx_config(filename)
        with open(os.path.join(NGX_SITES_PATH,filename), 'w',encoding='utf8') as fileC:
            fileC.write(config)
        logging.info(f"Nginx config {os.path.join(NGX_SITES_PATH,filename)} created")
        if not os.path.exists(os.path.join(NGX_SITES_PATH2,filename)):
            os.symlink(os.path.join(NGX_SITES_PATH,filename),os.path.join(NGX_SITES_PATH2,filename))
        logging.info(f"Nginx config {os.path.join(NGX_SITES_PATH2,filename)} symlink created")
        result = subprocess.run(["/usr/sbin/nginx","-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result.stderr) and re.search(r".*syntax is ok.*",result.stderr):
            logging.info(f"Nginx config test passed successfully: {result.stderr.strip()}. Reloading Nginx...")
            result = subprocess.run(["/usr/sbin/nginx","-s", "reload"], text=True, capture_output=True)
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
        asyncio.run(send_to_telegram(f"🚒Provision job error({JOB_ID}):",f"Error: {msg}"))
        finishJob(file)

def checkZip_2(file):
    logging.info(f">>>Start processing of archive #{JOB_COUNTER} of {JOB_TOTAL} total - {file}")
    asyncio.run(send_to_telegram(f"🎢Provisoin job start({JOB_ID}):",f"Archive #{JOB_COUNTER} of {JOB_TOTAL}: {file}"))
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
    load_config()
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
        ngx_en = os.path.join(NGX_SITES_PATH2,sitename)
        ngx_av = os.path.join(NGX_SITES_PATH,sitename)
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
        result1 = subprocess.run(["/usr/sbin/nginx","-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
            result2 = subprocess.run(["/usr/sbin/nginx","-s", "reload"], text=True, capture_output=True)
            if  re.search(r".*started.*",result2.stderr):
                logging.info(f"Nginx reloaded successfully. Result: {result2.stderr.strip()}")
        else:
            logging.error(f"Error while reloading Nginx: {result1.stderr.strip()}")
            error_message += f"Error while reloading Nginx: {result1.stderr.strip()}"
            asyncio.run(send_to_telegram(f"🚒Provision site delete error({sitename}):",f"Error while reloading Nginx"))
        #------------------------Delete in php pool.d/
        php = os.path.join(PHP_POOL,sitename+".conf")
        php_dis = os.path.join(PHP_POOL,sitename+".conf.disabled")
        if os.path.isfile(php):
            os.unlink(php)
            logging.info(f"PHP config {php} deleted successfully")
        elif os.path.isfile(php_dis):
            os.unlink(php_dis)
            logging.info(f"PHP config {php_dis} deleted successfully")
        else:
            logging.info(f"PHP config {php} already deleted")
        result2 = subprocess.run([PHPFPM_PATH,"-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result2.stderr):
        #gettings digits of PHP version from the path to the PHP-FPM
            phpVer = re.search(r"(.*)(\d\.\d)",PHPFPM_PATH).group(2)
            logging.info(f"PHP config test passed successfully: {result2.stderr.strip()}. Reloading PHP, version {phpVer}...")
            result3 = subprocess.run(["systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
            if  result3.returncode == 0:
                logging.info(f"PHP reloaded successfully.")
        else:
            logging.error(f"Error while reloading PHP: {result2.stderr.strip()}")
            error_message += f"Error while reloading PHP: {result2.stderr.strip()}"
            asyncio.run(send_to_telegram(f"🚒Provision site delete error({sitename}):",f"Error while reloading PHP"))
        #--------------Delete of the site folder
        path = os.path.join(WEB_FOLDER,sitename)
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
        ngx = os.path.join(NGX_SITES_PATH2,sitename)
        if os.path.isfile(ngx) or os.path.islink(ngx):
            os.unlink(ngx)
            logging.info(f"Nginx symlink {ngx} removed")
            result1 = subprocess.run(["/usr/sbin/nginx","-t"], capture_output=True, text=True)
            if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
                result2 = subprocess.run(["/usr/sbin/nginx","-s", "reload"], text=True, capture_output=True)
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
        php = os.path.join(PHP_POOL,sitename+".conf")
        if os.path.isfile(php) or os.path.islink(php):
            os.rename(php,php+".disabled")
            result2 = subprocess.run([PHPFPM_PATH,"-t"], capture_output=True, text=True)
            if  re.search(r".*test is successful.*",result2.stderr):
            #gettings digits of PHP version from the path to the PHP-FPM
                phpVer = re.search(r"(.*)(\d\.\d)",PHPFPM_PATH).group(2)
                logging.info(f"PHP config test passed successfully: {result2.stderr.strip()}. Reloading PHP, version {phpVer}...")
                result3 = subprocess.run(["systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
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
        asyncio.run(send_to_telegram(f"🚒Provision site disable error({JOB_ID}):",f"Error: {msg}"))
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
        ngx_en = os.path.join(NGX_SITES_PATH2,sitename)
        ngx_av = os.path.join(NGX_SITES_PATH,sitename)
        php_cnf = os.path.join(PHP_POOL,sitename+".conf")
        php_cnf_dis = os.path.join(PHP_POOL,sitename+".conf.disabled")
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
            logging.info(f"PHP config {os.path.join(PHP_POOL,sitename)} created because it wasn't exist")
        #start of checks - nginx
        result1 = subprocess.run(["/usr/sbin/nginx","-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result1.stderr) and re.search(r".*syntax is ok.*",result1.stderr):
            result2 = subprocess.run(["/usr/sbin/nginx","-s", "reload"], text=True, capture_output=True)
            if  re.search(r".*started.*",result2.stderr):
                logging.info(f"Nginx reloaded successfully. Result: {result2.stderr.strip()}")
        else:
            logging.error(f"Error while reloading Nginx: {result1.stderr.strip()}")
            error_message += f"Error while reloading Nginx: {result1.stderr.strip()}"
            asyncio.run(send_to_telegram(f"🚒Provision site disable error({sitename}):",f"Error while reloading Nginx"))
        #start of checks - php
        result2 = subprocess.run([PHPFPM_PATH,"-t"], capture_output=True, text=True)
        if  re.search(r".*test is successful.*",result2.stderr):
        #gettings digits of PHP version from the path to the PHP-FPM
            phpVer = re.search(r"(.*)(\d\.\d)",PHPFPM_PATH).group(2)
            logging.info(f"PHP config test passed successfully: {result2.stderr.strip()}. Reloading PHP, version {phpVer}...")
            result3 = subprocess.run(["systemctl", "reload", f"php{phpVer}-fpm"], capture_output=True, text=True)
            if  result3.returncode == 0:
                logging.info(f"PHP reloaded successfully.")
        else:
            logging.error(f"Error while reloading PHP: {result2.stderr.strip()}")
            error_message += f"Error while reloading PHP: {result2.stderr.strip()}"
            asyncio.run(send_to_telegram(f"🚒Provision site disable error({sitename}):",f"Error while reloading PHP"))
    except Exception as msg:
        logging.error(f"Global error while site enable. Error: {msg}")
        error_message += f"Global error while site disable. Error: {msg}"
        asyncio.run(send_to_telegram(f"🚒Provision site enable global error({JOB_ID}):",f"Error: {msg}"))
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

#catch logout form. Deleting cookies and redirect to /
@application.route("/logout", methods=['POST'])
@login_required
def logout():
    logout_user()
    flash("You are logged out", "alert alert-info")
    return redirect(url_for("login"),301)

#catch login form. Check if user exists in the list and password is correct. If yes - set cookies and redirect to /
@application.route("/login", methods=['GET','POST'])
def login():
    #is this is POST request so we are trying to login
    if request.method == 'POST':
        if current_user.is_authenticated:
            return redirect('/',301)
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            logging.info(f"Login: User {username} logged in")
            return redirect("/",301)
        else:
            logging.error(f"Login: Wrong password \"{password}\" for user \"{username}\"")
            asyncio.run(send_to_telegram("🚷Provision:",f"Login error.Wrong password for user \"{username}\""))
            flash('Wrong username or password!', 'alert alert-danger')
            return render_template("template-login.html")    
    if current_user.is_authenticated:
        return redirect('/',301)
    else:
        return render_template("template-login.html")

#catch upload form. Save files to the current folder. Redirect to /
@application.route("/upload", methods=['GET','POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        #check if fileUpload[] is in the request
        if 'fileUpload[]' not in request.files:
            logging.error(f"Upload: No <fileUpload> name in the request fields")
            flash('Upload: No <fileUpload> in the request fields', 'alert alert-danger')
            return redirect(url_for("upload"),301)
        else:
            #get the list of files. saving them to the current folder. Redirect to /
            files = request.files.getlist("fileUpload[]")
            nameList = ""
            for file in files:
                if file.filename:
                    filename = os.path.join(os.path.abspath(os.path.dirname(__file__)),secure_filename(file.filename))
                    file.save(f"{filename}")
                    nameList += filename+","
            flash('File(s) uploaded successfully!', 'alert alert-success')
            logging.info(f"Upload by {request.cookies.get('realname')}: Files {nameList} uploaded successfully")
            asyncio.run(send_to_telegram(f"⬆Provision\nUpload by {request.cookies.get('realname')}:",f"Files {nameList} uploaded successfully"))
            #now call this script from shell to start deploy procedure
            subprocess.run([__file__, 'main'])
            return redirect("/",301)
    #if this is GET request - show page
    if request.method == 'GET':
        return render_template("template-upload.html")

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

#main route. If cookies are set - show main page. If not - redirect to login page
@application.route("/", methods=['GET'])
@login_required
def index():
    try:
        table = ""
        sites_list = []
        sites_list = [
            name for name in os.listdir(WEB_FOLDER)
            if os.path.isdir(os.path.join(WEB_FOLDER, name))
        ]
        for i, s in enumerate(sites_list, 1):
            #general check all Nginx sites-available, sites-enabled folder + php pool.d/ are available
            #variable with full path to nginx sites-enabled symlink to the site
            ngx_site = os.path.join(NGX_SITES_PATH2,s)
            #variable with full path to php pool config of the site
            php_site = os.path.join(PHP_POOL,s+".conf")
            #check of nginx and php have active links and configs of the site
            if os.path.islink(ngx_site) and os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-success">{i}</th>
                <td class="table-success"><form method="post" action="/action"><button type="submit" value="{s}" name="delete" onclick="showLoading()" class="btn btn-danger">Delete site</button><button type="submit" value="{s}" name="disable" onclick="showLoading()" class="btn btn-warning">Disable site</button></form>
                <td class="table-success">{s}</td>
                <td class="table-success">{os.path.join(WEB_FOLDER,s)}</td>
                <td class="table-success">OK</td>
                \n</tr>"""
            #if nginx is ok but php is not
            elif os.path.islink(ngx_site) and not os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-danger">{i}</th>
                <td class="table-danger"><form method="post" action="/action"><button type="submit" value="{s}" name="delete" onclick="showLoading()" class="btn btn-danger">Delete site</button><button type="submit" value="{s}" name="enable" onclick="showLoading()" class="btn btn-warning">Re-enable site</button></form>
                <td class="table-danger">{s}</td>
                <td class="table-danger">{os.path.join(WEB_FOLDER,s)}</td>
                <td class="table-danger">PHP config error</td>
                \n</tr>"""
            #if php is ok but nginx is not
            elif not os.path.islink(ngx_site) and os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-danger">{i}</th>
                <td class="table-danger"><form method="post" action="/action"><button type="submit" value="{s}" name="delete" onclick="showLoading()" class="btn btn-danger">Delete site</button><button type="submit" value="{s}" name="enable" onclick="showLoading()" class="btn btn-warning">Re-enable site</button></form>
                <td class="table-danger">{s}</td>
                <td class="table-danger">{os.path.join(WEB_FOLDER,s)}</td>
                <td class="table-danger">Nginx config error</td>
                \n</tr>"""
            #if really disabled
            elif not os.path.islink(ngx_site) and not os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-warning">{i}</th>
                <td class="table-warning"><form method="post" action="/action"><button type="submit" value="{s}" name="delete" onclick="showLoading()" class="btn btn-danger">Delete site</button><button type="submit" value="{s}" name="enable" onclick="showLoading()" class="btn btn-success">Enable site</button></form>
                <td class="table-warning">{s}</td>
                <td class="table-warning">{os.path.join(WEB_FOLDER,s)}</td>
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
    generate_default_config()
    load_config()
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
                show_config()
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
    generate_default_config()
    load_config()
