from flask import Blueprint
from .projects import projects_bp
from .requests import requests_bp
from .proxy import proxy_bp
from .resender import resender_bp
from .agent import agent_bp

# Create main API blueprint
api_bp = Blueprint('api', __name__, url_prefix='/api')

# Register sub-blueprints
api_bp.register_blueprint(projects_bp, url_prefix='/projects')
api_bp.register_blueprint(proxy_bp, url_prefix='/proxy')
api_bp.register_blueprint(agent_bp, url_prefix='/agent')

# Register requests blueprint with project_id in URL
# This creates routes like /api/projects/<project_id>/requests
def register_requests_blueprint(app):
    """Register requests blueprint with project_id parameter"""
    app.register_blueprint(
        requests_bp,
        url_prefix='/api/projects/<int:project_id>/requests'
    )


# Register resender blueprint with project_id in URL
# This creates routes like /api/projects/<project_id>/resender/tabs
def register_resender_blueprint(app):
    """Register resender blueprint with project_id parameter"""
    app.register_blueprint(
        resender_bp,
        url_prefix='/api/projects/<int:project_id>/resender'
    )
