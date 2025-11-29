from flask import render_template,Blueprint,current_app
import logging,os
from flask_login import login_required
from functions.site_actions import count_redirects

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
        for i, s in enumerate(sites_list, 1):
            #general check all Nginx sites-available, sites-enabled folder + php pool.d/ are available
            #variable with full path to nginx sites-enabled symlink to the site
            ngx_site = os.path.join(current_app.config["NGX_SITES_PATHEN"],s)
            ngx_av = os.path.join(current_app.config["NGX_SITES_PATHAV"],s)
            #variable with full path to php pool config of the site
            php_site = os.path.join(current_app.config["PHP_POOL"],s+".conf")
            #check of nginx and php have active links and configs of the site
            checkbox_state = ""
            button_state = "enabled"
            if os.path.islink(ngx_site) and os.path.isfile(php_site):
                #check if redirects are enabled or disabled in nginx site config and set checkbox to the proper state
                with open(ngx_av, "r", encoding="utf-8") as f:
                    for line in f:
                        if line.lstrip().startswith("if ( $request_uri !="):
                            checkbox_state = "checked"
                            button_state = "disabled"
                table += f"""\n<tr>\n<th scope="row" class="table-success">{i}</th>
                <td class="table-success"><form method="post" action="/action">
                    <button type="submit" value="{s}" name="delete" onclick="showLoading()" class="btn btn-danger" 
                    title="Повне та невозвратне видалення сайту та його конфігурації з серверу.">Видалити</button>
                    <button type="submit" value="{s}" name="disable" onclick="showLoading()" class="btn btn-warning" 
                    title="Тимчасово вимкнути сайт - він не будет оброблятися при запитах зовні,але фізично залишається на сервері.">Вимкнути</button>
                    <button type="submit" value="{s}" name="clone" onclick="showLoading()" class="btn btn-success" 
                    title="Взяти за основу даний сайт та зробити копію для іншого домену.">Клонувати</button>
                </form>
                <form method="post" action="/redirects_manager" id="redirect_form{s}">
                    <a href="/redirects_manager?site={s}" class="btn btn-info" type="submit" name="manager" value="{s}" style="margin-top: 5px; margin-left: 1px;" {button_state}
                    title="Керування 301-и редіректами для цього сайту.">Керування редіректами\n(~{count_redirects(s)} шт. вже є)</a>
                    <div class="form-check form-switch">
                        <input type="hidden" name="redirect_checkbox" value="0">
                        <input type="hidden" name="sitename" value="{s}">
                        <input class="form-check-input" type="checkbox" style="margin-left: -38px; name="redirect_checkbox" id="redirect_checkbox" onchange="document.getElementById('redirect_form{s}').submit();" value="1" {checkbox_state} 
                        title="Якщо ввімкнений - абсолютно всі адреси,що ідуть до сайту, редіректяться на головну.Якщо вимкнено - то спочатку шукаються доступні в папці сайту,а потім редірект або помилка.">Редірект усіх запитів на головну
                    </div>
                </form>
                <td class="table-success">{s}</td>
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
                <td class="table-success">OK</td>
                \n</tr>"""
            #if nginx is ok but php is not
            elif os.path.islink(ngx_site) and not os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-danger">{i}</th>
                <td class="table-danger"><form method="post" action="/action">
                    <button type="submit" value="{s}" name="delete" onclick="showLoading()" class="btn btn-danger" 
                    title="Повне та невозвратне видалення сайту та його конфігурації з серверу.">Видалити</button>
                    <button type="submit" value="{s}" name="enable" onclick="showLoading()" class="btn btn-success" 
                    title="Активувати сайт - він буде оброблятися при запитах ззовні.">Активувати</button>
                </form>
                <td class="table-danger">{s}</td>
                <td class="table-danger">{os.path.join(current_app.config["WEB_FOLDER"],s)}</td>
                <td class="table-danger">PHP config error</td>
                \n</tr>"""
            #if php is ok but nginx is not
            elif not os.path.islink(ngx_site) and os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-danger">{i}</th>
                <td class="table-danger"><form method="post" action="/action">
                    <button type="submit" value="{s}" name="delete" onclick="showLoading()" class="btn btn-danger" 
                    title="Повне та невозвратне видалення сайту та його конфігурації з серверу.">Видалити</button>
                    <button type="submit" value="{s}" name="enable" onclick="showLoading()" class="btn btn-success" 
                    title="Активувати сайт - він буде оброблятися при запитах ззовні.">Активувати</button>
                </form>
                <td class="table-danger">{s}</td>
                <td class="table-danger">{os.path.join(current_app.config["WEB_FOLDER"],s)}</td>
                <td class="table-danger">Nginx config error</td>
                \n</tr>"""
            #if really disabled
            elif not os.path.islink(ngx_site) and not os.path.isfile(php_site):
                table += f"""\n<tr>\n<th scope="row" class="table-warning">{i}</th>
                <td class="table-warning"><form method="post" action="/action">
                    <button type="submit" value="{s}" name="delete" onclick="showLoading()" class="btn btn-danger" 
                    title="Повне та невозвратне видалення сайту та його конфігурації з серверу.">Видалити</button>
                    <button type="submit" value="{s}" name="enable" onclick="showLoading()" class="btn btn-success" 
                    title="Активувати сайт - він буде оброблятися при запитах ззовні.">Активувати</button>
                    <button style="margin: inherit; margin-top: 4px;" type="submit" value="{s}" name="clone" onclick="showLoading()" class="btn btn-success" 
                    title="Взяти за основу даний сайт та зробити копію для іншого домену.">Клонувати</button>
                </form>
                <td class="table-warning">{s}</td>
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
                <td class="table-warning">Site is disabled</td>
                \n</tr>"""
            else:
                table += f"""\n<tr>\n<th scope="row" class="table-danger">{i}</th>
                <td class="table-danger">General</td>
                <td class="table-danger">Error</td>
                <td class="table-danger">Important folders are not available or not exist</td>
                \n</tr>"""
        return render_template("template-main.html",table=table)
    except Exception as msg:
        logging.error(f"Error in index(/): {msg}")
