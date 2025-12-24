from flask import render_template,request,redirect,flash,Blueprint,current_app,jsonify
from flask_login import current_user, login_required
import logging,asyncio,os,pathlib
from functions.send_to_telegram import send_to_telegram

robots_bp = Blueprint("/robots", __name__)
@robots_bp.route("/robots", methods=['POST'])
@login_required
def editRobots():
    data = request.json
    domain = data["domain"]
    content = data["content"]
    robots_file = os.path.join(current_app.config['WEB_FOLDER'],domain,"public","robots.txt")
    if robots_file in ('/', '/home', '/root', '/etc', '/var', '/tmp', os.path.expanduser("~")):
        logging.error(f"editRobots() error: unsafe path found in robots.txt path - {robots_file}")
        asyncio.run(send_to_telegram(f"editRobots() error: unsafe path found in robots.txt path!",f"🚒Provision robots edior:"))
        return jsonify({"error": "Unsafe path!"})
    try:
        with open(robots_file, "w") as f:
            f.write(content)
        return jsonify({"status": "ok"})
    except Exception as msg:
        logging.error(f"editRobots() general error: {msg}")
        asyncio.run(send_to_telegram(f"editRobots() general error: {msg}",f"🚒Provision robots edior:"))
        flash(f'Помилка! {msg}','alert alert-danger')
        return redirect("/",301)

@robots_bp.route("/robots", methods=['GET'])
@login_required
def showRobots():
    if request.args.get('domain'):
        domain = request.args.get("domain").lower().strip()
        robots_file = os.path.join(current_app.config['WEB_FOLDER'],domain,"public","robots.txt")
        try:
            if os.path.exists(robots_file):
                with open(robots_file) as f:
                    return jsonify({"content": f.read()})
            else:
                logging.info(f"Get robots.txt content: file {robots_file} is not exists.")
                return jsonify({"content": "#empty file. Replace with new text content"})
        except Exception as msg:
            logging.error(f"showRobots() general error: {msg}")
            asyncio.run(send_to_telegram(f"showRobots() general error: {msg}",f"🚒Provision robots edior:"))
            return jsonify({"error": str(msg)}), 500
    else:
        logging.error(f"showRobots() error: domain variable is not recevied.")
        asyncio.run(send_to_telegram("showRobots() error: domain variable is not recevied.",f"🚒Provision robots edior:"))
        flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
        return redirect("/",301)
