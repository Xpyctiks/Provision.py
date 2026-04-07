import logging
import os
import re
from flask import render_template,Blueprint,current_app,flash,make_response
from flask_login import login_required,current_user
from functions.site_actions import count_redirects, is_admin
from functions.pages_forms import getSiteOwner,getSiteCreated
from db.database import Domain_account,User,Messages,Cloudflare
from functions.send_to_telegram import send_to_telegram
from db.db import db
from functions.cache_func import page_cache

#allows to sort with natural keys - when after 10 goes 11, not 20
def natural_key(s):
  return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

root_bp = Blueprint("root", __name__)
@root_bp.route("/", methods=['GET'])
@login_required
def index():
  """Main function: generates root page /."""
  CACHE_KEY = f"user:{current_user.realname}"
  try:
    cached = page_cache.get(CACHE_KEY)
    if cached:
        response = make_response(cached)
        response.headers["X-Cache"] = "HIT"
        response.set_cookie("x_cache", "HIT")
        return response
    web_folder = current_app.config.get("WEB_FOLDER","")
    if web_folder == "":
      logging.error(f"index(): root page generate function ERROR! - web_folder variable is empty!")
      return "index(): root page generate function ERROR!", 500
    sites_list = []
    html_data = []
    users_list = []
    cf_accounts_list = []
    sites_list = [
      name for name in os.listdir(web_folder)
      if os.path.isdir(os.path.join(web_folder, name)) and not name.startswith('.')
    ]
    #gathering all list of available users to put them into user filter list
    ul = User.query.order_by(User.username).all()
    for i, s in enumerate(ul, 1):
      users_list.append(f'<option value="{s.realname}">{s.realname}</option>')
    #gathering all list of available Cloudflare accounts to put them into accounts filter list
    ac = Cloudflare.query.order_by(Cloudflare.account).all()
    for ii, a in enumerate(ac, 1):
      cf_accounts_list.append(f'<option value="{a.account}">{a.account}</option>')
    #starting main procedure
    for i, s in enumerate(sorted(sites_list, key=natural_key), 1):
      #general check all Nginx sites-available, sites-enabled folder + php pool.d/ are available
      #variable with full path to nginx sites-enabled symlink to the site
      ngx_site = os.path.join(current_app.config["NGX_SITES_PATHEN"],s)
      #check robots.txt for existance and change its button color
      if os.path.exists(os.path.join(web_folder,s,"public","robots.txt")):
        robots_button = "btn-primary"
      else:
        robots_button = "btn-light"
      #check if the account has domain linked to its cloudflare account in DB
      acc = Domain_account.query.filter_by(domain=s).first()
      if not acc:
        dnsValidation_button = f'<a href="/dns_validation?domain={s}" class="btn btn-secondary disabled dropdown-item" type="submit" name="validation" value="{s}" style="margin-top: 5px;">📮DNS валідація</a><br>'
        cf_account = "⌛нема інформації"
      else:
        dnsValidation_button = f'<a href="/dns_validation?domain={s}" class="btn btn-secondary dropdown-item" data-bs-toggle="tooltip" data-bs-placement="top" type="submit" name="validation" value="{s}" onclick="showLoading()" style="margin-top: 5px;" title="Керування CNAME записами для валідації домену для пошукових систем.">📮DNS валідація</a>'
        cf_account = acc.account
      #If everything is ok, main view:
      if os.path.islink(ngx_site):
        html_data.append({
          "table_type": f'<tr data-owner="{getSiteOwner(s)}" data-account="{cf_account}">\n<th scope="row" class="table-success">{i}</th>',
          "button_2": f'<button class="btn btn-warning dropdown-item" type="submit" value="{s}" name="disable" data-bs-toggle="tooltip" data-bs-placement="top" form="main_form" onclick="showLoading()" title="Тимчасово вимкнути сайт - він не будет оброблятися при запитах зовні,але фізично залишається на сервері.">🚧Вимкнути</button>',
          "site_name": s,
          "table_type2": '<td class="table-success">',
          "count_redirects": count_redirects(s),
          "getSiteCreated": getSiteCreated(s),
          "id": i,
          "accordeon_path": os.path.join(web_folder,s),
          "getSiteOwner": getSiteOwner(s),
          "site_status": '✅Статус сайту OK',
          "robots_button": robots_button,
          "dns_validation": dnsValidation_button,
          "cf_account": cf_account
        })
      elif not os.path.islink(ngx_site):
        html_data.append({
          "table_type": f'<tr data-owner="{getSiteOwner(s)}" data-account="{cf_account}">\n<th scope="row" class="table-warning">{i}</th>',
          "button_2": f'<button class="btn btn-success dropdown-item" type="submit" value="{s}" name="enable" data-bs-toggle="tooltip" data-bs-placement="top" form="main_form" onclick="showLoading()" title="Активувати сайт - він буде оброблятися при запитах ззовні.">🏃Активувати</button>',
          "site_name": s,
          "table_type2": '<td class="table-warning">',
          "count_redirects": count_redirects(s),
          "getSiteCreated": getSiteCreated(s),
          "id": i,
          "accordeon_path": os.path.join(web_folder,s),
          "getSiteOwner": f"{getSiteOwner(s)}",
          "site_status": '🚧Сайт вимкнено',
          "robots_button": robots_button,
          "dns_validation": dnsValidation_button,
          "cf_account": cf_account
        })
    #getting into DB and checking is there any messages for the current user
    messages = Messages.query.filter_by(foruserid=current_user.id).all()
    if len(messages) != 0:
      logging.info(f"index(): Some messages found for user {current_user.realname} - {len(messages)} of them...")
      msg = ""
      for i, s in enumerate(messages, 1):
        msg += f"<strong>📫 Массове повідомлення №{i}</strong>\n"
        msg += s.text+"\n"
        del_msg = Messages.query.filter_by(id=s.id).first()
        if del_msg:
          db.session.delete(del_msg)
          logging.info(f"Message with ID={s.id} deleted from DB as the read one.")
      db.session.commit()
      flash(msg,'alert alert-info')
      logging.info(f"index(): Flash popup windows is ready for the user {current_user.realname}...")
    response = make_response(render_template("template-main.html",html_data=html_data,admin_panel=is_admin(),users_list=users_list,cf_accounts_list=cf_accounts_list))
    page_cache.set(CACHE_KEY, response.get_data(), timeout=300)
    response.headers["X-Cache"] = "MISS"
    response.set_cookie("x_cache", "MISS")
    return response
  except Exception as msg:
    logging.error(f"Error in index(/): {msg}")
    send_to_telegram(f"Root page render general error: {msg}",f"🚒Provision error by {current_user.realname}:")
    page_cache.delete(CACHE_KEY)
    return "index(): root page generate function ERROR!", 500
