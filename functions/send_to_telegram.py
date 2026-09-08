import logging
import httpx
import threading
from flask import current_app

def send_to_telegram_func(message: str, subject: str = "Provision", chatid: str = "", token: str = "" ) -> None:
  """Sends messages via Telegram if TELEGRAM_CHATID and TELEGRAM_TOKEN are both set. Requires "message" parameters and can accept "subject" """
  try:
    if not chatid or not token:
      logging.info("!!! Telegram ChatID or/and Token is not set...")
      return
    data = {
      "chat_id": chatid,
      "text": f"{subject}\n{message}",
    }
    with httpx.Client(timeout=5) as client:
      response = client.post(f"https://api.telegram.org/bot{token}/sendMessage",json=data)
      if response.status_code != 200:
        logging.error(f"Telegram bot error! Status: {response.status_code} Body: {response.text}")
  except Exception as err:
    logging.error(f"Error while sending message to Telegram: {err}")

def send_to_telegram(message: str, subject: str = "Provision"):
  chatid = current_app.config.get("TELEGRAM_CHATID","")
  token = current_app.config.get("TELEGRAM_TOKEN","")
  threading.Thread(target=send_to_telegram_func,args=(message, subject, chatid, token),daemon=True).start()

def send_job_report(message: str, subject: str = "Provision"):
  """Same as send_to_telegram(), but only actually sends when Settings.sendJobDoneReports is enabled
  (default True). Use this only for routine "job finished successfully" progress reports - errors,
  security warnings and failed logins must always go through send_to_telegram() directly, regardless
  of this setting."""
  if not current_app.config.get("SEND_JOB_DONE_REPORTS", True):
    logging.info(f"send_job_report(): sendJobDoneReports is disabled - suppressing report: {subject} {message}")
    return
  send_to_telegram(message, subject)
