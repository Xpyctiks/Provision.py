from flask import flash
from flask_login import current_user
import logging
from db.database import *
from werkzeug.security import generate_password_hash
from functions.rights_required import rights_required

@rights_required(255)
def handler_settings(form):
  """Handler for saving global settings to DB, received from admin panel"""
  logging.info(f"---------------------------Processing global settings from admin panel by {current_user.realname}---------------------------")
  try:
    for count, db_field in enumerate(form, 1):
      #skip processing of the button
      if db_field == "buttonSaveSettings":
        continue
      data = {"id": 1, db_field: form.get(db_field)}
      t = Settings(**data)
      db.session.merge(t)
    db.session.commit()
    logging.info(f"Admin {current_user.realname}>Saving global settings done---------------------------")
    flash('Нові параметри збережено та застосовано!','alert alert-success')
  except Exception as err:
    logging.error(f"Admin {current_user.realname}>handler_settings() global error: {err}")
    flash('Помилка збереження параметрів программи!','alert alert-danger')
    return

@rights_required(255)
def handler_users(form):
  """Handler for saving/deleting users to DB, received from admin panel"""
  logging.info(f"---------------------------Processing user management from admin panel by {current_user.realname}---------------------------")
  try:
    #process delete user request
    if "buttonDeleteUser" in form:
      user = User.query.filter_by(id=int(form.get('buttonDeleteUser').strip())).first()
      if user:
        db.session.delete(user)
        db.session.commit()
        logging.info(f"Admin {current_user.realname}>User {user.username} with ID {form.get('buttonDeleteUser').strip()} deleted successfully!")
        flash(f'Користувач {user.username} з ID {form.get("buttonDeleteUser").strip()} успішно видален!','alert alert-success')
        return
      else:
        logging.error(f"Admin {current_user.realname}>User with ID {form.get('buttonDeleteUser').strip()} deletion error - no such user!")
        flash(f'Помилка видалення користувача з ID {form.get("buttonDeleteUser").strip()} - такого не існує!','alert alert-warning')
        return
    #processing add user request
    elif "buttonAddUser" in form:
      username = form.get("new-username", "").strip()
      realname = form.get("new-realname", "").strip()
      password = form.get("new-password", "").strip()
      if not username or not realname or not password:
        logging.error(f"Admin {current_user.realname}>Some of important parameters for user add procedure has not been received!")
        flash(f'Один або декілька важливих параметрів для створення користувача не були отримані сервером!','alert alert-warning')
        return
      if "new-is-admin" in form:
        rights = 255
      else:
        rights = 1
      data = {"username": username, "realname": realname, "password_hash": generate_password_hash(password), "rights": rights}
      new_user = User(**data)
      db.session.add(new_user)
      db.session.commit()
      if rights == 1:
        logging.info(f"Admin {current_user.realname}>User {username} created successfully!")
        flash(f'Користувач {username} успішно створен!','alert alert-success')
      else:
        logging.info(f"Admin {current_user.realname}>User {username} with admin rights created successfully!")
        flash(f'Користувач {username} з адмін правами успішно створен!','alert alert-success')
      return
        #process delete user request
    if "buttonMakeAdminUser" in form:
      user = User.query.filter_by(id=form.get('buttonMakeAdminUser').strip()).first()
      if user:
        new_rights = User(id=int(user.id),rights=255)
        db.session.merge(new_rights)
        db.session.commit()
        logging.info(f"Admin {current_user.realname}>User {user.username} with ID {form.get('buttonMakeAdminUser').strip()} successfully set as admin!")
        flash(f'Користувач {user.username} з ID {form.get("buttonMakeAdminUser").strip()} успішно став адміністратором!','alert alert-success')
        return
      else:
        logging.error(f"Admin {current_user.realname}>User with ID {form.get('buttonMakeAdminUser').strip()} set admin rights error - no such user!")
        flash(f'Помилка додавання адмін прав користувачу з ID {form.get("buttonMakeAdminUser").strip()} - такого не існує!','alert alert-warning')
        return
    if "buttonRemoveAdminUser" in form:
      user = User.query.filter_by(id=form.get('buttonRemoveAdminUser').strip()).first()
      if user:
        new_rights = User(id=int(user.id),rights=1)
        db.session.merge(new_rights)
        db.session.commit()
        logging.info(f"Admin {current_user.realname}>User {user.username} with ID {form.get('buttonRemoveAdminUser').strip()} successfully set as the regular user!")
        flash(f'Користувач {user.username} з ID {form.get("buttonRemoveAdminUser").strip()} успішно став звичайним користувачем!','alert alert-success')
        return
      else:
        logging.error(f"Admin {current_user.realname}>User with ID {form.get('buttonRemoveAdminUser').strip()} unset admin rights error - no such user!")
        flash(f'Помилка видалення адмін прав користувачу з ID {form.get("buttonRemoveAdminUser").strip()} - такого не існує!','alert alert-warning')
        return
  except Exception as err:
    logging.error(f"Admin {current_user.realname}>handler_users() global error: {err}")
    flash('Помилка обробки функцій користувачів!','alert alert-danger')
    return

@rights_required(255)
def handler_templates(form):
  """Handler for saving/deleting templates to DB, received from admin panel"""
  logging.info(f"---------------------------Processing templates management from admin panel by {current_user.realname}---------------------------")
  try:
    #processing delete template request
    if "buttonDeleteTemplate" in form:
      template = Provision_templates.query.filter_by(id=int(form.get('buttonDeleteTemplate').strip())).first()
      if template:
        isdefault = template.isdefault
        db.session.delete(template)
        db.session.commit()
        if isdefault:
          flash(f'Шаблон {template.name} з ID {form.get("buttonDeleteTemplate").strip()} успішно видален! УВАГА! це був шаблон за замовчанням. Не забудьте встановити новий шаблон за замовчанням!','alert alert-success')  
        else:
          flash(f'Шаблон {template.name} з ID {form.get("buttonDeleteTemplate").strip()} успішно видален!','alert alert-success')
        logging.info(f"Admin {current_user.realname}>Template {template.name} with ID {form.get('buttonDeleteTemplate').strip()} deleted successfully!")
        return
      else:
        logging.error(f"Admin {current_user.realname}>Template with ID {form.get('buttonDeleteTemplate').strip()} deletion error - no such template!")
        flash(f'Помилка видалення шаблону з ID {form.get("buttonDeleteTemplate").strip()} - такого не існує!','alert alert-warning')
        return
    #processing add template request
    elif "buttonAddTemplate" in form:
      name = form.get("new-template-name", "").strip()
      path = form.get("new-template-path", "").strip()
      if not name or not path:
        logging.error(f"Admin {current_user.realname}>Some of important parameters for template add procedure has not been received!")
        flash(f'Один або декілька важливих параметрів для створення шаблону не були отримані сервером!','alert alert-warning')
        return
      data = {"name": name, "repository": path}
      new_template = Provision_templates(**data)
      db.session.add(new_template)
      db.session.commit()
      logging.info(f"Admin {current_user.realname}>Template {name} created successfully!")
      flash(f'Шаблон {name} успішно створен!','alert alert-success')
      return
    #processing set default template request
    elif "buttonDefaultTemplate" in form:
      id = int(form.get("buttonDefaultTemplate", "").strip())
      if not id:
        logging.error(f"Admin {current_user.realname}>Some of important parameters for template set default procedure has not been received!")
        flash(f'Один або декілька важливих параметрів для встановлення шаблону за замовчанням не були отримані сервером!','alert alert-warning')
        return
      #Check is the new record, which will be the default one, exists at all
      template = Provision_templates.query.filter_by(id=id).first()
      if not template:
        logging.error(f"Admin {current_user.realname}>Template with ID {id} doesn't exists! Can set it as the default one!")
        flash(f'Шаблон з ID {id} не існує у базі чомусь..','alert alert-warning')
        return
      #Check if it is already is the default one
      default_template = Provision_templates.query.filter_by(isdefault=True).first()
      if default_template:
        if str(default_template.id) == str(id):
          logging.error(f"cli>Template {default_template.name} with ID {id} already is the default one!")
          flash(f'Шаблон {default_template.name} з ID {id} вже і так є за замовчанням...','alert alert-success')
          return
      #Main function. First of all set all existing records as not default
      Provision_templates.query.update({Provision_templates.isdefault: False})
      #set one selected record as the default one
      template = Provision_templates.query.filter_by(id=id).first()
      if template:
        template.isdefault = True
        db.session.commit()
        logging.info(f"Admin {current_user.realname}>Template {template.name} set as default successfully!")
        flash(f'Шаблон {template.name} успішно встановлен за замовчанням!','alert alert-success')
        return
  except Exception as err:
    logging.error(f"Admin {current_user.realname}>handler_templates() global error: {err}")
    flash('Помилка обробки функцій шаблонів!','alert alert-danger')
    return

@rights_required(255)
def handler_cloudflare(form):
  """Handler for saving/deleting CF accounts to DB, received from admin panel"""
  logging.info(f"---------------------------Processing cloudflare management from admin panel by {current_user.realname}---------------------------")
  try:
    #processing delete account request
    if "buttonDeleteCloudflare" in form:
      cloudflare = Cloudflare.query.filter_by(id=int(form.get('buttonDeleteClourflare').strip())).first()
      if cloudflare:
        isdefault = cloudflare.isdefault
        db.session.delete(cloudflare)
        db.session.commit()
        if isdefault:
          flash(f'Аккаунт Cloudflare {cloudflare.account} з ID {form.get("buttonDeleteCloudflare").strip()} успішно видален! УВАГА! це був аккаунт за замовчанням. Не забудьте встановити новий аккаунт за замовчанням!','alert alert-success')  
        else:
          flash(f'Аккаунт Cloudflare {cloudflare.account} з ID {form.get("buttonDeleteCloudflare").strip()} успішно видален!','alert alert-success')        
        logging.info(f"Admin {current_user.realname}>Cloudflare account {cloudflare.account} with ID {form.get('buttonDeleteCloudflare').strip()} deleted successfully!")
        return
      else:
        logging.error(f"Admin {current_user.realname}>Cloudflare account with ID {form.get('buttonDeleteCloudflare').strip()} deletion error - no such account!")
        flash(f'Помилка видалення аккаунту Cloudlfare з ID {form.get("buttonDeleteCloudflare").strip()} - такого не існує!','alert alert-warning')
        return
    #processing add template request
    elif "buttonAddCloudflare" in form:
      name = form.get("new-cloudflare-name", "").strip()
      token = form.get("new-cloudflare-token", "").strip()
      if not name or not token:
        logging.error(f"Admin {current_user.realname}>Some of important parameters for Cloudflare account add procedure has not been received!")
        flash(f'Один або декілька важливих параметрів для створення аккаунту Cloudflare не були отримані сервером!','alert alert-warning')
        return
      data = {"account": name, "token": token}
      new_account = Cloudflare(**data)
      db.session.add(new_account)
      db.session.commit()
      logging.info(f"Admin {current_user.realname}>Cloudflare account {name} created successfully!")
      flash(f'Cloudflare аккаунт {name} успішно створен!','alert alert-success')
      return
    #processing set default template request
    elif "buttonDefaultCloudflare" in form:
      id = int(form.get("buttonDefaultCloudflare", "").strip())
      if not id:
        logging.error(f"Admin {current_user.realname}>Some of important parameters for Cloudflare account set default procedure has not been received!")
        flash(f'Один або декілька важливих параметрів для встановлення аккаунту Cloudflare за замовчанням не були отримані сервером!','alert alert-warning')
        return
      #Check is the new record, which will be the default one, exists at all
      acc = Cloudflare.query.filter_by(id=id).first()
      if not acc:
        logging.error(f"Admin {current_user.realname}>Cloudflare account with ID {id} doesn't exists! Can set it as the default one!")
        flash(f'Cloudflare аккаунт з ID {id} не існує у базі чомусь..','alert alert-warning')
        return
      #Check if it is already is the default one
      default_acc = Cloudflare.query.filter_by(isdefault=True).first()
      if default_acc:
        if str(default_acc.id) == str(id):
          logging.error(f"cli>Cloudflare account {default_acc.account} with ID {id} already is the default one!")
          flash(f'Cloudflare аккаунт {default_acc.account} з ID {id} вже і так є за замовчанням...','alert alert-success')
          return
      #Main function. First of all set all existing records as not default
      Cloudflare.query.update({Cloudflare.isdefault: False})
      #set one selected record as the default one
      account = Cloudflare.query.filter_by(id=id).first()
      if account:
        account.isdefault = True
        db.session.commit()
        logging.info(f"Admin {current_user.realname}>Cloudflare account {account.account} set as default successfully!")
        flash(f'Cloudflare аккаунт {account.account} успішно встановлен за замовчанням!','alert alert-success')
        return
  except Exception as err:
    logging.error(f"Admin {current_user.realname}>handler_accounts() global error: {err}")
    flash('Помилка обробки функцій аккаунтів Cloudflare!','alert alert-danger')
    return

@rights_required(255)
def handler_ownership(form):
  """Handler for saving/deleting ownership info to DB, received from admin panel"""
  logging.info(f"---------------------------Processing ownership management from admin panel by {current_user.realname}---------------------------")
  try:
    #process delete owner request
    if "buttonDeleteOwnership" in form:
      owner = Ownership.query.filter_by(id=int(form.get('buttonDeleteOwnership').strip())).first()
      if owner:
        db.session.delete(owner)
        db.session.commit()
        logging.info(f"Admin {current_user.realname}>Owner with ID {form.get('buttonDeleteOwnership').strip()} deleted successfully!")
        flash(f'Власник з ID {form.get("buttonDeleteOwnership").strip()} успішно видален від свого домену!','alert alert-success')
        return
      else:
        logging.error(f"Admin {current_user.realname}>Owner with ID {form.get('buttonDeleteOwnership').strip()} deletion error - no such owner!")
        flash(f'Помилка видалення власника домену з ID {form.get("buttonDeleteOwnership").strip()} - такого не існує!','alert alert-warning')
        return
    #process delete request about site is cloned
    if "buttonDeleteOwnershipClone" in form:
      owner = Ownership.query.filter_by(id=int(form.get('buttonDeleteOwnershipClone').strip())).first()
      if owner:
        owner.cloned = ""
        db.session.commit()
        logging.info(f"Admin {current_user.realname}>Owner with ID {form.get('buttonDeleteOwnershipClone').strip()} site clone information deleted successfully!")
        return
      else:
        logging.error(f"Admin {current_user.realname}>Owner with ID {form.get('buttonDeleteOwnershipClone').strip()} deletion error - no such owner!")
        flash(f'Помилка видалення інформації про колнування - власник домену з ID {form.get("buttonDeleteOwnershipClone").strip()} - такого не існує!','alert alert-warning')
        return
    #processing add user request
    elif "buttonAddOwnership" in form:
      domain = form.get("new-ownership-domain", "").strip()
      id = int(form.get("new-ownership-id", "").strip())
      if form.get("new-ownership-clone") != "":
        clone = form.get("new-ownership-clone", "").strip()
      else:
        clone = ""
      if not domain or not id:
        logging.error(f"Admin {current_user.realname}>Some of important parameters for ownership add procedure has not been received!")
        flash(f'Один або декілька важливих параметрів для створення власника домену не були отримані сервером!','alert alert-warning')
        return
      if clone != "":
        data = {"domain": domain, "owner": id, "cloned": clone}
      else:
        data = {"domain": domain, "owner": id}
      new_owner = Ownership(**data)
      db.session.add(new_owner)
      db.session.commit()
      logging.info(f"Admin {current_user.realname}>Owner for {domain} created successfully!")
      flash(f'Власник для домену {domain} успішно створен!','alert alert-success')
      return
  except Exception as err:
    logging.error(f"Admin {current_user.realname}>handler_ownership() global error: {err}")
    flash('Помилка обробки функцій власників доменів!','alert alert-danger')
    return

@rights_required(255)
def handler_servers(form):
  """Handler for saving/deleting servers to DB, received from admin panel"""
  logging.info(f"---------------------------Processing servers management from admin panel by {current_user.realname}---------------------------")
  try:
    #processing delete server request
    if "buttonDeleteServer" in form:
      server = Servers.query.filter_by(id=int(form.get('buttonDeleteServer').strip())).first()
      if server:
        isdefault = server.isdefault
        db.session.delete(server)
        db.session.commit()
        if isdefault:
          flash(f'Сервер {server.name} з ID {form.get("buttonDeleteServer").strip()} успішно видален! УВАГА! це був сервер за замовчанням. Не забудьте встановити новий сервер за замовчанням!','alert alert-success')
        else:
          flash(f'Сервер {server.name} з ID {form.get("buttonDeleteServer").strip()} успішно видален!','alert alert-success')
        logging.info(f"Admin {current_user.realname}>Server {server.name} with ID {form.get('buttonDeleteServer').strip()} deleted successfully!")
        return
      else:
        logging.error(f"Admin {current_user.realname}>Server with ID {form.get('buttonDeleteServer').strip()} deletion error - no such server!")
        flash(f'Помилка видалення серверу з ID {form.get("buttonDeleteServer").strip()} - такого не існує!','alert alert-warning')
        return
    #processing add template request
    elif "buttonAddServer" in form:
      name = form.get("new-server-name", "").strip()
      ip = form.get("new-server-ip", "").strip()
      if not name or not ip:
        logging.error(f"Admin {current_user.realname}>Some of important parameters for server add procedure has not been received!")
        flash(f'Один або декілька важливих параметрів для створення серверу не були отримані сервером!','alert alert-warning')
        return
      data = {"name": name, "ip": ip}
      new_server = Servers(**data)
      db.session.add(new_server)
      db.session.commit()
      logging.info(f"Admin {current_user.realname}>Server {name} created successfully!")
      flash(f'Сервер {name} успішно створен!','alert alert-success')
      return
    #processing set default template request
    elif "buttonDefaultServer" in form:
      id = int(form.get("buttonDefaultServer", "").strip())
      if not id:
        logging.error(f"Admin {current_user.realname}>Some of important parameters for server set default procedure has not been received!")
        flash(f'Один або декілька важливих параметрів для встановлення серверу за замовчанням не були отримані сервером!','alert alert-warning')
        return
      #Check is the new record, which will be the default one, exists at all
      srv = Servers.query.filter_by(id=id).first()
      if not srv:
        logging.error(f"Admin {current_user.realname}>Server with ID {id} doesn't exists! Can set it as the default one!")
        flash(f'Сервер з ID {id} не існує у базі чомусь..','alert alert-warning')
        return
      #Check if it is already is the default one
      default_srv = Servers.query.filter_by(isdefault=True).first()
      if default_srv:
        if str(default_srv.id) == str(id):
          logging.error(f"cli>Server {default_srv.name} with ID {id} already is the default one!")
          flash(f'Сервер {default_srv.name} з ID {id} вже і так є за замовчанням...','alert alert-success')
          return
      #Main function. First of all set all existing records as not default
      Servers.query.update({Servers.isdefault: False})
      #set one selected record as the default one
      server = Servers.query.filter_by(id=id).first()
      if server:
        server.isdefault = True
        db.session.commit()
        logging.info(f"Admin {current_user.realname}>Server {server.name} set as default successfully!")
        flash(f'Сервер {server.name} успішно встановлен за замовчанням!','alert alert-success')
        return
  except Exception as err:
    logging.error(f"Admin {current_user.realname}>handler_servers() global error: {err}")
    flash('Помилка обробки функцій серверів!','alert alert-danger')
    return

@rights_required(255)
def handler_links(form):
  """Handler for saving/deleting links between Cloudflare account and domain info to DB, received from admin panel"""
  logging.info(f"---------------------------Processing links management from admin panel by {current_user.realname}---------------------------")
  try:
    #process delete link request
    if "buttonDeleteLink" in form:
      link = Domain_account.query.filter_by(id=int(form.get('buttonDeleteLink').strip())).first()
      if link:
        db.session.delete(link)
        db.session.commit()
        logging.info(f"Admin {current_user.realname}>Link with ID {form.get('buttonDeleteLink').strip()} deleted successfully!")
        flash(f'Лінк з ID {form.get("buttonDeleteLink").strip()} успішно видален від свого домену!','alert alert-success')
        return
      else:
        logging.error(f"Admin {current_user.realname}>Link with ID {form.get('buttonDeleteLink').strip()} deletion error - no such link!")
        flash(f'Помилка видалення лінку з ID {form.get("buttonDeleteLink").strip()} - такого не існує!','alert alert-warning')
        return
    #processing add link request
    elif "buttonAddLink" in form:
      domain = form.get("new-link-domain", "").strip()
      account = form.get("new-link-account", "").strip()
      if not domain or not account:
        logging.error(f"Admin {current_user.realname}>Some of important parameters for link add procedure has not been received!")
        flash(f'Один або декілька важливих параметрів для створення лінку домена з аккаунтом CF не були отримані сервером!','alert alert-warning')
        return
      data = {"domain": domain, "account": account}
      new_link = Domain_account(**data)
      db.session.add(new_link)
      db.session.commit()
      logging.info(f"Admin {current_user.realname}>Link for {domain} created successfully!")
      flash(f'Лінк для домену {domain} успішно створен!','alert alert-success')
      return
  except Exception as err:
    logging.error(f"Admin {current_user.realname}>handler_links() global error: {err}")
    flash('Помилка обробки функцій лінку доменів до аккаунтів CF!','alert alert-danger')
    return

@rights_required(255)
def handler_accounts(form):
  """Handler for saving/deleting links between Cloudflare account and allowed user info to DB, received from admin panel"""
  logging.info(f"---------------------------Processing accounts management from admin panel by {current_user.realname}---------------------------")
  try:
    #process delete account request
    if "buttonDeleteAccount" in form:
      acc = Cloudflare_account_ownership.query.filter_by(id=int(form.get('buttonDeleteAccount').strip())).first()
      if acc:
        db.session.delete(acc)
        db.session.commit()
        logging.info(f"Admin {current_user.realname}>Account with ID {form.get('buttonDeleteAccount').strip()} deleted successfully!")
        flash(f'Аккаунт Cloudflare з ID {form.get("buttonDeleteAccount").strip()} успішно видален від свого власника!','alert alert-success')
        return
      else:
        logging.error(f"Admin {current_user.realname}>Account with ID {form.get('buttonDeleteAccount').strip()} deletion error - no such account!")
        flash(f'Помилка видалення аккаунту з ID {form.get("buttonDeleteAccount").strip()} - такого не існує!','alert alert-warning')
        return
    #processing add account request
    elif "buttonAddAccount" in form:
      owner = form.get("new-accounts-id", "").strip()
      account = form.get("new-accounts-account", "").strip()
      if not owner or not account:
        logging.error(f"Admin {current_user.realname}>Some of important parameters for account add procedure has not been received!")
        flash(f"Один або декілька важливих параметрів для створення аккаунту зв'язку користувача з аккаунтом CF не були отримані сервером!",'alert alert-warning')
        return
      data = {"account": account, "owner": owner}
      new_acc = Cloudflare_account_ownership(**data)
      db.session.add(new_acc)
      db.session.commit()
      logging.info(f"Admin {current_user.realname}>Owner for account {account} created successfully!")
      flash(f'Власник для аккаунту {account} успішно створен!','alert alert-success')
      return
  except Exception as err:
    logging.error(f"Admin {current_user.realname}>handler_accounts() global error: {err}")
    flash('Помилка обробки функцій лінку власників до аккаунтів CF!','alert alert-danger')
    return

@rights_required(255)
def handler_messages(form):
  """Handler for saving some text message to DB and show it to all current users via flash window"""
  logging.info(f"---------------------------Processing messages from admin panel by {current_user.realname}---------------------------")
  try:
    #process addition of the received message to DB
    if "buttonPublishMessage" in form and form.get("message-textform").strip():
      #getting list of all available users in DB
      users = User.query.order_by(User.username).all()
      for i, s in enumerate(users, 1):
        data = {"foruserid": s.id, "text": form.get("message-textform").strip()}
        new_msg = Messages(**data)
        db.session.add(new_msg)
        logging.info(f"Broadcast message successfully added for user {s.id}...")
      db.session.commit()
      logging.info(f"Admin {current_user.realname}>Broadcast message for all users added successfully for all available users in DB!")
      flash(f'Массове повідомлення успішно додано в чергу для всіх користувачів!','alert alert-success')
      return
    #process full clearance of all messages in DB
    elif "buttonClearMessages" in form:
      Messages.query.delete()
      db.session.commit()
      logging.info(f"Admin {current_user.realname}>All messages were cleared in DB!")
      flash(f'Всі всі очікуючі массові повідомлення успішно видалені з бази!','alert alert-success')
      return
    else:
      logging.error(f"Admin {current_user.realname}>handler_messages() called without any actual parameter. How?")
      flash(f'Не ясно як ви сюди потрапили, дивіться логи...','alert alert-warning')
      return
  except Exception as err:
    logging.error(f"Admin {current_user.realname}>handler_publishMessage() global error: {err}")
    flash('Якась глобальна помилка при додаванні повідомлення! Дивіться логи!','alert alert-danger')
    return