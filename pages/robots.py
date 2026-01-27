from flask import request,redirect,flash,Blueprint,current_app,jsonify
from flask_login import current_user, login_required
import logging,asyncio,os
from functions.send_to_telegram import send_to_telegram
from functions.site_actions import normalize_domain

robots_bp = Blueprint("/robots", __name__)
@robots_bp.route("/robots/", methods=['POST'])
@login_required
def editRobots():
  try:
    data = request.json
    domain = normalize_domain(data["domain"])
    content = data["content"]
    robots_file = os.path.join(current_app.config['WEB_FOLDER'],domain,"public","robots.txt")
    if robots_file in ('/', '/home', '/root', '/etc', '/var', '/tmp', os.path.expanduser("~")):
      logging.error(f"editRobots() error by {current_user.realname}: unsafe path found in robots.txt path - {robots_file}")
      asyncio.run(send_to_telegram(f"editRobots() error by {current_user.realname}: unsafe path found in robots.txt path!",f"🚒Provision robots edior:"))
      return jsonify({"error": "Unsafe path!"})
    with open(robots_file, "w") as f:
      f.write(content)
    return jsonify({"status": "ok"})
  except Exception as msg:
    logging.error(f"editRobots() general error by {current_user.realname}: {msg}")
    flash(f'Помилка при POST запиті на сторінці /robots! Дивіться логи!','alert alert-danger')
    return redirect("/",302)

@robots_bp.route("/robots/", methods=['GET'])
@login_required
def showRobots():
  try:
    if request.args.get('domain'):
      domain = normalize_domain(request.args.get("domain"))
      robots_file = os.path.join(current_app.config.get('WEB_FOLDER'),domain,"public","robots.txt")
      if os.path.exists(robots_file):
        with open(robots_file) as f:
          return jsonify({"content": f.read()})
      else:
        logging.info(f"Get robots.txt content by {current_user.realname}: file {robots_file} is not exists.")
        return jsonify({"content": "#empty file. Replace with new text content"})
    else:
      logging.error(f"showRobots() error by {current_user.realname}: domain variable is not recevied.")
      asyncio.run(send_to_telegram("showRobots() error by {current_user.realname}: domain variable is not recevied.",f"🚒Provision robots edior:"))
      flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
      return redirect("/",301)
  except Exception as msg:
    logging.error(f"showRobots() general error by {current_user.realname}: {msg}")
    flash(f'Помилка при POST запиті на сторінці /robots! Дивіться логи!','alert alert-danger')
    asyncio.run(send_to_telegram(f"showRobots() general error by {current_user.realname}: {msg}",f"🚒Provision robots edior:"))
    return jsonify({"error": str(msg)}), 500
