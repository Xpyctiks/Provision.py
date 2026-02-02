import tldextract,os,logging
from pathlib import Path
from functions.send_to_telegram import send_to_telegram

try:
  root = Path(__file__).resolve().parents[1]
  cache_dir = os.path.join(root,".tldcache")
  if not os.path.exists(cache_dir):
    logging.info(f"TLDExtract cache dir is not exists. Creating {cache_dir}...")
    os.makedirs(cache_dir, exist_ok=True)
except Exception as err:
  logging.error(f"tld.py general error: {err}")
  send_to_telegram(f"tld.py general error: {err}",f"🚒Provision validation page error:")

tld = tldextract.TLDExtract(cache_dir=cache_dir,fallback_to_snapshot=True)
