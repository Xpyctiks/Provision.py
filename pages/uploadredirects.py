from flask import render_template,request,redirect,flash,Blueprint
from flask_login import current_user, login_required
import logging,os
from werkzeug.utils import secure_filename
from functions.site_actions import normalize_domain,is_admin

uploadredir_bp = Blueprint("upload_redirects", __name__)
@uploadredir_bp.route("/upload_redirects", methods=['POST'])
@login_required
def uploadredir_file():
  """POST request processor: getting uploaded CSV file and takes redirects from it."""
  try:
    logging.info(f"-----------------------Adding new redirects for {request.form.get('sitename').strip()} by {current_user.realname}-----------------")
    sitename = request.form.get("sitename", "")
    sitename = str(normalize_domain(sitename))
    #name of the redirect config file
    file301 = os.path.join("/etc/nginx/additional-configs","301-" + sitename + ".conf")
    logging.info(f"Redirect config file: {file301}")
    #if this is submitted form and fileUpload[] exists in the request
    if request.form.get('addnewSubmit') and 'fileUpload' in request.files and not request.form.get('RedirectFromField') and not request.form.get('RedirectToField'):
      #get the list of files. saving them to the current folder. Redirect to /
      if request.form.get('templateField') == "strict":
        type = "="
      else:
        type = "~"
      logging.info(f"CSV file with redirects uploaded. Type of redirects: {type}")
      redirectsCount = 0
      file = request.files["fileUpload"]
      filename = os.path.join("/tmp/",secure_filename(file.filename))
      file.save(filename)
      logging.info(f"Uploaded file: {filename}")
      totalData = ""
      with open(filename, "r", encoding="utf-8") as redirectsFile:
        for line in redirectsFile:
          redirFrom, redirTo = line.strip().split(",")
          template = f"""location {type} {redirFrom} {{
  return 301 https://{sitename}{redirTo};
}}
"""
          totalData += template
          redirectsCount = redirectsCount + 1
      #now write down all redirects to the file
      with open(file301, "a", encoding="utf-8") as f:
        f.write(totalData)
      logging.info(f"New redirects were saved to {file301}")
      os.unlink(filename)
      logging.info(f"Uploaded CSV file {filename} was deleted")
      #here we create a marker file which makes "Apply changes" button to glow yellow
      if not os.path.exists("/tmp/provision.marker"):
        with open("/tmp/provision.marker", 'w',encoding='utf8') as file3:
          file3.write("")
        logging.info("Marker file for Apply button created")
      flash(f"{redirectsCount} редіректів успішно додано!", 'alert alert-success')
      logging.info(f"-----------------------New redirects added successfully for {sitename}-----------------")
      return redirect(f"/redirects_manager?site={sitename}",301)
    #if this is submitted form and single redirect lines exist there
    elif request.form.get('addnewSubmit') and request.form.get('RedirectFromField') and request.form.get('RedirectToField') and request.form.get('templateField'):
      logging.info(f"-----------------------Adding new single redirect for {sitename} by {current_user.realname}-----------------")
      logging.info(f"Redirect config file: {file301}")
      if request.form.get('templateField') == "strict":
        type = "="
      else:
        type = "~"
      logging.info(f"Type of redirect: {type}")
      logging.info(f"Redirect: From: {sitename} to {request.form.get('RedirectToField').strip()}")
      template = f"""location {type} {request.form.get('RedirectFromField').strip()} {{
  return 301 https://{sitename}{request.form.get('RedirectToField').strip()};
}}
"""
      with open(file301, "a", encoding="utf-8") as f:
        f.write(template)
      #here we create a marker file which makes "Apply changes" button to glow yellow
      if not os.path.exists("/tmp/provision.marker"):
        with open("/tmp/provision.marker", 'w',encoding='utf8') as file3:
          file3.write("")
        logging.info("Marker file for Apply button created")
      logging.info(f"-----------------------New redirect added successfully for {sitename}-----------------")
      return redirect(f"/redirects_manager?site={sitename}",301)
    else:
      logging.error("Some unknown error - not a file was uploaded and not single redirect was added. Looks like some fields are not set or messed.")
      flash("Якась помилка - ні файл, ні текстові поля не були завантажені.Схоже на технічну помилку в коді.",'alert alert-danger')
      return redirect(f"/redirects_manager?site={sitename}",301)
  except Exception as err:
    logging.error(f"uploadredir_file(): general error by {current_user.realname}: {err}")
    flash(f"Неочікувана помилка при POST запиту на сторінці /upload_redirects! Дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

@uploadredir_bp.route("/upload_redirects", methods=['GET'])
@login_required
def show_uploadredir_file():
  """GET request: show /upload_redirects page."""
  try:
    args = request.args
    site = args.get('site')
    return render_template("template-upload_redir.html",sitename=site,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"show_uploadredir_file(): general error by {current_user.realname}: {err}")
    flash(f"Неочікувана помилка при GET запиту на сторінці /upload_redirects! Дивіться логи!", 'alert alert-danger')
    return redirect("/",302)
