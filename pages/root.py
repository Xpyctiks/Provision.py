import logging,os,re,asyncio
from flask import render_template,Blueprint,current_app
from flask_login import login_required,current_user
from functions.site_actions import count_redirects
from functions.pages_forms import getSiteOwner,getSiteCreated
from db.database import Domain_account,User
from functions.send_to_telegram import send_to_telegram

#allows to sort with natural keys - when after 10 goes 11, not 20
def natural_key(s):
  return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

root_bp = Blueprint("root", __name__)
@root_bp.route("/", methods=['GET'])
@login_required
def index():
  """Main function: generates root page /."""
  try:
    sites_list = []
    sites_list = [
      name for name in os.listdir(current_app.config["WEB_FOLDER"])
      if os.path.isdir(os.path.join(current_app.config["WEB_FOLDER"], name))
    ]
    html_data = []
    #check if user has admin rights and draw the admin panel link
    user = User.query.filter_by(realname=current_user.realname).first()
    if user:
      rights = user.rights
      if rights == 255:
        rights_menu = '<li><a class="dropdown-item" href="/admin_panel" class="btn btn-secondary">🎮Панель адміністрування</a></li>'
      else:
        rights_menu = ""
    else:
      rights_menu = ""
    for i, s in enumerate(sorted(sites_list, key=natural_key), 1):
      #general check all Nginx sites-available, sites-enabled folder + php pool.d/ are available
      #variable with full path to nginx sites-enabled symlink to the site
      ngx_site = os.path.join(current_app.config["NGX_SITES_PATHEN"],s)
      #variable with full path to php pool config of the site
      php_site = os.path.join(current_app.config["PHP_POOL"],s+".conf")
      #check robots.txt for existance and change its button color
      if os.path.exists(os.path.join(current_app.config['WEB_FOLDER'],s,"public","robots.txt")):
        robots_button = "btn-primary"
      else:
        robots_button = "btn-light"
      #check if the account has domain linked to its cloudflare account in DB
      acc = Domain_account.query.filter_by(domain=s).first()
      if not acc:
        dnsValidation_button = f'<a href="/dns_validation?domain={s}" class="btn btn-secondary disabled" type="submit" name="validation" value="{s}" style="margin-top: 5px;">📮DNS валідація</a><br>'
      else:
        dnsValidation_button = f'<a href="/dns_validation?domain={s}" class="btn btn-secondary" data-bs-toggle="tooltip" data-bs-placement="top" type="submit" name="validation" value="{s}" onclick="showLoading()" style="margin-top: 5px;" title="Керування CNAME записами для валідації домену для пошукових систем.">📮DNS валідація</a><br>'
      #If everything is ok, main view:
      if os.path.islink(ngx_site) and os.path.isfile(php_site):
        html_data.append({
          "table_type": f'<tr>\n<th scope="row" class="table-success">{i}</th>',
          "button_2": f'<button class="btn btn-warning" type="submit" value="{s}" name="disable" data-bs-toggle="tooltip" data-bs-placement="top" form="main_form" onclick="showLoading()" title="Тимчасово вимкнути сайт - він не будет оброблятися при запитах зовні,але фізично залишається на сервері.">🚧Вимкнути</button>',
          "site_name": s,
          "table_type2": '<td class="table-success">',
          "count_redirects": count_redirects(s),
          "getSiteCreated": getSiteCreated(s),
          "id": i,
          "accordeon_path": os.path.join(current_app.config["WEB_FOLDER"],s),
          "getSiteOwner": getSiteOwner(s),
          "site_status": '✅OK',
          "robots_button": robots_button,
          "dns_validation": dnsValidation_button          
        })
      #if nginx is ok but php is not
      elif os.path.islink(ngx_site) and not os.path.isfile(php_site):
        html_data.append({
          "table_type": f'<tr>\n<th scope="row" class="table-danger">{i}</th>',
          "button_2": f'<button class="btn btn-success" type="submit" value="{s}" name="enable" data-bs-toggle="tooltip" data-bs-placement="top" form="main_form" onclick="showLoading()" title="Активувати сайт - він буде оброблятися при запитах ззовні.">🏃Активувати</button>',
          "site_name": s,
          "table_type2": '<td class="table-danger">',
          "count_redirects": count_redirects(s),
          "getSiteCreated": getSiteCreated(s),
          "id": i,
          "accordeon_path": os.path.join(current_app.config["WEB_FOLDER"],s),
          "getSiteOwner": getSiteOwner(s),
          "site_status": '🚨Помилка конфігураціх РНР',
          "robots_button": robots_button,
          "dns_validation": dnsValidation_button
        })
      #if php is ok but nginx is not
      elif not os.path.islink(ngx_site) and os.path.isfile(php_site):
        html_data.append({
          "table_type": f'<tr>\n<th scope="row" class="table-danger">{i}</th>',
          "button_2": f'<button class="btn btn-success" type="submit" value="{s}" name="enable" data-bs-toggle="tooltip" data-bs-placement="top" form="main_form" onclick="showLoading()" title="Активувати сайт - він буде оброблятися при запитах ззовні.">🏃Активувати</button>',
          "site_name": s,
          "table_type2": '<td class="table-danger">',
          "count_redirects": count_redirects(s),
          "getSiteCreated": getSiteCreated(s),
          "id": i,
          "accordeon_path": os.path.join(current_app.config["WEB_FOLDER"],s),
          "getSiteOwner": getSiteOwner(s),
          "site_status": '🚨Помилка конфігураціх Nginx',
          "robots_button": robots_button,
          "dns_validation": dnsValidation_button
        })
      #if really disabled
      elif not os.path.islink(ngx_site) and not os.path.isfile(php_site):
        html_data.append({
          "table_type": f'<tr>\n<th scope="row" class="table-warning">{i}</th>',
          "button_2": f'<button class="btn btn-success" type="submit" value="{s}" name="enable" data-bs-toggle="tooltip" data-bs-placement="top" form="main_form" onclick="showLoading()" title="Активувати сайт - він буде оброблятися при запитах ззовні.">🏃Активувати</button>',
          "site_name": s,
          "table_type2": '<td class="table-warning">',
          "count_redirects": count_redirects(s),
          "getSiteCreated": getSiteCreated(s),
          "id": i,
          "accordeon_path": os.path.join(current_app.config["WEB_FOLDER"],s),
          "getSiteOwner": getSiteOwner(s),
          "site_status": '🚧Сайт вимкнено',
          "robots_button": robots_button,
          "dns_validation": dnsValidation_button
        })
      else:
        html_data.append({
          "table_type": f'<tr>\n<th scope="row" class="table-danger">{i}</th>',
          "button_2": '',
          "site_name": 'ЗАГАЛЬНА',
          "table_type2": '<td class="table-danger">',
          "count_redirects": '',
          "getSiteCreated": '',
          "id": i,
          "accordeon_path": 'ПОМИЛКА',
          "getSiteOwner": 'СИСТЕМИ',
          "site_status": 'Важливі файли або папки не існують',
          "robots_button": '',
          "dns_validation": ''
        })
    return render_template("template-main.html",html_data=html_data,admin_panel=rights_menu)
  except Exception as msg:
    logging.error(f"Error in index(/): {msg}")
    asyncio.run(send_to_telegram(f"Root page render general error: {msg}",f"🚒Provision error by {current_user.realname}:"))
    return "root.py ERROR!"
