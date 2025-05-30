# backend/routes/settings_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from ..db import SessionLocal # Import the new model
from ..models import User, LLMSettings # Import the new model

settings_routes = Blueprint('settings', __name__,
                            template_folder='../templates',
                            url_prefix='/settings')

@settings_routes.route('/', methods=['GET', 'POST'])
@login_required
def manage_settings():
    session = SessionLocal() # This gets a session from the scoped_session factory
    user_settings = None

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
        pass
    
    # For GET requests or if POST failed before redirect
    return render_template(
        'settings.html',
        title='Application Settings',
        settings=user_settings # This will be the LLMSettings object or None
    )