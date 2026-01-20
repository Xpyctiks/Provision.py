from flask import render_template,request,redirect,flash,Blueprint
from flask_login import login_required,current_user
import os,logging,re,asyncio
from functions.send_to_telegram import send_to_telegram

redirects_bp = Blueprint("redirects_manager", __name__)
@redirects_bp.route("/redirects_manager", methods=['GET'])
@login_required
def show_redirects():
  try:
    args = request.args
    site = args.get('site')
    if site:
      file301 = os.path.join("/etc/nginx/additional-configs","301-" + site + ".conf")
      if not os.path.exists(file301):
        with open(file301, 'w',encoding='utf8') as file3:
          file3.write("")
        flash(f"Новий порожній файл редіректів для {site} був створен автоматично.",'alert alert-info')
        logging.info(f"Empty redirects config file {file301} for {site} was created.")
      table = ""
      i = 1
      with open(file301, "r", encoding="utf-8") as f:
        content = f.read()
      pattern = re.compile(
        r'location\s*=\s*(?P<path>/[^\s{]+)\s*{[^}]*?return\s+(?P<type>301)\s+(?P<target>https?://[^\s;]+);',
        re.DOTALL
      )
      for match in pattern.finditer(content):
        table += f"""\n<tr>\n
        <th scope="row" class="table-success">{i}</th>
        <td class="table-success">{match.group("path")}</td>
        <td class="table-success"><input type="checkbox" name="selected" value="{match.group("path")}"></td>
        <td class="table-success">{match.group("target")}</td>
        <td class="table-success">{match.group("type")}</td>
        <td class="table-success">
          <button class="btn btn-danger" type="submit" name="del_redir" value="{match.group("path")}">Видалити</button>
          <input type="hidden" name="sitename" value="{site}">
        </td>
        \n</tr>"""
        i = i+1
      #here we check file marker to make Apply button glow yellow if there is something to apply
      if os.path.exists("/tmp/provision.marker"):
        applyButton = "btn-warning"
      else:
        applyButton = "btn-outline-warning"
      return render_template("template-redirects.html",table=table,sitename=site,applyButton=applyButton)
    else:
      return redirect("/",302)
  except Exception as err:
    logging.error(f"show_redirects(): general error by {current_user.realname}: {err}")
    asyncio.run(send_to_telegram(f"show_redirects(): general error: {err}",f"🚒Provision redirects manager error by {current_user.realname}:"))
    flash(f"Неочікувана помилка при POST запиту на сторінці /uredirects_manager! Дивіться логи!", 'alert alert-danger')
    return redirect("/",302)
