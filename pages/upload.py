from flask import render_template,request,redirect,flash,Blueprint
from flask_login import current_user, login_required
import logging,asyncio,subprocess,os,pathlib
from functions.send_to_telegram import send_to_telegram
from werkzeug.utils import secure_filename

upload_bp = Blueprint("upload", __name__)
@upload_bp.route("/upload", methods=['GET','POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        if 'fileUpload[]' not in request.files:
            logging.error(f"Upload by {current_user.realname}: No <fileUpload> name in the request fields")
            flash('Завантаження: Файлу <fileUpload> немає в заголовках запиту', 'alert alert-danger')
            return redirect("/upload",301)
        else:
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
            flash('Файл(и) успішно завантажені!', 'alert alert-success')
            logging.info(f"Upload by {current_user.realname} IP:{request.remote_addr}: Files {nameList} uploaded to {project_root} successfully")
            asyncio.run(send_to_telegram(f"Files {nameList} uploaded successfully",f"⬆Provision\nUpload by {current_user.realname}:"))
            #now call this script from shell to start deploy procedure
            executive = os.path.join(project_root,"main.py")
            subprocess.run([executive, 'main'])
            return redirect("/",301)
    #if this is GET request - show page
    if request.method == 'GET':
        return render_template("template-upload.html")
