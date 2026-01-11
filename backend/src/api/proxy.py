from flask import Blueprint, jsonify
from .. import proxy_manager, browser_manager

proxy_bp = Blueprint('proxy', __name__)


@proxy_bp.route('/status', methods=['GET'])
def get_proxy_status():
    """Get the current proxy status"""
    try:
        is_running = proxy_manager.is_proxy_running()
        port = proxy_manager.get_proxy_port()
        
        return jsonify({
            'running': is_running,
            'port': port
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@proxy_bp.route('/start', methods=['POST'])
def start_proxy():
    """Start the proxy server"""
    try:
        if proxy_manager.is_proxy_running():
            return jsonify({
                'message': 'Proxy is already running',
                'running': True,
                'port': proxy_manager.get_proxy_port()
            }), 200
        
        success = proxy_manager.start_proxy()
        
        if success:
            return jsonify({
                'message': 'Proxy started successfully',
                'running': True,
                'port': proxy_manager.get_proxy_port()
            }), 200
        else:
            return jsonify({
                'error': 'Failed to start proxy. Make sure mitmproxy is installed.',
                'running': False
            }), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@proxy_bp.route('/stop', methods=['POST'])
def stop_proxy():
    """Stop the proxy server"""
    try:
        if not proxy_manager.is_proxy_running():
            return jsonify({
                'message': 'Proxy is not running',
                'running': False
            }), 200
        
        success = proxy_manager.stop_proxy()
        
        if success:
            return jsonify({
                'message': 'Proxy stopped successfully',
                'running': False
            }), 200
        else:
            return jsonify({
                'error': 'Failed to stop proxy',
                'running': True
            }), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@proxy_bp.route('/settings', methods=['GET'])
def get_proxy_settings():
    """Get proxy settings (port, status, etc.)"""
    try:
        is_running = proxy_manager.is_proxy_running()
        port = proxy_manager.get_proxy_port()
        
        return jsonify({
            'port': port,
            'running': is_running,
            'host': 'localhost',
            'url': f'http://localhost:{port}'
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@proxy_bp.route('/browser/start', methods=['POST'])
def start_browser():
    """Start the browser with proxy settings"""
    try:
        success = browser_manager.start_browser()
        
        if success:
            return jsonify({
                'message': 'Browser started successfully',
                'running': True
            }), 200
        else:
            return jsonify({
                'error': 'Failed to start browser. Make sure the proxy is running.',
                'running': False
            }), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@proxy_bp.route('/intercept', methods=['GET'])
def get_intercept_status():
    """Get intercept state"""
    try:
        enabled = proxy_manager.get_intercept_enabled()
        return jsonify({
            'enabled': enabled
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@proxy_bp.route('/intercept', methods=['POST'])
def set_intercept_status():
    """Set intercept state"""
    try:
        from flask import request
        data = request.get_json() or {}
        enabled = data.get('enabled', False)
        
        success = proxy_manager.set_intercept_enabled(enabled)
        
        if success:
            return jsonify({
                'message': f'Intercept {"enabled" if enabled else "disabled"}',
                'enabled': enabled
            }), 200
        else:
            return jsonify({
                'error': 'Failed to set intercept state'
            }), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@proxy_bp.route('/intercepted', methods=['GET'])
def get_intercepted_flows():
    """Get list of intercepted flow IDs"""
    try:
        flow_ids = proxy_manager.get_intercepted_flows()
        return jsonify({
            'flow_ids': flow_ids
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@proxy_bp.route('/intercepted/<flow_id>/forward', methods=['POST'])
def forward_intercepted_flow(flow_id):
    """Forward an intercepted flow (optionally with edited request)"""
    try:
        from flask import request
        data = request.get_json() or {}
        edited_request = data.get('edited_request')
        
        success = proxy_manager.forward_intercepted_flow(flow_id, edited_request)
        
        if success:
            return jsonify({
                'message': 'Flow forwarded successfully',
                'flow_id': flow_id
            }), 200
        else:
            return jsonify({
                'error': 'Failed to forward flow'
            }), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@proxy_bp.route('/intercepted/<flow_id>/drop', methods=['POST'])
def drop_intercepted_flow(flow_id):
    """Drop an intercepted flow (kill it without forwarding)"""
    try:
        success = proxy_manager.drop_intercepted_flow(flow_id)
        
        if success:
            return jsonify({
                'message': 'Flow dropped successfully',
                'flow_id': flow_id
            }), 200
        else:
            return jsonify({
                'error': 'Failed to drop flow'
            }), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500
