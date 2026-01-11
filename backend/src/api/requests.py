from flask import Blueprint, request, jsonify
from .. import db

requests_bp = Blueprint('requests', __name__)


@requests_bp.route('', methods=['GET'])
def get_project_requests(project_id):
    """Get all requests for a specific project"""
    try:
        # Verify project exists
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        limit = request.args.get('limit', type=int)  # No default limit
        requests = db.get_project_requests(project_id, limit)
        return jsonify(requests), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@requests_bp.route('/<int:request_id>', methods=['GET'])
def get_project_request(project_id, request_id):
    """Get a specific request from a project"""
    try:
        # Verify project exists
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        req = db.get_project_request(project_id, request_id)
        if not req:
            return jsonify({'error': 'Request not found'}), 404
        
        return jsonify(req), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@requests_bp.route('', methods=['POST'])
def add_project_request(project_id):
    """Add a new request to a project"""
    try:
        # Verify project exists
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        data = request.get_json()
        
        # Validation
        if not data or 'method' not in data or 'url' not in data:
            return jsonify({'error': 'Method and URL are required'}), 400
        
        request_id = db.add_request_to_project(
            project_id,
            method=data['method'],
            url=data['url'],
            headers=data.get('headers'),
            body=data.get('body'),
            response_status=data.get('response_status'),
            response_headers=data.get('response_headers'),
            response_body=data.get('response_body')
        )
        
        # Get the created request
        created_request = db.get_project_request(project_id, request_id)
        return jsonify(created_request), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@requests_bp.route('/<int:request_id>', methods=['DELETE'])
def delete_project_request(project_id, request_id):
    """Delete a request from a project"""
    try:
        # Verify project exists
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Verify request exists
        req = db.get_project_request(project_id, request_id)
        if not req:
            return jsonify({'error': 'Request not found'}), 404
        
        db.delete_project_request(project_id, request_id)
        
        return jsonify({'message': 'Request deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@requests_bp.route('', methods=['DELETE'])
def clear_project_requests(project_id):
    """Clear all requests from a project"""
    try:
        # Verify project exists
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        db.clear_project_requests(project_id)
        
        return jsonify({'message': 'All requests cleared successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
