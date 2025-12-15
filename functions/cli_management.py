import logging,os
from db.db import db
from db.database import *
from functions.load_config import load_config
from flask import current_app
from werkzeug.security import generate_password_hash
from sqlalchemy import text

def help_owner() -> None:
    """CLI only function: shows hints for OWNER command"""
    print (f"""
Possible completion:
    add    <domain> <database ID>
    upd    <domain> <new_database_ID>
    del    <domain>
        Important: <ID> means unique user ID from its database record in Users table. Integer value only.
    """)

def help_set() -> None:
    """CLI only function: shows hints for SET command"""
    print (f"""
Possible completion:
    chat             <telegram_chat_id>
    token            <telegram_token>
    log              <path_and_filename>
    webFolder        <full_path>
    nginxCrtPath     <full_path>
    wwwUser          <user>
    wwwGroup         <group>
    nginxSitesPathAv <full_path>
    nginxSitesPathEn <full_path>
    nginxPath        <full_path>
    nginxAddConfDir  <full_path>
    phpPool          <full_path>
    phpFpmPath       <full_path>
    """)

def help_user() -> None:
    """CLI only function: shows hints for USER command"""
    print (f"""
Possible completion:
    add    <login> <password> <realName>
    setpwd <login> <new_password>
    del    <login>
    """)

def help_show() -> None:
    """CLI only function: shows hints for SHOW command"""
    print (f"""
Possible completion:
    config
    users
    config
    cloudflare
    servers
    templates
    """)

def help_templates() -> None:
    """CLI only function: shows hints for TEMPLATES command"""
    print (f"""
Possible completion:
    add     <name> <git_repo_address>
    upd     <name> <new_git_repo_address>
    del     <name>
    default <name>
    """)

def help_cloudflare() -> None:
    """CLI only function: shows hints for CLOUDFLARE command"""
    print (f"""
Possible completion:
    add     <email> <api_token>
    upd     <email> <new_api_token>
    del     <email>
    default <email>
    """)

def help_servers() -> None:
    """CLI only function: shows hints for SERVERS command"""
    print (f"""
Possible completion:
    add     <server_name> <IP_address>
    upd     <server_name> <new_IP_address>
    del     <server_name>
    default <server_name>
    """)

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

def set_nginxPath(data: str) -> None:
    """CLI only function: sets Nginx main configs directory"""
    logging.info("Starting CLI functions: set_nginxPath")
    try:
        t = Settings(id=1,nginxPath=data)
        db.session.merge(t)
        db.session.commit()
        load_config(current_app)
        updated = db.session.get(Settings, 1)
        print(f"Nginx Path updated successfully to: \"{updated.nginxPath}\"")
        logging.info(f"Nginx Path updated to \"{updated.nginxPath}\"")
    except Exception as err:
        logging.error(f"Nginx Path \"{data}\" set error: {err}")
        print(f"Nginx Path \"{data}\" set error: {err}")

def set_nginxAddConfDir(data: str) -> None:
    """CLI only function: sets the directory for additional config files"""
    logging.info("Starting CLI functions: set_nginxAddConfDir")
    try:
        t = Settings(id=1,nginxAddConfDir=data)
        db.session.merge(t)
        db.session.commit()
        load_config(current_app)
        updated = db.session.get(Settings, 1)
        print(f"Nginx Additional configs dir. updated successfully to: \"{updated.nginxAddConfDir}\"")
        logging.info(f"Nginx Additional configs dir. updated to \"{updated.nginxAddConfDir}\"")
    except Exception as err:
        logging.error(f"Nginx Additional configs dir. \"{data}\" set error: {err}")
        print(f"Nginx Additional configs dir. \"{data}\" set error: {err}")

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
Telegram ChatID:         {current_app.config["TELEGRAM_TOKEN"]}
Telegram Token:          {current_app.config["TELEGRAM_CHATID"]}
Log file:                {current_app.config["LOG_FILE"]}
SessionKey:              {current_app.config["SECRET_KEY"]}
Web root folder:         {current_app.config["WEB_FOLDER"]}
Nginx SSL folder:        {current_app.config["NGX_CRT_PATH"]}
WWW folders user:        {current_app.config["WWW_USER"]}
WWW folders group:       {current_app.config["WWW_GROUP"]}
Nginx Sites-Available:   {current_app.config["NGX_SITES_PATHAV"]}
Nginx Sites-Enabled:     {current_app.config["NGX_SITES_PATHEN"]}
Nginx conf. main dir:    {current_app.config["NGX_PATH"]}
Nginx add. configs dir:  {current_app.config["NGX_ADD_CONF_DIR"]}
Php Pool.d folder:       {current_app.config["PHP_POOL"]}
Php-fpm executable:      {current_app.config["PHPFPM_PATH"]}
key:                     {current_app.secret_key}
    """)

def show_help(programm: str) -> None:
    """CLI only function: shows program CLI commands usage information"""
    print(f"""Usage: \n{programm} set 
\tGet info about all SET options.
{programm} show
\tGet info about all SHOW options.
{programm} user
\tGet info about all USER options.
{programm} templates
\tGet info about all TEMPLATES options.
{programm} cloudflare
\tGet info about all CLOUDFLARE options.
{programm} servers
\tGet info about all SERVERS options.
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
        #check if there is only one just added record - set it as default
        if len(Provision_templates.query.filter_by().all()) == 1:
            tmp = Provision_templates.query.filter_by(name=name).first()
            if tmp:
                tmp.isdefault = True
                db.session.commit()
    except Exception as err:
        logging.error(f"New repository \"{name}\" - \"{repository}\" creation error: {err}")
        print(f"New repository \"{name}\" - \"{repository}\" creation error: {err}")

def del_template(name: str) -> None:
    """CLI only function: deletes a template of site provision from the database"""
    logging.info("Starting CLI functions: del_template")
    try:
        template = Provision_templates.query.filter_by(name=name).first()
        if template:
            if template.isdefault == True:
                print("Warning, that was the Default template. You need to make another template the default one!")
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

def add_cloudflare(account: str,token: str) -> None:
    """CLI only function: adds a new Cloudflare account and its token to the database"""
    logging.info("Starting CLI functions: add_cloudflare")
    try:
        if Cloudflare.query.filter_by(account=account).first():
            print(f"Account \"{account}\" creation error - already exists!")
            logging.error(f"Account \"{account}\" creation error - already exists!")
        else:
            new_account = Cloudflare(
                account=account,
                token=token,
            )
            db.session.add(new_account)
            db.session.commit()
            print(f"New account \"{account}\" created successfully!")
            logging.info(f"New account \"{account}\" created successfully!")
        #check if there is only one just added record - set it as default
        if len(Cloudflare.query.filter_by().all()) == 1:
            acc = Cloudflare.query.filter_by(account=account).first()
            if acc:
                acc.isdefault = True
                db.session.commit()
    except Exception as err:
        logging.error(f"New account \"{account}\" creation error: {err}")
        print(f"New account \"{account}\" creation error: {err}")

def del_cloudflare(account: str) -> None:
    """CLI only function: deletes a Cloudflare account from the database"""
    logging.info("Starting CLI functions: del_cloudflare")
    try:
        acc = Cloudflare.query.filter_by(account=account).first()
        if acc:
            if acc.isdefault == True:
                print("Warning, that was the Default account. You need to make another account the default one!")
            db.session.delete(acc)
            db.session.commit()
            load_config(current_app)
            print(f"Cloudflare account \"{acc.account}\" deleted successfully!")
            logging.info(f"Cloudflare account \"{acc.account}\" deleted successfully!")
        else:
            print(f"Cloudflare account \"{account}\" deletion error - no such account!")
            logging.error(f"Cloudflare account \"{account}\" deletion error - no such account!")
            quit(1)
    except Exception as err:
        logging.error(f"Cloudflare account \"{account}\" deletion error: {err}")
        print(f"Cloudflare account \"{account}\" deletion error: {err}")

def upd_cloudflare(account: str, new_token: str) -> None:
    """CLI only function: updates a Cloudflare account with the new token"""
    logging.info("Starting CLI functions: upd_cloudflare")
    try:
        acc = Cloudflare.query.filter_by(account=account).first()
        if acc:
            acc.token = new_token
            db.session.commit()
            print(f"Account \"{account}\" updated successfully to {new_token}!")
            logging.info(f"Account \"{account}\" updated successfully to{new_token}!")
        else:
            print(f"Account \"{account}\" update error - no such account!")
            logging.error(f"Account \"{account}\" update error - no such account!")
            quit(1)
    except Exception as err:
        logging.error(f"Account \"{account}\" update error: {err}")
        print(f"Account \"{account}\" update error: {err}")

def show_cloudflare() -> None:
    """CLI only function: shows all available Cloudflare accounts from the database"""
    logging.info("Starting CLI functions: show_cloudflare")
    try:
        accs = Cloudflare.query.order_by(Cloudflare.account).all()
        if len(accs) == 0:
            print("No accounts found in DB!")
            quit()
        for i, s in enumerate(accs, 1):
            print(f"ID: {s.id},\nAccount: {s.account},\nToken: {s.token},\nIsDefault: {s.isdefault},\nCreated: {s.created}\n--------------------------------------------------------")
    except Exception as err:
        logging.error(f"CLI show accounts function error: {err}")
        print(f"CLI show accounts function error: {err}")

def default_cloudflare(account: str) -> None:
    """CLI only function: sets a Cloudflare account as the default one"""
    logging.info("Starting CLI functions: default_cloudflare")
    try:
        #Check is the new record, which will be the default one, exists at all
        acc = Cloudflare.query.filter_by(account=account).first()
        if not acc:
            print(f"Account \"{account}\" doesn't exists! Can set it as the default one!")
            logging.error(f"Account \"{account}\" doesn't exists! Can set it as the default one!")
            quit(1)
        #Check if it is already is the default one
        default_acc = Cloudflare.query.filter_by(isdefault=True).first()
        if default_acc:
            if default_acc.account == account:
                print(f"Account \"{account}\" already is the default one!")
                logging.error(f"Account \"{account}\" already is the default one!")
                quit(1)
        #Main function. First of all set all existing records as not default
        Cloudflare.query.update({Cloudflare.isdefault: False})
        #set one selected record as the default one
        acc = Cloudflare.query.filter_by(account=account).first()
        if acc:
            acc.isdefault = True
            db.session.commit()
            print(f"Account \"{account}\" is set as default one!")
            logging.info(f"Account \"{account}\" is set as default one!")
    except Exception as err:
        logging.error(f"Set default account \"{account}\" error: {err}")
        print(f"Set default account \"{account}\" error: {err}")

def add_servers(name: str,ip: str) -> None:
    """CLI only function: adds a new server and its ip to the database"""
    logging.info("Starting CLI functions: add_servers")
    try:
        if Servers.query.filter_by(name=name).first():
            print(f"Server \"{name}\" creation error - already exists!")
            logging.error(f"Server \"{name}\" creation error - already exists!")
        else:
            new_server = Servers(
                name=name,
                ip=ip,
            )
            db.session.add(new_server)
            db.session.commit()
            print(f"New Server \"{name}\" created successfully!")
            logging.info(f"New Server \"{name}\" created successfully!")
        #check if there is only one just added record - set it as default
        if len(Servers.query.filter_by().all()) == 1:
            srv = Servers.query.filter_by(name=name).first()
            if srv:
                srv.isdefault = True
                db.session.commit()
    except Exception as err:
        logging.error(f"New Server \"{name}\" creation error: {err}")
        print(f"New Server \"{name}\" creation error: {err}")

def del_servers(name: str) -> None:
    """CLI only function: deletes a Server from the database"""
    logging.info("Starting CLI functions: del_servers")
    try:
        srv = Servers.query.filter_by(name=name).first()
        if srv:
            if srv.isdefault == True:
                print("Warning, that was the Default Server. You need to make another Server the default one!")
            db.session.delete(srv)
            db.session.commit()
            load_config(current_app)
            print(f"Server \"{srv.name}\" deleted successfully!")
            logging.info(f"Server \"{srv.name}\" deleted successfully!")
        else:
            print(f"Server \"{name}\" deletion error - no such Server!")
            logging.error(f"Server \"{name}\" deletion error - no such Server!")
            quit(1)
    except Exception as err:
        logging.error(f"Server \"{name}\" deletion error: {err}")
        print(f"Server \"{name}\" deletion error: {err}")

def upd_servers(name: str, new_ip: str) -> None:
    """CLI only function: updates a Server with the new token"""
    logging.info("Starting CLI functions: upd_servers")
    try:
        srv = Servers.query.filter_by(name=name).first()
        if srv:
            srv.ip = new_ip
            db.session.commit()
            print(f"Server \"{name}\" updated successfully to {new_ip}!")
            logging.info(f"Server \"{name}\" updated successfully to{new_ip}!")
        else:
            print(f"Server \"{name}\" update error - no such Server!")
            logging.error(f"Server \"{name}\" update error - no such Server!")
            quit(1)
    except Exception as err:
        logging.error(f"Server \"{name}\" update error: {err}")
        print(f"Server \"{name}\" update error: {err}")

def show_servers() -> None:
    """CLI only function: shows all available Servers from the database"""
    logging.info("Starting CLI functions: show_servers")
    try:
        accs = Servers.query.order_by(Servers.name).all()
        if len(accs) == 0:
            print("No Servers found in DB!")
            quit()
        for i, s in enumerate(accs, 1):
            print(f"ID: {s.id},\nServer: {s.name},\nIP: {s.ip},\nIsDefault: {s.isdefault},\nCreated: {s.created}\n--------------------------------------------------------")
    except Exception as err:
        logging.error(f"CLI show Server function error: {err}")
        print(f"CLI show Server function error: {err}")

def default_servers(name: str) -> None:
    """CLI only function: sets a Server as the default one"""
    logging.info("Starting CLI functions: default_servers")
    try:
        #Check is the new record, which will be the default one, exists at all
        srv = Cloudflare.query.filter_by(name=name).first()
        if not srv:
            print(f"Server \"{name}\" doesn't exists! Can set it as the default one!")
            logging.error(f"Server \"{name}\" doesn't exists! Can set it as the default one!")
            quit(1)
        #Check if it is already is the default one
        default_srv = Servers.query.filter_by(isdefault=True).first()
        if default_srv:
            if default_srv.name == name:
                print(f"Server \"{name}\" already is the default one!")
                logging.error(f"Server \"{name}\" already is the default one!")
                quit(1)
        #Main function. First of all set all existing records as not default
        Servers.query.update({Servers.isdefault: False})
        #set one selected record as the default one
        srv = Servers.query.filter_by(name=name).first()
        if srv:
            srv.isdefault = True
            db.session.commit()
            print(f"Server \"{name}\" is set as default one!")
            logging.info(f"Server \"{name}\" is set as default one!")
    except Exception as err:
        logging.error(f"Set default Server \"{name}\" error: {err}")
        print(f"Set default Server \"{name}\" error: {err}")

def add_owner(domain: str, id: int) -> None:
    """CLI only function: adds an owner for the given domain"""
    logging.info("Starting CLI functions: add_owner")
    try:
        #Check if the user with given ID exists
        usr = User.query.filter_by(id=id).first()
        if not usr:
            print(f"Error! User with the given ID {id} is not exists!")
            quit()
        #Check if the given domain is already owned by the given user
        check = Ownership.query.filter_by(domain=domain).all()
        for i, c in enumerate(check,1):
            if c.owner == str(id):
                print(f"Domain \"{domain}\" already owned by user with id {id}!")
                logging.error(f"Domain \"{domain}\" already owned by user with id {id}!")
                quit()
        #check if the domain physically exists on the server
        if not os.path.exists(os.path.join(current_app.config['WEB_FOLDER'],domain)):
            print(f"Domain \"{domain}\" phisycally not exists on the server!")
            logging.error(f"Domain \"{domain}\" phisycally not exists on the server!")
            quit()
        #Else start addition procedure
        new_owner = Ownership(
            domain=domain,
            owner=id,
        )
        db.session.add(new_owner)
        db.session.commit()
        print(f"Domain \"{domain}\" now is owned by user with ID {id}!")
        logging.info(f"Domain \"{domain}\" now is owned by user with ID {id}!")
    except Exception as err:
        logging.error(f"Add_owner() general error: {err}")
        print(f"Add_owner() general error: {err}")

def del_owner(domain: str) -> None:
    """CLI only function: deletes an owner for a selected domain from database"""
    logging.info("Starting CLI functions: del_owner")
    try:
        check = Ownership.query.filter_by(domain=domain).first()
        if check:
            db.session.delete(check)
            db.session.commit()
            print(f"Ownership for domain \"{domain}\" deleted successfully!")
            logging.info(f"Ownership for domain \"{domain}\" deleted successfully!")
        else:
            print(f"Ownership for domain \"{domain}\" deletion error - no such domain!")
            logging.error(f"Ownership for domain \"{domain}\" deletion error - no such domain!")
            quit(1)
    except Exception as err:
        logging.error(f"Ownership for domain \"{domain}\" general error: {err}")
        print(f"Ownership for domain \"{domain}\" general error: {err}")

def upd_owner(domain: str, new_owner: int) -> None:
    """CLI only function: updates a domain with the new owner"""
    logging.info("Starting CLI functions: upd_owner")
    try:
        check = Ownership.query.filter_by(domain=domain).first()
        if check:
            check.owner = new_owner
            db.session.commit()
            print(f"Domain \"{domain}\" owner updated successfully to {new_owner}!")
            logging.info(f"Domain \"{domain}\" updated successfully to{new_owner}!")
        else:
            print(f"Domain \"{domain}\" owner update error - no such domain!")
            logging.error(f"Domain \"{domain}\" owner update error - no such domain!")
            quit(1)
    except Exception as err:
        logging.error(f"Domain \"{domain}\" owner update general error: {err}")
        print(f"Domain \"{domain}\" owner update general error: {err}")

def show_owners() -> None:
    """CLI only function: shows all domains and their owners from the database"""
    logging.info("Starting CLI functions: show_owners")
    try:
        accs = Ownership.query.order_by(Ownership.domain).all()
        if len(accs) == 0:
            print("No domains with owners found in DB!")
            quit()
        print("-------------------------------------------------------------------------------------------------------")
        for i, s in enumerate(accs, 1):
            realn = User.query.filter_by(id=s.id).first()
            print(f"ID: {s.id},Domain: {s.domain},Owner: {realn.realname}(ID:{s.owner}),Created: {s.created}")
        print("-------------------------------------------------------------------------------------------------------")
    except Exception as err:
        logging.error(f"CLI show owner function error: {err}")
        print(f"CLI show owner function error: {err}")
