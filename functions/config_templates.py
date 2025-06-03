import os
from flask import current_app

def create_php_config(filename):
    config = f"""[{filename}]
user = {current_app.config["WWW_USER"]}
group = {current_app.config["WWW_GROUP"]}
listen = /run/php/{filename}.sock
listen.owner = {current_app.config["WWW_USER"]}
listen.group = {current_app.config["WWW_GROUP"]}
listen.mode = 0660
listen.allowed_clients = 127.0.0.1
pm = dynamic
pm.max_children = 5
pm.start_servers = 2
pm.min_spare_servers = 1
pm.max_spare_servers = 3
chdir = {os.path.join(current_app.config["WEB_FOLDER"],filename)}
env[HOSTNAME] = {filename}
env[PATH] = /usr/local/bin:/usr/bin:/bin
env[TMP] = /tmp
env[TMPDIR] = /tmp
env[TEMP] = /tmp
php_admin_value[error_log] = /var/log/nginx/php-fpm_{filename}.log
php_admin_flag[log_errors] = on
php_admin_value[open_basedir] = {os.path.join(current_app.config["WEB_FOLDER"],filename)}:/tmp
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
      return 301 https://{filename}$request_uri;
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
    root {os.path.join(current_app.config["WEB_FOLDER"],filename)}/public;
    charset utf8;
    index index.php index.html index.htm;
    include additional-configs/301-{filename}.conf;
    
    if ($request_method !~ ^(GET|POST|HEAD)$ ) {{
      return 403 "Forbidden!";
    }}

    location ~ /\..*/ {{
      deny all;
    }}

    location /admin/ {{
      auth_basic "Prove you are who you are";
      auth_basic_user_file {os.path.join(current_app.config["WEB_FOLDER"],filename)}/htpasswd;
      location ~* ^/admin/.+\.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/var/run/php/{filename}.sock;
      }}
    }}

    location ~* ^/(?:robots.txt) {{
      allow all;
      root {os.path.join(current_app.config["WEB_FOLDER"],filename)}/public;
      try_files $uri $uri/ /index.php?$args;
    }}

    location ~* ".+\.(?:svg|svgz|eot|otf|webmanifest|woff|woff2|ttf|rss|css|swf|js|atom|jpe?g|gif|png|ico|html)$" {{
        allow all;
        root {os.path.join(current_app.config["WEB_FOLDER"],filename)}/public;
        try_files $uri $uri/;
    }}

    location / {{
      if ( $request_uri != "/") {{ return 301 https://{filename}/; }}
      try_files $uri $uri/ /index.php?$args @home;
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
