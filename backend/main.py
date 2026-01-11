from flask import Flask, jsonify
from flask_cors import CORS
from src import db, state, proxy_manager, browser_manager
from src.api import api_bp, register_requests_blueprint, register_resender_blueprint
import os
import atexit
import signal
import sys


def create_app():
    """Create and configure the Flask application"""
    app = Flask(__name__)
    
    # Enable CORS for frontend connection
    CORS(app, resources={
        r"/api/*": {
            "origins": ["http://localhost:5173", "http://localhost:5174", "http://localhost:8080"],
            "methods": ["GET", "POST", "PUT", "DELETE"],
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
