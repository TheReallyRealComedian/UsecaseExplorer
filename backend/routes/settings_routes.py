# backend/routes/settings_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from ..db import SessionLocal # Import the new model
from ..models import User, LLMSettings, Area, ProcessStep, UseCase # Import the new model
# NEW IMPORT FOR BREADCRUMBS DATA
from ..utils import serialize_for_js
# END NEW IMPORT

settings_routes = Blueprint('settings', __name__,
                            template_folder='../templates',
                            url_prefix='/settings')

@settings_routes.route('/', methods=['GET', 'POST'])
@login_required
def manage_settings():
    session = SessionLocal() # This gets a session from the scoped_session factory
    user_settings = None

    # NEW BREADCRUMB DATA FETCHING
    all_areas_flat = []
    all_steps_flat = []
    all_usecases_flat = []
    # END NEW BREADCRUMB DATA FETCHING

    try:
        # Try to load existing settings for the current user, eagerly loading LLMSettings
        user = session.query(User).options(joinedload(User.llm_settings)).get(current_user.id)
        
        if user:
            user_settings = user.llm_settings
            
        if request.method == 'POST':
            # Create settings object if it doesn't exist for the user
            if user_settings is None:
                user_settings = LLMSettings(user=user)
                session.add(user_settings)

            user_settings.openai_api_key = request.form.get('openai_api_key', '').strip() or None
            user_settings.anthropic_api_key = request.form.get('anthropic_api_key', '').strip() or None
            user_settings.google_api_key = request.form.get('google_api_key', '').strip() or None
            user_settings.ollama_base_url = request.form.get('ollama_base_url', '').strip() or None

            session.commit()
            flash("LLM settings updated successfully!", "success")
            return redirect(url_for('settings.manage_settings')) # Redirect to GET to show updated values

    except Exception as e:
        session.rollback()
        flash(f"An error occurred while saving settings: {e}", "danger")
        print(f"Error saving settings for user {current_user.id}: {e}")
    finally:
        # REMOVED: session.remove() is not needed here because app.py's @app.teardown_request
        # already calls SessionLocal.remove() automatically after each request.
        # Calling session.close() is also not strictly necessary with scoped_session managed by teardown.
        # NEW BREADCRUMB DATA FETCHING (regardless of POST success/failure for rendering)
        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        # END NEW BREADCRUMB DATA FETCHING
        # REMOVED: SessionLocal.remove() as per change instructions
        pass

    # For GET requests or if POST failed before redirect
    return render_template(
        'settings.html',
        title='Application Settings',
        settings=user_settings, # This will be the LLMSettings object or None for the form
        current_item=None, # Indicates this is a top-level page
        current_area=None, # Ensure consistency
        current_step=None, # Ensure consistency
        current_usecase=None, # Ensure consistency
        # NEW BREADCRUMB DATA PASSING
        all_areas_flat=all_areas_flat,
        all_steps_flat=all_steps_flat,
        all_usecases_flat=all_usecases_flat
        # END NEW BREADCRUMB DATA PASSING
    )
