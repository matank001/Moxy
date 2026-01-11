"""
Global application state management
"""

# Global state
_current_project_id = None


def set_current_project(project_id):
    """Set the current active project"""
    global _current_project_id
    _current_project_id = project_id


def get_current_project():
    """Get the current active project ID"""
    return _current_project_id


def clear_current_project():
    """Clear the current project"""
    global _current_project_id
    _current_project_id = None
