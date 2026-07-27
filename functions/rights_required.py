from flask import redirect,flash
from flask_login import login_required,current_user
from functools import wraps
import logging
from functions.send_to_telegram import send_to_telegram

#rights levels used across the app
USER_RIGHTS = 1
MAIL_ADMIN_RIGHTS = 50
ADMIN_RIGHTS = 255

def rights_required(min_level):
  def decorator(func):
    @wraps(func)
    @login_required
    def wrapper(*args, **kwargs):
      if current_user.rights < min_level:
        logging.warning(f"rights_required(): Attempt to get into admin panel functions by not privileged user {current_user.realname}")
        send_to_telegram(f"Attempt to get into admin panel functions by not privileged user {current_user.realname}",f"🚒Provision warning:")
        flash('У вас немає прав тут бути!', 'alert alert-danger')
        return redirect("/",301)
      return func(*args, **kwargs)
    return wrapper
  return decorator

def block_mail_admin(func):
  """Decorator: forbids the mail-admin role from accessing site-modifying actions (activate/deactivate/delete/update code/clone/create/deploy/redirects/robots.txt)."""
  @wraps(func)
  @login_required
  def wrapper(*args, **kwargs):
    if current_user.rights == MAIL_ADMIN_RIGHTS:
      logging.warning(f"block_mail_admin(): Attempt to access a site-modifying action by mail-admin user {current_user.realname}")
      send_to_telegram(f"Attempt to access a site-modifying action by mail-admin user {current_user.realname}",f"🚒Provision warning:")
      flash('У вас немає прав тут бути!', 'alert alert-danger')
      return redirect("/",301)
    return func(*args, **kwargs)
  return wrapper

def deny_mail_admin_action():
  """For shared dispatcher routes: returns True (and flashes a warning) if the current user is a mail-admin trying to run a site-modifying action."""
  if current_user.rights == MAIL_ADMIN_RIGHTS:
    logging.warning(f"deny_mail_admin_action(): Attempt to run a site-modifying action by mail-admin user {current_user.realname}")
    flash('У вас немає прав тут бути!', 'alert alert-danger')
    return redirect("/",301)
  return False
