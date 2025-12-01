from flask import render_template,request,redirect,flash,Blueprint
from flask_login import login_required
import logging
from db.database import Provision_templates

provision_bp = Blueprint("provision", __name__)
@provision_bp.route("/provision", methods=['GET','POST'])
@login_required
def provision():
    #Draw the main provision page interface
    if request.method == 'GET':
        try:
            templates = Provision_templates.query.order_by(Provision_templates.name).all()
            first_template = templates_list = ""
            if len(templates) == 0:
                templates_list = first_template = "Шаблони відсутні у базі!"
            else:
                for i, s in enumerate(templates, 1):
                    templates_list += f"<li><a class=\"dropdown-item\" href=\"#\" data-value=\"{s.name}\">{s.name} ({s.repository})</a></li>\n\t\t"
            #Select one template which has Default=True setting in the database
            def_template = Provision_templates.query.filter_by(isdefault=True).first()
            if def_template:
                first_template = def_template.name
            else:
                first_template = "Шаблон за замовчуванням не знайден! Виберіть вручну"
                logging.error("Unknown error selecting default template!")
        except Exception as err:
            logging.error(f"CLI show templates function error: {err}")
            print(f"CLI show templates function error: {err}")
        return render_template("template-provision.html",templates=templates_list,first_template=first_template)
    #Do some updates with a new data
    if request.method == 'POST':
        #check if we have all necessary data received
        if not request.form['domain'] or not request.form['selected_template'] or not request.form['buttonSubmit']:
            flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
            return redirect("/provision",301)
        #starts main provision actions
        if request.form['domain'] and request.form['selected_template'] and request.form['buttonSubmit']:
            flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-success')
            return redirect("/provision",301)
        return redirect("/",301)
