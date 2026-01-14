from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from src import db, state, proxy_manager, browser_manager
from src.api import api_bp, register_requests_blueprint, register_resender_blueprint
import os
import atexit
import signal
import sys
from pathlib import Path


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Enable CORS for frontend connection
    # In Docker/production, allow all origins for flexibility
    cors_origins = os.environ.get('CORS_ORIGINS', 'http://localhost:5173,http://localhost:5174,http://localhost:8080').split(',')
    CORS(app, resources={
        r"/api/*": {
            "origins": cors_origins,
            "methods": ["GET", "POST", "PUT", "DELETE"],
            "allow_headers": ["Content-Type"]
        },
        r"/health": {
            "origins": cors_origins,
            "methods": ["GET"],
            "allow_headers": ["Content-Type"]
        }
    })
    
    # Initialize database
    db.init_db()
    
    # Ensure there's a default project
    default_project = db.ensure_default_project()
    
    # Set it as current if no current project
    if state.get_current_project() is None:
        state.set_current_project(default_project['id'])
        proxy_manager.save_active_project(default_project['name'])
        print(f"📁 Default project set: {default_project['name']}")
    
    # Register blueprints
    app.register_blueprint(api_bp)
    register_requests_blueprint(app)
    register_resender_blueprint(app)
    
    # Serve frontend static files (for Docker/production)
    # This should be registered last so API routes take precedence
    # Check both possible locations: Docker (/app/frontend/dist) and local dev (../frontend/dist)
    app_dir = Path(__file__).parent
    frontend_dist = app_dir / 'frontend' / 'dist'
    if not frontend_dist.exists():
        frontend_dist = app_dir.parent / 'frontend' / 'dist'
    if frontend_dist.exists():
        @app.route('/', defaults={'path': ''})
        @app.route('/<path:path>')
        def serve_frontend(path):
            """Serve frontend static files (only for non-API routes)"""
            # Serve static files (JS, CSS, images, etc.) if they exist
            if path:
                static_file = frontend_dist / path
                if static_file.exists() and static_file.is_file():
                    return send_from_directory(str(frontend_dist), path)
            # Serve index.html for all other routes (SPA routing)
            return send_from_directory(str(frontend_dist), 'index.html')
    
    # Health check route
    @app.route('/health', methods=['GET'])
    def health():
        """Health check endpoint"""
        proxy_status = 'running' if proxy_manager.is_proxy_running() else 'stopped'
        return jsonify({
            'status': 'healthy',
            'proxy_status': proxy_status,
            'proxy_port': proxy_manager.get_proxy_port()
        }), 200
    
    return app


def signal_handler(sig, frame):
    """Handle shutdown signals"""
    print("\n🛑 Shutting down gracefully...")
    proxy_manager.cleanup_proxy()
    sys.exit(0)


def main():
    """Run the Flask application"""
    # Register cleanup handlers
    atexit.register(proxy_manager.cleanup_proxy)
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start Flask app
    app = create_app()
    port = int(os.environ.get('PORT', 5000))
    print(f"🌐 Starting Flask server on http://localhost:{port}")
    print(f"🔗 CORS enabled for frontend at http://localhost:5173")
    print(f"📡 Proxy API available at /api/proxy")
    app.run(host='0.0.0.0', port=port, debug=True, use_reloader=False)


if __name__ == "__main__":
    main()
