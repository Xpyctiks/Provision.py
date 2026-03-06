import os
from flask import current_app

def create_nginx_config(filename: str,has_subdomain: str = "---") -> str:
  """Template. Function which creates an Nginx configuration for a site, taken from filename parameter."""
  #check if we have a subdomain to use correct certificates name
  if has_subdomain == "---":
    crt_filename = filename
  else:
    crt_filename = has_subdomain
  config = f"""server {{
    listen 203.161.35.70:80;
    server_name {filename} www.{filename};
    return 301 https://{filename};
}}

server {{
  listen 203.161.35.70:443 ssl http2;
  server_name www.{filename};
  ssl_certificate /etc/nginx/ssl/{crt_filename}.crt;
  ssl_certificate_key /etc/nginx/ssl/{crt_filename}.key;
  return 301 https://{filename}$request_uri;
}}

server {{
  listen 203.161.35.70:443 ssl http2;
  server_name {filename};
  ssl_certificate /etc/nginx/ssl/{crt_filename}.crt;
  ssl_certificate_key /etc/nginx/ssl/{crt_filename}.key;
  access_log /var/log/nginx/access.log postdata;
  error_log /var/log/nginx/error.log;
  root {os.path.join(current_app.config.get("WEB_FOLDER"),filename)}/public;
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
    root {os.path.join(current_app.config.get("WEB_FOLDER"),filename)}/public;
    auth_basic "Prove you are who you are";
    auth_basic_user_file {os.path.join(current_app.config.get("NGX_PATH"),".htpasswd")};
    try_files $uri $uri/ /index.php?$args;
    location ~* ^/admin/.+\.php$ {{
      include snippets/fastcgi-php.conf;
      fastcgi_pass unix:/var/run/php/php.sock;
    }}
  }}

  location ~* ^/(?:robots.txt) {{
    allow all;
    root {os.path.join(current_app.config.get("WEB_FOLDER"),filename)}/public;
    try_files $uri $uri/ /index.php?$args;
  }}

  location ~* ".+\.(?:svg|svgz|eot|otf|webmanifest|woff|woff2|ttf|rss|css|swf|js|atom|jpe?g|gif|png|ico|html)$" {{
    allow all;
    root {os.path.join(current_app.config.get("WEB_FOLDER"),filename)}/public;
    try_files $uri $uri/;
  }}

  location / {{
    try_files $uri $uri/ /index.php?$args;
  }}

  location ~ \.php$ {{
    include snippets/fastcgi-php.conf;
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Content-Type-Options nosniff;
    add_header X-Frame-Options SAMEORIGIN;
    fastcgi_pass unix:/var/run/php/php.sock;
  }}
}}"""
  return config
