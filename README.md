# Important files for application:
-Create Gunicorn config file in programm's directory (gunicorn_config.py)  
-Create gunicorn-provision.service in programm's directory and make symlink to /etc/system.d/system/, then command:   
```
systemctl daemon-reload  
systemctl start gunicorn-provision  
```
Don't foreget to replace path to yours one  
  
-Systemd service file(gunicorn-provision.service):
```
[Unit]
Description=Gunicorn instance for provision.py
After=network.target

[Service]
User=root
Group=root
WorkingDirectory=/opt/provision
Environment="PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
ExecStart=/usr/bin/gunicorn -c /opt/provision/gunicorn_config.py main:application
StandardOutput=append:/var/log/gunicorn/provision.log
StandardError=append:/var/log/gunicorn/provision-error.log

[Install]
WantedBy=multi-user.target
```
-Gunicorn settings file:
```
import sys
import os

#change to yours
venv_path = "/usr/local/"
sys.path.insert(0, os.path.join(venv_path, "lib/python3.11/site-packages"))
#change to yours
sys.path.insert(0, "/opt/provision")

bind = "0.0.0.0:8880"
workers = 3
timeout = 30
loglevel = "info"
wsgi_app = "main:application"
```  