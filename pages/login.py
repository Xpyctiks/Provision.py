from flask import render_template,request,redirect,flash,Blueprint,session
import logging,asyncio
from flask_login import login_user,current_user
from db.database import User
from functions.send_to_telegram import send_to_telegram
from datetime import timedelta

login_bp = Blueprint("login", __name__)
@login_bp.route("/login", methods=['POST'])
def do_login():
    """POST request processor: logging in the user."""
    try:
        ip = request.remote_addr
        real_ip = request.headers.get('X-Real-IP', '-.-.-.-')
        if current_user.is_authenticated:
            logging.info(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>POST request: User {current_user.username} IP:{request.remote_addr} is already logged in. Redirecting to the main page.")
            return redirect('/',301)
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and user.check_password(password):
            session.clear()
            session.permanent = True
            session.permanent_session_lifetime = timedelta(hours=8)
            login_user(user, remember=True, duration=timedelta(hours=8))
            logging.info(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>User {user.realname} logged in successfully. IP:{ip}, Real-IP:{real_ip}")
            return redirect("/",302)
        else:
            logging.error(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>Login: Wrong password \"{password}\" for user \"{username}\", IP:{ip}, Real-IP:{real_ip}")
            asyncio.run(send_to_telegram("🚷Provision:",f"Login error! Wrong password for user \"{username}\", IP:{request.remote_addr}, Real-IP:{real_ip}"))
            flash('Невірний юзер або пароль!', 'alert alert-danger')
            return redirect("/login",302)
    except Exception as err:
        logging.error(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>do_login(): general error: {err}")
        asyncio.run(send_to_telegram(f"do_login(): general error: {err}",f"🚒Provision login error:"))
        flash(f"Неочікувана помилка при POST запиту на сторінці /login! Дивіться логи!", 'alert alert-danger')
        return redirect("/login",302)

@login_bp.route("/login", methods=['GET'])
def show_login_page():
    """GET request: shows /login page"""
    try:
        ip = request.remote_addr
        real_ip = request.headers.get('X-Real-IP', '-.-.-.-')
        if current_user.is_authenticated:
            logging.info(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>GET request: User {current_user.username} IP:{ip}, Real-IP:{real_ip} is already logged in. Redirecting to the main page.")
            return redirect('/',302)
        else:
            return render_template("template-login.html")
    except Exception as err:
        logging.error(f">>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>show_login_page(): general error: {err}")
        asyncio.run(send_to_telegram(f"show_login_page(): general error: {err}",f"🚒Provision error by {current_user.realname}:"))
        flash(f"Неочікувана помилка при GET запиту на сторінці /login! Дивіться логи!", 'alert alert-danger')
        return "<html><body>GENERAL ERROR! Can't even render this page!</body></hml>"
