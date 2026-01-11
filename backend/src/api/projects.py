from flask import Blueprint, request, jsonify, send_file
from .. import db, state, proxy_manager
import os
import subprocess
import platform

projects_bp = Blueprint('projects', __name__)


@projects_bp.route('/current', methods=['GET'])
def get_current_project():
    """Get the current active project"""
    try:
        current_id = state.get_current_project()
        if current_id is None:
            return jsonify({'current_project_id': None}), 200
        
        project = db.get_project_by_id(current_id)
        if not project:
            # Project was deleted, clear current
            state.clear_current_project()
            return jsonify({'current_project_id': None}), 200
        
        return jsonify({
            'current_project_id': current_id,
            'project': project
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/current', methods=['POST'])
def set_current_project():
    """Set the current active project"""
    try:
        data = request.get_json()
        project_id = data.get('project_id')
        
        if project_id is None:
            state.clear_current_project()
            proxy_manager.save_active_project(None)
            return jsonify({'message': 'Current project cleared'}), 200
        
        # Verify project exists
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        state.set_current_project(project_id)
        # Update proxy state so it knows which project to record to
        proxy_manager.save_active_project(project['name'])
        
        return jsonify({
            'message': 'Current project set',
            'current_project_id': project_id,
            'project': project
        }), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('', methods=['GET'])
def get_projects():
    """Get all projects"""
    try:
        projects = db.get_all_projects()
        return jsonify(projects), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<int:project_id>', methods=['GET'])
def get_project(project_id):
    """Get a specific project by ID"""
    try:
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        return jsonify(project), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('', methods=['POST'])
def create_project():
    """Create a new project"""
    try:
        data = request.get_json()
        
        # Validation
        if not data or 'name' not in data:
            return jsonify({'error': 'Name is required'}), 400
        
        # Check if project with same name exists
        existing_project = db.get_project_by_name(data['name'])
        if existing_project:
            return jsonify({'error': 'Project with this name already exists'}), 409
        
        # Create new project
        project = db.create_project(
            name=data['name'],
            description=data.get('description', '')
        )
        
        return jsonify(project), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<int:project_id>', methods=['PUT'])
def update_project(project_id):
    """Update an existing project"""
    try:
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        data = request.get_json()
        
        # Check if name already exists for another project
        if 'name' in data:
            existing_project = db.get_project_by_name(data['name'])
            if existing_project and existing_project['id'] != project_id:
                return jsonify({'error': 'Project with this name already exists'}), 409
        
        # Update project
        updated_project = db.update_project(
            project_id,
            name=data.get('name'),
            description=data.get('description')
        )
        
        return jsonify(updated_project), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<int:project_id>', methods=['DELETE'])
def delete_project(project_id):
    """Delete a project"""
    try:
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        # Clear current project if this was it
        if state.get_current_project() == project_id:
            state.clear_current_project()
            proxy_manager.save_active_project(None)
        
        db.delete_project(project_id)
        
        return jsonify({'message': 'Project deleted successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<int:project_id>/open-folder', methods=['POST'])
def open_project_folder(project_id):
    """Open the project's database folder in the system file manager"""
    try:
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        db_path = db.get_project_db_path(project['name'])
        folder_path = os.path.dirname(os.path.abspath(db_path))
        
        # Check if folder exists
        if not os.path.exists(folder_path):
            return jsonify({'error': 'Project folder not found'}), 404
        
        # Open folder based on operating system
        system = platform.system()
        try:
            if system == 'Darwin':  # macOS
                subprocess.run(['open', folder_path], check=True)
            elif system == 'Windows':
                subprocess.run(['explorer', folder_path], check=True)
            elif system == 'Linux':
                subprocess.run(['xdg-open', folder_path], check=True)
            else:
                return jsonify({'error': f'Unsupported operating system: {system}'}), 400
            
            return jsonify({
                'message': 'Folder opened successfully',
                'path': folder_path
            }), 200
        except subprocess.CalledProcessError as e:
            return jsonify({'error': f'Failed to open folder: {str(e)}'}), 500
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@projects_bp.route('/<int:project_id>/export', methods=['GET'])
def export_project_database(project_id):
    """Download the project's database file"""
    try:
        project = db.get_project_by_id(project_id)
        if not project:
            return jsonify({'error': 'Project not found'}), 404
        
        db_path = db.get_project_db_path(project['name'])
        
        # Check if database file exists
        if not os.path.exists(db_path):
            return jsonify({'error': 'Project database not found'}), 404
        
        # Generate download filename
        sanitized_name = db.sanitize_filename(project['name'])
        download_name = f"{sanitized_name}.db"
        
        # Send file for download
        return send_file(
            db_path,
            as_attachment=True,
            download_name=download_name,
            mimetype='application/x-sqlite3'
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500
