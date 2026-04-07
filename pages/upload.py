import logging
import os
import pathlib
from flask import render_template,request,redirect,flash,Blueprint
from flask_login import current_user, login_required
from functions.send_to_telegram import send_to_telegram
from werkzeug.utils import secure_filename
from functions.pages_forms import *
from functions.provision_func import *
from functions.site_actions import is_admin,clearCache

upload_bp = Blueprint("upload", __name__)
@upload_bp.route("/upload/", methods=['POST'])
@login_required
def upload_file():
  """POST request processor: getting uploaded zip archive and deploys the site from it."""
  try:
    if 'fileUpload[]' not in request.files:
      logging.error(f"upload_file(): Upload by {current_user.realname}: No <fileUpload> name in the request fields")
      send_to_telegram(f"Upload by {current_user.realname}: No <fileUpload> name in the request fields",f"🚒Provision upload page:")
      flash('Завантаження: Файлу <fileUpload> немає в заголовках запиту', 'alert alert-danger')
      return redirect("/",302)
    #check if we have all necessary data received
    elif not request.form.get('selected_server') or not request.form.get('selected_account') or not request.form.get('buttonSubmit'):
      flash('Помилка! Якісь важливі параметри не передані серверу!','alert alert-danger')
      logging.error(f"upload_file(): error! some of important parameters has not been sent!")
      send_to_telegram(f"upload_file(): some of the important parameters has not been received!",f"🚒Provision upload page:")
      return redirect("/",302)
    #starts main provision actions
    else:
      if not request.form.get("selected_account") or not request.form.get("selected_server"):
        logging.error(f"upload_file(): selected_account or selected_server has not been received in request!")
        send_to_telegram(f"upload_file(): selected_account or selected_server has not been received in request!",f"🚒Provision job error({functions.variables.JOB_ID}):")
        flash('Загальна помилки: деякі важливі параметри не були отримані сервером! Дивіться логи.', 'alert alert-danger')
        return redirect("/",302)
      selected_account = request.form.get("selected_account")
      selected_server = request.form.get("selected_server")
      logging.info(f"----------------------------------Files Upload by {current_user.realname}, IP:{request.remote_addr}, Real-IP:{request.headers.get('X-Real-IP', '-.-.-.-')}---------------------------------------------")
      #get name of the parent directory for the whole project
      current_file = pathlib.Path(__file__)
      directory = current_file.resolve().parent
      project_root = directory.parent
      #get the list of files. saving them to the current folder. Redirect to /
      files = request.files.getlist("fileUpload[]")
      nameList = ""
      for file in files:
        if file.filename:
          filename = os.path.join(project_root,secure_filename(file.filename))
          file.save(f"{filename}")
          nameList += filename+","
          logging.info(f">File {filename} uploaded and saved.")
      logging.info(f"upload_file(): All files uploaded to {project_root} successfully!")
      if not start_provision(selected_account,selected_server,current_user.realname):
        finishJob(filename,"",emerg_shutdown=True)
        flash(f"Розгортання завершилось з помилками! Дивіться логи!", 'alert alert-danger')
        clearCache()
        return redirect("/",302)
      finishJob(filename,"",selected_account,selected_server,current_user.realname)
      logging.info(f"upload_file(): master function finished successfully!")
      flash(f"Розгортання успішно завершено!", 'alert alert-success')
      clearCache()
      return redirect("/",302)
  except Exception as err:
    logging.error(f"upload_file(): Upload page general error: {err}")
    flash(f"Неочікувана помилка на сторінці ручного розгортання, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)

@upload_bp.route("/upload/", methods=['GET'])
@login_required
def show_upload_page():
  """GET request: show /upload page."""
  try:
    #parsing git repositories available
    templates_list, first_template = loadTemplatesList()
    #parsing Cloudflare accounts available
    cf_list, first_cf = loadClodflareAccounts()
    #parsing Servers accounts available
    server_list, first_server = loadServersList()
    return render_template("template-upload.html",source_site=(request.args.get('source_site') or 'Error').strip(),templates=templates_list,first_template=first_template,cf_list=cf_list,first_cf=first_cf,first_server=first_server,server_list=server_list,admin_panel=is_admin())
  except Exception as err:
    logging.error(f"show_upload_page(): Upload page general render error: {err}")
    flash(f"Неочікувана помилка на сторінці ручного розгортання, дивіться логи!", 'alert alert-danger')
    return redirect("/",302)
