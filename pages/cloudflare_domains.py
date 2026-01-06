from flask import render_template,request,redirect,flash,Blueprint
from flask_login import login_required,current_user
import logging,asyncio,requests
from db.database import Domain_account, Cloudflare
from functions.send_to_telegram import send_to_telegram
from functions.site_actions import normalize_domain

cloudflare_domains_bp = Blueprint("cloudflare_domains", __name__)
@cloudflare_domains_bp.route("/cloudflare_domains", methods=['GET'])
@login_required
def cloudflare_domains():
    pass