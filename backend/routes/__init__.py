# backend/routes/__init__.py

from flask import Blueprint

# Define Blueprint objects for each functional area
# auth_routes definition is moved to routes/auth_routes.py
area_routes = Blueprint('areas', __name__, url_prefix='/api/areas')
step_routes = Blueprint('steps', __name__, url_prefix='/api/steps')
usecase_routes = Blueprint('usecases', __name__, url_prefix='/api/usecases')
llm_routes = Blueprint('llm', __name__, url_prefix='/api/llm')
injection_routes = Blueprint('injection', __name__, url_prefix='/api/injection')

# Note: The actual route definitions (@blueprint_name.route(...)) will go into
# their respective files (e.g., area_routes.py, step_routes.py etc.)
# These blueprint *objects* are imported into app.py to register them.