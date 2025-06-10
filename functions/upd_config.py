import logging
from db.db import db
from db.database import Settings,User
from functions.load_config import load_config
from flask import current_app
from werkzeug.security import generate_password_hash

def set_telegramChat(tgChat: str) -> None:
    """CLI only function: sets Telegram ChatID value in database"""
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

def set_webFolder(data: str) -> None:
    """CLI only function: sets webFolder parameter in database"""
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
