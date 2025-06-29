# backend/routes/settings_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from ..db import SessionLocal
from ..models import User, LLMSettings, Area, ProcessStep, UseCase
from ..utils import serialize_for_js
from ..injection_service import import_database_from_json
import traceback
import json

settings_routes = Blueprint('settings', __name__,
                            template_folder='../templates',
                            url_prefix='/settings')

@settings_routes.route('/', methods=['GET', 'POST'])
@login_required
def manage_settings():
    session = SessionLocal()
    user_settings = None

    all_areas_flat = []
    all_steps_flat = []
    all_usecases_flat = []

    try:
        user = session.query(User).options(joinedload(User.llm_settings)).get(current_user.id)
        if user:
            user_settings = user.llm_settings
            
        if request.method == 'POST':
            # Check if this POST is for the database import
            if 'database_file' in request.files:
                file = request.files['database_file']
                if file.filename == '':
                    flash('No selected database file.', 'warning')
                elif file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() == 'json':
                    clear_data = request.form.get('clear_existing_data') == 'on'
                    try:
                        file_content = file.read().decode('utf-8')
                        result = import_database_from_json(file_content, clear_existing_data=clear_data)
                        flash_category = 'success' if result['success'] else 'danger'
                        flash(result['message'], flash_category)
                    except Exception as e:
                        traceback.print_exc()
                        flash(f"An unexpected error occurred during database import: {str(e)}", 'danger')
                else:
                    flash('Invalid file type for database import. Please upload a .json file.', 'danger')
                return redirect(url_for('settings.manage_settings'))

            # Otherwise, it's for the LLM settings form
            if user_settings is None:
                user_settings = LLMSettings(user=user)
                session.add(user_settings)

            user_settings.openai_api_key = request.form.get('openai_api_key', '').strip() or None
            user_settings.anthropic_api_key = request.form.get('anthropic_api_key', '').strip() or None
            user_settings.google_api_key = request.form.get('google_api_key', '').strip() or None
            user_settings.ollama_base_url = request.form.get('ollama_base_url', '').strip() or None
            user_settings.apollo_client_id = request.form.get('apollo_client_id', '').strip() or None
            user_settings.apollo_client_secret = request.form.get('apollo_client_secret', '').strip() or None

            session.commit()
            flash("LLM settings updated successfully!", "success")
            return redirect(url_for('settings.manage_settings'))

    except Exception as e:
        session.rollback()
        flash(f"An error occurred: {e}", "danger")
        print(f"Error in settings page for user {current_user.id}: {e}")
    finally:
        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        pass

    return render_template(
        'settings.html',
        title='Application Settings',
        settings=user_settings,
        current_item=None,
        current_area=None,
        current_step=None,
        current_usecase=None,
        all_areas_flat=all_areas_flat,
        all_steps_flat=all_steps_flat,
        all_usecases_flat=all_usecases_flat
    )