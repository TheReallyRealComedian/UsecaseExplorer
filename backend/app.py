# backend/app.py
import os
from flask import Flask, render_template, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_login import LoginManager, current_user

# Change these relative imports to absolute imports
# from .config import get_config
# from .models import Base, User
from backend.config import get_config # Import the configuration
from backend.models import Base, User # Import Base and User model


# Database setup
SessionLocal = scoped_session(sessionmaker())
engine = None # Engine will be created in create_app

# Flask-Login setup
login_manager = LoginManager()
# Note: login_view should point to the blueprint name and then the function name
# which will handle the route, e.g., 'auth.login_route_function'
# We'll keep it as 'auth.login' for now, assuming we'll name the login function 'login' in auth_routes.py
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    """Loads a user from the database given their ID."""
    try:
        user_id = int(user_id)
    except (ValueError, TypeError): # Also handle TypeError if user_id is not a string/int
        return None

    # Use the scoped session to query the database
    # We need the session context to be available here via SessionLocal
    # Important: SessionLocal needs to be configured *before* load_user is called in a request context.
    # This happens in create_app(). However, load_user might be called early.
    # A common pattern is to get the session within the function if SessionLocal is globally configured.
    try:
        session = SessionLocal()
        user = session.query(User).get(user_id)
        return user
    except Exception as e:
        # Log the exception in production
        print(f"Error loading user {user_id}: {e}")
        return None
    finally:
         # Note: Scoped sessions often handle removal automatically after request
         # If not, you might need to handle it, but SessionLocal.remove() in teardown *should* suffice.
         pass # For now, rely on teardown_request


def create_app():
    """
    Flask application factory function.
    Initializes the Flask app, loads config, sets up DB, and registers blueprints.
    """
    # Flask app creation with instance folder
    app = Flask(__name__, instance_relative_config=True, static_folder='static', template_folder='templates')

    # Create the instance folder if it doesn't exist
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass # Instance folder already exists

    # Load configuration from config.py
    app.config.from_object(get_config())

    # You might also load configuration from instance/config.py for overrides
    # app.config.from_pyfile('config.py', silent=True)


    # Initialize Flask-Login
    login_manager.init_app(app)

    # Database engine setup
    global engine
    # Use 'app.instance_path' if you decide to put a local SQLite DB there for dev
    # For Postgres in Docker, the URL from config is correct.
    db_url = app.config['SQLALCHEMY_DATABASE_URI']
    print(f"Attempting to connect to database: {db_url}") # Debug print
    engine = create_engine(db_url)

    # Bind the scoped session to the engine
    SessionLocal.configure(bind=engine)

    # Test database connection (optional, but helps debug early)
    try:
        with engine.connect() as connection:
            print("Database connection successful!")
    except Exception as e:
        print(f"Database connection failed: {e}")
        # Depending on severity, you might want to raise or handle this differently

    # Optional: Create database tables if they don't exist.
    # For Docker setup with init.sql, this might not be strictly necessary on *every* run,
    # but can be useful for development/testing outside Docker or on initial setup.
    # If you are NOT using init.sql for Docker, uncomment the following line.
    # If you ARE using init.sql, keep it commented out to avoid conflicts.
    # Base.metadata.create_all(engine)


    # Teardown database session after each request
    @app.teardown_request
    def remove_session(exception=None):
        print("Removing DB session...") # Debug print
        SessionLocal.remove()

    # --- Register Blueprints ---
    # Import blueprints using absolute paths
    # from .routes import auth_routes, area_routes, step_routes, usecase_routes, relevance_routes, llm_routes, injection_routes
    from backend.routes import auth_routes
    from backend.routes import area_routes
    from backend.routes import step_routes
    from backend.routes import usecase_routes
    from backend.routes import relevance_routes
    from backend.routes import llm_routes
    from backend.routes import injection_routes


    app.register_blueprint(auth_routes.bp)
    app.register_blueprint(area_routes.bp)
    app.register_blueprint(step_routes.bp)
    app.register_blueprint(usecase_routes.bp)
    app.register_blueprint(relevance_routes.bp)
    app.register_blueprint(llm_routes.bp)
    app.register_blueprint(injection_routes.bp)

    # --- Basic Root Route ---
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return render_template('index.html')
        else:
            return redirect(url_for('auth.login')) # Redirect to the login blueprint's login route


    # Debug endpoint to check imports and config
    @app.route('/debug-check')
    def debug_check():
        try:
            # Try importing something from a sub-module
            from backend.routes import auth_routes
            from backend.models import User
            from backend.config import Config

            # Try accessing config
            secret_key = app.config['SECRET_KEY']
            db_url = app.config['SQLALCHEMY_DATABASE_URI']
            openai_key_present = 'OPENAI_API_KEY' in app.config and bool(app.config['OPENAI_API_KEY'])

            # Try a basic DB query (requires session context)
            # This won't work directly here without a request context,
            # but the successful import and config check is a good sign.

            return {
                "status": "success",
                "message": "Imports and config loading successful!",
                "secret_key_loaded": bool(secret_key),
                "db_url_loaded": bool(db_url),
                "openai_key_loaded": openai_key_present,
                "imported_modules": ["auth_routes", "User", "Config"]
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Import or config check failed: {e}",
                "error_type": type(e).__name__
            }, 500


    return app

# The __main__ block for local development remains commented out for Docker Compose
# if __name__ == '__main__':
#     app = create_app()
#     app.run(debug=True)