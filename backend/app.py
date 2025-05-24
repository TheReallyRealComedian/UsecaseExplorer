# backend/app.py
import os
from flask import Flask, render_template, redirect, url_for, flash
from sqlalchemy.orm import joinedload # Kept for use in index route
from flask_login import LoginManager, current_user
import markupsafe # For the nl2br filter

from .config import get_config
from .models import Base, User, Area, ProcessStep, UseCase
from .db import SessionLocal, init_engine as init_db_engine # Updated import

# NEW: Import llm_service to ensure it's loaded and can access Flask's session proxy
from . import llm_service # This line is important

# Flask-Login setup
login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Loads a user from the database given their ID."""
    try:
        user_id = int(user_id)
    except (ValueError, TypeError):
        return None

    session = SessionLocal() # SessionLocal is now imported from .db
    try:
        user = session.query(User).get(user_id)
        return user
    except Exception as e:
        print(f"Error loading user {user_id}: {e}")
        return None
    finally:
        SessionLocal.remove() # Ensure session is removed as per CHANGE

# --- CUSTOM JINJA FILTER ---
def nl2br(value):
    """Converts newlines in a string to HTML <br> tags."""
    if value is None:
        return ''
    escaped_value = markupsafe.escape(value)
    return markupsafe.Markup(escaped_value.replace('\n', '<br>\n'))


def create_app():
    """
    Flask application factory function.
    Initializes the Flask app, loads config, sets up DB, and registers blueprints.
    """
    app = Flask(__name__,
                instance_relative_config=True,
                static_folder='static',
                template_folder='templates')

    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    app.config.from_object(get_config())
    login_manager.init_app(app)

    app.jinja_env.filters['nl2br'] = nl2br

    db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
    # Initialize the engine using the function from db.py
    # This also configures SessionLocal in db.py
    current_engine = init_db_engine(db_url)

    try:
        # Use the returned engine from init_db_engine
        with current_engine.connect() as connection:
            print("Database connection successful!")
    except Exception as e:
        print(f"Database connection failed: {e}")
        # Potentially raise a more critical error or exit if DB is essential for startup

    @app.teardown_request
    def remove_session(exception=None):
        SessionLocal.remove() # SessionLocal is imported from .db

    print("Importing and registering blueprints...")
    from .routes.auth_routes import auth_routes
    app.register_blueprint(auth_routes)
    from .routes.injection_routes import injection_routes
    app.register_blueprint(injection_routes)
    from .routes.usecase_routes import usecase_routes
    app.register_blueprint(usecase_routes)
    from .routes.relevance_routes import relevance_routes
    app.register_blueprint(relevance_routes)
    from .routes.llm_routes import llm_routes
    app.register_blueprint(llm_routes)
    from .routes.area_routes import area_routes
    app.register_blueprint(area_routes)
    from .routes.step_routes import step_routes
    app.register_blueprint(step_routes)
    from .routes.export_routes import export_routes 
    app.register_blueprint(export_routes)
    print("Blueprint registration complete.")


    @app.route('/')
    def index():
        if current_user.is_authenticated:
            session = SessionLocal() # SessionLocal from .db
            areas = []
            try:
                areas = session.query(Area).options(
                    joinedload(Area.process_steps).joinedload(ProcessStep.use_cases)
                ).order_by(Area.name).all()
            except Exception as e:
                print(f"Error querying areas with steps and use cases: {e}")
                flash("Could not load necessary data from the database.", "danger")
            # The finally block with SessionLocal.remove() is handled by @app.teardown_request
            return render_template('index.html', title='Home', areas=areas)
        else:
            return redirect(url_for('auth.login'))


    @app.route('/debug-check')
    def debug_check():
        print("Accessing /debug-check route")
        results = {"status": "success", "checks": {}}
        session_for_debug = SessionLocal() # SessionLocal from .db, create once for this route
        try:
            from .config import Config # noqa: F401 (unused import)
            results["checks"]["config_import"] = "OK"
            from .models import User as DebugUser # noqa: F401 (unused import), aliased
            results["checks"]["models_import"] = "OK"

            # Test access to blueprint objects AFTER registration
            auth_bp_registered = app.blueprints.get('auth') is not None
            results["checks"]["auth_blueprint_registered"] = auth_bp_registered
            usecase_bp_registered = app.blueprints.get('usecases') is not None
            results["checks"]["usecase_blueprint_registered"] = usecase_bp_registered
            relevance_bp_registered = app.blueprints.get('relevance') is not None
            results["checks"]["relevance_blueprint_registered"] = relevance_bp_registered
            llm_bp_registered = app.blueprints.get('llm') is not None
            results["checks"]["llm_blueprint_registered"] = llm_bp_registered
            area_bp_registered = app.blueprints.get('areas') is not None
            results["checks"]["area_blueprint_registered"] = area_bp_registered
            step_bp_registered = app.blueprints.get('steps') is not None
            results["checks"]["step_blueprint_registered"] = step_bp_registered

            # Test config access
            secret_key_present = bool(app.config.get('SECRET_KEY'))
            db_url_present = bool(app.config.get('SQLALCHEMY_DATABASE_URI'))
            openai_key_present = 'OPENAI_API_KEY' in app.config and \
                                 bool(app.config.get('OPENAI_API_KEY'))
            results["checks"]["secret_key_loaded"] = secret_key_present
            results["checks"]["db_url_loaded"] = db_url_present
            results["checks"]["openai_key_loaded"] = openai_key_present


            try:
                login_url = url_for('auth.login')
                results["checks"]["url_for_auth_login"] = f"OK ({login_url})"
                add_area_rel_url = url_for('relevance.add_area_relevance')
                results["checks"]["url_for_relevance_add_area"] = f"OK ({add_area_rel_url})"
                list_areas_url = url_for('areas.list_areas')
                results["checks"]["url_for_areas_list"] = f"OK ({list_areas_url})"
            except Exception as url_err:
                results["checks"]["url_for_generation"] = f"FAILED ({url_err})"

            try:
                # Use the session instance created at the start of the route
                user_count = session_for_debug.query(User).count()
                results["checks"]["db_connection_request_context"] = \
                    f"OK (User count: {user_count})"
            except Exception as db_err:
                results["checks"]["db_connection_request_context"] = f"FAILED ({db_err})"
                results["status"] = "warning"
        except Exception as e:
            results["status"] = "error"
            results["message"] = f"Debug check failed: {e}"
            results["error_type"] = type(e).__name__
            print(f"Error in /debug-check: {e}")
            return results, 500
        finally:
            SessionLocal.remove() # Remove the session used for debug_check

        return results

    print("create_app function finished.")
    return app

# Run via WSGI server (Gunicorn)