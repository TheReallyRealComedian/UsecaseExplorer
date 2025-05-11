# backend/app.py
import os
from flask import Flask, render_template, redirect, url_for, flash
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker, joinedload
from flask_login import LoginManager, current_user
import markupsafe # For the nl2br filter

from .config import get_config
from .models import Base, User, Area, ProcessStep, UseCase

# Database setup
SessionLocal = scoped_session(sessionmaker())
engine = None

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

    session = SessionLocal()
    try:
        user = session.query(User).get(user_id)
        return user
    except Exception as e:
        print(f"Error loading user {user_id}: {e}")
        return None
    # No finally needed here; teardown_request handles removal


# --- CUSTOM JINJA FILTER ---
def nl2br(value):
    """Converts newlines in a string to HTML <br> tags."""
    if value is None:
        return ''
    # Ensure the value is escaped before replacing newlines to prevent XSS
    # if it contains user-provided HTML. If it's plain text, simple replace is fine.
    # For safety with potentially complex text, markupsafe.escape is good.
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

    # --- REGISTER CUSTOM FILTER ---
    app.jinja_env.filters['nl2br'] = nl2br

    global engine
    db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
    if not db_url:
        raise ValueError("SQLALCHEMY_DATABASE_URI is not set in the configuration!")
    print("Attempting to connect to database using URI from config.")
    engine = create_engine(db_url)

    SessionLocal.configure(bind=engine)

    try:
        with engine.connect() as connection:
            print("Database connection successful!")
    except Exception as e:
        print(f"Database connection failed: {e}")

    @app.teardown_request
    def remove_session(exception=None):
        SessionLocal.remove()

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
    print("Blueprint registration complete.")

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            session = SessionLocal()
            areas = []
            try:
                areas = session.query(Area).options(
                    joinedload(Area.process_steps).joinedload(ProcessStep.use_cases)
                ).order_by(Area.name).all()
            except Exception as e:
                print(f"Error querying areas with steps and use cases: {e}")
                flash("Could not load necessary data from the database.", "danger")
            finally:
                SessionLocal.remove()

            return render_template('index.html', title='Home', areas=areas)
        else:
            return redirect(url_for('auth.login'))


    @app.route('/debug-check')
    def debug_check():
        print("Accessing /debug-check route")
        results = {"status": "success", "checks": {}}
        try:
            # Test relative imports needed by this app context
            from .config import Config # noqa: F401 (unused import)
            results["checks"]["config_import"] = "OK"
            # Renamed to avoid potential conflict if User model is used later in this function
            from .models import User as DebugUser # noqa: F401 (unused import)
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
            area_bp_registered = app.blueprints.get('areas') is not None # Added check for areas
            results["checks"]["area_blueprint_registered"] = area_bp_registered
            step_bp_registered = app.blueprints.get('steps') is not None # Added check for steps
            results["checks"]["step_blueprint_registered"] = step_bp_registered

            # Test config access
            secret_key_present = bool(app.config.get('SECRET_KEY'))
            db_url_present = bool(app.config.get('SQLALCHEMY_DATABASE_URI'))
            openai_key_present = 'OPENAI_API_KEY' in app.config and bool(app.config.get('OPENAI_API_KEY'))
            results["checks"]["secret_key_loaded"] = secret_key_present
            results["checks"]["db_url_loaded"] = db_url_present
            results["checks"]["openai_key_loaded"] = openai_key_present

            # Verify URL generation for known registered routes
            try:
                login_url = url_for('auth.login')
                results["checks"]["url_for_auth_login"] = f"OK ({login_url})"
                add_area_rel_url = url_for('relevance.add_area_relevance')
                results["checks"]["url_for_relevance_add_area"] = f"OK ({add_area_rel_url})"
                list_areas_url = url_for('areas.list_areas') # Check for an area route
                results["checks"]["url_for_areas_list"] = f"OK ({list_areas_url})"

            except Exception as url_err:
                results["checks"]["url_for_generation"] = f"FAILED ({url_err})"

            try:
                # Using SessionLocal() ensures teardown is handled
                user_count = SessionLocal().query(User).count()
                results["checks"]["db_connection_request_context"] = f"OK (User count: {user_count})"
                SessionLocal.remove() # Manually remove session used just for count
            except Exception as db_err:
                results["checks"]["db_connection_request_context"] = f"FAILED ({db_err})"
                results["status"] = "warning"


        except Exception as e:
            results["status"] = "error"
            results["message"] = f"Debug check failed: {e}"
            results["error_type"] = type(e).__name__
            print(f"Error in /debug-check: {e}")
            return results, 500

        return results

    print("create_app function finished.")
    return app

# Run via WSGI server (Gunicorn)