# backend/routes/main_routes.py
from flask import Blueprint, render_template, redirect, url_for, g
from flask_login import current_user
from sqlalchemy.orm import joinedload

from ..models import Area, ProcessStep, UseCase
from ..services import step_service, dashboard_service
from ..utils import serialize_for_js

main_routes = Blueprint('main', __name__)

@main_routes.route('/')
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

@main_routes.route('/dashboard')
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