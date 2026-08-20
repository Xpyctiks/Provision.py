import logging
import os
import shutil
import tarfile
import tempfile
import zipfile
from flask import current_app
from werkzeug.utils import secure_filename

ALLOWED_EXTENSIONS = (".zip", ".tar.gz", ".tgz")

def _get_extension(filename: str) -> str:
  """Returns the recognized archive extension (lowercase) for filename, or "" if unsupported."""
  lower = filename.lower()
  for ext in ALLOWED_EXTENSIONS:
    if lower.endswith(ext):
      return ext
  return ""

def _safe_extract_zip(archive_path: str, destination: str):
  """Extracts a zip archive into destination, rejecting any member whose path would escape it (zip-slip protection)."""
  dest_real = os.path.realpath(destination)
  with zipfile.ZipFile(archive_path, 'r') as zip_ref:
    for member in zip_ref.namelist():
      member_real = os.path.realpath(os.path.join(destination, member))
      if member_real != dest_real and not member_real.startswith(dest_real + os.sep):
        raise ValueError(f"Архів містить небезпечний шлях: {member}")
    zip_ref.extractall(destination)

def _safe_extract_targz(archive_path: str, destination: str):
  """Extracts a tar.gz/tgz archive into destination, rejecting any member whose path would escape it (path-traversal protection)."""
  dest_real = os.path.realpath(destination)
  with tarfile.open(archive_path, "r:*") as tar_ref:
    for member in tar_ref.getmembers():
      member_real = os.path.realpath(os.path.join(destination, member.name))
      if member_real != dest_real and not member_real.startswith(dest_real + os.sep):
        raise ValueError(f"Архів містить небезпечний шлях: {member.name}")
    tar_ref.extractall(destination)

def deploy_drop_archive(sitename: str, uploaded_file, original_filename: str, realname: str) -> tuple[bool, str]:
  """Saves an uploaded zip/tar.gz archive to a temp location, wipes the site's public/drop folder (if it
  exists) and unpacks the archive's content into it. Returns (success, message)."""
  tmp_file = None
  try:
    logging.info(f"-----------------------Starting drop archive upload: {original_filename} -> {sitename}/public/drop by {realname}-----------------------")
    ext = _get_extension(original_filename)
    if not ext:
      logging.error(f"deploy_drop_archive(): Unsupported archive format for {original_filename} (site {sitename}, by {realname})")
      return False, "Непідтримуваний формат архіву! Дозволені лише .zip, .tar.gz, .tgz"
    web_folder = current_app.config.get("WEB_FOLDER","")
    if not web_folder or not sitename:
      logging.error("deploy_drop_archive(): WEB_FOLDER variable or sitename is empty!")
      return False, "Внутрішня помилка конфігурації (WEB_FOLDER)"
    site_path = os.path.join(web_folder, sitename)
    if not os.path.isdir(site_path):
      logging.error(f"deploy_drop_archive(): Site folder {site_path} does not exist!")
      return False, f"Сайт {sitename} не знайдено на сервері"
    #save the uploaded file to a temp location first
    safe_name = secure_filename(original_filename) or f"drop_upload{ext}"
    tmp_file = os.path.join(tempfile.gettempdir(), f"{sitename}_{safe_name}")
    uploaded_file.save(tmp_file)
    size = os.path.getsize(tmp_file)
    logging.info(f"deploy_drop_archive(): Archive {original_filename} ({size} bytes) saved to {tmp_file}")
    #wipe drop folder completely (including subfolders) if it already exists, then recreate it
    drop_path = os.path.join(site_path, "public", "drop")
    if os.path.exists(drop_path):
      shutil.rmtree(drop_path)
      logging.info(f"deploy_drop_archive(): Existing drop folder {drop_path} wiped clean")
    os.makedirs(drop_path)
    logging.info(f"deploy_drop_archive(): Drop folder {drop_path} ready")
    #unpack
    if ext == ".zip":
      _safe_extract_zip(tmp_file, drop_path)
    else:
      _safe_extract_targz(tmp_file, drop_path)
    logging.info(f"deploy_drop_archive(): Archive {original_filename} ({size} bytes) uploaded and unpacked to {drop_path} by {realname}")
    return True, "OK"
  except Exception as err:
    logging.error(f"deploy_drop_archive(): general error while deploying archive {original_filename} for site {sitename} by {realname}: {err}")
    return False, str(err)
  finally:
    if tmp_file and os.path.exists(tmp_file):
      os.remove(tmp_file)
      logging.info(f"deploy_drop_archive(): Temporary file {tmp_file} removed")
