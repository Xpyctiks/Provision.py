from flask import render_template,request,redirect,flash,Blueprint
from flask_login import current_user, login_required
import logging,asyncio,subprocess,os,pathlib
from functions.send_to_telegram import send_to_telegram
from werkzeug.utils import secure_filename
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
                templates_list = first_template = "No templates found in database!"
            else:
                for i, s in enumerate(templates, 1):
                    templates_list += f"<li><a class=\"dropdown-item\" href=\"#\" data-value=\"{s.name}\">{s.name}</a></li>\n\t\t"
            #Select one template which has Default=True setting in the database
            def_template = Provision_templates.query.filter_by(isdefault=True).first()
            if def_template:
                first_template = def_template.name
            else:
                first_template = "Unknown error selecting default template!"
                logging.error("Unknown error selecting default template!")
        except Exception as err:
            logging.error(f"CLI show templates function error: {err}")
            print(f"CLI show templates function error: {err}")
        return render_template("template-provision.html",templates=templates_list,first_template=first_template)
    #Do some updates with a new data
    if request.method == 'POST':
        
        return redirect("/",301)
        
