import logging,os
from db.db import db
from db.database import *

def add_account(domain: str, email: str) -> None:
    """CLI only function: adds an account info for the given domain"""
    logging.info("-----------------------Starting CLI functions: add_account")
    try:
        email = email.lower()
        domain = domain.lower()
        #Check if the account with given email exists
        acc = Cloudflare.query.filter_by(account=email).first()
        if not acc:
            print(f"Error! Cloudflare account with the given email {email} is not exists in our database!")
            logging.error(f"cli>Error! Cloudflare account with the given email {email} is not exists in our database!")
            quit()
        #Check if the given account is already linked with the given domain
        check = Domain_account.query.filter_by(domain=domain).all()
        for i, c in enumerate(check,1):
            if c.account == email:
                print(f"Domain \"{domain}\" already linked with account {email}!")
                logging.error(f"cli>Domain \"{domain}\" already linked with account {email}!")
                quit()
        #Else start addition procedure
        new_account = Domain_account(
            domain=domain,
            account=email,
        )
        db.session.add(new_account)
        db.session.commit()
        print(f"Domain \"{domain}\" now is linked to account {email}!")
        logging.info(f"cli>Domain \"{domain}\" now is linked to account {email}!")
    except Exception as err:
        logging.error(f"cli>Add_account() general error: {err}")
        print(f"Add_account() general error: {err}")

def upload_accounts(filename: str) -> None:
    """CLI only function: adds a lot of accounts via file uploading"""
    logging.info("-----------------------Starting CLI functions: add_accounts_bulk")
    try:
        if os.path.exists(filename):
            with open(filename) as f:
                for line in f:
                    parts = line.strip().split()
                    if len(parts) == 2:
                        domain, account = parts
                        domain = domain.lower()
                        account = account.lower()
                        #Check if the account with given email exists
                        acc = Cloudflare.query.filter_by(account=account).first()
                        if not acc:
                            print(f"Error! Cloudflare account for domain {domain} with the given email {account} is not exists in our database!")
                            logging.error(f"cli>Error! Cloudflare account for domain {domain} with the given email {account} is not exists in our database!")
                            continue
                        #Check if the given account is already linked with the given domain
                        check = Domain_account.query.filter_by(domain=domain).all()
                        if check:
                            print(f"Domain \"{domain}\" already linked with account {account}!")
                            logging.error(f"cli>Domain \"{domain}\" already linked with account {account}!")
                            continue
                        #Else start addition procedure
                        new_account = Domain_account(
                            domain=domain,
                            account=account,
                        )
                        db.session.add(new_account)
                        db.session.commit()
                        print(f"Domain \"{domain}\" now is linked to account {account}!")
                        logging.info(f"cli>Domain \"{domain}\" now is linked to account {account}!")
                    else:
                        logging.error("cli>Some error during parsing some link from the file...")
                        print("Some error during parsing some link from the file...")
                        continue
        else:
            logging.error(f"cli>upload_accounts(): Error opening file {filename}!")
            print(f"Error opening file {filename}!")
            quit()
    except Exception as err:
        logging.error(f"cli>Upload_accounts() general error: {err}")
        print(f"Upload_accounts() general error: {err}")

def del_account(domain: str, cli: bool = True):
    """CLI only function: deletes a domain-to-account link from database"""
    if cli:
        logging.info("-----------------------Starting CLI functions: del_account")
    else:
        logging.info(f"Deleting link of domain {domain} with its account in the database...")
    try:
        domain = domain.lower()
        check = Domain_account.query.filter_by(domain=domain).first()
        if check:
            db.session.delete(check)
            db.session.commit()
            if cli:
                print(f"Link of domain {domain} with its account deleted successfully!")
                logging.info(f"cli>Link of domain {domain} with its account deleted successfully!")
                quit(0)
            else:
                logging.info(f"Link of domain {domain} with its account deleted successfully!")
                return True
        else:
            if cli:
                print(f"Link to account for domain \"{domain}\" deletion error - no such domain!")
                logging.error(f"cli>Link to account for domain \"{domain}\" deletion error - no such domain!")
                quit(1)
            else:
                logging.error(f"Link to account for domain \"{domain}\" deletion error - no such domain!")
                return False
    except Exception as err:
        if cli:
            logging.error(f"cli>Link to account for domain \"{domain}\" general error: {err}")
            print(f"Link to account for domain \"{domain}\" general error: {err}")
        else:
            logging.error(f"Link to account for domain \"{domain}\" general error: {err}")
            return False

def upd_account(domain: str, email: str) -> None:
    """CLI only function: updates a domain with the new account link"""
    logging.info("Starting CLI functions: upd_account")
    try:
        domain = domain.lower()
        check = Domain_account.query.filter_by(domain=domain).first()
        if check:
            #Check if the account with given email exists
            acc = Cloudflare.query.filter_by(account=email).first()
            if not acc:
                print(f"Error! Cloudflare account with the given email {email} is not exists in our database!")
                logging.error(f"cli>Error! Cloudflare account with the given email {email} is not exists in our database!")
                quit()
            check.account = email
            db.session.commit()
            print(f"Domain \"{domain}\" account updated successfully to {email}!")
            logging.info(f"cli>Domain \"{domain}\" account successfully to{email}!")
        else:
            print(f"Domain \"{domain}\" account update error - no such domain!")
            logging.error(f"cli>Domain \"{domain}\" account update error - no such domain!")
            quit(1)
    except Exception as err:
        logging.error(f"cli>Domain \"{domain}\" account update general error: {err}")
        print(f"Domain \"{domain}\" account update general error: {err}")

def show_accounts() -> None:
    """CLI only function: shows all domains and their owners from the database"""
    logging.info("-----------------------Starting CLI functions: show_accounts")
    try:
        accs = Domain_account.query.order_by(Domain_account.domain).all()
        if len(accs) == 0:
            print("No domains with accounts found in DB!")
            logging.error("cli>No domains with accounts found in DB!")
            quit()
        print("-------------------------------------------------------------------------------------------------------")
        for i, s in enumerate(accs, 1):
            print(f"ID: {s.id}, Domain: {s.domain}, Account: {s.account}, Created: {s.created}")
        print("-------------------------------------------------------------------------------------------------------")
    except Exception as err:
        logging.error(f"cli>CLI show accounts function error: {err}")
        print(f"CLI show accounts function error: {err}")

def help_account() -> None:
    """CLI only function: shows hints for ACCOUNT command"""
    print (f"""
Possible completion:
    add    <domain> <Cloudflare account email>
    del    <domain>
    upd    <domain> <new Cloudflare account email>
    upload <file with account information>
           Format inside the file:
           <domain> <account email>
    """)
