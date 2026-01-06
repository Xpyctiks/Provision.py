import logging
from db.db import db
from db.database import *
from functions.load_config import load_config
from flask import current_app

def add_cloudflare(account: str,token: str) -> None:
    """CLI only function: adds a new Cloudflare account and its token to the database"""
    logging.info("-----------------------Starting CLI functions: add_cloudflare")
    try:
        account = account.lower()
        if Cloudflare.query.filter_by(account=account).first():
            print(f"Account \"{account}\" creation error - already exists!")
            logging.error(f"cli>Account \"{account}\" creation error - already exists!")
            quit(1)
        else:
            new_account = Cloudflare(
                account=account,
                token=token,
            )
            db.session.add(new_account)
            db.session.commit()
            print(f"New account \"{account}\" created successfully!")
            logging.info(f"cli>New account \"{account}\" created successfully!")
        #check if there is only one just added record - set it as default
        if len(Cloudflare.query.filter_by().all()) == 1:
            acc = Cloudflare.query.filter_by(account=account).first()
            if acc:
                acc.isdefault = True
                db.session.commit()
        quit(0)
    except Exception as err:
        logging.error(f"cli>New account \"{account}\" creation error: {err}")
        print(f"New account \"{account}\" creation error: {err}")
        quit(1)

def del_cloudflare(account: str) -> None:
    """CLI only function: deletes a Cloudflare account from the database"""
    logging.info("-----------------------Starting CLI functions: del_cloudflare")
    try:
        account = account.lower()
        acc = Cloudflare.query.filter_by(account=account).first()
        if acc:
            if acc.isdefault == True:
                print("Warning, that was the Default account. You need to make another account the default one!")
            db.session.delete(acc)
            db.session.commit()
            load_config(current_app)
            print(f"Cloudflare account \"{acc.account}\" deleted successfully!")
            logging.info(f"cli>Cloudflare account \"{acc.account}\" deleted successfully!")
            quit(0)
        else:
            print(f"Cloudflare account \"{account}\" deletion error - no such account!")
            logging.error(f"cli>Cloudflare account \"{account}\" deletion error - no such account!")
            quit(1)
    except Exception as err:
        logging.error(f"cli>Cloudflare account \"{account}\" deletion error: {err}")
        print(f"Cloudflare account \"{account}\" deletion error: {err}")
        quit(1)

def upd_cloudflare(account: str, new_token: str) -> None:
    """CLI only function: updates a Cloudflare account with the new token"""
    logging.info("-----------------------Starting CLI functions: upd_cloudflare")
    try:
        account = account.lower()
        acc = Cloudflare.query.filter_by(account=account).first()
        if acc:
            acc.token = new_token
            db.session.commit()
            print(f"Account \"{account}\" updated successfully to {new_token}!")
            logging.info(f"cli>Account \"{account}\" updated successfully to{new_token}!")
            quit(0)
        else:
            print(f"Account \"{account}\" update error - no such account!")
            logging.error(f"cli>Account \"{account}\" update error - no such account!")
            quit(1)
    except Exception as err:
        logging.error(f"cli>Account \"{account}\" update error: {err}")
        print(f"Account \"{account}\" update error: {err}")
        quit(1)

def show_cloudflare() -> None:
    """CLI only function: shows all available Cloudflare accounts from the database"""
    logging.info("-----------------------Starting CLI functions: show_cloudflare")
    try:
        accs = Cloudflare.query.order_by(Cloudflare.account).all()
        if len(accs) == 0:
            print("No accounts found in DB!")
            logging.error("cli>No accounts found in DB!")
            quit(0)
        for i, s in enumerate(accs, 1):
            print("-------------------------------------------------------------------------------------------------------")
            print(f"ID: {s.id}, Account: {s.account}, Token: {s.token}, IsDefault: {s.isdefault}, Created: {s.created}")
            print("-------------------------------------------------------------------------------------------------------")
        quit(0)
    except Exception as err:
        logging.error(f"cli>CLI show accounts function error: {err}")
        print(f"CLI show accounts function error: {err}")
        quit(1)

def default_cloudflare(account: str) -> None:
    """CLI only function: sets a Cloudflare account as the default one"""
    logging.info("-----------------------Starting CLI functions: default_cloudflare")
    try:
        account = account.lower()
        #Check is the new record, which will be the default one, exists at all
        acc = Cloudflare.query.filter_by(account=account).first()
        if not acc:
            print(f"Account \"{account}\" doesn't exists! Can set it as the default one!")
            logging.error(f"cli>Account \"{account}\" doesn't exists! Can set it as the default one!")
            quit(1)
        #Check if it is already is the default one
        default_acc = Cloudflare.query.filter_by(isdefault=True).first()
        if default_acc:
            if default_acc.account == account:
                print(f"Account \"{account}\" already is the default one!")
                logging.error(f"cli>Account \"{account}\" already is the default one!")
                quit(1)
        #Main function. First of all set all existing records as not default
        Cloudflare.query.update({Cloudflare.isdefault: False})
        #set one selected record as the default one
        acc = Cloudflare.query.filter_by(account=account).first()
        if acc:
            acc.isdefault = True
            db.session.commit()
            print(f"Account \"{account}\" is set as default one!")
            logging.info(f"cli>Account \"{account}\" is set as default one!")
        quit(0)
    except Exception as err:
        logging.error(f"cli>Set default account \"{account}\" error: {err}")
        print(f"Set default account \"{account}\" error: {err}")
        quit(1)

def help_cloudflare() -> None:
    """CLI only function: shows hints for CLOUDFLARE command"""
    print (f"""
Possible completion:
    add     <email> <api_token>
    default <email>
    del     <email>
    upd     <email> <new_api_token>
    """)
    quit(0)
