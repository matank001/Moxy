"""REST endpoints for security findings."""
from flask import Blueprint, jsonify, request
from .. import db, state
import logging

logger = logging.getLogger(__name__)

findings_bp = Blueprint('findings', __name__)


@findings_bp.route('', methods=['GET'])
def get_findings(project_id: int):
    try:
        severity = request.args.get('severity')
        tool = request.args.get('tool')
        findings = db.get_findings(project_id, severity=severity, tool=tool)
        return jsonify(findings), 200
    except Exception as e:
        logger.error("Error getting findings: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500


@findings_bp.route('/<int:finding_id>', methods=['DELETE'])
def delete_finding(project_id: int, finding_id: int):
    try:
        success = db.delete_finding(project_id, finding_id)
        if not success:
            return jsonify({'error': 'Finding not found'}), 404
        return jsonify({'success': True}), 200
    except Exception as e:
        logger.error("Error deleting finding: %s", e, exc_info=True)
        return jsonify({'error': str(e)}), 500
