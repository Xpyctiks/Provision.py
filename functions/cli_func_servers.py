import logging
from db.db import db
from db.database import *
from functions.load_config import load_config
from flask import current_app

def add_servers(name: str,ip: str) -> None:
    """CLI only function: adds a new server and its ip to the database"""
    logging.info("-----------------------Starting CLI functions: add_servers")
    try:
        if Servers.query.filter_by(name=name).first():
            print(f"Server \"{name}\" creation error - already exists!")
            logging.error(f"cli>Server \"{name}\" creation error - already exists!")
        else:
            new_server = Servers(
                name=name,
                ip=ip,
            )
            db.session.add(new_server)
            db.session.commit()
            print(f"New Server \"{name}\" created successfully!")
            logging.info(f"cli>New Server \"{name}\" created successfully!")
        #check if there is only one just added record - set it as default
        if len(Servers.query.filter_by().all()) == 1:
            srv = Servers.query.filter_by(name=name).first()
            if srv:
                srv.isdefault = True
                db.session.commit()
    except Exception as err:
        logging.error(f"cli>New Server \"{name}\" creation error: {err}")
        print(f"New Server \"{name}\" creation error: {err}")

def del_servers(name: str) -> None:
    """CLI only function: deletes a Server from the database"""
    logging.info("-----------------------Starting CLI functions: del_servers")
    try:
        srv = Servers.query.filter_by(name=name).first()
        if srv:
            if srv.isdefault == True:
                print("Warning, that was the Default Server. You need to make another Server the default one!")
            db.session.delete(srv)
            db.session.commit()
            load_config(current_app)
            print(f"Server \"{srv.name}\" deleted successfully!")
            logging.info(f"cli>Server \"{srv.name}\" deleted successfully!")
        else:
            print(f"Server \"{name}\" deletion error - no such Server!")
            logging.error(f"cli>Server \"{name}\" deletion error - no such Server!")
            quit(1)
    except Exception as err:
        logging.error(f"cli>Server \"{name}\" deletion error: {err}")
        print(f"Server \"{name}\" deletion error: {err}")

def upd_servers(name: str, new_ip: str) -> None:
    """CLI only function: updates a Server with the new token"""
    logging.info("-----------------------Starting CLI functions: upd_servers")
    try:
        srv = Servers.query.filter_by(name=name).first()
        if srv:
            srv.ip = new_ip
            db.session.commit()
            print(f"Server \"{name}\" updated successfully to {new_ip}!")
            logging.info(f"cli>Server \"{name}\" updated successfully to{new_ip}!")
        else:
            print(f"Server \"{name}\" update error - no such Server!")
            logging.error(f"cli>Server \"{name}\" update error - no such Server!")
            quit(1)
    except Exception as err:
        logging.error(f"cli>Server \"{name}\" update error: {err}")
        print(f"Server \"{name}\" update error: {err}")

def show_servers() -> None:
    """CLI only function: shows all available Servers from the database"""
    logging.info("-----------------------Starting CLI functions: show_servers")
    try:
        accs = Servers.query.order_by(Servers.name).all()
        if len(accs) == 0:
            print("No Servers found in DB!")
            logging.error("cli>No Servers found in DB!")
            quit()
        for i, s in enumerate(accs, 1):
            print("-------------------------------------------------------------------------------------------------------")
            print(f"ID: {s.id}, Server: {s.name}, IP: {s.ip}, IsDefault: {s.isdefault}, Created: {s.created}")
            print("-------------------------------------------------------------------------------------------------------")
    except Exception as err:
        logging.error(f"cli>CLI show Server function error: {err}")
        print(f"CLI show Server function error: {err}")

def default_servers(name: str) -> None:
    """CLI only function: sets a Server as the default one"""
    logging.info("-----------------------Starting CLI functions: default_servers")
    try:
        #Check is the new record, which will be the default one, exists at all
        srv = Cloudflare.query.filter_by(name=name).first()
        if not srv:
            print(f"Server \"{name}\" doesn't exists! Can set it as the default one!")
            logging.error(f"cli>Server \"{name}\" doesn't exists! Can set it as the default one!")
            quit(1)
        #Check if it is already is the default one
        default_srv = Servers.query.filter_by(isdefault=True).first()
        if default_srv:
            if default_srv.name == name:
                print(f"Server \"{name}\" already is the default one!")
                logging.error(f"cli>Server \"{name}\" already is the default one!")
                quit(1)
        #Main function. First of all set all existing records as not default
        Servers.query.update({Servers.isdefault: False})
        #set one selected record as the default one
        srv = Servers.query.filter_by(name=name).first()
        if srv:
            srv.isdefault = True
            db.session.commit()
            print(f"Server \"{name}\" is set as default one!")
            logging.info(f"cli>Server \"{name}\" is set as default one!")
    except Exception as err:
        logging.error(f"cli>Set default Server \"{name}\" error: {err}")
        print(f"Set default Server \"{name}\" error: {err}")

def help_servers() -> None:
    """CLI only function: shows hints for SERVERS command"""
    print (f"""
Possible completion:
    add     <server_name> <IP_address>
    default <server_name>
    del     <server_name>
    upd     <server_name> <new_IP_address>
    """)
