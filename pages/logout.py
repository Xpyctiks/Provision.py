from flask import redirect,flash,Blueprint,session
from flask_login import current_user
import logging
from flask_login import logout_user, login_required, current_user

logout_bp = Blueprint("logout", __name__)
@logout_bp.route("/logout", methods=['POST'])
@login_required
def logout():
    session.clear()
    logging.info(f"User {current_user.realname} is logging out")
    logout_user()
    flash("You are logged out", "alert alert-info")
    return redirect("/login",301)