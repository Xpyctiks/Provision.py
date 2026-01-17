import logging
from db.db import db
from db.database import *
from functions.load_config import load_config
from flask import current_app

def add_template(name: str,repository: str) -> None:
  """CLI only function: adds new template of site provision to the database"""
  logging.info("-----------------------Starting CLI functions: add_template")
  try:
    if Provision_templates.query.filter_by(name=name).first():
      print(f"Template name \"{name}\" creation error - already exists!")
      logging.error(f"cli>Template name \"{name}\" creation error - already exists!")
      quit(1)
    else:
      new_template = Provision_templates(
        name=name,
        repository=repository,
      )
      db.session.add(new_template)
      db.session.commit()
      print(f"New template \"{name}\" - \"{repository}\" created successfully!")
      logging.info(f"cli>New template \"{name}\" - \"{repository}\" created successfully!")
    #check if there is only one just added record - set it as default
    if len(Provision_templates.query.filter_by().all()) == 1:
      tmp = Provision_templates.query.filter_by(name=name).first()
      if tmp:
        tmp.isdefault = True
        db.session.commit()
    quit(0)
  except Exception as err:
    logging.error(f"cli>New repository \"{name}\" - \"{repository}\" creation error: {err}")
    print(f"New repository \"{name}\" - \"{repository}\" creation error: {err}")
    quit(1)

def del_template(name: str) -> None:
  """CLI only function: deletes a template of site provision from the database"""
  logging.info("-----------------------Starting CLI functions: del_template")
  try:
    template = Provision_templates.query.filter_by(name=name).first()
    if template:
      if template.isdefault == True:
        print("Warning, that was the Default template. You need to make another template the default one!")
      db.session.delete(template)
      db.session.commit()
      load_config(current_app)
      print(f"Template \"{template.name}\" deleted successfully!")
      logging.info(f"cli>Template \"{template.name}\" deleted successfully!")
      quit(0)
    else:
      print(f"Template \"{name}\" deletion error - no such template!")
      logging.error(f"cli>Template \"{name}\" deletion error - no such template!")
      quit(1)
  except Exception as err:
    logging.error(f"cli>Template \"{name}\" deletion error: {err}")
    print(f"Template \"{name}\" deletion error: {err}")
    quit(1)

def upd_template(name: str, new_repository: str) -> None:
  """CLI only function: updates a template with a new repository address"""
  logging.info("-----------------------Starting CLI functions: upd_template")
  try:
    template = Provision_templates.query.filter_by(name=name).first()
    if template:
      template.repository = new_repository
      db.session.commit()
      print(f"Repository for template \"{name}\" updated successfully to {new_repository}!")
      logging.info(f"cli>Repository for template \"{name}\" updated successfully to{new_repository}!")
      quit(0)
    else:
      print(f"Template \"{name}\" update error - no such template!")
      logging.error(f"cli>Template \"{name}\" update error - no such template!")
      quit(1)
  except Exception as err:
    logging.error(f"cli>Template \"{name}\" update error: {err}")
    print(f"Template \"{name}\" update error: {err}")
    quit(1)

def show_templates() -> None:
  """CLI only function: shows all available site provision repositories from the database"""
  logging.info("-----------------------Starting CLI functions: show_templates")
  try:
    templates = Provision_templates.query.order_by(Provision_templates.name).all()
    if len(templates) == 0:
      print("No templates found in DB!")
      logging.error("cli>No templates found in DB!")
      quit(0)
    for i, s in enumerate(templates, 1):
      print("-------------------------------------------------------------------------------------------------------")
      print(f"ID: {s.id}, Name: {s.name}, Repository address: {s.repository}, IsDefault: {s.isdefault}, Created: {s.created}")
      print("-------------------------------------------------------------------------------------------------------")
    quit(0)
  except Exception as err:
    logging.error(f"cli>CLI show templates function error: {err}")
    print(f"CLI show templates function error: {err}")
    quit(1)

def default_template(name: str) -> None:
  """CLI only function: sets a template as the default one"""
  logging.info("-----------------------Starting CLI functions: default_template")
  try:
    #Check is the new record, which will be the default one, exists at all
    template = Provision_templates.query.filter_by(name=name).first()
    if not template:
      print(f"Template \"{name}\" doesn't exists! Can set it as the default one!")
      logging.error(f"cli>Template \"{name}\" doesn't exists! Can set it as the default one!")
      quit(1)
    #Check if it is already is the default one
    default_template = Provision_templates.query.filter_by(isdefault=True).first()
    if default_template:
      if default_template.name == name:
        print(f"Template \"{name}\" already is the default one!")
        logging.error(f"cli>Template \"{name}\" already is the default one!")
        quit(1)
    #Main function. First of all set all existing records as not default
    Provision_templates.query.update({Provision_templates.isdefault: False})
    #set one selected record as the default one
    template = Provision_templates.query.filter_by(name=name).first()
    if template:
      template.isdefault = True
      db.session.commit()
      print(f"The template \"{name}\" is set as default one!")
      logging.info(f"cli>The template \"{name}\" is set as default one!")
    quit(0)
  except Exception as err:
    logging.error(f"cli>Set default template \"{name}\" error: {err}")
    print(f"Set default template \"{name}\" error: {err}")
    quit(1)

def help_templates() -> None:
  """CLI only function: shows hints for TEMPLATES command"""
  print (f"""
Possible completion:
  add   <name> <git_repo_address>
  default <name>
  del   <name>
  upd   <name> <new_git_repo_address>
  """)
  quit(0)
