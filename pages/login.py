from flask import render_template,request,redirect,flash,Blueprint,session
from flask_login import current_user
import logging,asyncio
from flask_login import login_user, current_user
from db.database import User
from functions.send_to_telegram import send_to_telegram

login_bp = Blueprint("login", __name__)
@login_bp.route("/login", methods=['GET','POST'])
def login():
    #is this is POST request so we are trying to login
    if request.method == 'POST':
        if current_user.is_authenticated:
            logging.info(f"POST: User {current_user.username} is already logged in. Redirecting to the main page.")
            return redirect('/',301)
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            login_user(user)
            session.permanent = True
            logging.info(f"Login: User {username} logged in")
            return redirect("/",301)
        else:
            logging.error(f"Login: Wrong password \"{password}\" for user \"{username}\"")
            asyncio.run(send_to_telegram("🚷Provision:",f"Login error.Wrong password for user \"{username}\""))
            flash('Wrong username or password!', 'alert alert-danger')
            return render_template("template-login.html")    
    if current_user.is_authenticated:
        logging.info(f"not POST: User {current_user.username} is already logged in. Redirecting to the main page.")
        return redirect('/',301)
    else:
        return render_template("template-login.html")
