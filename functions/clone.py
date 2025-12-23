import os,asyncio,logging,shutil,subprocess,sqlite3
from functions.send_to_telegram import send_to_telegram
from functions.certificates import cloudflare_certificate
from functions.provision import setupNginx,finishJob
from flask import current_app,flash
import functions.variables

def start_clone(domain: str, source_site: str, selected_account: str, selected_server: str, realname: str):
    """Main function to clone any selected site to the new one, keeping all files and settings from the original site"""
    domain = domain.lower()
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
            #setting git safe value to allow this folder works with git
            finalPath = os.path.join(current_app.config["WEB_FOLDER"],domain)
            if os.path.exists(os.path.join(current_app.config["WEB_FOLDER"],domain,".git")):
                result = subprocess.run(["sudo","git","config","--global", "--add", "safe.directory", f"{finalPath}"], capture_output=True, text=True)
                if result.returncode != 0:
                    logging.error(f"Error while git add safe.directory for {finalPath}: {result.stderr}")
                    asyncio.run(send_to_telegram(f"Error while git add safe directory for {finalPath}!",f"🚒Provision clone error:"))
                else:
                    logging.info("Git add safe directory done successfully!")
            #Set the global variable to the name of the source site. This value will be applied to DB record while setSiteOwner() procedure
            functions.variables.CLONED_FROM = source_site
            if not setupNginx(domain+".zip"):
                logging.error("start_clone(): setupNginx() function returned an error!")
                finishJob("",domain,selected_account,selected_server)
                return False
            #the last moment - turn off indexing in Db of the clonned site
            DB_PATH=os.path.join(dstPath,"database","database.db")
            if os.path.exists(DB_PATH):
                with sqlite3.connect(DB_PATH) as conn:
                    cur = conn.cursor()
                    cur.execute("UPDATE settings SET value = '0' WHERE grupa = 'seo' AND name = 'allow_indexing'")
                    if cur.rowcount == 0:
                        cur.execute("INSERT INTO settings (grupa, name, value) VALUES ('seo', 'allow_indexing', '0')")
                    conn.commit()
                    logging.info(f"SQLite3 database of the clonned site {DB_PATH} updated successfully!")
            else:
                logging.error(f"SQLite3 database of the clonned site {DB_PATH} is not exists! Skipping update...")
            finishJob("",domain,selected_account,selected_server)
            return True
        except Exception as msg:
            finishJob("",domain,selected_account,selected_server)
            logging.error(f"start_clone() general error: {msg}")
            asyncio.run(send_to_telegram(f"start_clone() general error: {msg}",f"🚒Provision clone error:"))
            return False
    else:
        finishJob("",domain,selected_account,selected_server)
        return False
