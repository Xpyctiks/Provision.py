import argparse
from functions.cli_func_account import *
from functions.cli_func_cloudflare import *
from functions.cli_func_owner import *
from functions.cli_func_servers import *
from functions.cli_func_template import *
from functions.cli_func_user import *
from functions.cli_func_settings import *
from main import with_app_context
import click

@click.group(context_settings=dict(help_option_names=["-h", "--help"]))
def show_cli():
  """1000 sites provision system CLI"""
  pass

# SET
@show_cli.group()
def set():
  """Set configuration values"""
  pass

@set.command()
@click.argument("chatid")
@with_app_context
def chat(chatid):
  """Set Telegram Chat ID"""
  set_telegramChat(chatid)

@set.command()
@click.argument("token")
@with_app_context
def token(token):
  """Set Telegram bot token"""
  set_telegramToken(token)

@set.command()
@click.argument("path")
@with_app_context
def log(path):
  """Set log path"""
  set_logpath(path)

@set.command()
@click.argument("path")
@with_app_context
def webfolder(path):
  """Set web root folder"""
  set_webFolder(path)

@set.command()
@click.argument("path")
@with_app_context
def nginxpath(path):
  """Set nginx main config path"""
  set_nginxPath(path)

# USER
@show_cli.group()
def user():
  """User management"""
  pass

@user.command("add")
@click.argument("username")
@click.argument("realname")
@click.argument("password")
@with_app_context
def user_add(username, realname, password):
  """Add new user"""
  register_user(username, realname, password)

@user.command("del")
@click.argument("username")
@with_app_context
def user_del(username):
  """Delete user"""
  delete_user(username)

@user.command("setpwd")
@click.argument("username")
@click.argument("password")
@with_app_context
def user_setpwd(username, password):
  """Change user password"""
  update_user(username, password)

@user.command("setadmin")
@click.argument("username")
@with_app_context
def user_setadmin(username):
  """Grant admin rights"""
  make_admin_user(username)

@user.command("unsetadmin")
@click.argument("username")
@with_app_context
def user_unsetadmin(username):
  """Remove admin rights"""
  remove_admin_user(username)

# TEMPLATES
@show_cli.group()
def templates():
  """Templates management"""
  pass

@templates.command("add")
@click.argument("name")
@click.argument("repo")
@with_app_context
def templates_add(name, repo):
  add_template(name, repo)

@templates.command("del")
@click.argument("name")
@with_app_context
def templates_del(name):
  del_template(name)

@templates.command("upd")
@click.argument("name")
@click.argument("repo")
@with_app_context
def templates_upd(name, repo):
  upd_template(name, repo)

@templates.command("default")
@click.argument("name")
@with_app_context
def templates_default(name):
  default_template(name)

# SHOW
@show_cli.group()
def show():
  """Show information"""
  pass

@show.command("users")
@with_app_context
def show_users_cmd():
  show_users()

@show.command("config")
@with_app_context
def show_config_cmd():
  show_config()

@show.command("templates")
@with_app_context
def show_templates_cmd():
  show_templates()

@show.command("cloudflare")
@with_app_context
def show_cloudflare_cmd():
  show_cloudflare()

@show.command("servers")
@with_app_context
def show_servers_cmd():
  show_servers()

@show.command("owners")
@with_app_context
def show_owners_cmd():
  show_owners()

@show.command("accounts")
@with_app_context
def show_accounts_cmd():
  show_accounts()
