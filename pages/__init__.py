from flask import Blueprint
from .login import login_bp
from .logout import logout_bp
from .upload import upload_bp
from .action import action_bp
from .root import root_bp
from .redirects_manager import redirects_bp
from .uploadredirects import uploadredir_bp

blueprint = Blueprint("main", __name__)
blueprint.register_blueprint(login_bp)
blueprint.register_blueprint(logout_bp)
blueprint.register_blueprint(upload_bp)
blueprint.register_blueprint(action_bp)
blueprint.register_blueprint(root_bp)
blueprint.register_blueprint(redirects_bp)
blueprint.register_blueprint(uploadredir_bp)
