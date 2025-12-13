import os,asyncio,logging,shutil
from functions.send_to_telegram import send_to_telegram
from functions.certificates import cloudflare_certificate
from functions.provision import setupNginx
from flask import current_app,flash
import functions.variables

def start_clone(domain: str, source_site: str, selected_account: str, selected_server: str, realname: str):
    logging.info(f"---------------------------Starting clone of the site {source_site} to new site {domain} by {realname}----------------------------")
    logging.info(f"Cloudflare account: {selected_account}, IP of the server: {selected_server}")
    dstPath = os.path.join(current_app.config["WEB_FOLDER"],domain)
    srcPath = os.path.join(current_app.config["WEB_FOLDER"],source_site)
    logging.info(f"Src. path: {srcPath}")
    logging.info(f"Dst. path: {dstPath}")
    functions.variables.JOB_ID = f"Autoprovision"
    #First of all starting DNS and certificates check and setup procedure
    if cloudflare_certificate(domain,selected_account,selected_server):
        try:
            result = shutil.copytree(srcPath, dstPath,dirs_exist_ok=True,symlinks=True)
            if result != dstPath:
                logging.error(f"Error while copying {srcPath} to {dstPath}!")
                asyncio.run(send_to_telegram(f"Error while copying {srcPath} to {dstPath}!",f"🚒Provision clone error:"))
                flash('Помилка при копіюванні {srcPath} в {dstPath}','alert alert-danger')
                return False
            logging.info(f"Copying {srcPath} to {dstPath} is done successfully!")
            #Set the global variable to the name of the source site. This value will be applied to DB record while setSiteOwner() procedure
            functions.variables.CLONED_FROM = source_site
            setupNginx(domain+".zip")
            return True
        except Exception as msg:
            logging.error(f"start_clone() general error: {msg}")
            asyncio.run(send_to_telegram(f"start_clone() general error: {msg}",f"🚒Provision clone error:"))
            return False
    else:
        return False
