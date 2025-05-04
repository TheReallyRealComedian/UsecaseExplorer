# backend/app.py
import os
from flask import Flask, render_template, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_login import LoginManager, current_user

# Use relative imports for modules within the same package (backend)
from .config import get_config
from .models import Base, User, Area

# Database setup
SessionLocal = scoped_session(sessionmaker())
engine = None # Engine will be created in create_app

# Flask-Login setup
login_manager = LoginManager()
login_manager.login_view = 'auth.login' # Use the blueprint name ('auth') and function name ('login')
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
        pass # Already exists

    # Load configuration
    app.config.from_object(get_config())

    # Initialize Flask-Login
    login_manager.init_app(app)

    # Database engine setup
    global engine
    db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
    if not db_url:
        raise ValueError("SQLALCHEMY_DATABASE_URI is not set in the configuration!")
    print("Attempting to connect to database using URI from config.")
    engine = create_engine(db_url)

    # Bind the scoped session to the engine
    SessionLocal.configure(bind=engine)

    # Test database connection
    try:
        with engine.connect() as connection:
            print("Database connection successful!")
    except Exception as e:
        print(f"Database connection failed: {e}")
        # Consider raising the error or exiting depending on severity
        # raise e

    # Teardown database session after each request
    @app.teardown_request
    def remove_session(exception=None):
        SessionLocal.remove()

    # --- Register Blueprints ---
    print("Importing and registering blueprints...")

    # Import the auth blueprint object directly from its defining module
    from .routes.auth_routes import auth_routes
    app.register_blueprint(auth_routes)
    from .routes.injection_routes import injection_routes
    app.register_blueprint(injection_routes)

    # Keep the others as they are for now (defined in routes/__init__.py)
    # TODO: Refactor other blueprints later following the auth_routes pattern
    from .routes import (
        area_routes,
        step_routes,
        usecase_routes,
        relevance_routes,
        llm_routes,
    )
    app.register_blueprint(area_routes)
    app.register_blueprint(step_routes)
    app.register_blueprint(usecase_routes)
    app.register_blueprint(relevance_routes)
    app.register_blueprint(llm_routes)

    print("Blueprint registration complete.")


    # --- Basic Root Route ---
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            # --- ADD QUERY ---
            session = SessionLocal()
            try:
                areas = session.query(Area).order_by(Area.name).all()
            except Exception as e:
                print(f"Error querying areas: {e}")
                flash("Could not load areas from database.", "danger")
                areas = [] # Pass empty list on error
            finally:
                SessionLocal.remove()
            # --- END QUERY ---

            # Pass areas to the template
            return render_template('index.html', title='Home', areas=areas) # Added areas=areas
        else:
            # User is not logged in, redirect to login
            return redirect(url_for('auth.login'))

    # --- Debug Check Route ---
    @app.route('/debug-check')
    def debug_check():
        print("Accessing /debug-check route")
        results = {"status": "success", "checks": {}}
        try:
            # Test relative imports needed by this app context
            from .config import Config
            results["checks"]["config_import"] = "OK"
            from .models import User
            results["checks"]["models_import"] = "OK"

            # Test access to a blueprint object AFTER registration
            auth_bp_registered = app.blueprints.get('auth') is not None
            results["checks"]["auth_blueprint_registered"] = auth_bp_registered

            # Test config access
            secret_key = app.config.get('SECRET_KEY')
            db_url_present = bool(app.config.get('SQLALCHEMY_DATABASE_URI'))
            openai_key_present = 'OPENAI_API_KEY' in app.config and bool(app.config.get('OPENAI_API_KEY'))
            results["checks"]["secret_key_loaded"] = bool(secret_key)
            results["checks"]["db_url_loaded"] = db_url_present
            results["checks"]["openai_key_loaded"] = openai_key_present

            # Verify URL generation for a known registered route
            try:
                login_url = url_for('auth.login')
                results["checks"]["url_for_auth_login"] = f"OK ({login_url})"
            except Exception as url_err:
                results["checks"]["url_for_auth_login"] = f"FAILED ({url_err})"

        except Exception as e:
            results["status"] = "error"
            results["message"] = f"Debug check failed: {e}"
            results["error_type"] = type(e).__name__
            print(f"Error in /debug-check: {e}")
            return results, 500

        return results

    print("create_app function finished.")
    return app

# No WSGI server execution here. Run via Gunicorn, Waitress, etc.