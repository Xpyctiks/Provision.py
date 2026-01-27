from flask import redirect,Blueprint,request
from flask_login import login_required
import os
from functions.site_actions import *

action_bp = Blueprint("action", __name__)
@action_bp.route("/action", methods=['POST'])
@login_required
def do_action():
  """POST request processor: process all requests to /action page."""
  try:
    #sites delete block
    if (request.form.get('delete') and not request.form.get('selected')):
      delete_site(request.form['delete'].strip())
      return redirect(f"/",301)
    elif (request.form.get('delete') and request.form.get('selected')):
      array = request.form.getlist("selected")
      del_selected_sites(request.form['delete'].strip(),array)
      return redirect(f"/",301)
    #sites actions
    elif (request.form.get('disable')):
      disable_site(request.form['disable'].strip())
    elif (request.form.get('enable')):
      enable_site(request.form['enable'].strip())
    #redirects management block
    elif (request.form.get('del_redir') and not request.form.get('selected')):
      del_redirect(request.form['del_redir'].strip(),request.form['sitename'].strip())
      return redirect(f"/redirects_manager?site={request.form['sitename'].strip()}",302)
    elif (request.form.get('del_redir') and request.form.get('selected')):
      array = request.form.getlist("selected")
      del_selected_redirects(array,request.form['sitename'].strip())
      return redirect(f"/redirects_manager?site={request.form['sitename'].strip()}",302)
    elif (request.form.get('applyChanges')):
      applyChanges(request.form['sitename'].strip())
      return redirect(f"/redirects_manager?site={request.form['sitename'].strip()}",302)
    #Git block
    elif (request.form.get('gitPull') and not request.form.get('selected')):
      makePull(request.form['gitPull'].strip())
    elif (request.form.get('gitPull') and request.form.get('selected')):
      pullArray = request.form.getlist("selected")
      makePull(request.form['gitPull'].strip(),pullArray)
    return redirect("/",302)
  except Exception as err:
    logging.error(f"do_action(): general error by {current_user.realname}: {err}")
    flash(f"Неочікувана помилка при POST запиту на сторінці /action! Дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

@action_bp.route("/action/showstructure/", methods=['GET'])
@login_required
def showstructure():
  """GET request: takes folder name as the parameter and shows what is inside of."""
  try:
    path = request.args.get("showstructure", "/tmp")
    try:
      dirs = sorted([x for x in os.listdir(os.path.join(path,"public")) if os.path.isdir(os.path.join(os.path.join(path,"public"), x))])
      files = sorted([x for x in os.listdir(os.path.join(path,"public")) if not os.path.isdir(os.path.join(os.path.join(path,"public"), x))])
      items = dirs + files
    except Exception as e:
      return f"<div class='text-danger'>Ошибка: {e}</div>"
    html = "<ul>"
    for item in items:
      full = os.path.join(os.path.join(path,"public"), item)
      if os.path.isdir(full):
        html += f"<li><b>📁</b> {item}</li>"
      else:
        html += f"<li>{item}</li>"
    html += "</ul>"
    return html
  except Exception as err:
    logging.error(f"showstructure(): general error by {current_user.realname}: {err}")
    flash(f"Неочікувана помилка при GET запиту на сторінці /action/showstructire/! Дивіться логи!", 'alert alert-danger')
    return redirect("/",302)
