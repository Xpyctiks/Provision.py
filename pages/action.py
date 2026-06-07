import os
import json
from html import escape
from flask import redirect,Blueprint,request
from flask_login import login_required,current_user
from functions.site_actions import *

action_bp = Blueprint("action", __name__)
@action_bp.route("/action/", methods=["POST"])
@login_required
def do_action():
  """POST request processor: process all requests to /action page."""
  try:
    #sites delete block
    if (request.form.get("delete") and not request.form.get("selected")):
      delete_site(request.form.get("delete","").strip())
      clearCache()
      return redirect(f"/",302)
    elif (request.form.get("delete") and request.form.get("selected")):
      array = request.form.getlist("selected")
      del_selected_sites(request.form.get("delete","").strip(),array)
      clearCache()
      return redirect(f"/",302)
    #sites actions
    elif (request.form.get("disable")):
      disable_site(request.form["disable"].strip())
      clearCache()
    elif (request.form.get("enable")):
      enable_site(request.form.get("enable","").strip())
      clearCache()
    #redirects management block
    elif (request.form.get("del_redir") and not request.form.get("selected")):
      del_redirect(request.form.get("del_redir","").strip(),request.form.get("sitename","").strip())
      return redirect(f"/redirects_manager?site={request.form.get('sitename','').strip()}",302)
    elif (request.form.get("del_redir") and request.form.get("selected")):
      array = request.form.getlist("selected")
      del_selected_redirects(array,request.form.get("sitename","").strip())
      return redirect(f"/redirects_manager?site={request.form.get('sitename','').strip()}",302)
    elif (request.form.get("applyChanges")):
      applyChanges(request.form.get("sitename","").strip())
      return redirect(f"/redirects_manager?site={request.form.get('sitename','').strip()}",302)
    #Git block
    elif (request.form.get("gitPull") and not request.form.get("selected")):
      makePull(request.form["gitPull"].strip())
    elif (request.form.get("gitPull") and request.form.get("selected")):
      pullArray = request.form.getlist("selected")
      makePull(request.form.get("gitPull","").strip(),pullArray)
    return redirect("/",302)
  except Exception as err:
    logging.error(f"do_action(): general error by {current_user.realname}: {err}")
    flash(f"Неочікувана помилка при POST запиту на сторінці /action! Дивіться логи!", "alert alert-danger")
    return redirect("/",302)

@action_bp.route("/action/show/hrefhistory", methods=["GET"])
@login_required
def showHrefHistory():
  """GET request: takes a domain as the parameter, reads its clones-history.json from the site's root folder and returns HTML for the accordion with the history of Href changes."""
  try:
    domain = str(normalize_domain(request.args.get("domain","")))
    history_path = os.path.join(current_app.config.get("WEB_FOLDER",""),domain,"clones-history.json")
    if not os.path.exists(history_path):
      return '<div class="text-muted">Файл clones-history.json для цього сайту не знайдено.</div>'
    with open(history_path,"r",encoding="utf-8") as f:
      history = json.load(f)
    if not history:
      return '<div class="text-muted">Файл clones-history.json порожній.</div>'
    badges = {"current": "bg-success", "deleted": "bg-danger"}
    html = ""
    for entry in history:
      html += '<div class="border rounded p-2 mb-2">'
      for key,value in entry.items():
        if key == "status":
          html += f'<div><b>{escape(key)}:</b> <span class="badge rounded-pill {badges.get(value,"bg-secondary")}">{escape(str(value))}</span></div>'
        elif key == "href":
          html += f'<div><b>{escape(key)}:</b> <a href="{escape(value)}" target="_blank">{escape(value)}</a></div>'
        else:
          html += f'<div><b>{escape(key)}:</b> {escape(str(value))}</div>'
      html += '</div>'
    return html
  except Exception as err:
    logging.error(f"showHrefHistory(): general error by {current_user.realname}: {err}")
    return f'<div class="text-danger">Помилка при завантаженні історії Href: {escape(str(err))}</div>'

@action_bp.route("/action/clear_cache/", methods=["GET"])
@login_required
def clrCache():
  """GET request: clears web page cache"""
  try:
    if clearCache():
      logging.info(f"clrCache(): web cache is manually cleared by {current_user.realname}")
    else:
      flash(f"Помилка при спробі очистки кешу! Дивіться логи!", "alert alert-danger")
    return redirect("/",302)
  except Exception as err:
    logging.error(f"clrCache(): general error by {current_user.realname}: {err}")
    flash(f"Неочікувана помилка при спробі очистки кешу! Дивіться логи!", "alert alert-danger")
    return redirect("/",302)