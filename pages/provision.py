from flask import render_template,request,redirect,flash,Blueprint,current_app
from flask_login import login_required,current_user
import logging,os
from db.database import Provision_templates
from functions.provision import start_autoprovision
from functions.pages_forms import *

provision_bp = Blueprint("provision", __name__)
@provision_bp.route("/provision", methods=['GET','POST'])
@login_required
def provision():
    #Draw the main provision page interface
    if request.method == 'GET':
        try:
            #parsing git repositories available
            templates_list, first_template = loadTemplatesList()
            #parsing Cloudflare accounts available
            cf_list, first_cf = loadClodflareAccounts()
            #parsing Servers accounts available
            server_list, first_server = loadServersList()
            return render_template("template-provision.html",templates=templates_list,first_template=first_template,cf_list=cf_list,first_cf=first_cf,first_server=first_server,server_list=server_list)
        except Exception as err:
            logging.error(f"Provision page provision() render error: {err}")
            asyncio.run(send_to_telegram(f"provision() error: {err}",f"🚒Provision page render:"))
            return ""
    #Do some updates with a new data
    if request.method == 'POST':
        #check if we have all necessary data received
        if not request.form['domain'] or not request.form['selected_template'] or not request.form['selected_server'] or not request.form['selected_account'] or not request.form['buttonSubmit']:
            flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
            logging.error(f"provision() error: some of important parameters has not been sent!")
            asyncio.run(send_to_telegram(f"provision(): some of the important parameters has not been received!",f"🚒Provision function:"))
            return redirect("/",301)
        #starts main provision actions
        else:
            #cleans up the domain string
            domain = request.form['domain'].strip().removeprefix("https://").removeprefix("http://").rstrip("/").lower()
            finalPath = os.path.join(current_app.config["WEB_FOLDER"],domain)
            if os.path.exists(finalPath):
                logging.info(f"---------------------------Starting automatic deploy for site {domain} by {current_user.realname}----------------------------")
                logging.error(f"Site {domain} already exists! Remove it before new deploy!")
                flash(f"Сайт вже існує! Спочатку видаліть його і потім можна буде розгорнути знову!", 'alert alert-danger')
                logging.info(f"--------------------Automatic deploy for site {domain} from template {request.form['selected_template'].strip()} by {current_user.realname} finshed with error-----------------------")
                return redirect("/provision",301)
            #Getting repository's git path after we know its name as given in the request
            repo = Provision_templates.query.filter_by(name=request.form['selected_template'].strip()).first()
            if repo:
                #starting autoprovision. If everything is ok, redirect to root page
                if start_autoprovision(domain,request.form['selected_account'].strip(),request.form['selected_server'].strip(),repo.repository,current_user.realname):
                    flash(f"Сайт {domain} успішно встановлено!",'alert alert-success')
                    logging.info(f"Site {domain} provisioned successfully!")
                    return redirect("/",301)
                else:
                    logging.error(f"Error while site {domain} provision!")
                    flash(f"Помилки при запуску сайту {domain}, дивіться логи!",'alert alert-danger')
                    return redirect("/provision",301)
            else:
                flash('Помилка! Не можу отримати шлях гіт репозиторію для вибраного шаблону!','alert alert-danger')
                logging.error(f"Error getting repository path for the given name({request.form['selected_template']}) from the request")
            return redirect("/",301)
