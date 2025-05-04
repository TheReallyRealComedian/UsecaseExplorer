# backend/routes/__init__.py

from flask import Blueprint

# Define Blueprint objects for each functional area
auth_routes = Blueprint('auth', __name__, url_prefix='/auth')
area_routes = Blueprint('areas', __name__, url_prefix='/api/areas') # Using /api prefix for REST endpoints
step_routes = Blueprint('steps', __name__, url_prefix='/api/steps')
usecase_routes = Blueprint('usecases', __name__, url_prefix='/api/usecases')
relevance_routes = Blueprint('relevance', __name__, url_prefix='/api/relevance')
llm_routes = Blueprint('llm', __name__, url_prefix='/api/llm')
injection_routes = Blueprint('injection', __name__, url_prefix='/api/injection')

# Note: The actual route definitions (@blueprint_name.route(...)) will go into
# their respective files (e.g., auth_routes.py, area_routes.py, etc.)
# We import these blueprint *objects* into app.py to register them.