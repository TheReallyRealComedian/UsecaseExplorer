# backend/app.py
import os
from flask import Flask, render_template, redirect, url_for, flash, jsonify
import json

from sqlalchemy import func # For count
from sqlalchemy.orm import joinedload
from flask_login import LoginManager, current_user
import markupsafe
import markdown

from flask_session import Session

from .config import get_config
from .models import Base, User, Area, ProcessStep, UseCase, LLMSettings
from .db import init_app_db, SessionLocal, db as flask_sqlalchemy_db
from .utils import serialize_for_js # <<< NEW IMPORT

from . import llm_service

# --- Blueprint Imports ---
from .routes.auth_routes import auth_routes
from .routes.injection_routes import injection_routes
from .routes.usecase_routes import usecase_routes
from .routes.relevance_routes import relevance_routes
from .routes.llm_routes import llm_routes
from .routes.area_routes import area_routes
from .routes.step_routes import step_routes
from .routes.export_routes import export_routes
from .routes.data_alignment_routes import data_alignment_routes
from .routes.settings_routes import settings_routes
from .routes.review_routes import review_routes


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

    session = flask_sqlalchemy_db.session
    try:
        user = session.query(User).get(user_id)
        return user
    except Exception as e:
        print(f"Error loading user {user_id}: {e}")
        return None
    finally:
        pass

# --- CUSTOM JINJA FILTERS ---
def nl2br(value):
    """Converts newlines in a string to HTML <br> tags."""
    if value is None:
        return ''
    escaped_value = markupsafe.escape(value)
    return markupsafe.Markup(escaped_value.replace('\n', '<br>\n'))

def markdown_to_html_filter(value):
    """Converts markdown text to HTML."""
    if value is None:
        return ''
    return markupsafe.Markup(markdown.markdown(value, extensions=['fenced_code', 'tables']))

def truncate_filter(s, length=255, killwords=False, end='...'):
    """Truncates a string."""
    if s is None:
        return ''
    if len(s) <= length:
        return s
    if killwords:
        return s[:length] + end
    else:
        words = s.split(' ')
        out = []
        l = 0
        for word in words:
            if (l + len(word)) <= length:
                out.append(word)
                l += len(word)
            else:
                break
        return ' '.join(out) + end

def zfill_filter(value, width):
    """Fills numeric string with zeros on the left to reach a specified width."""
    if value is None:
        return ''
    return str(value).zfill(width)

def htmlsafe_json_filter(value):
    """
    Dumps a Python object to a JSON string and marks it as HTML safe.
    This is useful for embedding JSON data directly into HTML script tags.
    """
    return markupsafe.Markup(json.dumps(value))


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
    app.jinja_env.filters['markdown'] = markdown_to_html_filter
    app.jinja_env.filters['truncate'] = truncate_filter
    app.jinja_env.filters['zfill'] = zfill_filter
    app.jinja_env.filters['htmlsafe_json'] = htmlsafe_json_filter

    db_url = app.config.get('SQLALCHEMY_DATABASE_URI')
    print(f"DEBUG: Initializing database with URL: {db_url}")
    db_instance = init_app_db(app)

    app.config['SESSION_TYPE'] = 'sqlalchemy'
    app.config['SESSION_SQLALCHEMY_TABLE'] = 'flask_sessions'
    app.config['SESSION_SQLALCHEMY'] = db_instance
    app.config['SESSION_PERMANENT'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = 3600 * 24 * 7
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_COOKIE_NAME'] = 'usecase_explorer_session'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SECURE'] = False # Set to True in production if using HTTPS
    app.config['SESSION_SQLALCHEMY_CREATE_TABLE'] = False
    
    print("DEBUG: Initializing Flask-Session...")
    Session(app) 
    print("DEBUG: Flask-Session initialized.")
    
    with app.app_context():
        try:
            with db_instance.engine.connect() as connection: 
                print("Database connection successful!")
        except Exception as e:
            print(f"Database connection failed: {e}")
        print("DEBUG: Database connection check passed within app_context.")

    @app.teardown_request
    def remove_session(exception=None):
        SessionLocal.remove()

    print("DEBUG: About to import and register blueprints.")
    
    print("DEBUG: Registering auth_routes.")
    app.register_blueprint(auth_routes)
    
    print("DEBUG: Registering injection_routes.")
    app.register_blueprint(injection_routes)
    
    print("DEBUG: Registering usecase_routes.")
    app.register_blueprint(usecase_routes)
    
    print("DEBUG: Registering relevance_routes.")
    app.register_blueprint(relevance_routes)
    
    print("DEBUG: Registering llm_routes.")
    app.register_blueprint(llm_routes)
    
    print("DEBUG: Registering area_routes.")
    app.register_blueprint(area_routes)
    
    print("DEBUG: Registering step_routes.")
    app.register_blueprint(step_routes)
    
    print("DEBUG: Registering export_routes.")
    app.register_blueprint(export_routes)
    
    print("DEBUG: Registering data_alignment_routes.")
    app.register_blueprint(data_alignment_routes)
    
    print("DEBUG: Registering settings_routes.")
    app.register_blueprint(settings_routes)
    
    print("DEBUG: Registering review_routes.")
    app.register_blueprint(review_routes) 
    
    print("Blueprint registration complete.")

    @app.route('/')
    def index():
        if current_user.is_authenticated:
            session_db = flask_sqlalchemy_db.session
            
            all_areas_flat = serialize_for_js(session_db.query(Area).order_by(Area.name).all(), 'area')
            all_steps_flat = serialize_for_js(session_db.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
            all_usecases_flat = serialize_for_js(session_db.query(UseCase).order_by(UseCase.name).all(), 'usecase')

            total_areas = session_db.query(func.count(Area.id)).scalar()
            total_steps = session_db.query(func.count(ProcessStep.id)).scalar()
            total_usecases = session_db.query(func.count(UseCase.id)).scalar()

            usecases_by_priority = session_db.query(
                UseCase.priority, func.count(UseCase.id)
            ).group_by(UseCase.priority).all()
            
            return render_template(
                'index.html', 
                title='Dashboard', 
                total_areas=total_areas,
                total_steps=total_steps,
                total_usecases=total_usecases,
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
        print("Accessing /debug-check route")
        results = {"status": "success", "checks": {}}
        session_for_debug = flask_sqlalchemy_db.session
        try:
            from .config import Config
            results["checks"]["config_import"] = "OK"
            from .models import User as DebugUser, LLMSettings as DebugLLMSettings
            results["checks"]["models_import"] = "OK"

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
            data_alignment_bp_registered = app.blueprints.get('data_alignment') is not None
            results["checks"]["data_alignment_blueprint_registered"] = data_alignment_bp_registered
            injection_bp_registered = app.blueprints.get('injection') is not None
            results["checks"]["injection_blueprint_registered"] = injection_bp_registered
            settings_bp_registered = app.blueprints.get('settings') is not None
            results["checks"]["settings_blueprint_registered"] = settings_bp_registered
            review_bp_registered = app.blueprints.get('review') is not None
            results["checks"]["review_blueprint_registered"] = review_bp_registered


            secret_key_present = bool(app.config.get('SECRET_KEY'))
            db_url_present = bool(app.config.get('SQLALCHEMY_DATABASE_URI'))
            openai_key_present = 'OPENAI_API_KEY' in app.config and \
                                 bool(app.config.get('OPENAI_API_KEY'))
            results["checks"]["secret_key_loaded"] = secret_key_present
            results["checks"]["db_url_loaded"] = db_url_present
            results["checks"]["openai_key_loaded"] = openai_key_present

            results["checks"]["session_type"] = app.config.get('SESSION_TYPE')
            results["checks"]["session_sqlalchemy_table"] = app.config.get('SESSION_SQLALCHEMY_TABLE')
            results["checks"]["session_sqlalchemy_instance_type"] = str(type(app.config.get('SESSION_SQLALCHEMY')))


            try:
                login_url = url_for('auth.login')
                results["checks"]["url_for_auth_login"] = f"OK ({login_url})"
                add_area_rel_url = url_for('relevance.add_area_relevance')
                results["checks"]["url_for_relevance_add_area"] = f"OK ({add_area_rel_url})"
                try:
                    list_areas_url = url_for('areas.list_areas') 
                    results["checks"]["url_for_areas_list"] = f"OK ({list_areas_url})"
                except Exception as area_url_err:
                    results["checks"]["url_for_areas_list"] = f"FAILED ({area_url_err})"

                data_alignment_url = url_for('data_alignment.data_alignment_page')
                results["checks"]["url_for_data_alignment"] = f"OK ({data_alignment_url})"
                settings_url = url_for('settings.manage_settings')
                results["checks"]["url_for_settings"] = f"OK ({settings_url})"
                
                try:
                    review_dashboard_url = url_for('review.review_dashboard')
                    results["checks"]["url_for_review_dashboard"] = f"OK ({review_dashboard_url})"
                except Exception as review_url_err:
                    results["checks"]["url_for_review_dashboard"] = f"FAILED ({review_url_err})"


            except Exception as url_err:
                results["checks"]["url_for_generation"] = f"FAILED ({url_err})"

            try:
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
            return jsonify(results), 500
        finally:
            pass
        
        return jsonify(results)

    print("DEBUG: create_app function about to return app object.")
    return app