from flask import render_template,request,redirect,flash,Blueprint,current_app
from flask_login import login_required
import logging,os

logs_bp = Blueprint("logs", __name__)
@logs_bp.route("/logs", methods=['GET'])
@login_required
def showLogs():
    try:
        if os.path.exists(current_app.config['LOG_FILE']):
            with open(current_app.config['LOG_FILE'], "r", encoding="utf-8") as f:
                log = f.read()
            return render_template("template-logs.html",log=log)
        else:
            return redirect("/",301)
    except Exception as err:
        print(err)
        logging.error(f"Provision page provision() render error: {err}")
        return ""
