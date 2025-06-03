from flask import redirect,Blueprint,request
from flask_login import login_required
from functions.site_actions import disable_site, delete_site, enable_site

action_bp = Blueprint("action", __name__)
@action_bp.route("/action", methods=['POST'])
@login_required
def do_action():
    delete_form = request.form.get('delete')
    if delete_form:
        delete_site(request.form['delete'].strip())
    disable_form = request.form.get('disable')
    if disable_form:
        disable_site(request.form['disable'].strip())
    enable_form = request.form.get('enable')
    if enable_form:
        enable_site(request.form['enable'].strip())
    return redirect("/",301)