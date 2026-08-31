import os
import re
import logging
import subprocess
from flask import current_app

#since nginx 1.25.1, the 'http2' listen parameter is deprecated in favor of a separate 'http2 on;' directive
NGINX_HTTP2_DIRECTIVE_MIN_VERSION = (1, 25, 1)

def _get_nginx_version() -> tuple:
  """Returns the installed nginx version as a (major, minor, patch) tuple, or None if it can't be detected."""
  try:
    result = subprocess.run(["sudo","nginx","-v"], capture_output=True, text=True, timeout=10)
    match = re.search(r"nginx/(\d+)\.(\d+)\.(\d+)", (result.stderr or "") + (result.stdout or ""))
    if not match:
      logging.error(f"_get_nginx_version(): could not parse nginx version from output: {result.stderr or result.stdout}")
      return None
    return tuple(int(part) for part in match.groups())
  except Exception as err:
    logging.error(f"_get_nginx_version(): error detecting nginx version: {err}")
    return None

def _nginx_supports_http2_directive() -> bool:
  """True if the installed nginx is >= 1.25.1 (separate 'http2 on;' directive instead of the 'listen ... http2;'
  parameter). Defaults to False (old-style, 'listen ... http2;') when the version can't be detected - this
  matches the behavior the project always had before this check existed."""
  version = _get_nginx_version()
  if version is None:
    return False
  return version >= NGINX_HTTP2_DIRECTIVE_MIN_VERSION

def create_nginx_config(filename: str,has_subdomain: str = "---") -> str:
  """Template. Function which creates an Nginx configuration for a site, taken from filename parameter."""
  #check if we have a subdomain to use correct certificates name
  if has_subdomain == "---":
    crt_filename = filename
  else:
    crt_filename = has_subdomain
  bind_ip = current_app.config.get("NGX_BIND_IP_ADDR","")
  #nginx >= 1.25.1: http2 moves off the listen line onto its own directive right below it
  if _nginx_supports_http2_directive():
    listen_ssl = f"listen {bind_ip}:443 ssl;\n  http2 on;"
  else:
    listen_ssl = f"listen {bind_ip}:443 ssl http2;"
  config = f"""server {{
    listen {bind_ip}:80;
    server_name {filename} www.{filename};
    return 301 https://{filename}$request_uri;
}}

server {{
  {listen_ssl}
  server_name www.{filename};
  ssl_certificate /etc/nginx/ssl/{crt_filename}.crt;
  ssl_certificate_key /etc/nginx/ssl/{crt_filename}.key;
  return 301 https://{filename}$request_uri;
}}

server {{
  {listen_ssl}
  server_name {filename};
  ssl_certificate /etc/nginx/ssl/{crt_filename}.crt;
  ssl_certificate_key /etc/nginx/ssl/{crt_filename}.key;
  access_log /var/log/nginx/access.log postdata;
  error_log /var/log/nginx/error.log;
  root {os.path.join(current_app.config.get("WEB_FOLDER"),filename)}/public;
  charset utf8;
  index index.php index.html index.htm;
  include additional-configs/301-{filename}.conf;
  add_header X-Content-Type-Options nosniff always;
  add_header X-Frame-Options SAMEORIGIN always;
  add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;

  if ($request_method !~ ^(GET|POST|HEAD)$) {{
    return 405;
  }}

  location ~ /\. {{
    deny all;
  }}

  location /admin/ {{
    set $no_cache 1;
    auth_basic "Prove you are who you are";
    auth_basic_user_file {os.path.join(current_app.config.get("NGX_PATH"),".htpasswd")};
    add_header Cache-Control "no-store, no-cache, must-revalidate" always;
    add_header Pragma "no-cache" always;
    try_files $uri $uri/ /index.php?$args;
    location ~* ^/admin/.+\.php$ {{
      include snippets/fastcgi-php.conf;
      fastcgi_pass unix:/var/run/php/php.sock;
      fastcgi_cache off;
      fastcgi_no_cache 1;
      fastcgi_cache_bypass 1;
      add_header Cache-Control "no-store, no-cache, must-revalidate" always;
      add_header Pragma "no-cache" always;
    }}
  }}

  location ~* ^/(?:robots.txt) {{
    try_files $uri $uri/ /index.php?$args;
  }}

  location ~* "\.(svg|svgz|eot|otf|webmanifest|woff|woff2|ttf|rss|css|swf|js|atom|jpe?g|gif|png|ico|html)$" {{
    add_header Cache-Control "public, max-age=2592000, immutable" always;
    try_files $uri =404;
  }}

  location / {{
    try_files $uri $uri/ /index.php?$args;
  }}

  location ~ \.php$ {{
    include snippets/fastcgi-php.conf;
    fastcgi_pass unix:/var/run/php/php.sock;
    fastcgi_cache PHP;
    fastcgi_cache_valid 200 10m;
    fastcgi_cache_valid 404 1m;
    fastcgi_cache_bypass $no_cache $cookie_session $cookie_PHPSESSID;
    fastcgi_no_cache     $no_cache $cookie_session $cookie_PHPSESSID;
    add_header X-Cache-Status $upstream_cache_status;
  }}
}}"""
  return config
