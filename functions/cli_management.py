import logging
from db.db import db
from db.database import *
from functions.load_config import load_config
from flask import current_app
from sqlalchemy import text
from functions.cli_func_account import *
from functions.cli_func_cloudflare import *
from functions.cli_func_owner import *
from functions.cli_func_servers import *
from functions.cli_func_template import *
from functions.cli_func_user import *

def help_set() -> None:
  """CLI only function: shows hints for SET command"""
  print (f"""
Possible completion:
  chat       <telegram_chat_id>   
  log        <path_and_filename>
  nginxAddConfDir  <full_path>
  nginxCrtPath   <full_path>
  nginxPath    <full_path>
  phpPool      <full_path>
  nginxSitesPathAv <full_path>
  nginxSitesPathEn <full_path>
  phpFpmPath     <full_path>
  token      <telegram_token>
  webFolder    <full_path>
  wwwUser      <user>
  wwwGroup     <group>
  """)

def help_show() -> None:
  """CLI only function: shows hints for SHOW command"""
  print (f"""
Possible completion:
  accounts
  cloudflare
  config
  servers
  templates
  users
  """)

def set_telegramChat(tgChat: str) -> None:
  """CLI only function: sets Telegram ChatID value in database"""
  logging.info("-----------------------Starting CLI functions: set_telegramChat")
  try:
    t = Settings(id=1,telegramChat=tgChat.strip())
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    print("Telegram ChatID added successfully")
    logging.info(f"cli>Telegram ChatID updated successfully!")
    quit(0)
  except Exception as err:
    logging.error(f"cli>Telegram ChatID {tgChat} set error: {err}")
    print(f"Telegram ChatID {tgChat} set error: {err}")
    quit(1)

def set_telegramToken(tgToken: str) -> None:
  """CLI only function: sets Telegram Token value in database"""
  logging.info("-----------------------Starting CLI functions: set_telegramToken")
  try:
    t = Settings(id=1,telegramToken=tgToken)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    print("Telegram Token added successfully")
    logging.info(f"cli>Telegram Token updated successfully!")
    quit(0)
  except Exception as err:
    logging.error(f"cli>Telegram Token \"{tgToken}\" set error: {err}")
    print(f"Telegram Token \"{tgToken}\" set error: {err}")
    quit(1)

def set_logpath(logpath: str) -> None:
  """CLI only function: sets Logger file path value in database"""
  logging.info("-----------------------Starting CLI functions: set_logpath")
  try:
    t = Settings(id=1,logFile=logpath)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    updated = db.session.get(Settings, 1)
    print(f"logPath updated successfully. New log path: \"{updated.logFile}\"")
    logging.info(f"cli>logPath updated to \"{updated.logFile}\"")
    quit(0)
  except Exception as err:
    logging.error(f"cli>logPath update to \"{logpath}\" error: {err}")
    print(f"logPath update to \"{logpath}\" error: {err}")
    quit(1)

def set_webFolder(data: str) -> None:
  """CLI only function: sets webFolder parameter in database"""
  logging.info("-----------------------Starting CLI functions: set_webFolder")
  try:
    t = Settings(id=1,webFolder=data)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    updated = db.session.get(Settings, 1)
    print(f"Root web folder updated successfully. New path: \"{updated.webFolder}\"")
    logging.info(f"cli>Root web folder updated to \"{updated.webFolder}\"")
    quit(0)
  except Exception as err:
    logging.error(f"cli>Root web folder \"{data}\" set error: {err}")
    print(f"Root web folder \"{data}\" set error: {err}")
    quit(1)

def set_nginxCrtPath(data: str) -> None:
  """CLI only function: sets Nginx SSL certs path parameter in database"""
  logging.info("-----------------------Starting CLI functions: set_nginxCrtPath")
  try:
    t = Settings(id=1,nginxCrtPath=data)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    updated = db.session.get(Settings, 1)
    print(f"Nginx SSL folder updated successfully. New path: \"{updated.nginxCrtPath}\"")
    logging.info(f"cli>Nginx SSL folder updated to \"{updated.nginxCrtPath}\"")
    quit(0)
  except Exception as err:
    logging.error(f"cli>Nginx SSL folder \"{data}\" set error: {err}")
    print(f"Nginx SSL folder \"{data}\" set error: {err}")
    quit(1)

def set_wwwUser(data: str) -> None:
  """CLI only function: sets wwwUser parameter in database"""
  logging.info("-----------------------Starting CLI functions: set_wwwUser")
  try:
    t = Settings(id=1,wwwUser=data)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    updated = db.session.get(Settings, 1)
    print(f"User for web folders updated successfully to: \"{updated.wwwUser}\"")
    logging.info(f"cli>User for web folders updated to \"{updated.wwwUser}\"")
    quit(0)
  except Exception as err:
    logging.error(f"cli>User for web folders \"{data}\" set error: {err}")
    print(f"User for web folders \"{data}\" set error: {err}")
    quit(1)

def set_wwwGroup(data: str) -> None:
  """CLI only function: sets webGroup parameter in database"""
  logging.info("-----------------------Starting CLI functions: set_wwwGroup")
  try:
    t = Settings(id=1,wwwGroup=data)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    updated = db.session.get(Settings, 1)
    print(f"Group for web folders updated successfully to: \"{updated.wwwGroup}\"")
    logging.info(f"cli>Group for web folders updated to \"{updated.wwwGroup}\"")
    quit(0)
  except Exception as err:
    logging.error(f"cli>Group for web folders \"{data}\" set error: {err}")
    print(f"Group for web folders \"{data}\" set error: {err}")
    quit(1)

def set_nginxSitesPathAv(data: str) -> None:
  """CLI only function: sets Nginx Sites-Available folder path in database"""
  logging.info("-----------------------Starting CLI functions: set_nginxSitesPathAv")
  try:
    t = Settings(id=1,nginxSitesPathAv=data)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    updated = db.session.get(Settings, 1)
    print(f"Nginx Sites-available folder updated successfully to: \"{updated.nginxSitesPathAv}\"")
    logging.info(f"cli>Nginx Sites-available folder updated to \"{updated.nginxSitesPathAv}\"")
    quit(0)
  except Exception as err:
    logging.error(f"cli>Nginx Sites-available folder \"{data}\" set error: {err}")
    print(f"Nginx Sites-available folder \"{data}\" set error: {err}")
    quit(1)

def set_nginxSitesPathEn(data: str) -> None:
  """CLI only function: sets Nginx Sites-Enabled folder path in database"""
  logging.info("-----------------------Starting CLI functions: set_nginxSitesPathEn")
  try:
    t = Settings(id=1,nginxSitesPathEn=data)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    updated = db.session.get(Settings, 1)
    print(f"Nginx Sites-enabled folder updated successfully to: \"{updated.nginxSitesPathEn}\"")
    logging.info(f"cli>Nginx Sites-enabled folder updated to \"{updated.nginxSitesPathEn}\"")
    quit(0)
  except Exception as err:
    logging.error(f"cli>Nginx Sites-enabled folder \"{data}\" set error: {err}")
    print(f"Nginx Sites-enabled folder \"{data}\" set error: {err}")
    quit(1)

def set_nginxPath(data: str) -> None:
  """CLI only function: sets Nginx main configs directory"""
  logging.info("-----------------------Starting CLI functions: set_nginxPath")
  try:
    t = Settings(id=1,nginxPath=data)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    updated = db.session.get(Settings, 1)
    print(f"Nginx Path updated successfully to: \"{updated.nginxPath}\"")
    logging.info(f"cli>Nginx Path updated to \"{updated.nginxPath}\"")
    quit(0)
  except Exception as err:
    logging.error(f"cli>Nginx Path \"{data}\" set error: {err}")
    print(f"Nginx Path \"{data}\" set error: {err}")
    quit(1)

def set_nginxAddConfDir(data: str) -> None:
  """CLI only function: sets the directory for additional config files"""
  logging.info("-----------------------Starting CLI functions: set_nginxAddConfDir")
  try:
    t = Settings(id=1,nginxAddConfDir=data)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    updated = db.session.get(Settings, 1)
    print(f"Nginx Additional configs dir. updated successfully to: \"{updated.nginxAddConfDir}\"")
    logging.info(f"cli>Nginx Additional configs dir. updated to \"{updated.nginxAddConfDir}\"")
    quit(0)
  except Exception as err:
    logging.error(f"cli>Nginx Additional configs dir. \"{data}\" set error: {err}")
    print(f"Nginx Additional configs dir. \"{data}\" set error: {err}")
    quit(1)

def set_phpPool(data: str) -> None:
  """CLI only function: sets PHP pool.d/ folder path in database"""
  logging.info("-----------------------Starting CLI functions: set_phpPool")
  try:
    t = Settings(id=1,nginxSitesPathEn=data)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    updated = db.session.get(Settings, 1)
    print(f"PHP Pool.d/ folder updated successfully to: \"{updated.phpPool}\"")
    logging.info(f"cli>PHP Pool.d/ folder updated to \"{updated.phpPool}\"")
    quit(0)
  except Exception as err:
    logging.error(f"cli>PHP Pool.d/ folder \"{data}\" set error: {err}")
    print(f"PHP Pool.d/ folder \"{data}\" set error: {err}")
    quit(1)

def set_phpFpmPath(data: str) -> None:
  """CLI only function: sets PHP binary path in database"""
  logging.info("-----------------------Starting CLI functions: set_phpFpmPath")
  try:
    t = Settings(id=1,nginxSitesPathEn=data)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    updated = db.session.get(Settings, 1)
    print(f"Php-fpm executable path updated successfully to: \"{updated.phpFpmPath}\"")
    logging.info(f"cli>Php-fpm executable path updated to \"{updated.phpFpmPath}\"")
    quit(0)
  except Exception as err:
    logging.error(f"cli>Php-fpm executable path \"{data}\" set error: {err}")
    print(f"Php-fpm executable path \"{data}\" set error: {err}")
    quit(1)

def flush_sessions() -> None:
  """CLI only function: deletes all sessions records from the Flask table in the database"""
  logging.info("-----------------------Starting CLI functions: flush_sessions")
  try:
    db.session.execute(text("TRUNCATE TABLE flask_sessions RESTART IDENTITY"))
    db.session.commit()
    quit(0)
  except Exception as err:
    logging.error(f"cli>CLI flush sessions function error: {err}")
    print(f"CLI flush sessions function error: {err}")
    quit(1)

def show_config() -> None:
  """CLI only function: shows all current config from the database"""
  print (f"""
Telegram ChatID:     {current_app.config["TELEGRAM_TOKEN"]}
Telegram Token:      {current_app.config["TELEGRAM_CHATID"]}
Log file:        {current_app.config["LOG_FILE"]}
SessionKey:        {current_app.config["SECRET_KEY"]}
Web root folder:     {current_app.config["WEB_FOLDER"]}
Nginx SSL folder:    {current_app.config["NGX_CRT_PATH"]}
WWW folders user:    {current_app.config["WWW_USER"]}
WWW folders group:     {current_app.config["WWW_GROUP"]}
Nginx Sites-Available:   {current_app.config["NGX_SITES_PATHAV"]}
Nginx Sites-Enabled:   {current_app.config["NGX_SITES_PATHEN"]}
Nginx conf. main dir:  {current_app.config["NGX_PATH"]}
Nginx add. configs dir:  {current_app.config["NGX_ADD_CONF_DIR"]}
Php Pool.d folder:     {current_app.config["PHP_POOL"]}
Php-fpm executable:    {current_app.config["PHPFPM_PATH"]}
key:           {current_app.secret_key}
  """)
  quit(0)
