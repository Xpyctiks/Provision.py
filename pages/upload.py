from flask import render_template,request,redirect,flash,Blueprint
from flask_login import current_user, login_required
import logging,asyncio,subprocess,os
from functions.send_to_telegram import send_to_telegram
from werkzeug.utils import secure_filename

upload_bp = Blueprint("upload", __name__)
@upload_bp.route("/upload", methods=['GET','POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        #check if fileUpload[] is in the request
        if 'fileUpload[]' not in request.files:
            logging.error(f"Upload by {current_user.realname}: No <fileUpload> name in the request fields")
            flash('Upload: No <fileUpload> in the request fields', 'alert alert-danger')
            return redirect("/upload",301)
        else:
            #get the list of files. saving them to the current folder. Redirect to /
            files = request.files.getlist("fileUpload[]")
            nameList = ""
            for file in files:
                if file.filename:
                    filename = os.path.join(os.path.abspath(os.path.dirname(__file__)),secure_filename(file.filename))
                    file.save(f"{filename}")
                    nameList += filename+","
            flash('File(s) uploaded successfully!', 'alert alert-success')
            logging.info(f"Upload by {current_user.realname}: Files {nameList} uploaded successfully")
            asyncio.run(send_to_telegram(f"⬆Provision\nUpload by {current_user.realname}:",f"Files {nameList} uploaded successfully"))
            #now call this script from shell to start deploy procedure
            subprocess.run([__file__, 'main'])
            return redirect("/",301)
    #if this is GET request - show page
    if request.method == 'GET':
        return render_template("template-upload.html")