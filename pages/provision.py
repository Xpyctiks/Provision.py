from flask import render_template,request,redirect,flash,Blueprint
from flask_login import login_required,current_user
import logging
from db.database import Provision_templates, Cloudflare, Servers
from functions.provision import start_autoprovision

provision_bp = Blueprint("provision", __name__)
@provision_bp.route("/provision", methods=['GET','POST'])
@login_required
def provision():
    #Draw the main provision page interface
    if request.method == 'GET':
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
                logging.error("Unknown error selecting default template!")
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
                logging.error("Unknown error selecting default account!")
            #parsing Servers accounts available
            srv = Servers.query.order_by(Servers.name).all()
            first_server = server_list = ""
            if len(cf) == 0:
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
                logging.error("Unknown error selecting default account!")
            return render_template("template-provision.html",templates=templates_list,first_template=first_template,cf_list=cf_list,first_cf=first_cf,first_server=first_server,server_list=server_list)
        except Exception as err:
            logging.error(f"Provision page render error: {err}")
            print(f"Provision page render error: {err}")
    #Do some updates with a new data
    if request.method == 'POST':
        #check if we have all necessary data received
        if not request.form['domain'] or not request.form['selected_template'] or not request.form['buttonSubmit']:
            flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
            return redirect("/provision",301)
        #starts main provision actions
        if request.form['domain'] and request.form['selected_template'] and request.form['selected_server'] and request.form['selected_account'] and request.form['buttonSubmit']:
            #Getting repository's git path after we know its name as given in the request
            repo = Provision_templates.query.filter_by(name=request.form['selected_template'].strip()).first()
            if repo:
                start_autoprovision(request.form['domain'].strip(),request.form['selected_account'].strip(),request.form['selected_server'].strip(),repo.repository,current_user.realname)
            else:
                flash('Помилка! Не можу отримати шлях гіт репозиторію для вибраного шаблону!','alert alert-danger')
                logging.error(f"Error getting repository path for the given name({request.form['selected_template']}) from the request")
            return redirect("/",301)
        return redirect("/",301)
