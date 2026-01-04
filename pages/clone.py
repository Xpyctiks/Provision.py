from flask import redirect,Blueprint,request,render_template,flash,current_app
from flask_login import login_required,current_user
from functions.pages_forms import *
from functions.clone import *
import os,asyncio
from functions.send_to_telegram import send_to_telegram

clone_bp = Blueprint("clone", __name__)
@clone_bp.route("/clone", methods=['GET'])
@login_required
def showClonePage():
    try:
        if not request.args.get('source_site'):
            flash(f"Не передано обов'язкового параметру для сторінки клонування. Мабуть ви опинилсь там в результаті помилки.", 'alert alert-danger')
            logging.error(f"showClonePage(): GET parameter source_site was not received!")
            asyncio.run(send_to_telegram(f"GET parameter source_site was not received!",f"🚒Provision error by {current_user.realname}:"))
            return redirect("/",301)
        #parsing git repositories available
        templates_list, first_template = loadTemplatesList()
        #parsing Cloudflare accounts available
        cf_list, first_cf = loadClodflareAccounts()
        #parsing Servers accounts available
        server_list, first_server = loadServersList()
        return render_template("template-clone.html",source_site=(request.args.get('source_site') or 'Error').strip(),templates=templates_list,first_template=first_template,cf_list=cf_list,first_cf=first_cf,first_server=first_server,server_list=server_list)
    except Exception as err:
        logging.error(f"Clone page general render error: {err}")
        asyncio.run(send_to_telegram(f"Clone page general render error: {err}",f"🚒Provision error by {current_user.realname}:"))
        flash(f"Неочікувана помилка на сторінці колнування, дивіться логи!", 'alert alert-danger')
        return redirect("/",301)

@clone_bp.route("/clone", methods=['POST'])
@login_required
def doClone():
    try:
        #check if we have all necessary data received
        if not request.form['domain'] or not request.form['selected_account'] or not request.form['selected_server'] or not request.form['buttonStartClone']:
            flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
            logging.error(f"doClone(): some of the important parameters has not been received!")
            asyncio.run(send_to_telegram(f"doClone(): some of the important parameters has not been received!",f"🚒Provision error by {current_user.realname}:"))
            return redirect(f"/clone?source_site={request.form['buttonStartClone']}",301)
        #starts main provision actions
        else:
            #cleans up the domain string
            domain = request.form['domain'].strip().removeprefix("https://").removeprefix("http://").rstrip("/")
            source_site = request.form['buttonStartClone'].strip()
            selected_account = request.form['selected_account'].strip()
            selected_server = request.form['selected_server'].strip()
            finalPath = os.path.join(current_app.config["WEB_FOLDER"],domain)
            if os.path.exists(finalPath):
                logging.info(f"---------------------------Starting clone for site {domain} from the site {source_site} by {current_user.realname}----------------------------")
                logging.error(f"Site {domain} already exists! Remove it before cloning!")
                flash(f"Сайт {domain} вже існує! Спочатку видаліть його і потім можна буде клонувати!", 'alert alert-danger')
                logging.info(f"--------------------Clone of the site {source_site} as the {domain} by {current_user.realname} finshed with error-----------------------")
                return redirect("/",301)
            #starting clone procedure
            if start_clone(domain,source_site,selected_account,selected_server,current_user.realname):
                flash(f"Сайт {source_site} успішно клоновано в сайт {domain}!",'alert alert-success')
                logging.info(f"Site {source_site} sucessfully cloned into {domain} site!")
                return redirect("/",301)
            else:
                logging.error(f"Error cloning of {source_site} as site {domain} - repository of template {request.form['selected_template']} is not found!")
                asyncio.run(send_to_telegram(f"Error cloning of {request.form['buttonStartClone'].strip()} as site {domain} - repository of template {request.form['selected_template']} is not found!",f"🚒Provision clone page:"))
                flash(f"Помилка клонування {request.form['buttonStartClone'].strip()} до сайту {domain} - репозиторій шаблону {request.form['selected_template']} не знайден!",'alert alert-danger')
                return redirect("/",301)
    except Exception as err:
        logging.error(f"Provision page render error: {err}")
        print(f"Provision page render error: {err}")
        return render_template("template-clone.html",)
