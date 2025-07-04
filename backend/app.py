# backend/app.py
import os
from flask import Flask, render_template, redirect, url_for, flash, jsonify, g
import json

from sqlalchemy import func
from sqlalchemy.orm import joinedload
from flask_login import LoginManager, current_user
import markupsafe
import markdown

from flask_session import Session

from .config import get_config
from .models import User, Area, ProcessStep, UseCase
from .db import init_app_db, SessionLocal, db as flask_sqlalchemy_db
from .utils import serialize_for_js

# --- Blueprint Imports ---
from .routes.auth_routes import auth_routes
from .routes.usecase_routes import usecase_routes
from .routes.relevance_routes import relevance_routes
from .routes.llm_routes import llm_routes
from .routes.area_routes import area_routes
from .routes.step_routes import step_routes
from .routes.export_routes import export_routes
from .routes.settings_routes import settings_routes
from .routes.review_routes import review_routes
from .routes.data_management_routes import data_management_bp

# --- Service Imports ---
from .services import step_service, dashboard_service


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

# --- CUSTOM JINJA FILTERS ---
def nl2br(value):
    if value is None: return ''
    return markupsafe.Markup(markupsafe.escape(value).replace('\n', '<br>\n'))

def markdown_to_html_filter(value):
    if value is None: return ''
    return markupsafe.Markup(markdown.markdown(value, extensions=['fenced_code', 'tables']))

def truncate_filter(s, length=255, end='...'):
    if s is None: return ''
    return s[:length] + end if len(s) > length else s

def zfill_filter(value, width):
    if value is None: return ''
    return str(value).zfill(width)

def htmlsafe_json_filter(value):
    return markupsafe.Markup(json.dumps(value))

def map_priority_to_benefit_filter(priority):
    if priority == 1: return "High"
    if priority == 2: return "Medium"
    if priority == 3: return "Low"
    return "N/A"

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

    # Register Jinja filters
    app.jinja_env.filters['nl2br'] = nl2br
    app.jinja_env.filters['markdown'] = markdown_to_html_filter
    app.jinja_env.filters['truncate'] = truncate_filter
    app.jinja_env.filters['zfill'] = zfill_filter
    app.jinja_env.filters['htmlsafe_json'] = htmlsafe_json_filter
    app.jinja_env.filters['map_priority_to_benefit'] = map_priority_to_benefit_filter

    db_instance = init_app_db(app)

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

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            all_steps = step_service.get_all_steps_with_details(g.db_session)
            areas_with_steps = g.db_session.query(Area).options(
                joinedload(Area.process_steps)
            ).order_by(Area.name).all()
            all_areas_query = g.db_session.query(Area).order_by(Area.name).all()
            all_usecases_query = g.db_session.query(UseCase).order_by(UseCase.name).all()
            
            # Prepare data for JS
            all_areas_for_select_js = serialize_for_js(all_areas_query, 'area')
            all_areas_flat = serialize_for_js(all_areas_query, 'area')
            all_steps_flat = serialize_for_js(all_steps, 'step')
            all_usecases_flat = serialize_for_js(all_usecases_query, 'usecase')

            return render_template(
                'ptps.html',
                title='Process Target Pictures (PTPs)',
                all_steps=all_steps,
                areas_with_steps=areas_with_steps,
                all_areas_for_select=all_areas_for_select_js,
                current_item=None,
                current_area=None,
                current_step=None,
                current_usecase=None,
                all_areas_flat=all_areas_flat,
                all_steps_flat=all_steps_flat,
                all_usecases_flat=all_usecases_flat
            )
        else:
            return redirect(url_for('auth.login'))

    @app.route('/dashboard')
    def dashboard():
        if current_user.is_authenticated:
            stats = dashboard_service.get_dashboard_stats(g.db_session)
            all_areas_flat = serialize_for_js(g.db_session.query(Area).order_by(Area.name).all(), 'area')
            all_steps_flat = serialize_for_js(g.db_session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
            all_usecases_flat = serialize_for_js(g.db_session.query(UseCase).order_by(UseCase.name).all(), 'usecase')

            return render_template(
                'index.html',
                title='Dashboard',
                total_areas=stats["total_areas"],
                total_steps=stats["total_steps"],
                total_usecases=stats["total_usecases"],
                current_item=None,
                current_area=None,
                current_step=None,
                current_usecase=None,
                all_areas_flat=all_areas_flat,
                all_steps_flat=all_steps_flat,
                all_usecases_flat=all_usecases_flat
            )
        else:
            return redirect(url_for('auth.login'))

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