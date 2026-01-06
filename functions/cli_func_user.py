import logging
from db.db import db
from db.database import *
from functions.load_config import load_config
from flask import current_app
from werkzeug.security import generate_password_hash

def register_user(username: str,password: str,realname: str) -> None:
    """CLI only function: adds new user and saves to database"""
    logging.info("-----------------------Starting CLI functions: register_user")
    try:
        if User.query.filter_by(username=username).first():
            print(f"User \"{username}\" creation error - already exists!")
            logging.error(f"cli>User \"{username}\" creation error - already exists!")
            quit(1)
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
            logging.info(f"cli>New user \"{username}\" - \"{realname}\" created successfully!")
            quit(0)
    except Exception as err:
        logging.error(f"cli>User \"{username}\" - \"{realname}\" creation error: {err}")
        print(f"User \"{username}\" - \"{realname}\" creation error: {err}")
        quit(1)

def update_user(username: str,password: str) -> None:
    """CLI only function: password change for existing user"""
    logging.info("-----------------------Starting CLI functions: update_user")
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            d = User(id=user.id,password_hash=generate_password_hash(password))
            db.session.merge(d)
            db.session.commit()
            print(f"Password for user \"{user.username}\" updated successfully!")
            logging.info(f"cli>Password for user \"{user.username}\" updated successfully!")
        else:
            print(f"User \"{username}\" set password error - no such user!")
            logging.error(f"cli>User \"{username}\" set password error - no such user!")
            quit(1)
    except Exception as err:
        logging.error(f"cli>User \"{username}\" set password error: {err}")
        print(f"User \"{username}\" set password error: {err}")
        quit(1)

def delete_user(username: str) -> None:
    """CLI only function: deletes an existing user from database"""
    logging.info("-----------------------Starting CLI functions: delete_user")
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            load_config(current_app)
            print(f"User \"{user.username}\" deleted successfully!")
            logging.info(f"cli>User \"{user.username}\" deleted successfully!")
            quit(0)
        else:
            print(f"User \"{username}\" delete error - no such user!")
            logging.error(f"cli>User \"{username}\" delete error - no such user!")
            quit(1)
    except Exception as err:
        logging.error(f"cli>User \"{username}\" delete error: {err}")
        print(f"User \"{username}\" delete error: {err}")
        quit(1)

def show_users() -> None:
    """CLI only function: Shows all users in database"""
    logging.info("-----------------------Starting CLI functions: show_users")
    try:
        users = User.query.order_by(User.username).all()
        if len(users) == 0:
            print("No users found in DB!")
            quit(1)
        for i, s in enumerate(users, 1):
            print(f"ID: {s.id}, Login: {s.username}, RealName: {s.realname}, Created: {s.created}")
        quit(0)
    except Exception as err:
        logging.error(f"cli>CLI show users function error: {err}")
        print(f"CLI show users function error: {err}")
        quit(1)

def make_admin_user(username: str) -> None:
    """CLI only function: Grants to the given user admin. rights"""
    logging.info("-----------------------Starting CLI functions: make_admin_user")
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            new_rights = User(username=username,rights=255)
            db.session.merge(new_rights)
            db.session.commit()
            logging.info(f"cli>User {username} successfully set as admin!")
            print(f"User {username} successfully set as admin!")
            quit(0)
        else:
            logging.error(f"cli>User {username} set admin rights error - no such user!")
            print(f"User {username} set admin rights error - no such user!")
            quit(1)
    except Exception as err:
        logging.error(f"cli>User {username} set admin rights global error: {err}")
        print(f"User {username} set admin rights global error: {err}")
        quit(1)

def remove_admin_user(username: str) -> None:
    try:
        user = User.query.filter_by(username=username).first()
        if user:
            new_rights = User(username=username,rights=1)
            db.session.merge(new_rights)
            db.session.commit()
            logging.info(f"cli>User {username} successfully set as the regular user!")
            print(f"User {username} successfully set as the regular user!")
            quit(0)
        else:
            logging.error(f"cli>User {username} unset admin rights error - no such user!")
            print(f"User {username} unset admin rights error - no such user!")
            quit(1)
    except Exception as err:
        logging.error(f"cli>User {username} unset admin rights global error: {err}")
        print(f"User {username} unset admin rights global error: {err}")
        quit(1)

def help_user() -> None:
    """CLI only function: shows hints for USER command"""
    print (f"""
Possible completion:
    add    <login> <password> <realName>
    del    <login>
    setpwd <login> <new_password>
    """)
    quit(0)

