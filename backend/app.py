# backend/app.py
import os
from flask import Flask, render_template, redirect, url_for
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_login import LoginManager, current_user

from config import get_config
from models import Base, User

# Database setup
SessionLocal = scoped_session(sessionmaker())
engine = None # Engine will be created in create_app

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
    finally:
        # The session is typically removed in teardown_request,
        # but ensure closure if an error occurs during user loading itself.
        # SessionLocal.remove() is handled by teardown_request in normal flow.
        pass


def create_app():
    """
    Flask application factory function.
    Initializes the Flask app, loads config, sets up DB, and registers blueprints.
    """
    app = Flask(__name__,
                instance_relative_config=True,
                static_folder='static',
                template_folder='templates')

    # Ensure the instance folder exists
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
    db_url = app.config['SQLALCHEMY_DATABASE_URI']
    print(f"Attempting to connect to database: {db_url}")
    engine = create_engine(db_url)

    # Bind the scoped session to the engine
    SessionLocal.configure(bind=engine)

    # Test database connection
    try:
        with engine.connect() as connection:
            print("Database connection successful!")
    except Exception as e:
        print(f"Database connection failed: {e}")

    # Teardown database session after each request
    @app.teardown_request
    def remove_session(exception=None):
        SessionLocal.remove()

    # --- Register Blueprints ---
    from routes import auth_routes
    from routes import area_routes
    from routes import step_routes
    from routes import usecase_routes
    from routes import relevance_routes
    from routes import llm_routes
    from routes import injection_routes

    # Register blueprints directly (assuming the imported module IS the blueprint)
    app.register_blueprint(auth_routes)
    app.register_blueprint(area_routes)
    app.register_blueprint(step_routes)
    app.register_blueprint(usecase_routes)
    app.register_blueprint(relevance_routes)
    app.register_blueprint(llm_routes)
    app.register_blueprint(injection_routes)


    # --- Basic Root Route ---
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return render_template('index.html')
        else:
            return redirect(url_for('auth.login'))

    # --- Debug Check Route ---
    @app.route('/debug-check')
    def debug_check():
        try:
            # Test imports using direct paths
            from routes import auth_routes # Example route import check
            from config import Config
            from models import User

            # Test config access
            secret_key = app.config.get('SECRET_KEY')
            db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
            openai_key_present = 'OPENAI_API_KEY' in app.config and bool(app.config.get('OPENAI_API_KEY'))

            return {
                "status": "success",
                "message": "Imports and config loading successful!",
                "secret_key_loaded": bool(secret_key),
                "db_url_loaded": bool(db_url),
                "openai_key_loaded": openai_key_present,
                "imported_modules": ["routes.auth_routes", "models.User", "config.Config"]
            }
        except Exception as e:
            return {
                "status": "error",
                "message": f"Import or config check failed: {e}",
                "error_type": type(e).__name__
            }, 500

    return app

# No if __name__ == '__main__': block executing app.run() here
# It should be run using a WSGI server like Gunicorn or Waitress, typically via Docker Compose.