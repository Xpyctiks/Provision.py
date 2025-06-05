from flask import redirect,Blueprint,request
from flask_login import login_required
from functions.site_actions import disable_site, delete_site, enable_site, del_redirect, del_selected_redirects, applyChanges

action_bp = Blueprint("action", __name__)
@action_bp.route("/action", methods=['POST'])
@login_required
def do_action():
    if (request.form.get('delete')):
        delete_site(request.form['delete'].strip())
    elif (request.form.get('disable')):
        disable_site(request.form['disable'].strip())
    elif (request.form.get('enable')):
        enable_site(request.form['enable'].strip())
    elif (request.form.get('selected')):
        array = request.form.getlist("selected")
        del_selected_redirects(array,request.form['sitename'].strip())
        return redirect(f"/redirects_manager?site={request.form['sitename'].strip()}",301)
    elif (request.form.get('del_redir')):
        del_redirect(request.form['del_redir'].strip(),request.form['sitename'].strip())
        return redirect(f"/redirects_manager?site={request.form['sitename'].strip()}",301)
    elif (request.form.get('applyChanges')):
        applyChanges(request.form['sitename'].strip())
        return redirect(f"/redirects_manager?site={request.form['sitename'].strip()}",301)
    return redirect("/",301)
