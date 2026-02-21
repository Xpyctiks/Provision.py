from flask import redirect,Blueprint,request,render_template,flash,current_app
from flask_login import login_required,current_user
from functions.pages_forms import *
from functions.clone_func import *
from functions.site_actions import normalize_domain,is_admin,clearCache
from functions.provision_func import finishJob

import os

clone_bp = Blueprint("clone", __name__)
@clone_bp.route("/clone/", methods=['GET'])
@login_required
def showClonePage():
  """GET request: show /clone page"""
  try:
    if not request.args.get('source_site'):
      flash(f"Не передано обов'язкового параметру для сторінки клонування. Мабуть ви опинилсь там в результаті помилки.", 'alert alert-danger')
      logging.error(f"showClonePage(): GET parameter source_site was not received! by {current_user.realname}")
      return redirect("/",302)
    #parsing git repositories available
    templates_list, first_template = loadTemplatesList()
    #parsing Cloudflare accounts available
    cf_list, first_cf = loadClodflareAccounts()
    #parsing Servers accounts available
    server_list, first_server = loadServersList()
    return render_template("template-clone.html",source_site=(request.args.get('source_site') or 'Error').strip(),templates=templates_list,first_template=first_template,cf_list=cf_list,first_cf=first_cf,first_server=first_server,server_list=server_list,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"Clone page general render error by {current_user.realname}: {err}")
    flash(f"Неочікувана помилка на сторінці колнування, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

@clone_bp.route("/clone/", methods=['POST'])
@login_required
def doClone():
  """POST request processor: processes a site clone request"""
  try:
    #check if we have all necessary data received
    if not request.form.get('domain') or not request.form.get('selected_account') or not request.form.get('selected_server') or not request.form.get('buttonStartClone'):
      flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
      logging.error(f"doClone(): some of the important parameters has not been received!")
      return redirect(f"/clone?source_site={request.form.get('buttonStartClone')}",302)
    #starts main provision actions
    else:
      #cleans up the domain string
      domain = str(normalize_domain(request.form.get("domain","")))
      source_site = request.form.get("buttonStartClone","").strip()
      selected_account = request.form.get("selected_account","").strip()
      selected_server = request.form.get("selected_server","").strip()
      web_folder = current_app.config.get("WEB_FOLDER") or ""
      if not web_folder or not domain:
        logging.error(f"doClone(): somehow web_folder or domain variable is empty!")
        flash(f"Помилка! Якась змінна web_folder({web_folder}) чи domain({domain}) прийшла порожньою! Дивіться логи.",'alert alert-danger')
        return redirect(f"/clone?source_site={request.form.get('buttonStartClone')}",302)
      finalPath = os.path.join(web_folder,domain)
      if os.path.exists(finalPath):
        logging.info(f"---------------------------Starting clone for site {domain} from the site {source_site} by {current_user.realname}----------------------------")
        logging.error(f"doClone(): Site {domain} already exists! Remove it before cloning!")
        flash(f"Сайт {domain} вже існує! Спочатку видаліть його і потім можна буде клонувати!", 'alert alert-danger')
        logging.info(f"--------------------Clone of the site {source_site} as the {domain} by {current_user.realname} finshed with error-----------------------")
        return redirect(f"/clone?source_site={source_site}",302)
      if 'not-a-subdomain' in request.form:
        its_not_a_subdomain = True
      else:
        its_not_a_subdomain = False
      #starting clone procedure
      if start_clone(domain,source_site,selected_account,selected_server,current_user.realname,web_folder,its_not_a_subdomain):
        logging.info(f"doClone(): Site {source_site} sucessfully cloned into {domain} site!")
        finishJob("",domain,selected_account,selected_server)
        flash(f"Сайт {source_site} успішно клоновано в сайт {domain}!",'alert alert-success')
        clearCache()
        return redirect("/",302)
      else:
        finishJob("",domain,selected_account,selected_server,emerg_shutdown=True)
        flash(f"Помилка клонування {source_site} до сайту {domain}! Дивіться логи!",'alert alert-danger')
        clearCache()
        return redirect(f"/clone?source_site={source_site}",302)
  except Exception as err:
    logging.error(f"doClone(): POST process error by {current_user.realname}: {err}")
    finishJob("",domain,selected_account,selected_server,emerg_shutdown=True)
    flash(f"Загальна помилка обробки POST запиту на сторінці /clone! Дивіться логи!",'alert alert-danger')
    clearCache()
    return redirect(f"/clone?source_site={request.form.get('buttonStartClone')}",302)
