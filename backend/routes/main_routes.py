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
        
        # --- START REFACTOR: Consolidate data for the data island ---
        # Data needed specifically for this page's JavaScript (e.g., inline editing).
        page_data = {
            "all_areas_for_select": serialize_for_js(all_areas_query, 'area')
        }

        return render_template(
            'ptps.html',
            title='Process Target Pictures (PTPs)',
            all_steps=all_steps,
            areas_with_steps=areas_with_steps,
            page_data=page_data,  # Pass the new data island object
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None
        )
        # --- END REFACTOR ---
    else:
        return redirect(url_for('auth.login'))

@main_routes.route('/dashboard')
def dashboard():
    if current_user.is_authenticated:
        stats = dashboard_service.get_dashboard_stats(g.db_session)
        
        # --- REFACTOR: Remove unused flat navigation data ---
        return render_template(
            'index.html',
            title='Dashboard',
            total_areas=stats["total_areas"],
            total_steps=stats["total_steps"],
            total_usecases=stats["total_usecases"],
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None
        )
        # --- END REFACTOR ---
    else:
        return redirect(url_for('auth.login'))