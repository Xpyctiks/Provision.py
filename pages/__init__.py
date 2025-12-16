from flask import Blueprint
from .action import action_bp
from .clone import clone_bp
from .login import login_bp
from .logout import logout_bp
from .logs import logs_bp
from .provision import provision_bp
from .redirects_manager import redirects_bp
from .root import root_bp
from .upload import upload_bp
from .uploadredirects import uploadredir_bp
from .validate import validate_bp


blueprint = Blueprint("main", __name__)
blueprint.register_blueprint(action_bp)
blueprint.register_blueprint(clone_bp)
blueprint.register_blueprint(login_bp)
blueprint.register_blueprint(logout_bp)
blueprint.register_blueprint(logs_bp)
blueprint.register_blueprint(provision_bp)
blueprint.register_blueprint(redirects_bp)
blueprint.register_blueprint(root_bp)
blueprint.register_blueprint(upload_bp)
blueprint.register_blueprint(uploadredir_bp)
blueprint.register_blueprint(validate_bp)
