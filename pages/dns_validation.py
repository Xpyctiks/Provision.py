from flask import render_template,request,redirect,flash,Blueprint,current_app
from flask_login import login_required,current_user
import logging,os
from db.database import Provision_templates
from functions.provision import start_autoprovision
from functions.pages_forms import *

dns_validation_bp = Blueprint("dns_validation", __name__)
@dns_validation_bp.route("/dns_validation", methods=['GET','POST'])
@login_required
def dns_validation():
    return render_template("template-dns_validation.html")