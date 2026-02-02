from flask import render_template,redirect,Blueprint,current_app,flash,jsonify
from flask_login import login_required
import logging,os
from functions.site_actions import is_admin

logs_bp = Blueprint("logs", __name__)
@logs_bp.route("/logs/", methods=['GET'])
@login_required
def showLogs():
  """Simple functions that shows up a current content of programm log file."""
  try:
    return render_template("template-logs.html",admin_panel=is_admin())
  except Exception as err:
    logging.error(f"Logs page showLogs() gereral error: {err}")
    flash(f"Загальна помилка сторінки логу!",'alert alert-danger')
    return redirect("/",302)

@logs_bp.route("/logs/api/")
def logs_api():
  log_file = current_app.config.get("LOG_FILE")
  if not os.path.exists(log_file):
    return jsonify({"error": "Log not found"}), 404
  with open(log_file, "r", encoding="utf-8", errors="replace") as f:
    data = f.readlines()
  return jsonify({
    "lines": data,
    "count": len(data)
  })
