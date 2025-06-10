from flask import redirect,flash,Blueprint,session,make_response
from flask_login import current_user
import logging
from flask_login import logout_user, login_required, current_user

logout_bp = Blueprint("logout", __name__)
@logout_bp.route("/logout", methods=['POST'])
@login_required
def logout():
    logging.info(f"User {current_user.realname} is logging out")
    logout_user()
    session.clear()
    response = make_response(redirect("/login",301))
    response.delete_cookie('session')
    response.delete_cookie('remember_token')
    flash("You are logged out", "alert alert-info")
    return response
