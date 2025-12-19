from flask import render_template,Blueprint,current_app
import logging,os,re
from flask_login import login_required
from functions.site_actions import count_redirects
from functions.pages_forms import getSiteOwner, getSiteCreated

#allows to sort with natural keys - when after 10 goes 11, not 20
def natural_key(s):
    return [int(text) if text.isdigit() else text.lower() for text in re.split(r'(\d+)', s)]

root_bp = Blueprint("root", __name__)
@root_bp.route("/", methods=['GET'])
@login_required
def index():
    try:
        table = ""
        sites_list = []
        sites_list = [
            name for name in os.listdir(current_app.config["WEB_FOLDER"])
            if os.path.isdir(os.path.join(current_app.config["WEB_FOLDER"], name))
        ]
        for i, s in enumerate(sorted(sites_list, key=natural_key), 1):
            #general check all Nginx sites-available, sites-enabled folder + php pool.d/ are available
            #variable with full path to nginx sites-enabled symlink to the site
            ngx_site = os.path.join(current_app.config["NGX_SITES_PATHEN"],s)
            ngx_av = os.path.join(current_app.config["NGX_SITES_PATHAV"],s)
            #variable with full path to php pool config of the site
            php_site = os.path.join(current_app.config["PHP_POOL"],s+".conf")
            #check of nginx and php have active links and configs of the site
            button_state = "enabled"
            if os.path.islink(ngx_site) and os.path.isfile(php_site):
                #check if redirects are enabled or disabled in nginx site config and set checkbox to the proper state
                with open(ngx_av, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.lstrip().startswith("if ( $request_uri !="):
                            button_state = "disabled"
                table += f"""\n<tr>\n<th scope="row" class="table-success">{i}</th>
                <form method="post" action="/action" id="main_form"></form>
                <form method="post" action="/redirects_manager" id="redirect_form{s}"></form>
                <td class="table-success">
                    <button class="btn btn-danger delete-btn" data-bs-toggle="tooltip" data-bs-placement="top" type="submit" value="{s}" data-site="{s}" name="delete" form="main_form" onclick="showLoading()" title="Повне та невозвратне видалення сайту та його конфігурації з серверу.">🙅‍♂️Видалити</button>
                    <button class="btn btn-warning" data-bs-toggle="tooltip" data-bs-placement="top" type="submit" value="{s}" name="disable" form="main_form" onclick="showLoading()"  title="Тимчасово вимкнути сайт - він не будет оброблятися при запитах зовні,але фізично залишається на сервері.">🚧Вимкнути</button>
                    <a name="clone" data-bs-toggle="tooltip" data-bs-placement="top" onclick="showLoading()" class="btn btn-success" href="/clone?source_site={s}" style="width: 139px;" title="Взяти за основу даний сайт та зробити копію для іншого домену.">🚻Клонувати</a>
                    <button data-bs-toggle="tooltip" data-bs-placement="top" type="submit" value="{s}" id="gitPullButton" name="gitPull" form="main_form" onclick="showLoading()" class="btn btn-primary gitpull-btn" style="margin-top: 5px;" title="Зробити пул із репозиторію для оновлення коду сайту до актуального">♻Оновити код</button>
                    <a href="/redirects_manager?site={s}" class="btn btn-info" data-bs-toggle="tooltip" data-bs-placement="top" type="submit" name="manager" value="{s}" style="margin-top: 5px; width: 236px;" title="Керування 301-ми редіректами для цього сайту." {button_state}>🚥Редіректи\n(~{count_redirects(s)} шт. вже є)</a><br>
                    <input type="hidden" name="sitename" value="{s}">
                    <u>Сайт розгорнут: {getSiteCreated(s)}</u>
                <td class="table-success">
                    <input class="selected-site form-check-input chk" type="checkbox" name="selected" value="{s}" form="main_form">
                    <a href="https://{s}" target="blank">{s}</a>
                </td>
                <td class="table-success">
                <div class="accordion" id="folderAccordion{i}">
                    <div class="accordion-item">
                        <h2 class="accordion-header" id="headingOne{i}">
                            <button class="accordion-button collapsed" type="button" style="background-color: #B5FFF1;" data-bs-toggle="collapse" data-bs-target="#collapseOne{i}" aria-expanded="false" aria-controls="collapseOne{i}" data-path="{os.path.join(current_app.config["WEB_FOLDER"],s)}">
                                + 📁 {os.path.join(current_app.config["WEB_FOLDER"],s)}
                            </button>
                        </h2>
                        <div id="collapseOne{i}" class="accordion-collapse collapse" aria-labelledby="headingOne{i}" data-bs-parent="#folderAccordion{i}">
                            <div class="accordion-body">
                                Заватажую...
                            </div>
                        </div>
                    </div>
                </div></td>
                <td class="table-success">{getSiteOwner(s)}</td>
                <td class="table-success">✅OK</td>
                \n</tr>"""
            #if nginx is ok but php is not
            elif os.path.islink(ngx_site) and not os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-danger">{i}</th>
                <td class="table-danger"><form method="post" action="/action">
                    <button data-bs-toggle="tooltip" data-bs-placement="top" type="submit" value="{s}" data-site="{s}" name="delete" onclick="showLoading()" class="btn btn-danger delete-btn" 
                    title="Повне та невозвратне видалення сайту та його конфігурації з серверу.">🙅‍♂️Видалити</button>
                    <button data-bs-toggle="tooltip" data-bs-placement="top" type="submit" value="{s}" name="enable" onclick="showLoading()" class="btn btn-success" 
                    title="Активувати сайт - він буде оброблятися при запитах ззовні.">Активувати</button>
                </form>
                <td class="table-danger">                    
                    <input class="selected-site form-check-input chk" type="checkbox" name="selected" value="{s}" form="main_form">
                    <a href="https://{s}" target="blank">{s}</a>
                </td>
                <td class="table-danger">{os.path.join(current_app.config["WEB_FOLDER"],s)}</td>
                <td class="table-danger"></td>
                <td class="table-danger">🚨Помилка конфігураціх РНР</td>
                \n</tr>"""
            #if php is ok but nginx is not
            elif not os.path.islink(ngx_site) and os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-danger">{i}</th>
                <td class="table-danger"><form method="post" action="/action">
                    <button data-bs-toggle="tooltip" data-bs-placement="top" type="submit" value="{s}" data-site="{s}" name="delete" onclick="showLoading()" class="btn btn-danger delete-btn" 
                    title="Повне та невозвратне видалення сайту та його конфігурації з серверу.">🙅‍♂️Видалити</button>
                    <button data-bs-toggle="tooltip" data-bs-placement="top" type="submit" value="{s}" name="enable" onclick="showLoading()" class="btn btn-success" 
                    title="Активувати сайт - він буде оброблятися при запитах ззовні.">🏃Активувати</button>
                </form>
                <td class="table-danger">                    
                    <input class="selected-site form-check-input chk" type="checkbox" name="selected" value="{s}" form="main_form">
                    <a href="https://{s}" target="blank">{s}</a>
                </td>
                <td class="table-danger">{os.path.join(current_app.config["WEB_FOLDER"],s)}</td>
                <td class="table-danger">{getSiteOwner(s)}</td>
                <td class="table-danger">🚨Помилка конфігураціх Nginx</td>
                \n</tr>"""
            #if really disabled
            elif not os.path.islink(ngx_site) and not os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-warning">{i}</th>
                <td class="table-warning"><form method="post" action="/action">
                    <button data-bs-toggle="tooltip" data-bs-placement="top" type="submit" value="{s}" data-site="{s}" name="delete" onclick="showLoading()" class="btn btn-danger delete-btn" 
                    title="Повне та невозвратне видалення сайту та його конфігурації з серверу.">🙅‍♂️Видалити</button>
                    <button data-bs-toggle="tooltip" data-bs-placement="top" type="submit" value="{s}" name="enable" onclick="showLoading()" class="btn btn-success" 
                    title="Активувати сайт - він буде оброблятися при запитах ззовні.">🏃Активувати</button>
                    <button data-bs-toggle="tooltip" data-bs-placement="top" style="margin: inherit; margin-top: 1px;" type="submit" value="{s}" name="clone" formaction="/clone" formmethod="post" onclick="showLoading()" class="btn btn-success" 
                    title="Взяти за основу даний сайт та зробити копію для іншого домену.">🚻Клонувати</button>
                    Створено: {getSiteCreated(s)}
                </form>
                <td class="table-warning">
                    <input class="selected-site form-check-input chk" type="checkbox" name="selected" value="{s}" form="main_form">
                    <a href="https://{s}" target="blank">{s}</a>
                </td>
                <td class="table-warning">
                <div class="accordion" id="folderAccordion{i}">
                    <div class="accordion-item">
                        <h2 class="accordion-header" id="headingOne{i}">
                            <button class="accordion-button collapsed" type="button" style="background-color: #B5FFF1;" data-bs-toggle="collapse" data-bs-target="#collapseOne{i}" aria-expanded="false" aria-controls="collapseOne{i}" data-path="{os.path.join(current_app.config["WEB_FOLDER"],s)}">
                                + 📁 {os.path.join(current_app.config["WEB_FOLDER"],s)}
                            </button>
                        </h2>
                        <div id="collapseOne{i}" class="accordion-collapse collapse" aria-labelledby="headingOne{i}" data-bs-parent="#folderAccordion{i}">
                            <div class="accordion-body">
                                Заватажую...
                            </div>
                        </div>
                    </div>
                </div></td>
                <td class="table-warning">{getSiteOwner(s)}</td>
                <td class="table-warning">🚧Сайт вимкнено</td>
                \n</tr>"""
            else:
                table += f"""\n<tr>\n<th scope="row" class="table-danger">{i}</th>
                <td class="table-danger">ЗАГАЛЬНА</td>
                <td class="table-danger">ПОМИЛКА</td>
                <td class="table-danger">СИСТЕМИ</td>
                <td class="table-danger">Важливі файли або папки не існують</td>
                \n</tr>"""
        return render_template("template-main.html",table=table)
    except Exception as msg:
        logging.error(f"Error in index(/): {msg}")
    return "root.py ERROR!"