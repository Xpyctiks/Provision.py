from flask import render_template,request,redirect,flash,Blueprint,current_app
from flask_login import login_required,current_user
import logging,os
from db.database import Provision_templates
from functions.provision_func import start_autoprovision
from functions.pages_forms import *
from functions.site_actions import normalize_domain,is_admin

provision_bp = Blueprint("provision", __name__)
@provision_bp.route("/provision/", methods=['GET'])
@login_required
def show_provision_page():
  """GET request: shows /provision page"""
  try:
    #parsing git repositories available
    templates_list, first_template = loadTemplatesList()
    #parsing Cloudflare accounts available
    cf_list, first_cf = loadClodflareAccounts()
    #parsing Servers accounts available
    server_list, first_server = loadServersList()
    return render_template("template-provision.html",templates=templates_list,first_template=first_template,cf_list=cf_list,first_cf=first_cf,first_server=first_server,server_list=server_list,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"show_provision_page(): general error by {current_user.realname}: {err}")
    flash('Загальна помилка на сторінці /provision! Дивіться логи!','alert alert-danger')
    return redirect("/",302)

@provision_bp.route("/provision/", methods=['POST'])
@login_required
def do_provision():
  """POST request processor: process automatic site deployment"""
  try:
    web_folder = current_app.config.get("WEB_FOLDER","")
    if not web_folder:
      logging.error(f"do_provision(): web_folder variable is empty!")
      flash(f"Загальна помилка, дивіться логи!",'alert alert-danger')
      return redirect("/provision/",302)
    #check if we have all necessary data received
    if not request.form.get('domain') or not request.form.get('selected_template') or not request.form.get('selected_server') or not request.form.get('selected_account') or not request.form.get('buttonSubmit'):
      flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
      logging.error(f"provision() error: some of important parameters has not been sent!")
      return redirect("/",302)
    #starts main provision actions
    else:
      #cleans up the domain string
      domain = str(normalize_domain(request.form.get('domain','').removeprefix("https://").removeprefix("http://").rstrip("/")))
      finalPath = os.path.join(web_folder,domain)
      if os.path.exists(finalPath):
        logging.info(f"---------------------------Starting automatic deploy for site {domain} by {current_user.realname}----------------------------")
        logging.error(f"Site {domain} already exists! Remove it before new deploy!")
        flash(f"Сайт {domain} вже існує! Спочатку видаліть його і потім можна буде розгорнути знову!", 'alert alert-danger')
        logging.info(f"--------------------Automatic deploy for site {domain} from template {request.form.get('selected_template','').strip()} by {current_user.realname} finshed with error-----------------------")
        return redirect("/provision/",302)
      if 'not-a-subdomain' in request.form:
        its_not_a_subdomain = True
      else:
        its_not_a_subdomain = False
      #Getting repository's git path after we know its name as given in the request
      repo = Provision_templates.query.filter_by(name=request.form.get('selected_template','').strip()).first()
      if repo:
        #starting autoprovision. If everything is ok, redirect to root page
        if start_autoprovision(domain,request.form.get('selected_account','').strip(),request.form.get('selected_server','').strip(),repo.repository,current_user.realname,its_not_a_subdomain):
          flash(f"Сайт {domain} успішно встановлено!",'alert alert-success')
          logging.info(f"do_provision(): Site {domain} provisioned successfully!")
          return redirect("/",302)
        else:
          logging.error(f"do_provision(): Error while site {domain} provision!")
          flash(f"Помилки при запуску сайту {domain}, дивіться логи!",'alert alert-danger')
          return redirect("/provision/",302)
      else:
        flash('Помилка! Не можу отримати шлях гіт репозиторію для вибраного шаблону!','alert alert-danger')
        logging.error(f"do_provision(): Error getting repository path for the given name({request.form.get('selected_template')}) from the request")
      return redirect("/",302)
  except Exception as err:
    logging.error(f"do_provision(): general error by {current_user.realname}: {err}")
    flash('Загальна помилка при обробці POST запиту на сторінці /provision! Дивіться логи!','alert alert-danger')
    return redirect("/",302)
