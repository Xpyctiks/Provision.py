import logging,asyncio
from db.database import Provision_templates, Cloudflare, Servers
from functions.send_to_telegram import send_to_telegram

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
        logging.error(f"loadTemplatesList() error: {err}")
        asyncio.run(send_to_telegram(f"loadTemplatesList() error: {err}",f"🚒Provision page render:"))
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
        logging.error(f"loadClodflareAccounts() error: {err}")
        asyncio.run(send_to_telegram(f"loadClodflareAccounts() error: {err}",f"🚒Provision page render:"))
        return "Error", "Error"

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
        logging.error(f"loadServersList() error: {err}")
        asyncio.run(send_to_telegram(f"loadServersList() error: {err}",f"🚒Provision page render:"))
        return "Error", "Error"
