from flask import render_template,redirect,Blueprint,current_app,flash
from flask_login import login_required,current_user
from functions.send_to_telegram import send_to_telegram
import logging,os,asyncio

logs_bp = Blueprint("logs", __name__)
@logs_bp.route("/logs", methods=['GET'])
@login_required
def showLogs():
    """Simple functions that shows up a current content of programm log file."""
    try:
        if os.path.exists(current_app.config['LOG_FILE']):
            with open(current_app.config['LOG_FILE'], "r", encoding="utf-8") as f:
                log = f.read()
            return render_template("template-logs.html",log=log)
        else:
            flash(f"Помилка відкриття файла логу {current_app.config['LOG_FILE']}",'alert alert-danger')
            asyncio.run(send_to_telegram(f"Error opening log file {current_app.config['LOG_FILE']}!",f"🚒Provision log page by {current_user.realname}:"))
            return redirect("/",302)
    except Exception as err:
        asyncio.run(send_to_telegram(f"Error opening log file {current_app.config['LOG_FILE']}!",f"🚒Provision log page by {current_user.realname}:"))
        logging.error(f"Logs page showLogs() gereral error: {err}")
        flash(f"Загальна помилка при спробі відкриття файла логу {current_app.config['LOG_FILE']}",'alert alert-danger')
        return redirect("/",302)
