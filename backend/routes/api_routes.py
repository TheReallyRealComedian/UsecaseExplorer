# backend/routes/api_routes.py
from flask import Blueprint, jsonify, g
from ..models import Area, ProcessStep, UseCase
from ..utils import serialize_for_js

api_bp = Blueprint('api', __name__, url_prefix='/api')

@api_bp.route('/navigation_data')
def get_navigation_data():
    """
    Returns a single JSON object containing all the data required for the
    frontend navigation elements like breadcrumbs. This avoids passing
    this data to every single template.
    """
    try:
        # These are simple queries and should be efficient enough.
        all_areas = g.db_session.query(Area).order_by(Area.name).all()
        all_steps = g.db_session.query(ProcessStep).order_by(ProcessStep.name).all()
        all_usecases = g.db_session.query(UseCase).order_by(UseCase.name).all()

        # Using the existing serializer for consistency.
        data = {
            'areas': serialize_for_js(all_areas, 'area'),
            'steps': serialize_for_js(all_steps, 'step'),
            'usecases': serialize_for_js(all_usecases, 'usecase'),
        }
        return jsonify(data)
    except Exception as e:
        # In a real app, log this error.
        print(f"Error in /api/navigation_data: {e}")
        return jsonify(error="Failed to fetch navigation data"), 500