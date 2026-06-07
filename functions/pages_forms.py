import logging
import os
import sqlite3
import json
import requests
from db.database import *

def loadTemplatesList():
  try:
    #parsing git repositories available
    templates = Provision_templates.query.order_by(Provision_templates.name).all()
    first_template = templates_list = ""
    if len(templates) == 0:
      templates_list = first_template = "Шаблони відсутні у базі!"
    else:
      for i, t in enumerate(templates, 1):
        templates_list += f"<li><a class=\"dropdown-item template\" href=\"#\" data-value=\"{t.name}\">{t.name} ({t.repository})</a></li>\n\t\t"
    #Select one template which has Default=True setting in the database
    def_template = Provision_templates.query.filter_by(isdefault=True).first()
    if def_template:
      first_template = def_template.name
    else:
      first_template = "Шаблон за замовчуванням не знайден! Виберіть вручну"
      logging.error("loadTemplatesList(): Unknown error selecting default template!")
    return templates_list, first_template
  except Exception as err:
    logging.error(f"loadTemplatesList(): global error: {err}")
    return "Error", "Error"

def loadClodflareAccounts():
  try:
    #parsing Cloudflare accounts available
    cf = Cloudflare.query.order_by(Cloudflare.account).all()
    first_cf = cf_list = ""
    if len(cf) == 0:
      cf_list = "Аккаунти відсутні у базі!"
    else:
      for i, c in enumerate(cf, 1):
        cf_list += f"<li><a class=\"dropdown-item account\" href=\"#\" data-value=\"{c.account}\">{c.account}</a></li>\n\t\t"
    #Select one template which has Default=True setting in the database
    def_cf = Cloudflare.query.filter_by(isdefault=True).first()
    if def_cf:
      first_cf = def_cf.account
    else:
      first_cf = ""
      logging.error("loadClodflareAccounts(): Unknown error selecting default account!")
    return cf_list, first_cf
  except Exception as err:
    logging.error(f"loadClodflareAccounts(): global error {err}")
    return "Error", "Error"

def load_cf_active_zones() -> dict:
  """Loads all zones from all Cloudflare accounts in DB."""
  cf_zones = {}
  try:
    accounts = Cloudflare.query.all()
    for acc in accounts:
      try:
        headers = {
          "X-Auth-Email": acc.account,
          "X-Auth-Key": acc.token,
          "Content-Type": "application/json"
        }
        page = 1
        while True:
          url = f"https://api.cloudflare.com/client/v4/zones?per_page=50&page={page}"
          r = requests.get(url, headers=headers, timeout=10).json()
          if not r.get("success"):
            logging.error(f"load_cf_active_zones(): Failed to load zones for account {acc.account}: {r.get('errors')}")
            break
          for zone in r.get("result", []):
            cf_zones[zone["name"]] = zone["status"]
          if page >= r["result_info"]["total_pages"]:
            break
          page += 1
      except Exception as err:
        logging.error(f"load_cf_active_zones(): Error for account {acc.account}: {err}")
  except Exception as err:
    logging.error(f"load_cf_active_zones(): Global error: {err}")
  return cf_zones

def loadServersList():
  try:
    #parsing Servers accounts available
    srv = Servers.query.order_by(Servers.name).all()
    first_server = server_list = ""
    if len(srv) == 0:
      server_list = "Аккаунти відсутні у базі!"
    else:
      for i, s in enumerate(srv, 1):
        server_list += f"<li><a class=\"dropdown-item server\" href=\"#\" data-value=\"{s.name}\">{s.name}</a></li>\n\t\t"
    #Select one template which has Default=True setting in the database
    def_srv = Servers.query.filter_by(isdefault=True).first()
    if def_srv:
      first_server = def_srv.name
    else:
      first_server = ""
      logging.error("loadServersList(): Unknown error selecting default account!")
    return server_list, first_server
  except Exception as err:
    logging.error(f"loadServersList(): global error: {err}")
    return "Error", "Error"

def getSiteOwner(domain: str) -> str:
  """While parsing the root page, this function returns a Realname of the owner for every domain in the list"""
  try:
    owner = Ownership.query.filter_by(domain=domain).first()
    if owner:
      user = User.query.filter_by(id=owner.owner).first()
      return f"{user.realname}"
    else:
      return "Шукаю власника 💔"
  except Exception as err:
    logging.error(f"getSiteOwner(): global error: {err}")
    return "ERROR!"

def getSiteCreated(domain: str) -> str:
  """While parsing the root page, this function returns a creation date of the every domain in the list"""
  try:
    owner = Ownership.query.filter_by(domain=domain).first()
    #If the domain found in the DB
    if owner:
      if owner.cloned == "":
        #if the site is not cloned one
        return owner.created.strftime("%d-%m-%Y %H:%M:%S")
      else:
        #if the site is a cloned one
        return f"{owner.created.strftime('%d-%m-%Y %H:%M:%S')}.<br>Клон {owner.cloned}"
    else:
      return "невідомо🤷🏼‍♂️"
  except Exception as err:
    logging.error(f"getSiteCreated(): global error: {err}")
    return "ERROR!"

def getSiteHrefHistory(domain: str, web_folder: str) -> dict:
  """While parsing the root page, this function reads the site's clones-history.json and returns slug/hreflang of the entry"""
  try:
    history_path = os.path.join(web_folder, domain, "clones-history.json")
    if not os.path.exists(history_path):
      return {"slug": "🤕", "hreflang": "🤕"}
    with open(history_path, "r", encoding="utf-8") as f:
      history = json.load(f)
    for entry in history:
      if entry.get("status") == "current":
        return {"slug": entry.get("slug", "🤕"), "hreflang": entry.get("hreflang", "🤕")}
    return {"slug": "🤕", "hreflang": "🤕"}
  except Exception as err:
    logging.error(f"getSiteCurrentClone(): global error for domain {domain}: {err}")
    return {"slug": "🚨", "hreflang": "🚨"}

def getSiteLocale(domain: str, web_folder: str) -> str:
  """While parsing the root page, this function reads the site's database and returns its Lang tag"""
  try:
    db_path = os.path.join(web_folder, domain, "database", "database.db")
    if not os.path.exists(db_path):
      logging.error(f"getSiteLocale(): Error connecting to sqlite DB - no DB found at {db_path}!")
      return '<span data-bs-toggle="tooltip" data-bs-placement="top" title="Дивно,але бази немає...">🚨</span>'
    with sqlite3.connect(db_path) as conn:
      cur = conn.cursor()
      cur.execute("SELECT extra_fields FROM seo_metas LIMIT 1")
      row = cur.fetchone()
    if row and row[0]:
      return json.loads(row[0]).get("locale", "")
    return '🤔'
  except Exception as err:
    logging.error(f"getSiteLocale(): global error for domain {domain}: {err}")
    return '<span data-bs-toggle="tooltip" data-bs-placement="top" title="Якась дуже серьозна помилка...">🚨</span>'
