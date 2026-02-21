import os,logging,shutil,subprocess,sqlite3
from functions.certificates import cloudflare_certificate
from functions.provision_func import setupNginx
from functions.site_actions import normalize_domain
import functions.variables
from functions.tld import tld

def start_clone(domain: str, source_site: str, selected_account: str, selected_server: str, realname: str,  web_folder: str, its_not_a_subdomain: bool = False) -> bool:
  """Main function to clone any selected site to the new one, keeping all files and settings from the original site"""
  try:
    domain = str(normalize_domain(domain))
    logging.info(f"---------------------------Starting clone of the site {source_site} to new site {domain} by {realname}----------------------------")
    logging.info(f"Cloudflare account: {selected_account}, IP of the server: {selected_server}")
    dstPath = os.path.join(web_folder,domain)
    srcPath = os.path.join(web_folder,source_site)
    logging.info(f"Src. path: {srcPath}")
    logging.info(f"Dst. path: {dstPath}")
    functions.variables.JOB_ID = f"Autoprovision"
    #First of all starting DNS and certificates check and setup procedure
    if cloudflare_certificate(domain,selected_account,selected_server,its_not_a_subdomain):
        #copying source site to the new destination
        result = shutil.copytree(srcPath, dstPath,dirs_exist_ok=True,symlinks=True)
        if result != dstPath:
          logging.error(f"start_clone(): Error while copying {srcPath} to {dstPath}!")
          return False
        logging.info(f"start_clone(): Copying {srcPath} to {dstPath} is done successfully!")
        #setting git safe value to allow this folder works with git
        finalPath = os.path.join(web_folder,domain)
        if os.path.exists(os.path.join(web_folder,domain,".git")):
          result = subprocess.run(["sudo","git","config","--global", "--add", "safe.directory", f"{finalPath}"], capture_output=True, text=True)
          if result.returncode != 0:
            logging.error(f"start_clone(): Error while git add safe.directory for {finalPath}: {result.stderr}")
          else:
            logging.info("start_clone(): Git add safe directory done successfully!")
        #Set the global variable to the name of the source site. This value will be applied to DB record while setSiteOwner() procedure
        functions.variables.CLONED_FROM = source_site
        #prepare subdomain functions
        if its_not_a_subdomain:
          has_subdomain = "---"
          logging.info("start_clone(): we have forced parameter not_a_subdomain - passing it to setupNginx()")
        else:
          d = tld(domain)
          if bool(d.subdomain):
            has_subdomain = f"{d.domain}.{d.suffix}"
            logging.info("start_clone(): we have detected a subdomain - passing it to setupNginx()")
          else:
            has_subdomain = "---"
            logging.info("start_clone(): we have not detected a subdomain - passing it to setupNginx()")
        if not setupNginx(domain+".zip",has_subdomain):
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
            logging.info(f"start_clone(): SQLite3 database of the clonned site {DB_PATH} updated successfully!")
        else:
          logging.error(f"start_clone(): SQLite3 database of the clonned site {DB_PATH} is not exists! Skipping update...")
        return True
    else:
      return False
  except Exception as msg:
    logging.error(f"start_clone() general error: {msg}")
    return False
