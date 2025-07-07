# backend/routes/area_routes.py
from flask import Blueprint, g, render_template, flash, redirect, url_for, request
from flask_login import login_required
from sqlalchemy.exc import IntegrityError
import traceback

from ..models import Area, ProcessStep, UseCase
from ..utils import serialize_for_js
from ..services import area_service

area_routes = Blueprint('areas', __name__,
                        template_folder='../templates',
                        url_prefix='/areas')


@area_routes.route('/')
@login_required
def list_areas():
    all_areas = area_service.get_all_areas_with_details(g.db_session)
    return render_template(
        'area_overview.html',
        title="All Areas",
        all_areas=all_areas,
        current_item=None,
        current_area=None,
        current_step=None,
        current_usecase=None
    )


@area_routes.route('/<int:area_id>', methods=['GET', 'POST'])
@login_required
def view_area(area_id):
    area = area_service.get_area_by_id(g.db_session, area_id)

    if area is None:
        flash(f"Area with ID {area_id} not found.", "warning")
        return redirect(url_for('areas.list_areas'))

    if request.method == 'POST':
        try:
            success, message = area_service.update_area_from_form(g.db_session, area, request.form)
            flash(message, 'success' if success else 'danger')
            # Redirect to the same page to show the results (PRG pattern)
            return redirect(url_for('areas.view_area', area_id=area.id))
        except Exception as e:
            g.db_session.rollback()
            flash(f"An unexpected error occurred during update: {e}", "danger")
            traceback.print_exc()

    return render_template(
        'area_detail.html',
        title=f"Area: {area.name}",
        area=area,
        current_area=area,
        current_item=area,
        current_step=None,
        current_usecase=None
    )


@area_routes.route('/<int:area_id>/delete', methods=['POST'])
@login_required
def delete_area(area_id):
    try:
        area = area_service.get_area_by_id(g.db_session, area_id)
        if area:
            area_name = area.name # Get name before deleting
            g.db_session.delete(area)
            g.db_session.commit()
            flash(f"Area '{area_name}' and all its contents deleted successfully.", "success")
        else:
            flash(f"Area with ID {area_id} not found.", "warning")
    except Exception as e:
        g.db_session.rollback()
        flash(f"Error deleting area: {e}", "danger")
    return redirect(url_for('areas.list_areas'))