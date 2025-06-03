import sys
import os

#change to yours
venv_path = "/usr/local/"
sys.path.insert(0, os.path.join(venv_path, "lib/python3.11/site-packages"))
#change to yours
sys.path.insert(0, "/share/provision")

bind = "0.0.0.0:8880"
workers = 3
timeout = 30
loglevel = "info"
wsgi_app = "main:application"