# backend/routes/settings_routes.py
from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import login_required, current_user
from ..db import SessionLocal
from ..models import User, Area, ProcessStep, UseCase
from ..utils import serialize_for_js
from ..services import settings_service  # <-- Import the new service

settings_routes = Blueprint('settings', __name__,
                            template_folder='../templates',
                            url_prefix='/settings')

@settings_routes.route('/', methods=['GET', 'POST'])
@login_required
def manage_settings():
    session = SessionLocal()
    try:
        user_settings = settings_service.get_user_llm_settings(session, current_user.id)
            
        if request.method == 'POST':
            # This route now only handles the LLM settings form
            success, message = settings_service.save_user_llm_settings(session, current_user, request.form)
            flash(message, "success" if success else "danger")
            return redirect(url_for('settings.manage_settings'))

        # Data for breadcrumbs
        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')

        return render_template(
            'settings.html',
            title='Application Settings',
            settings=user_settings,
            current_item=None, current_area=None, current_step=None, current_usecase=None,
            all_areas_flat=all_areas_flat, all_steps_flat=all_steps_flat, all_usecases_flat=all_usecases_flat
        )
    except Exception as e:
        session.rollback()
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('dashboard'))
    finally:
        session.close()