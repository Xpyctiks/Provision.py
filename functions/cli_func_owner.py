import logging,os
from db.db import db
from db.database import *
from flask import current_app

def add_owner(domain: str, id: int) -> None:
    """CLI only function: adds an owner for the given domain"""
    logging.info("-----------------------Starting CLI functions: add_owner")
    try:
        domain = domain.lower()
        #Check if the user with given ID exists
        usr = User.query.filter_by(id=id).first()
        if not usr:
            print(f"Error! User with the given ID {id} is not exists!")
            logging.error(f"cli>Error! User with the given ID {id} is not exists!")
            quit()
        #Check if the given domain is already owned by the given user
        check = Ownership.query.filter_by(domain=domain).all()
        for i, c in enumerate(check,1):
            if c.owner == str(id):
                print(f"Domain \"{domain}\" already owned by user with id {id}!")
                logging.error(f"cli>Domain \"{domain}\" already owned by user with id {id}!")
                quit()
        #check if the domain physically exists on the server
        if not os.path.exists(os.path.join(current_app.config['WEB_FOLDER'],domain)):
            print(f"Domain \"{domain}\" phisycally not exists on the server!")
            logging.error(f"cli>Domain \"{domain}\" phisycally not exists on the server!")
            quit()
        #Else start addition procedure
        new_owner = Ownership(
            domain=domain,
            owner=id,
        )
        db.session.add(new_owner)
        db.session.commit()
        print(f"Domain \"{domain}\" now is owned by user with ID {id}!")
        logging.info(f"cli>Domain \"{domain}\" now is owned by user with ID {id}!")
    except Exception as err:
        logging.error(f"cli>Add_owner() general error: {err}")
        print(f"Add_owner() general error: {err}")

def del_owner(domain: str,cli: bool = True):
    """CLI only function: deletes an owner for a selected domain from database"""
    if cli:
        logging.info("-----------------------Starting CLI functions: del_owner")
    else:
        logging.info(f"Deleting the owner of domain {domain} from the database...")
    try:
        domain = domain.lower()
        check = Ownership.query.filter_by(domain=domain).first()
        if check:
            db.session.delete(check)
            db.session.commit()
            if cli:
                print(f"Ownership for domain \"{domain}\" deleted successfully!")
                logging.info(f"cli>Ownership for domain \"{domain}\" deleted successfully!")
                quit()
            else:
                logging.info(f"Ownership for domain \"{domain}\" deleted successfully!")
                return False
        else:
            if cli:
                print(f"Ownership for domain \"{domain}\" deletion error - no such domain!")
                logging.error(f"cli>Ownership for domain \"{domain}\" deletion error - no such domain!")
                quit(1)
            else:
                print(f"Ownership for domain \"{domain}\" deletion error - no such domain!")
                logging.error(f"cli>Ownership for domain \"{domain}\" deletion error - no such domain!")
                return False
    except Exception as err:
        if cli:
            print(f"Ownership for domain \"{domain}\" general error: {err}")
            logging.error(f"cli>Ownership for domain \"{domain}\" general error: {err}")
            quit(1)
        else:
            logging.error(f"Ownership for domain \"{domain}\" general error: {err}")
            return False

def upd_owner(domain: str, new_owner: int) -> None:
    """CLI only function: updates a domain with the new owner"""
    logging.info("-----------------------Starting CLI functions: upd_owner")
    try:
        domain = domain.lower()
        check = Ownership.query.filter_by(domain=domain).first()
        if check:
            check.owner = new_owner
            db.session.commit()
            print(f"Domain \"{domain}\" owner updated successfully to {new_owner}!")
            logging.info(f"cli>Domain \"{domain}\" updated successfully to{new_owner}!")
        else:
            print(f"Domain \"{domain}\" owner update error - no such domain!")
            logging.error(f"cli>Domain \"{domain}\" owner update error - no such domain!")
            quit(1)
    except Exception as err:
        logging.error(f"cli>Domain \"{domain}\" owner update general error: {err}")
        print(f"Domain \"{domain}\" owner update general error: {err}")

def show_owners() -> None:
    """CLI only function: shows all domains and their owners from the database"""
    logging.info("-----------------------Starting CLI functions: show_owners")
    try:
        accs = Ownership.query.order_by(Ownership.domain).all()
        if len(accs) == 0:
            print("No domains with owners found in DB!")
            logging.error("cli>No domains with owners found in DB!")
            quit()
        print("-------------------------------------------------------------------------------------------------------")
        for i, s in enumerate(accs, 1):
            rln = User.query.filter_by(id=s.id).first()
            print(f"ID: {s.id}, Domain: {s.domain}, Owner: {rln.realname}(ID:{s.owner}), Created: {s.created}")
        print("-------------------------------------------------------------------------------------------------------")
    except Exception as err:
        logging.error(f"cli>CLI show owner function error: {err}")
        print(f"CLI show owner function error: {err}")

def help_owner() -> None:
    """CLI only function: shows hints for OWNER command"""
    print (f"""
Possible completion:
    add    <domain> <database ID>
    del    <domain>
    upd    <domain> <new_database_ID>
        Important: <ID> means unique user ID from its database record in Users table. Integer value only.
    """)
