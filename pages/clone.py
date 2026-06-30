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
  """POST request processor: processes a site clone request - either to a single domain, or, if the bulk domains_list textarea is filled, to every domain listed there"""
  domain = ""
  selected_account = ""
  selected_server = ""
  try:
    #the bulk domains list (one domain per line) takes priority over the single domain field, if it's not empty
    domains_list_raw = (request.form.get('domains_list') or '').strip()
    #check if we have all necessary data received
    if (not request.form.get('domain') and not domains_list_raw) or not request.form.get('selected_account') or not request.form.get('selected_server') or not request.form.get('buttonStartClone'):
      flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
      logging.error(f"doClone(): some of the important parameters has not been received!")
      return redirect(f"/clone?source_site={request.form.get('buttonStartClone')}",302)
    source_site = request.form.get("buttonStartClone","").strip()
    selected_account = request.form.get("selected_account","").strip()
    selected_server = request.form.get("selected_server","").strip()
    web_folder = current_app.config.get("WEB_FOLDER") or ""
    if not web_folder:
      logging.error(f"doClone(): somehow web_folder variable is empty!")
      flash(f"Помилка! Змінна web_folder прийшла порожньою! Дивіться логи.",'alert alert-danger')
      return redirect(f"/clone?source_site={source_site}",302)
    its_not_a_subdomain = 'not-a-subdomain' in request.form
    #------------------------- bulk clone: one new site per domain listed in the textarea -------------------------
    if domains_list_raw:
      logging.info(f"doClone(): bulk list of domains has been received from {current_user.realname}: {domains_list_raw} ----------------------------")
      domains_to_clone = [d.strip() for d in domains_list_raw.splitlines() if d.strip()]
      succeeded = []
      failed = []
      for raw_domain in domains_to_clone:
        normalized = normalize_domain(raw_domain)
        if not isinstance(normalized, str):
          logging.error(f"doClone(): bulk clone - invalid domain format skipped: {raw_domain}")
          failed.append(f"{raw_domain} (невірний формат домену)")
          continue
        domain = normalized
        finalPath = os.path.join(web_folder,domain)
        if os.path.exists(finalPath):
          logging.error(f"doClone(): bulk clone - site {domain} already exists! Skipping...")
          failed.append(f"{domain} (вже існує)")
          continue
        logging.info(f"---------------------------Starting bulk clone for site {domain} from the site {source_site} by {current_user.realname}----------------------------")
        if start_clone(domain,source_site,selected_account,selected_server,current_user.realname,web_folder,its_not_a_subdomain):
          logging.info(f"doClone(): bulk clone - site {source_site} sucessfully cloned into {domain} site!")
          finishJob("",domain,selected_account,selected_server)
          succeeded.append(domain)
        else:
          logging.error(f"doClone(): bulk clone - failed to clone {source_site} into {domain}!")
          finishJob("",domain,selected_account,selected_server,emerg_shutdown=True)
          failed.append(f"{domain} (помилка клонування)")
      clearCache()
      if succeeded:
        flash(f"Сайт {source_site} успішно клоновано на {len(succeeded)} домен(ів): {', '.join(succeeded)}",'alert alert-success')
      if failed:
        flash(f"Не вдалося клонувати на {len(failed)} домен(ів): {', '.join(failed)}",'alert alert-danger')
      if not succeeded and not failed:
        flash("Не передано жодного валідного домену для клонування зі списку!",'alert alert-warning')
      return redirect("/",302)
    #------------------------- single domain clone -------------------------
    else:
      #cleans up the domain string
      domain = str(normalize_domain(request.form.get("domain","")))
      if not domain:
        logging.error(f"doClone(): somehow domain variable is empty!")
        flash(f"Помилка! Змінна domain({domain}) прийшла порожньою! Дивіться логи.",'alert alert-danger')
        return redirect(f"/clone?source_site={source_site}",302)
      finalPath = os.path.join(web_folder,domain)
      if os.path.exists(finalPath):
        logging.info(f"---------------------------Starting clone for site {domain} from the site {source_site} by {current_user.realname}----------------------------")
        logging.error(f"doClone(): Site {domain} already exists! Remove it before cloning!")
        flash(f"Сайт {domain} вже існує! Спочатку видаліть його і потім можна буде клонувати!", 'alert alert-danger')
        logging.info(f"--------------------Clone of the site {source_site} as the {domain} by {current_user.realname} finshed with error-----------------------")
        return redirect(f"/clone?source_site={source_site}",302)
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
