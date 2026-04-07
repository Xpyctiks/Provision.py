import logging
from flask import redirect,Blueprint,request,render_template,flash
from flask_login import login_required, current_user
from db.database import *
from functions.send_to_telegram import send_to_telegram
from functions.admin_panel_func import *
from functions.rights_required import rights_required
from functions.site_actions import is_admin
from datetime import datetime

admin_panel_bp = Blueprint("admin_panel", __name__)

@admin_panel_bp.route("/admin_panel/", methods=['POST'])
@login_required
@rights_required(255)
def catch_admin_panel():
  try:
    """POST request processor: process all requests to /admin_panel page and takes one of the choosen action."""
    if "buttonSaveSettings" in request.form:
      handler_settings(request.form)
      return redirect("/admin_panel/settings/",302)
    elif "buttonAddUser" in request.form or "buttonDeleteUser" in request.form or "buttonMakeAdminUser" in request.form or "buttonRemoveAdminUser" in request.form:
      handler_users(request.form)
      return redirect("/admin_panel/users/",302)
    elif "buttonDeleteTemplate" in request.form or "buttonDefaultTemplate" in request.form or "buttonAddTemplate" in request.form:
      handler_templates(request.form)
      return redirect("/admin_panel/templates/",302)
    elif "buttonDeleteCloudflare" in request.form or "buttonDefaultCloudflare" in request.form or "buttonAddCloudflare" in request.form:
      handler_cloudflare(request.form)
      return redirect("/admin_panel/cloudflare/",302)
    elif "buttonDeleteOwnership" in request.form or "buttonDeleteOwnershipClone" in request.form or "buttonAddOwnership" in request.form:
      handler_ownership(request.form)
      return redirect("/admin_panel/owners/",302)
    elif "buttonDeleteServer" in request.form or "buttonDefaultServer" in request.form or "buttonAddServer" in request.form:
      handler_servers(request.form)
      return redirect("/admin_panel/servers/",302)
    elif "buttonDeleteLink" in request.form or "buttonAddLink" in request.form:
      handler_links(request.form)
      return redirect("/admin_panel/links/",302)
    elif "buttonDeleteAccount" in request.form or "buttonAddAccount" in request.form:
      handler_accounts(request.form)
      return redirect("/admin_panel/accounts/",302)
    elif "buttonPublishMessage" in request.form or "buttonClearMessages" in request.form:
      handler_messages(request.form)
      return redirect("/admin_panel/messages/",302)
    else:
      flash('Помилка! Ні один з можливих параметрів не був передан сторінці /admin_panel в POST запиту!','alert alert-danger')
      logging.error("Something strange was received by /admin_panel via POST request and we can't process that.")
      send_to_telegram("Something strange was received by /admin_panel via POST request and we can't process that.",f"🚒Provision error by {current_user.realname}")
      redirect("/",302)
  except Exception as err:
    logging.error(f"catch_admin_panel(): global error {err}")
    flash('Загальна помилка адмін панелі! Дивіться логи.', 'alert alert-danger')
    return redirect("/",302)

@admin_panel_bp.route("/admin_panel/", methods=['GET'])
@login_required
@rights_required(255)
def admin_panel():
  return redirect("/admin_panel/settings/",302)

@admin_panel_bp.route("/admin_panel/settings/", methods=['GET'])
@login_required
@rights_required(255)
def admin_panel_settings():
  try:
    html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <form action="/admin_panel/" method="POST" id="postform" novalidate>"""
    settings = Settings.query.all()
    i = 0
    for setting in settings:
      for column in setting.__table__.columns:
        if column.name == "id":
          continue
        html_data += f"""
<div class="input-group mb-2">
  <span class="input-group-text settings-label">{column.name}:</span>
  <input type="text" class="form-control" id="settings-{i}" value="{getattr(setting, column.name)}">
  <input type="hidden" id="value-{i}" name="{column.name}" value="">
</div>"""
        i = i + 1
    html_data += """
  <div class="d-grid mt-2 col-12 col-md-4 mx-auto">
    <button type="submit" class="btn form-control SaveSettings-btn w-100" style="background-color: palegreen;" name="buttonSaveSettings" onclick="syncSettings()">Зберегти налаштування</button>
  </div>
 </form>
</div>"""
    return render_template("template-admin_panel.html",active1="active",data=html_data,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"admin_panel_settings(): global error {err}")
    flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
    return redirect("/",302)

@admin_panel_bp.route("/admin_panel/users/", methods=['GET'])
@login_required
@rights_required(255)
def admin_panel_users():
  try:
    html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered">
  <thead>
  <tr class="table-warning">
    <th scope="col" style="width: 45px;">ID:</th>
    <th scope="col" style="width: 150px;">Логін:</th>
    <th scope="col" style="width: 150px;">Ім'я:</th>
    <th scope="col" style="width: 150px;">Адмін права(якщо 255):</th>
    <th scope="col" style="width: 150px;">Створен:</th>
  </tr>
  </thead>
  <tbody>"""
    users = User.query.order_by(User.username).all()
    if len(users) == 0:
      print("No users found in DB!")
      quit()
    for i, s in enumerate(users, 1):
      if s.rights == 1:
        button = f'<button type="submit" class="btn btn-outline-warning AdminUser-btn" name="buttonMakeAdminUser" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Зробити даного користувача адміністратором.">👑</button>'
      else:
        button = f'<button type="submit" class="btn btn-outline-warning AdminUser-btn" name="buttonRemoveAdminUser" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Забрати у даного користувача адмін права.">🚶</button>'
      html_data += f"""
  <tr class="table-success">
    <form action="/admin_panel/" method="POST" id="postform" novalidate>
    <td class="table-success cname-cell" >{s.id}
    <button type="submit" class="btn btn-outline-warning DeleteUser-btn" name="buttonDeleteUser" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити даного користувача із бази.">❌</button>
    </td></form>
    <td class="table-success cname-cell" >{s.username}</td>
    <td class="table-success cname-cell" >{s.realname}</td>
    <form action="/admin_panel/" method="POST" id="postform" novalidate>
    <td class="table-success cname-cell" >{s.rights}
    {button}
    </td></form>
    <td class="table-success cname-cell" >{datetime.strftime(s.created,"%d.%m.%Y %H:%M:%S")}</td>
  </tr>"""
    html_data += """
  </tbody>
  </table>
  <form action="/admin_panel/" method="POST" id="postform2" class="needs-validation" novalidate>
  <div class="input-group mb-2">
  <span class="input-group-text">Логін:</span>
  <input type="text" class="form-control" id="new-username" name="new-username" value="">
  <span class="input-group-text">Пароль:</span>
  <input type="text" class="form-control" id="new-password" name="new-password" value="">
  <span class="input-group-text">І'мя</span>
  <input type="text" class="form-control" id="new-realname" name="new-realname" value="">
  <span class="input-group-text">Адмін права&nbsp;<input class="form-check-input" type="checkbox" value="" name="new-is-admin"></span>
  <button type="submit" class="btn form-control" style="background-color: palegreen;" name="buttonAddUser" onclick="showLoading()">Створити користувача</button>
   </div>
  </form>
 </div>
</div>"""
    return render_template("template-admin_panel.html",active2="active",data=html_data,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"admin_panel_users(): global error {err}")
    flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
    return redirect("/",302)

@admin_panel_bp.route("/admin_panel/templates/", methods=['GET'])
@login_required
@rights_required(255)
def admin_panel_templates():
  try:
    html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered">
  <thead>
  <tr class="table-warning">
    <th scope="col" style="width: 45px;">ID:</th>
    <th scope="col" style="width: 150px;">Назва:</th>
    <th scope="col" style="width: 150px;">Шлях:</th>
    <th scope="col" style="width: 150px;">За замовчуванням?:</th>
    <th scope="col" style="width: 150px;">Створен:</th>
  </tr>
  </thead>
  <tbody>"""
    templates = Provision_templates.query.order_by(Provision_templates.id).all()
    for i, s in enumerate(templates, 1):
      html_data += f"""
  <tr class="table-success">
    <form action="/admin_panel/" method="POST" id="postform" novalidate>
    <td class="table-success cname-cell" >{s.id}
    <button type="submit" class="btn btn-outline-warning DeleteTemplate-btn" name="buttonDeleteTemplate" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити даний шаблон із бази.">❌</button>    
    </td></form>
    <td class="table-success cname-cell" >{s.name}</td>
    <td class="table-success cname-cell" >{s.repository}</td>
    <form action="/admin_panel/" method="POST" id="postform" novalidate>
    <td class="table-success cname-cell" >{s.isdefault}
    <button type="submit" class="btn btn-outline-warning DefaultTemplate-btn" name="buttonDefaultTemplate" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Зробити даний шаблон за замовчанням">✅</button>    
    </td></form>
    <td class="table-success cname-cell" >{datetime.strftime(s.created,"%d.%m.%Y %H:%M:%S")}</td>
  </tr>"""
    html_data += """
  </tbody>
  </table>
  <form action="/admin_panel/" method="POST" id="postform3" class="needs-validation" novalidate>
  <div class="input-group mb-2">
  <span class="input-group-text">Назва:</span>
  <input type="text" class="form-control" id="field1" name="new-template-name" value="">
  <span class="input-group-text">Шлях:</span>
  <input type="text" class="form-control" id="field2" name="new-template-path" value="">
  <button type="submit" class="btn form-control" style="background-color: palegreen;" name="buttonAddTemplate" onclick="showLoading()">Додати новий шаблон</button>
   </div>
  </form>
 </div>
</div>"""
    return render_template("template-admin_panel.html",active3="active",data=html_data,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"admin_panel_templates(): global error {err}")
    flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
    return redirect("/",302)

@admin_panel_bp.route("/admin_panel/cloudflare/", methods=['GET'])
@login_required
@rights_required(255)
def admin_panel_cloudflare():
  try:
    html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered">
  <thead>
  <tr class="table-warning">
    <th scope="col" style="width: 45px;">ID:</th>
    <th scope="col" style="width: 150px;">Аккаунт:</th>
    <th scope="col" style="width: 350px;">Токен:</th>
    <th scope="col" style="width: 150px;">За замовчуванням?:</th>
    <th scope="col" style="width: 150px;">Створен:</th>
  </tr>
  </thead>
  <tbody>"""
    cloudflares = Cloudflare.query.order_by(Cloudflare.id).all()
    for i, s in enumerate(cloudflares, 1):
      html_data += f"""
  <tr class="table-success">
    <form action="/admin_panel/" method="POST" id="postform" novalidate>
    <td class="table-success cname-cell" >{s.id}
    <button type="submit" class="btn btn-outline-warning" name="buttonDeleteCloudflare" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити даний аккаунт із бази.">❌</button>    
    </td></form>
    <td class="table-success cname-cell" >{s.account}</td>
    <td class="table-success cname-cell" ><details><summary>Натисніть що б подивитись</summary>{s.token}</details></td>
    <form action="/admin_panel/" method="POST" id="postform" novalidate>
    <td class="table-success cname-cell" >{s.isdefault}
    <button type="submit" class="btn btn-outline-warning" name="buttonDefaultCloudflare" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Зробити даний аккаунт за замовчанням">✅</button>    
    </td></form>
    <td class="table-success cname-cell" >{datetime.strftime(s.created,"%d.%m.%Y %H:%M:%S")}</td>
  </tr>"""
    html_data += """
  </tbody>
  </table>
  <form action="/admin_panel/" method="POST" id="postform3" class="needs-validation" novalidate>
  <div class="input-group mb-2">
  <span class="input-group-text">Пошта:</span>
  <input type="text" class="form-control" id="field1" name="new-cloudflare-name" value="">
  <span class="input-group-text">API токен:</span>
  <input type="text" class="form-control" id="field2" name="new-cloudflare-token" value="">
  <button type="submit" class="btn form-control" style="background-color: palegreen;" name="buttonAddCloudflare" onclick="showLoading()">Додати новий аккаунт</button>
   </div>
  </form>
 </div>
</div>"""
    return render_template("template-admin_panel.html",active4="active",data=html_data,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"admin_panel_cloudflare(): global error {err}")
    flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
    return redirect("/",302)

@admin_panel_bp.route("/admin_panel/owners/", methods=['GET'])
@login_required
@rights_required(255)
def admin_panel_owners():
  try:
    html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered">
  <thead>
  <tr class="table-warning">
    <th scope="col" style="width: 45px;">ID:</th>
    <th scope="col" style="width: 150px;">Домен:</th>
    <th scope="col" style="width: 150px;">Власник:</th>
    <th scope="col" style="width: 150px;">Створен:</th>
    <th scope="col" style="width: 150px;">Склонован з:</th>
  </tr>
  </thead>
  <tbody>"""
    owners = Ownership.query.order_by(Ownership.id).all()
    for i, s in enumerate(owners, 1):
      user = User.query.filter_by(id=s.owner).first()
      if user:
        username = user.realname
      html_data += f"""
  <tr class="table-success">
    <form action="/admin_panel/" method="POST" id="postform" novalidate>
    <td class="table-success cname-cell" >{s.id}
      <button type="submit" class="btn btn-outline-warning" name="buttonDeleteOwnership" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити даний аккаунт та власника.">❌</button>    
    </td></form>
    <td class="table-success cname-cell" >{s.domain}</td>
    <td class="table-success cname-cell" >ID: {s.owner} ({username})</td>
    <td class="table-success cname-cell" >{datetime.strftime(s.created,"%d.%m.%Y %H:%M:%S")}</td>
    <form action="/admin_panel/" method="POST" id="postform" novalidate>
    <td class="table-success cname-cell" >{s.cloned}
      <button type="submit" class="btn btn-outline-warning" name="buttonDeleteOwnershipClone" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити інформацію що цей сайт клонований.">❌</button>
    </td></form>
  </tr>"""
    html_data += """
  </tbody>
  </table>
  <form action="/admin_panel/" method="POST" id="postform3" class="needs-validation" novalidate>
  <div class="input-group mb-2">
  <span class="input-group-text">Домен:</span>
  <input type="text" class="form-control" id="field1" name="new-ownership-domain" value="">
  <span class="input-group-text">ID власника:</span>
  <input type="text" class="form-control" id="field2" name="new-ownership-id" value="">
  <span class="input-group-text">Клон з:</span>
  <input type="text" class="form-control" id="field3" name="new-ownership-clone" value="">
  <button type="submit" class="btn form-control" style="background-color: palegreen;" name="buttonAddOwnership" onclick="showLoading()">Прив'язати домен</button>
   </div>
  </form>
 </div>
</div>"""
    return render_template("template-admin_panel.html",active5="active",data=html_data,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"admin_panel_owners(): global error {err}")
    flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
    return redirect("/",302)

@admin_panel_bp.route("/admin_panel/servers/", methods=['GET'])
@login_required
@rights_required(255)
def admin_panel_servers():
  try:
    html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered">
  <thead>
  <tr class="table-warning">
    <th scope="col" style="width: 45px;">ID:</th>
    <th scope="col" style="width: 150px;">Назва:</th>
    <th scope="col" style="width: 150px;">IP адреса:</th>
    <th scope="col" style="width: 150px;">За замовчуванням?:</th>
    <th scope="col" style="width: 150px;">Створен:</th>
  </tr>
  </thead>
  <tbody>"""
    servers = Servers.query.order_by(Servers.id).all()
    for i, s in enumerate(servers, 1):
      html_data += f"""
  <tr class="table-success">
    <form action="/admin_panel/" method="POST" id="postform" novalidate>
    <td class="table-success cname-cell" >{s.id}
    <button type="submit" class="btn btn-outline-warning" name="buttonDeleteServer" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити даний сервер.">❌</button>    
    </td></form>
    <td class="table-success cname-cell" >{s.name}</td>
    <td class="table-success cname-cell" >{s.ip}</td>
    <form action="/admin_panel/" method="POST" id="postform" novalidate>
    <td class="table-success cname-cell" >{s.isdefault}
    <button type="submit" class="btn btn-outline-warning" name="buttonDefaultServer" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Зробити даний сервер за замовчанням">✅</button>
    </td></form>
    <td class="table-success cname-cell" >{datetime.strftime(s.created,"%d.%m.%Y %H:%M:%S")}</td>
  </tr>"""
    html_data += """
  </tbody>
  </table>
  <form action="/admin_panel/" method="POST" id="postform3" class="needs-validation" novalidate>
  <div class="input-group mb-2">
  <span class="input-group-text">Назва:</span>
  <input type="text" class="form-control" id="field1" name="new-server-name" value="">
  <span class="input-group-text">IP адреса:</span>
  <input type="text" class="form-control" id="field2" name="new-server-ip" value="">
  <button type="submit" class="btn form-control" style="background-color: palegreen;" name="buttonAddServer" onclick="showLoading()">Додати сервер</button>
   </div>
  </form>
 </div>
</div>"""
    return render_template("template-admin_panel.html",active6="active",data=html_data,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"admin_panel_servers(): global error {err}")
    flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
    return redirect("/",302)

@admin_panel_bp.route("/admin_panel/links/", methods=['GET'])
@login_required
@rights_required(255)
def admin_panel_links():
  try:
    users_list = ""
    #gathering all list of available users to put them into user filter list
    ul = db.session.query(Domain_account.account).distinct().order_by(Domain_account.account).all()
    for i, s in enumerate(ul, 1):
      users_list += f'<option value="{s.account}">{s.account}</option>\n\t\t'
    html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered">
  <div class="d-flex align-items-center">
    <input type="text" id="domainFilter" class="form-control" placeholder="🔍 Фільтр по домену…" autofocus>&nbsp;
    <select id="accountFilter" class="form-select form-select">
      <option value="">👤 Фільтр по аккаунту</option>
      {users_list.strip()}
    </select>
  </div>
  <thead>
  <tr class="table-warning">
    <th scope="col" style="width: 45px;">ID:</th>
    <th scope="col" style="width: 150px;">Домен:</th>
    <th scope="col" style="width: 150px;">Аккаунт:</th>
    <th scope="col" style="width: 150px;">Створен:</th>
  </tr>
  </thead>
  <tbody>"""
    links = Domain_account.query.order_by(Domain_account.id).all()
    for i, s in enumerate(links, 1):
      html_data += f"""
  <tr class="table-success" data-owner="{s.account}">
    <form action="/admin_panel/" method="POST" id="postform" novalidate>
    <td class="table-success cname-cell" >{s.id}
    <button type="submit" class="btn btn-outline-warning" name="buttonDeleteLink" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити данну прив'язку.">❌</button>    
    </td></form>
    <td class="table-success cname-cell" >{s.domain}</td>
    <td class="table-success cname-cell" >{s.account}</td>
    <td class="table-success cname-cell" >{datetime.strftime(s.created,"%d.%m.%Y %H:%M:%S")}</td>
  </tr>"""
    html_data += f"""
  </tbody>
  </table>
  <form action="/admin_panel/" method="POST" id="postform3" class="needs-validation" novalidate>
    <div class="input-group mb-2">
      <span class="input-group-text">Домен:</span>
      <input type="text" class="form-control" id="field1" name="new-link-domain" value="">
      <span class="input-group-text">Аккаунт Cloudflare:</span>
      <select id="new-link-account" name="new-link-account" class="form-select form-select">
        {users_list.strip()}
      </select>
      <button type="submit" class="btn form-control" style="background-color: palegreen;" name="buttonAddLink" onclick="showLoading()">Додати</button>
    </div>
  </form>
 </div>
</div>"""
    return render_template("template-admin_panel.html",active7="active",data=html_data,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"admin_panel_links(): global error {err}")
    flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
    return redirect("/",302)

@admin_panel_bp.route("/admin_panel/accounts/", methods=['GET'])
@login_required
@rights_required(255)
def admin_panel_accounts():
  try:
    users_list = ""
    #gathering all list of available users to put them into user filter list
    ul = db.session.query(Cloudflare_account_ownership.owner).distinct().order_by(Cloudflare_account_ownership.owner).all()
    for i, s in enumerate(ul, 1):
      user = User.query.filter_by(id=s.owner).first()
      if user:
        username = user.realname
      users_list += f'<option value="{s.owner}">{s.owner} ({username})</option>\n\t\t'
    html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered">
  <div class="d-flex align-items-center">
    <input type="text" id="domainFilter" class="form-control" placeholder="🔍 Фільтр по аккаунту…" autofocus>&nbsp;
    <select id="accountFilter" class="form-select form-select">
      <option value="">👤 Фільтр по власнику</option>
      {users_list.strip()}
    </select>
  </div>
  <thead>
  <tr class="table-warning">
    <th scope="col" style="width: 45px;">ID:</th>
    <th scope="col" style="width: 150px;">Аккаунт Cloudflare:</th>
    <th scope="col" style="width: 150px;">Власники:</th>
    <th scope="col" style="width: 150px;">Створен:</th>
  </tr>
  </thead>
  <tbody>"""
    accounts = Cloudflare_account_ownership.query.order_by(Cloudflare_account_ownership.id).all()
    for i, s in enumerate(accounts, 1):
      user = User.query.filter_by(id=s.owner).first()
      if user:
        username = user.realname
      html_data += f"""
  <tr class="table-success" data-owner="{s.owner}">
    <form action="/admin_panel/" method="POST" id="postform" novalidate>
    <td class="table-success cname-cell" >{s.id}
    <button type="submit" class="btn btn-outline-warning" name="buttonDeleteAccount" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити данну прив'язку.">❌</button>    
    </td></form>
    <td class="table-success cname-cell" >{s.account}</td>
    <td class="table-success cname-cell" >ID: {s.owner} ({username})</td>
    <td class="table-success cname-cell" >{datetime.strftime(s.created,"%d.%m.%Y %H:%M:%S")}</td>
  </tr>"""
    html_data += f"""
  </tbody>
  </table>
  <form action="/admin_panel/" method="POST" id="postform3" class="needs-validation" novalidate>
    <div class="input-group mb-2">
      <span class="input-group-text">Аккаунт Cloudflare:</span>
      <input type="text" class="form-control" id="field1" name="new-accounts-account" value="">
      <span class="input-group-text">ID власника:</span>
      <select id="new-accounts-id" name="new-accounts-id" class="form-select form-select">
        {users_list.strip()}
      </select>
      <button type="submit" class="btn form-control" style="background-color: palegreen;" name="buttonAddAccount" onclick="showLoading()">Додати</button>
    </div>
  </form>
 </div>
</div>"""
    return render_template("template-admin_panel.html",active8="active",data=html_data,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"admin_panel_accounts(): global error {err}")
    flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
    return redirect("/",302)

@admin_panel_bp.route("/admin_panel/messages/", methods=['GET'])
@login_required
@rights_required(255)
def admin_panel_messages():
  try:
    html_data = f"""
<div class="container">
  <div class="row justify-content-center">
    <div class="col-12 col-lg-10">
      <div class="card shadow-sm">
        <div class="card-header bg-secondary text-white text-center">
          <h4 class="mb-0">📮 Повідомлення всім користувачам</h4>
        </div>
        <form action="/admin_panel/" method="POST" id="postform1" class="needs-validation" novalidate>
          <div class="card-body d-flex flex-column" style="min-height: 70vh;">
            <textarea class="form-control font-monospace mb-3 flex-grow-1" style="resize: none; line-height: 1.4;" id="textform" name="message-textform" placeholder="Введіть текст повідомлення…" autofocus required></textarea>
            <div class="invalid-feedback mb-3">
              Повідомлення не може бути порожнім
            </div>
            <div class="col-12 col-md-8 mx-auto">
              <button class="btn btn-warning btn-lg shadow-sm w-100 PublishMessage-btn" type="submit" name="buttonPublishMessage">Опублікувати повідомлення</button>
            </div><br>
        </form>
        <form action="/admin_panel/" method="POST" id="postform1" class="needs-validation" novalidate>
            <div class="col-12 col-md-12 mx-auto">
              <button class="btn btn-danger btn-lg shadow-sm w-100 ClearMessages-btn" type="submit" name="buttonClearMessages">Очистити все (Зараз копій на всіх користувачів: {len(Messages.query.all())} шт.)</button>
            </div>
          </div>
        </form>
      </div>
    </div>
  </div>
</div>"""
    return render_template("template-admin_panel.html",active9="active",data=html_data,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"admin_panel_accounts(): global error {err}")
    flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
    return redirect("/",302)
