from flask import redirect,Blueprint,request,render_template,flash
from flask_login import login_required, current_user
import logging,asyncio
from db.database import *
from functions.send_to_telegram import send_to_telegram

admin_panel_bp = Blueprint("admin_panel", __name__)

@admin_panel_bp.route("/admin_panel/", methods=['GET'])
@admin_panel_bp.route("/admin_panel", methods=['GET'])
@login_required
def admin_panel():
    return redirect("/admin_panel/settings/",301)

@admin_panel_bp.route("/admin_panel/settings/", methods=['GET'])
@login_required
def admin_panel_settings():
    try:
        html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <form action="/admin_panel" method="POST" id="postform" novalidate>"""
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
    <input type="hidden" id="value-{i}" name="value-{i}" value="">
</div>"""
                i = i + 1
        html_data += """
  <div class="input-group mb-2">
    <button type="submit" class="btn form-control" style="background-color: palegreen;" name="buttonSaveSettings" onclick="syncSettings()">Зберегти налаштування</button>
  </div>
 </form>
</div>
"""
        return render_template("template-admin_panel.html",active1="active",data=html_data)
    except Exception as err:
        logging.error(f"admin_panel_settings(): global error {err}")
        asyncio.run(send_to_telegram(f"admin_panel_settings(): global error {err}",f"🚒Provision error by {current_user.realname}"))
        flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
        return redirect("/",301)

@admin_panel_bp.route("/admin_panel/users/", methods=['GET'])
@login_required
def admin_panel_users():
    try:
        html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered" style="margin-top: 60px;">
  <thead>
    <tr class="table-warning">
      <th scope="col" style="width: 45px;">ID:</th>
      <th scope="col" style="width: 150px;">Логін:</th>
      <th scope="col" style="width: 150px;">Ім'я:</th>
      <th scope="col" style="width: 150px;">Створен:</th>
    </tr>
  </thead>
  <tbody>"""
        users = User.query.order_by(User.username).all()
        if len(users) == 0:
            print("No users found in DB!")
            quit()
        for i, s in enumerate(users, 1):
            html_data += f"""
    <tr class="table-success">
      <form action="/admin_panel" method="POST" id="postform" novalidate>
      <td class="table-success cname-cell" >{s.id}
        <button type="submit" class="btn btn-light" name="buttonDeleteUser" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити даного користувача із бази.">❌</button>        
      </td></form>
      <td class="table-success cname-cell" >{s.username}</td>
      <td class="table-success cname-cell" >{s.realname}</td>
      <td class="table-success cname-cell" >{s.created}</td>
    </tr>"""
        html_data += """
  </tbody>
  </table>
  <form action="/admin_panel" method="POST" id="postform2" class="needs-validation" novalidate>
  <div class="input-group mb-2">
    <span class="input-group-text">Логін:</span>
    <input type="text" class="form-control" id="new-username" name="new-username" value="">
    <span class="input-group-text">Пароль:</span>
    <input type="text" class="form-control" id="new-password" name="new-password" value="">
    <span class="input-group-text">І'мя</span>
    <input type="text" class="form-control" id="new-realname" name="new-realname" value="">
    <button type="submit" class="btn form-control" style="background-color: palegreen;" name="buttonCreateUser" onclick="showLoading()">Створити користувача</button>
   </div>
  </form>
 </div>
</div>"""
        return render_template("template-admin_panel.html",active2="active",data=html_data)
    except Exception as err:
        logging.error(f"admin_panel_users(): global error {err}")
        asyncio.run(send_to_telegram(f"admin_panel_users(): global error {err}",f"🚒Provision error by {current_user.realname}"))
        flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
        return redirect("/",301)

@admin_panel_bp.route("/admin_panel/templates/", methods=['GET'])
@login_required
def admin_panel_templates():
    try:
        html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered" style="margin-top: 60px;">
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
      <form action="/admin_panel" method="POST" id="postform" novalidate>
      <td class="table-success cname-cell" >{s.id}
        <button type="submit" class="btn btn-light" name="buttonDeleteTemplate" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити даний шаблон із бази.">❌</button>        
      </td></form>
      <td class="table-success cname-cell" >{s.name}</td>
      <td class="table-success cname-cell" >{s.repository}</td>
      <form action="/admin_panel" method="POST" id="postform" novalidate>
      <td class="table-success cname-cell" >{s.isdefault}
        <button type="submit" class="btn btn-light" name="buttonDefaultTemplate" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Зробити даний шаблон за замовчанням">✅</button>        
      </td></form>
      <td class="table-success cname-cell" >{s.created}</td>
    </tr>"""
        html_data += """
  </tbody>
  </table>
  <form action="/admin_panel" method="POST" id="postform3" class="needs-validation" novalidate>
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
        return render_template("template-admin_panel.html",active3="active",data=html_data)
    except Exception as err:
        logging.error(f"admin_panel_templates(): global error {err}")
        asyncio.run(send_to_telegram(f"admin_panel_templates(): global error {err}",f"🚒Provision error by {current_user.realname}"))
        flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
        return redirect("/",301)

@admin_panel_bp.route("/admin_panel/cloudflare/", methods=['GET'])
@login_required
def admin_panel_cloudflare():
    try:
        html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered" style="margin-top: 60px;">
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
      <form action="/admin_panel" method="POST" id="postform" novalidate>
      <td class="table-success cname-cell" >{s.id}
        <button type="submit" class="btn btn-light" name="buttonDeleteCloudflare" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити даний аккаунт із бази.">❌</button>        
      </td></form>
      <td class="table-success cname-cell" >{s.account}</td>
      <td class="table-success cname-cell" ><details><summary>Натисніть що б подивитись</summary>{s.token}</details></td>
      <form action="/admin_panel" method="POST" id="postform" novalidate>
      <td class="table-success cname-cell" >{s.isdefault}
        <button type="submit" class="btn btn-light" name="buttonDefaultCloudflare" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Зробити даний аккаунт за замовчанням">✅</button>        
      </td></form>
      <td class="table-success cname-cell" >{s.created}</td>
    </tr>"""
        html_data += """
  </tbody>
  </table>
  <form action="/admin_panel" method="POST" id="postform3" class="needs-validation" novalidate>
  <div class="input-group mb-2">
    <span class="input-group-text">Пошта:</span>
    <input type="text" class="form-control" id="field1" name="new-cloudflare-name" value="">
    <span class="input-group-text">API токен:</span>
    <input type="text" class="form-control" id="field2" name="new-cloudflare-token" value="">
    <button type="submit" class="btn form-control" style="background-color: palegreen;" name="buttonAddTemplate" onclick="showLoading()">Додати новий аккаунт</button>
   </div>
  </form>
 </div>
</div>"""
        return render_template("template-admin_panel.html",active4="active",data=html_data)
    except Exception as err:
        logging.error(f"admin_panel_cloudflare(): global error {err}")
        asyncio.run(send_to_telegram(f"admin_panel_cloudflare(): global error {err}",f"🚒Provision error by {current_user.realname}"))
        flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
        return redirect("/",301)

@admin_panel_bp.route("/admin_panel/owners/", methods=['GET'])
@login_required
def admin_panel_owners():
    try:
        html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered" style="margin-top: 60px;">
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
      <form action="/admin_panel" method="POST" id="postform" novalidate>
      <td class="table-success cname-cell" >{s.id}
        <button type="submit" class="btn btn-light" name="buttonDeleteOwnership" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити даний аккаунт та власника.">❌</button>        
      </td></form>
      <td class="table-success cname-cell" >{s.domain}</td>
      <td class="table-success cname-cell" >ID: {s.owner} ({username})</td>
      <td class="table-success cname-cell" >{s.created}</td>
      <td class="table-success cname-cell" >{s.cloned}</td>
    </tr>"""
        html_data += """
  </tbody>
  </table>
  <form action="/admin_panel" method="POST" id="postform3" class="needs-validation" novalidate>
  <div class="input-group mb-2">
    <span class="input-group-text">Домен:</span>
    <input type="text" class="form-control" id="field1" name="new-ownership-domain" value="">
    <span class="input-group-text">ID власника:</span>
    <input type="text" class="form-control" id="field2" name="new-ownership-id" value="">
    <button type="submit" class="btn form-control" style="background-color: palegreen;" name="buttonAddOwnership" onclick="showLoading()">Прив'язати домен</button>
   </div>
  </form>
 </div>
</div>"""
        return render_template("template-admin_panel.html",active5="active",data=html_data)
    except Exception as err:
        logging.error(f"admin_panel_owners(): global error {err}")
        asyncio.run(send_to_telegram(f"admin_panel_owners(): global error {err}",f"🚒Provision error by {current_user.realname}"))
        flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
        return redirect("/",301)

@admin_panel_bp.route("/admin_panel/servers/", methods=['GET'])
@login_required
def admin_panel_servers():
    try:
        html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered" style="margin-top: 60px;">
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
      <form action="/admin_panel" method="POST" id="postform" novalidate>
      <td class="table-success cname-cell" >{s.id}
        <button type="submit" class="btn btn-light" name="buttonDeleteServer" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити даний сервер.">❌</button>        
      </td></form>
      <td class="table-success cname-cell" >{s.name}</td>
      <td class="table-success cname-cell" >{s.ip}</td>
      <td class="table-success cname-cell" >{s.isdefault}
        <button type="submit" class="btn btn-light" name="buttonDefaultServer" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Зробити даний сервер за замовчанням">✅</button>        
      </td></form>
      <td class="table-success cname-cell" >{s.created}</td>
    </tr>"""
        html_data += """
  </tbody>
  </table>
  <form action="/admin_panel" method="POST" id="postform3" class="needs-validation" novalidate>
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
        return render_template("template-admin_panel.html",active6="active",data=html_data)
    except Exception as err:
        logging.error(f"admin_panel_servers(): global error {err}")
        asyncio.run(send_to_telegram(f"admin_panel_servers(): global error {err}",f"🚒Provision error by {current_user.realname}"))
        flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
        return redirect("/",301)

@admin_panel_bp.route("/admin_panel/links/", methods=['GET'])
@login_required
def admin_panel_links():
    try:
        html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered" style="margin-top: 60px;">
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
    <tr class="table-success">
      <form action="/admin_panel" method="POST" id="postform" novalidate>
      <td class="table-success cname-cell" >{s.id}
        <button type="submit" class="btn btn-light" name="buttonDeleteLink" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити данну прив'язку.">❌</button>        
      </td></form>
      <td class="table-success cname-cell" >{s.domain}</td>
      <td class="table-success cname-cell" >{s.account}</td>
      <td class="table-success cname-cell" >{s.created}</td>
    </tr>"""
        html_data += """
  </tbody>
  </table>
  <form action="/admin_panel" method="POST" id="postform3" class="needs-validation" novalidate>
  <div class="input-group mb-2">
    <span class="input-group-text">Домен:</span>
    <input type="text" class="form-control" id="field1" name="new-link-domain" value="">
    <span class="input-group-text">Аккаунт Cloudflare:</span>
    <input type="text" class="form-control" id="field2" name="new-link-account" value="">
    <button type="submit" class="btn form-control" style="background-color: palegreen;" name="buttonAddLink" onclick="showLoading()">Додати</button>
   </div>
  </form>
 </div>
</div>"""
        return render_template("template-admin_panel.html",active7="active",data=html_data)
    except Exception as err:
        logging.error(f"admin_panel_links(): global error {err}")
        asyncio.run(send_to_telegram(f"admin_panel_links(): global error {err}",f"🚒Provision error by {current_user.realname}"))
        flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
        return redirect("/",301)

@admin_panel_bp.route("/admin_panel/accounts/", methods=['GET'])
@login_required
def admin_panel_accounts():
    try:
        html_data = f"""
<div class="card mx-auto" style="max-width: 80vw;" id="SettingsBlock">
  <table class="table table-bordered" style="margin-top: 60px;">
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
    <tr class="table-success">
      <form action="/admin_panel" method="POST" id="postform" novalidate>
      <td class="table-success cname-cell" >{s.id}
        <button type="submit" class="btn btn-light" name="buttonDeleteLink" onclick="showLoading()" value="{s.id}" data-bs-toggle="tooltip" data-bs-placement="top" title="Видалити данну прив'язку.">❌</button>        
      </td></form>
      <td class="table-success cname-cell" >{s.account}</td>
      <td class="table-success cname-cell" >ID: {s.owner} ({username})</td>
      <td class="table-success cname-cell" >{s.created}</td>
    </tr>"""
        html_data += """
  </tbody>
  </table>
  <form action="/admin_panel" method="POST" id="postform3" class="needs-validation" novalidate>
  <div class="input-group mb-2">
    <span class="input-group-text">Аккаунт Cloudflare:</span>
    <input type="text" class="form-control" id="field1" name="new-accounts-account" value="">
    <span class="input-group-text">ID власника:</span>
    <input type="text" class="form-control" id="field2" name="new-accounts-id" value="">
    <button type="submit" class="btn form-control" style="background-color: palegreen;" name="buttonAddAccount" onclick="showLoading()">Додати</button>
   </div>
  </form>
 </div>
</div>"""
        return render_template("template-admin_panel.html",active8="active",data=html_data)
    except Exception as err:
        logging.error(f"admin_panel_accounts(): global error {err}")
        asyncio.run(send_to_telegram(f"admin_panel_accounts(): global error {err}",f"🚒Provision error by {current_user.realname}"))
        flash('Загальна помилка відображення данних! Дивіться логи.', 'alert alert-danger')
        return redirect("/",301)