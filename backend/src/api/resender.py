"""
API endpoints for resender functionality.
"""
from flask import Blueprint, request, jsonify
from .. import db, http_sender
import logging

logger = logging.getLogger(__name__)

resender_bp = Blueprint('resender', __name__)


@resender_bp.route('/tabs', methods=['GET'])
def get_resender_tabs(project_id):
    """Get all resender tabs for a project"""
    try:
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        tabs = db.get_resender_tabs(project_id)
        # Get versions for each tab
        for tab in tabs:
            versions = db.get_resender_versions(project_id, tab['id'])
            tab['versions'] = versions
        
        return jsonify(tabs), 200
    except Exception as e:
        logger.error(f"Error getting resender tabs: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@resender_bp.route('/tabs', methods=['POST'])
def create_resender_tab(project_id):
    """Create a new resender tab"""
    try:
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        data = request.get_json() or {}
        name = data.get('name', 'New Tab')
        host = data.get('host', 'example.com')
        port = data.get('port', '443')
        
        tab_id = db.create_resender_tab(project_id, name, host, port)
        tab = db.get_resender_tab(project_id, tab_id)
        tab['versions'] = []
        
        return jsonify(tab), 201
    except Exception as e:
        logger.error(f"Error creating resender tab: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@resender_bp.route('/tabs/<int:tab_id>', methods=['GET'])
def get_resender_tab(project_id, tab_id):
    """Get a specific resender tab"""
    try:
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        tab = db.get_resender_tab(project_id, tab_id)
        if not tab:
            return jsonify({'error': 'Tab not found'}), 404
        
        versions = db.get_resender_versions(project_id, tab_id)
        tab['versions'] = versions
        
        return jsonify(tab), 200
    except Exception as e:
        logger.error(f"Error getting resender tab: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@resender_bp.route('/tabs/<int:tab_id>', methods=['PUT'])
def update_resender_tab(project_id, tab_id):
    """Update a resender tab (name, host, port)"""
    try:
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        tab = db.get_resender_tab(project_id, tab_id)
        if not tab:
            return jsonify({'error': 'Tab not found'}), 404
        
        data = request.get_json() or {}
        updated_tab = db.update_resender_tab(
            project_id,
            tab_id,
            name=data.get('name'),
            host=data.get('host'),
            port=data.get('port')
        )
        
        versions = db.get_resender_versions(project_id, tab_id)
        updated_tab['versions'] = versions
        
        return jsonify(updated_tab), 200
    except Exception as e:
        logger.error(f"Error updating resender tab: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@resender_bp.route('/tabs/<int:tab_id>', methods=['DELETE'])
def delete_resender_tab(project_id, tab_id):
    """Delete a resender tab"""
    try:
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        tab = db.get_resender_tab(project_id, tab_id)
        if not tab:
            return jsonify({'error': 'Tab not found'}), 404
        
        db.delete_resender_tab(project_id, tab_id)
        return jsonify({'message': 'Tab deleted successfully'}), 200
    except Exception as e:
        logger.error(f"Error deleting resender tab: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@resender_bp.route('/tabs/<int:tab_id>/send', methods=['POST'])
def send_resender_request(project_id, tab_id):
    """Send a request from a resender tab"""
    try:
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        tab = db.get_resender_tab(project_id, tab_id)
        if not tab:
            return jsonify({'error': 'Tab not found'}), 404
        
        data = request.get_json() or {}
        raw_request = data.get('raw_request', '')
        
        if not raw_request:
            return jsonify({'error': 'raw_request is required'}), 400
        
        # Get host and port from tab
        host = tab.get('host', 'example.com')
        port = tab.get('port', '443')
        
        # Parse host to detect protocol (http:// or https://)
        # If host starts with http:// or https://, extract protocol and actual hostname
        use_https = None
        if host.startswith('http://'):
            use_https = False
            # Extract hostname from http://hostname or http://hostname:port
            host = host[7:]  # Remove 'http://' prefix
            if ':' in host:
                # Extract port if present in host (e.g., http://hostname:5001)
                host_parts = host.rsplit(':', 1)
                host = host_parts[0]
                port = host_parts[1]
        elif host.startswith('https://'):
            use_https = True
            # Extract hostname from https://hostname or https://hostname:port
            host = host[8:]  # Remove 'https://' prefix
            if ':' in host:
                # Extract port if present in host (e.g., https://hostname:8443)
                host_parts = host.rsplit(':', 1)
                host = host_parts[0]
                port = host_parts[1]
        else:
            # No protocol in host, determine from port (default True, unless port is 80)
            use_https = port != '80'
        
        # Send the request
        result = http_sender.send_raw_http_request(raw_request, host, port, use_https)
        
        # Save the version to database
        version_id = db.create_resender_version(
            project_id,
            tab_id,
            raw_request,
            result.get('raw_response')
        )
        
        # Get the created version
        version = db.get_resender_version(project_id, tab_id, version_id)
        
        return jsonify({
            'version': version,
            'status_code': result.get('status_code'),
            'error': result.get('error')
        }), 200
        
    except Exception as e:
        logger.error(f"Error sending resender request: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500


@resender_bp.route('/tabs/<int:tab_id>/versions', methods=['GET'])
def get_resender_versions(project_id, tab_id):
    """Get all versions for a resender tab"""
    try:
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        tab = db.get_resender_tab(project_id, tab_id)
        if not tab:
            return jsonify({'error': 'Tab not found'}), 404
        
        versions = db.get_resender_versions(project_id, tab_id)
        return jsonify(versions), 200
    except Exception as e:
        logger.error(f"Error getting resender versions: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
