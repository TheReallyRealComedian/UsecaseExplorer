# backend/app.py

import os
from flask import Flask, render_template, redirect, url_for, flash, jsonify, g
from flask_login import LoginManager, current_user
from flask_migrate import Migrate
from flask_session import Session
from flask_assets import Environment

# --- CORRECTED ABSOLUTE IMPORTS ---
from backend.config import get_config
from backend.models import User
from backend.db import init_app_db, SessionLocal, db as flask_sqlalchemy_db
from backend.utils import (
    serialize_for_js, nl2br, markdown_to_html_filter, truncate_filter,
    zfill_filter, htmlsafe_json_filter, map_priority_to_benefit_filter
)
# --- Asset Imports ---
from backend.assets import js_main_bundle, css_bundle

# --- Blueprint Imports ---
from backend.routes.auth_routes import auth_routes
from backend.routes.usecase_routes import usecase_routes
from backend.routes.relevance_routes import relevance_routes
from backend.routes.llm_routes import llm_routes
from backend.routes.area_routes import area_routes
from backend.routes.step_routes import step_routes
from backend.routes.export_routes import export_routes
from backend.routes.settings_routes import settings_routes
from backend.routes.review_routes import review_routes
from backend.routes.data_management_routes import data_management_bp
from backend.routes.main_routes import main_routes
from backend.routes.api_routes import api_bp

# --- Service Imports (now only needed by routes, but we'll leave it for now) ---
from backend.services import step_service, dashboard_service


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

    # Use the request-scoped session if available, otherwise create one
    session = g.get('db_session', SessionLocal())
    try:
        user = session.query(User).get(user_id)
        return user
    except Exception as e:
        print(f"Error loading user {user_id}: {e}")
        return None
    finally:
        # If we created the session here, we should remove it.
        # The teardown_appcontext will handle the one on `g`.
        if 'db_session' not in g:
            SessionLocal.remove()


def create_app(init_session=True):
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
    
    # --- START MODIFICATION: Initialize Flask-Assets ---
    assets = Environment(app)
    assets.register('js_main', js_main_bundle)
    assets.register('css_main', css_bundle)
    # The 'gen' folder will be created automatically in 'static'
    assets.url = app.static_url_path
    # --- END MODIFICATION ---

    # Register Jinja filters
    app.jinja_env.filters['nl2br'] = nl2br
    app.jinja_env.filters['markdown'] = markdown_to_html_filter
    app.jinja_env.filters['truncate'] = truncate_filter
    app.jinja_env.filters['zfill'] = zfill_filter
    app.jinja_env.filters['htmlsafe_json'] = htmlsafe_json_filter
    app.jinja_env.filters['map_priority_to_benefit'] = map_priority_to_benefit_filter

    db_instance, migrate_instance = init_app_db(app)

    #migrate = Migrate(app, db_instance, directory='/app/migrations')

    # Conditionally initialize Flask-Session
    if init_session:
        # Flask-Session configuration
        app.config['SESSION_TYPE'] = 'sqlalchemy'
        app.config['SESSION_SQLALCHEMY_TABLE'] = 'flask_sessions'
        app.config['SESSION_SQLALCHEMY'] = db_instance
        app.config['SESSION_PERMANENT'] = True
        app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24 * 7
        Session(app)

    # --- Centralized DB Session Management ---
    @app.before_request
    def before_request():
        """Create a database session for each request."""
        g.db_session = SessionLocal()

    @app.teardown_appcontext
    def teardown_appcontext(exception=None):
        """Close the database session at the end of the request."""
        db_session = g.pop('db_session', None)
        if db_session is not None:
            SessionLocal.remove()

    # Register Blueprints
    app.register_blueprint(auth_routes)
    app.register_blueprint(usecase_routes)
    app.register_blueprint(relevance_routes)
    app.register_blueprint(llm_routes)
    app.register_blueprint(area_routes)
    app.register_blueprint(step_routes)
    app.register_blueprint(export_routes)
    app.register_blueprint(settings_routes)
    app.register_blueprint(review_routes)
    app.register_blueprint(data_management_bp)
    app.register_blueprint(main_routes)
    app.register_blueprint(api_bp)


    @app.route('/debug-check')
    def debug_check():
        results = {"status": "success", "checks": {}}
        session_for_debug = g.db_session
        try:
            user_count = session_for_debug.query(User).count()
            results["checks"]["db_connection_request_context"] = f"OK (User count: {user_count})"
        except Exception as db_err:
            results["checks"]["db_connection_request_context"] = f"FAILED ({db_err})"
        return jsonify(results)

    return app