from flask import Blueprint
from .projects import projects_bp
from .requests import requests_bp
from .proxy import proxy_bp
from .resender import resender_bp
from .agent import agent_bp
from .findings import findings_bp

api_bp = Blueprint('api', __name__, url_prefix='/api')

api_bp.register_blueprint(projects_bp, url_prefix='/projects')
api_bp.register_blueprint(proxy_bp, url_prefix='/proxy')
api_bp.register_blueprint(agent_bp, url_prefix='/agent')


def register_requests_blueprint(app):
    app.register_blueprint(requests_bp, url_prefix='/api/projects/<int:project_id>/requests')


def register_resender_blueprint(app):
    app.register_blueprint(resender_bp, url_prefix='/api/projects/<int:project_id>/resender')


def register_findings_blueprint(app):
    app.register_blueprint(findings_bp, url_prefix='/api/projects/<int:project_id>/findings')
