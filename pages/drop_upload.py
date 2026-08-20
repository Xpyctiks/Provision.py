import logging
from flask import redirect,request,flash,Blueprint
from flask_login import current_user
from functions.rights_required import block_mail_admin
from functions.site_actions import clearCache
from functions.drop_upload_func import deploy_drop_archive

drop_upload_bp = Blueprint("drop_upload", __name__)
@drop_upload_bp.route("/drop_upload/", methods=['POST'])
@block_mail_admin
def do_drop_upload():
  """POST request processor: uploads a zip/tar.gz archive and unpacks it into the site's public/drop folder,
  wiping the folder clean first if it already exists."""
  try:
    sitename = (request.form.get("sitename") or "").strip()
    file = request.files.get("archiveFile")
    if not sitename or not file or not file.filename:
      logging.error(f"do_drop_upload(): sitename or archiveFile has not been received in request (by {current_user.realname})!")
      flash('Помилка! Не обрано сайт або файл архіву!', 'alert alert-danger')
      return redirect("/",302)
    logging.info(f"----------------------------------Drop archive upload requested by {current_user.realname}, IP:{request.remote_addr}, Real-IP:{request.headers.get('X-Real-IP', '-.-.-.-')}---------------------------------------------")
    ok, msg = deploy_drop_archive(sitename, file, file.filename, current_user.realname)
    if ok:
      flash(f'Архів "{file.filename}" успішно завантажено та розпаковано в папку drop сайту {sitename}!', 'alert alert-success')
    else:
      flash(f'Помилка завантаження архіву: {msg}', 'alert alert-danger')
    clearCache()
    return redirect("/",302)
  except Exception as err:
    logging.error(f"do_drop_upload(): general error by {current_user.realname}: {err}")
    flash('Неочікувана помилка при завантаженні архіву, дивіться логи!', 'alert alert-danger')
    return redirect("/",302)
