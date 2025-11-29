import logging
from db.db import db
from db.database import Settings,User,Provision_templates
from functions.load_config import load_config
from flask import current_app
from werkzeug.security import generate_password_hash
from sqlalchemy import text

def set_telegramChat(tgChat: str) -> None:
    """CLI only function: sets Telegram ChatID value in database"""
    logging.info("Starting CLI functions: set_telegramChat")
    t = Settings(id=1,telegramChat=tgChat.strip())
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    print("Telegram ChatID added successfully")
    try:
        logging.info(f"Telegram ChatID updated successfully!")
    except Exception as err:
        pass

def set_telegramToken(tgToken: str) -> None:
    """CLI only function: sets Telegram Token value in database"""
    logging.info("Starting CLI functions: set_telegramToken")
    t = Settings(id=1,telegramToken=tgToken)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    print("Telegram Token added successfully")
    try:
        logging.info(f"Telegram Token updated successfully!")
    except Exception as err:
        pass

def set_logpath(logpath: str) -> None:
    """CLI only function: sets Logger file path value in database"""
    logging.info("Starting CLI functions: set_logpath")
    t = Settings(id=1,logFile=logpath)
    db.session.merge(t)
    db.session.commit()
    load_config(current_app)
    updated = db.session.get(Settings, 1)
    print(f"logPath updated successfully. New log path: \"{updated.logFile}\"")
    try:
        logging.info(f"logPath updated to \"{updated.logFile}\"")
    except Exception as err:
        pass

def register_user(username: str,password: str,realname: str) -> None:
    """CLI only function: adds new user and saves to database"""
    logging.info("Starting CLI functions: register_user")
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
            load_config(current_app)
            print(f"New user \"{username}\" - \"{realname}\" created successfully!")
            logging.info(f"New user \"{username}\" - \"{realname}\" created successfully!")
    except Exception as err:
        logging.error(f"User \"{username}\" - \"{realname}\" creation error: {err}")
        print(f"User \"{username}\" - \"{realname}\" creation error: {err}")

def update_user(username: str,password: str) -> None:
    """CLI only function: password change for existing user"""
    logging.info("Starting CLI functions: update_user")
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            d = User(id=user.id,password_hash=generate_password_hash(password))
            db.session.merge(d)
            db.session.commit()
            print(f"Password for user \"{user.username}\" updated successfully!")
            logging.info(f"Password for user \"{user.username}\" updated successfully!")
        else:
            print(f"User \"{username}\" set password error - no such user!")
            logging.error(f"User \"{username}\" set password error - no such user!")
            quit(1)
    except Exception as err:
        logging.error(f"User \"{username}\" set password error: {err}")
        print(f"User \"{username}\" set password error: {err}")

def delete_user(username: str) -> None:
    """CLI only function: deletes an existing user from database"""
    logging.info("Starting CLI functions: delete_user")
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            load_config(current_app)
            print(f"User \"{user.username}\" deleted successfully!")
            logging.info(f"User \"{user.username}\" deleted successfully!")
        else:
            print(f"User \"{username}\" delete error - no such user!")
            logging.error(f"User \"{username}\" delete error - no such user!")
            quit(1)
    except Exception as err:
        logging.error(f"User \"{username}\" delete error: {err}")
        print(f"User \"{username}\" delete error: {err}")

def show_users() -> None:
    """Shows all users in database"""
    logging.info("Starting CLI functions: show_users")
    try:
        users = User.query.order_by(User.username).all()
        if len(users) == 0:
            print("No users found in DB!")
            quit()
        for i, s in enumerate(users, 1):
            print(f"ID: {s.id}, Login: {s.username}, RealName: {s.realname}, Created: {s.created}")
    except Exception as err:
        logging.error(f"CLI show users function error: {err}")
        print(f"CLI show users function error: {err}")

def set_webFolder(data: str) -> None:
    """CLI only function: sets webFolder parameter in database"""
    logging.info("Starting CLI functions: set_webFolder")
    try:
        t = Settings(id=1,webFolder=data)
        db.session.merge(t)
        db.session.commit()
        load_config(current_app)
        updated = db.session.get(Settings, 1)
        print(f"Root web folder updated successfully. New path: \"{updated.webFolder}\"")
        logging.info(f"Root web folder updated to \"{updated.webFolder}\"")
    except Exception as err:
        logging.error(f"Root web folder \"{data}\" set error: {err}")
        print(f"Root web folder \"{data}\" set error: {err}")

def set_nginxCrtPath(data: str) -> None:
    """CLI only function: sets Nginx SSL certs path parameter in database"""
    logging.info("Starting CLI functions: set_nginxCrtPath")
    try:
        t = Settings(id=1,nginxCrtPath=data)
        db.session.merge(t)
        db.session.commit()
        load_config(current_app)
        updated = db.session.get(Settings, 1)
        print(f"Nginx SSL folder updated successfully. New path: \"{updated.nginxCrtPath}\"")
        logging.info(f"Nginx SSL folder updated to \"{updated.nginxCrtPath}\"")
    except Exception as err:
        logging.error(f"Nginx SSL folder \"{data}\" set error: {err}")
        print(f"Nginx SSL folder \"{data}\" set error: {err}")

def set_wwwUser(data: str) -> None:
    """CLI only function: sets wwwUser parameter in database"""
    logging.info("Starting CLI functions: set_wwwUser")
    try:
        t = Settings(id=1,wwwUser=data)
        db.session.merge(t)
        db.session.commit()
        load_config(current_app)
        updated = db.session.get(Settings, 1)
        print(f"User for web folders updated successfully to: \"{updated.wwwUser}\"")
        logging.info(f"User for web folders updated to \"{updated.wwwUser}\"")
    except Exception as err:
        logging.error(f"User for web folders \"{data}\" set error: {err}")
        print(f"User for web folders \"{data}\" set error: {err}")

def set_wwwGroup(data: str) -> None:
    """CLI only function: sets webGroup parameter in database"""
    logging.info("Starting CLI functions: set_wwwGroup")
    try:
        t = Settings(id=1,wwwGroup=data)
        db.session.merge(t)
        db.session.commit()
        load_config(current_app)
        updated = db.session.get(Settings, 1)
        print(f"Group for web folders updated successfully to: \"{updated.wwwGroup}\"")
        logging.info(f"Group for web folders updated to \"{updated.wwwGroup}\"")
    except Exception as err:
        logging.error(f"Group for web folders \"{data}\" set error: {err}")
        print(f"Group for web folders \"{data}\" set error: {err}")

def set_nginxSitesPathAv(data: str) -> None:
    """CLI only function: sets Nginx Sites-Available folder path in database"""
    logging.info("Starting CLI functions: set_nginxSitesPathAv")
    try:
        t = Settings(id=1,nginxSitesPathAv=data)
        db.session.merge(t)
        db.session.commit()
        load_config(current_app)
        updated = db.session.get(Settings, 1)
        print(f"Nginx Sites-available folder updated successfully to: \"{updated.nginxSitesPathAv}\"")
        logging.info(f"Nginx Sites-available folder updated to \"{updated.nginxSitesPathAv}\"")
    except Exception as err:
        logging.error(f"Nginx Sites-available folder \"{data}\" set error: {err}")
        print(f"Nginx Sites-available folder \"{data}\" set error: {err}")

def set_nginxSitesPathEn(data: str) -> None:
    """CLI only function: sets Nginx Sites-Enabled folder path in database"""
    logging.info("Starting CLI functions: set_nginxSitesPathEn")
    try:
        t = Settings(id=1,nginxSitesPathEn=data)
        db.session.merge(t)
        db.session.commit()
        load_config(current_app)
        updated = db.session.get(Settings, 1)
        print(f"Nginx Sites-enabled folder updated successfully to: \"{updated.nginxSitesPathEn}\"")
        logging.info(f"Nginx Sites-enabled folder updated to \"{updated.nginxSitesPathEn}\"")
    except Exception as err:
        logging.error(f"Nginx Sites-enabled folder \"{data}\" set error: {err}")
        print(f"Nginx Sites-enabled folder \"{data}\" set error: {err}")

def set_phpPool(data: str) -> None:
    """CLI only function: sets PHP pool.d/ folder path in database"""
    logging.info("Starting CLI functions: set_phpPool")
    try:
        t = Settings(id=1,nginxSitesPathEn=data)
        db.session.merge(t)
        db.session.commit()
        load_config(current_app)
        updated = db.session.get(Settings, 1)
        print(f"PHP Pool.d/ folder updated successfully to: \"{updated.phpPool}\"")
        logging.info(f"PHP Pool.d/ folder updated to \"{updated.phpPool}\"")
    except Exception as err:
        logging.error(f"PHP Pool.d/ folder \"{data}\" set error: {err}")
        print(f"PHP Pool.d/ folder \"{data}\" set error: {err}")

def set_phpFpmPath(data: str) -> None:
    """CLI only function: sets PHP binary path in database"""
    logging.info("Starting CLI functions: set_phpFpmPath")
    try:
        t = Settings(id=1,nginxSitesPathEn=data)
        db.session.merge(t)
        db.session.commit()
        load_config(current_app)
        updated = db.session.get(Settings, 1)
        print(f"Php-fpm executable path updated successfully to: \"{updated.phpFpmPath}\"")
        logging.info(f"Php-fpm executable path updated to \"{updated.phpFpmPath}\"")
    except Exception as err:
        logging.error(f"Php-fpm executable path \"{data}\" set error: {err}")
        print(f"Php-fpm executable path \"{data}\" set error: {err}")

def flush_sessions() -> None:
    """CLI only function: deletes all sessions records from the Flask table in the database"""
    logging.info("Starting CLI functions: flush_sessions")
    try:
        db.session.execute(text("TRUNCATE TABLE flask_sessions RESTART IDENTITY"))
        db.session.commit()
    except Exception as err:
        logging.error(f"CLI flush sessions function error: {err}")
        print(f"CLI flush sessions function error: {err}")

def show_config() -> None:
    """CLI only function: shows all current config from the database"""
    print (f"""
Telegram ChatID:       {current_app.config["TELEGRAM_TOKEN"]}
Telegram Token:        {current_app.config["TELEGRAM_CHATID"]}
Log file:              {current_app.config["LOG_FILE"]}
SessionKey:            {current_app.config["SECRET_KEY"]}
Web root folder:       {current_app.config["WEB_FOLDER"]}
Nginx SSL folder:      {current_app.config["NGX_CRT_PATH"]}
WWW folders user:      {current_app.config["WWW_USER"]}
WWW folders group:     {current_app.config["WWW_GROUP"]}
Nginx Sites-Available: {current_app.config["NGX_SITES_PATHAV"]}
Nginx Sites-Enabled:   {current_app.config["NGX_SITES_PATHEN"]}
Php Pool.d folder:     {current_app.config["PHP_POOL"]}
Php-fpm executable:    {current_app.config["PHPFPM_PATH"]}
key:                   {current_app.secret_key}
    """)

def show_help(programm: str) -> None:
    """CLI only function: shows program CLI commands usage information"""
    print(f"""Usage: \n{programm} set chat <chatID>
\tAdd Telegram ChatID for notifications.
{programm} set token <Token>
\tAdd Telegram Token for notifications.
{programm} set logpath <new log file path>
\tAdd Telegram Token for notifications.
{programm} user add <login> <password> <realname>
\tAdd new user with its password and default permissions for all cache pathes.
{programm} user setpwd <user> <new password>
\tSet new password for existing user.
{programm} user del <user>
\tDelete existing user by its login
{programm} cfaccount add <name> <token>
\tAdd new CF account and its token
{programm} cfaccount import <path to file>
\tImport CF account records from file
{programm} cfaccount del <name>
\tDelete CF account entry\n
Info: full script should be launched via UWSGI server. In CLI mode use can only use commands above.
    """)

def add_template(name: str,repository: str) -> None:
    """CLI only function: adds new template of site provision to the database"""
    logging.info("Starting CLI functions: add_template")
    try:
        if Provision_templates.query.filter_by(name=name).first():
            print(f"Template name \"{name}\" creation error - already exists!")
            logging.error(f"Template name \"{name}\" creation error - already exists!")
        else:
            new_template = Provision_templates(
                name=name,
                repository=repository,
            )
            db.session.add(new_template)
            db.session.commit()
            print(f"New template \"{name}\" - \"{repository}\" created successfully!")
            logging.info(f"New template \"{name}\" - \"{repository}\" created successfully!")
    except Exception as err:
        logging.error(f"New repository \"{name}\" - \"{repository}\" creation error: {err}")
        print(f"New repository \"{name}\" - \"{repository}\" creation error: {err}")

def del_template(name: str) -> None:
    """CLI only function: deletes a template of site provision from the database"""
    logging.info("Starting CLI functions: del_template")
    try:
        template = Provision_templates.query.filter_by(name=name).first()
        if template:
            db.session.delete(template)
            db.session.commit()
            load_config(current_app)
            print(f"Template \"{template.name}\" deleted successfully!")
            logging.info(f"Template \"{template.name}\" deleted successfully!")
        else:
            print(f"Template \"{name}\" deletion error - no such template!")
            logging.error(f"Template \"{name}\" deletion error - no such template!")
            quit(1)
    except Exception as err:
        logging.error(f"Template \"{name}\" deletion error: {err}")
        print(f"Template \"{name}\" deletion error: {err}")

def upd_template(name: str, new_repository: str) -> None:
    """CLI only function: updates a template with a new repository address"""
    logging.info("Starting CLI functions: upd_template")
    try:
        template = Provision_templates.query.filter_by(name=name).first()
        if template:
            template.repository = new_repository
            db.session.commit()
            print(f"Repository for template \"{name}\" updated successfully to {new_repository}!")
            logging.info(f"Repository for template \"{name}\" updated successfully to{new_repository}!")
        else:
            print(f"Template \"{name}\" update error - no such template!")
            logging.error(f"Template \"{name}\" update error - no such template!")
            quit(1)
    except Exception as err:
        logging.error(f"Template \"{name}\" update error: {err}")
        print(f"Template \"{name}\" update error: {err}")

def show_templates() -> None:
    """CLI only function: shows all available site provision repositories from the database"""
    logging.info("Starting CLI functions: show_templates")
    try:
        templates = Provision_templates.query.order_by(Provision_templates.name).all()
        if len(templates) == 0:
            print("No templates found in DB!")
            quit()
        for i, s in enumerate(templates, 1):
            print(f"ID: {s.id},\nName: {s.name},\nRepository address: {s.repository},\nIsDefault: {s.isdefault},\nCreated: {s.created}\n--------------------------------------------------------")
    except Exception as err:
        logging.error(f"CLI show templates function error: {err}")
        print(f"CLI show templates function error: {err}")

def default_template(name: str) -> None:
    """CLI only function: sets a template as the default one"""
    logging.info("Starting CLI functions: default_template")
    try:
        #Check is the new record, which will be the default one, exists at all
        template = Provision_templates.query.filter_by(name=name).first()
        if not template:
            print(f"Template \"{name}\" doesn't exists! Can set it as the default one!")
            logging.error(f"Template \"{name}\" doesn't exists! Can set it as the default one!")
            quit(1)
        #Check if it is already is the default one
        default_template = Provision_templates.query.filter_by(isdefault=True).first()
        if default_template:
            if default_template.name == name:
                print(f"Template \"{name}\" already is the default one!")
                logging.error(f"Template \"{name}\" already is the default one!")
                quit(1)
        #Main function. First of all set all existing records as not default
        Provision_templates.query.update({Provision_templates.isdefault: False})
        #set one selected record as the default one
        template = Provision_templates.query.filter_by(name=name).first()
        if template:
            template.isdefault = True
            db.session.commit()
            print(f"The template \"{name}\" is set as default one!")
            logging.info(f"The template \"{name}\" is set as default one!")
    except Exception as err:
        logging.error(f"Set default template \"{name}\" error: {err}")
        print(f"Set default template \"{name}\" error: {err}")
