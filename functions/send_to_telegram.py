import logging,httpx,threading
from flask import current_app

def send_to_telegram_func(message: str, subject: str = "Provision", ) -> None:
  """Sends messages via Telegram if TELEGRAM_CHATID and TELEGRAM_TOKEN are both set. Requires "message" parameters and can accept "subject" """
  try:
    chatid = current_app.config.get("TELEGRAM_CHATID","")
    token = current_app.config.get("TELEGRAM_TOKEN","")
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
  threading.Thread(target=send_to_telegram_func,args=(message, subject),daemon=True).start()
