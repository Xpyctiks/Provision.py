from flask import render_template,request,redirect,flash,Blueprint
from flask_login import login_required
from functions.site_actions import enable_allredirects, disable_allredirects
import os,logging,re

redirects_bp = Blueprint("redirects_manager", __name__)
@redirects_bp.route("/redirects_manager", methods=['GET','POST'])
@login_required
def redirects():
    if request.method == 'POST':
        if not request.form.get('manager') and request.form.get('redirect_checkbox'):
            #parsing list of "redirect_checkbox" values because there can be 2 at the same time
            values = request.form.getlist("redirect_checkbox")
            checkbox_enabled = "1" in values
            if checkbox_enabled:
                enable_allredirects(request.form.get("sitename").strip())
                return redirect("/",301)
            else:
                disable_allredirects(request.form.get("sitename").strip())
                return redirect("/",301)
        else:
            return redirect("/",301)
    #if this is GET request - show page
    if request.method == 'GET':
        args = request.args
        site = args.get('site')
        if site:
            file301 = os.path.join("/etc/nginx/additional-configs","301-" + site + ".conf")
            if not os.path.exists(file301):
                with open(file301, 'w',encoding='utf8') as file3:
                    file3.write("")
                flash(f"Empty redirects config file for {site} was created.",'alert alert-info')
                logging.info(f"Empty redirects config file {file301} for {site} was created.")
            table = ""
            i = 1
            with open(file301, "r", encoding="utf-8") as f:
                content = f.read()
            pattern = re.compile(
                r'location\s+(?P<typ>.)\s+(?P<path>/[^\s{]+)\s*{[^}]*?rewrite\s+\^\(.\*\)\$\s+(?P<target>https?://[^\s]+)\s+permanent;',
                re.MULTILINE
            )
            for match in pattern.finditer(content):
                table += f"""\n<tr>\n
                <th scope="row" class="table-success">{i}</th>
                <td class="table-success">{match.group("path")}</td>
                <td class="table-success"><input type="checkbox" name="selected" value="{match.group("path")}"></td>
                <td class="table-success">{match.group("target")}</td>
                <td class="table-success">{match.group("typ")}</td>
                <td class="table-success">
                    <button class="btn btn-danger" type="submit" name="del_redir" value="{match.group("path")}">Delete</button>
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
            return redirect("/",301)