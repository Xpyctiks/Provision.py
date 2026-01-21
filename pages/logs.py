from flask import render_template,redirect,Blueprint,current_app,flash,jsonify, request
from flask_login import login_required,current_user
from functions.send_to_telegram import send_to_telegram
import logging,os,asyncio

logs_bp = Blueprint("logs", __name__)
@logs_bp.route("/logs", methods=['GET'])
@login_required
def showLogs():
  """Simple functions that shows up a current content of programm log file."""
  try:
    return render_template("template-logs.html")
  except Exception as err:
    asyncio.run(send_to_telegram(f"Global show log page error! {err}!",f"🚒Provision log page by {current_user.realname}:"))
    logging.error(f"Logs page showLogs() gereral error: {err}")
    flash(f"Загальна помилка сторінки логу!",'alert alert-danger')
    return redirect("/",302)

@logs_bp.route("/logs/api")
def logs_api():
  lines = int(request.args.get("lines", 200))
  log_file = current_app.config["LOG_FILE"]

  if not os.path.exists(log_file):
    return jsonify({"error": "Log not found"}), 404

  with open(log_file, "r", encoding="utf-8", errors="replace") as f:
    data = f.readlines()[-lines:]

  return jsonify({
    "lines": data,
    "count": len(data)
  })
