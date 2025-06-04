from flask import redirect,Blueprint,request
from flask_login import login_required
from functions.site_actions import disable_site, delete_site, enable_site, del_redirect, del_selected_redirects

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
    selected = request.form.get('selected')
    if selected:
        array = request.form.getlist("selected")
        del_selected_redirects(array,request.form['sitename'].strip())
        return redirect(f"/redirects_manager?site={request.form['sitename'].strip()}",301)
    del_redir = request.form.get('del_redir')
    if del_redir:
        del_redirect(request.form['del_redir'].strip(),request.form['sitename'].strip())
        return redirect(f"/redirects_manager?site={request.form['sitename'].strip()}",301)
    return redirect("/",301)