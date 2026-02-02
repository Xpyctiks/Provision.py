from flask import redirect,flash
from flask_login import login_required,current_user
from functools import wraps
import logging
from functions.send_to_telegram import send_to_telegram

def rights_required(min_level):
  def decorator(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
      if current_user.rights < min_level:
        logging.warning(f"Attempt to get into admin panel functions by not privileged user {current_user.realname}")
        send_to_telegram(f"Attempt to get into admin panel functions by not privileged user {current_user.realname}",f"🚒Provision warning:")
        flash('У вас немає прав тут бути!', 'alert alert-danger')
        return redirect("/",301)
      return func(*args, **kwargs)
    return wrapper
  return decorator
