from flask import Blueprint

from .login import login_bp
from .logout import logout_bp
from .upload import upload_bp

blueprint = Blueprint("main", __name__)
blueprint.register_blueprint(login_bp)
blueprint.register_blueprint(logout_bp)
blueprint.register_blueprint(upload_bp)