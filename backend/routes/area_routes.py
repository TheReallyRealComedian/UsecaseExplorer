# backend/routes/area_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal
from ..models import Area, ProcessStep, UseCase
from ..utils import serialize_for_js
from ..services import area_service

area_routes = Blueprint('areas', __name__,
                        template_folder='../templates',
                        url_prefix='/areas')


@area_routes.route('/')
@login_required
def list_areas():
    session = SessionLocal()
    try:
        all_areas = area_service.get_all_areas_with_details(session)

        all_areas_flat = serialize_for_js(all_areas, 'area')
        all_steps_flat = serialize_for_js(
            session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step'
        )
        all_usecases_flat = serialize_for_js(
            session.query(UseCase).order_by(UseCase.name).all(), 'usecase'
        )

        return render_template(
            'area_overview.html',
            title="All Areas",
            all_areas=all_areas,
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
        )
    finally:
        session.close()


@area_routes.route('/<int:area_id>')
@login_required
def view_area(area_id):
    session = SessionLocal()
    try:
        area = area_service.get_area_by_id(session, area_id)

        if area is None:
            flash(f"Area with ID {area_id} not found.", "warning")
            return redirect(url_for('dashboard'))

        all_areas_flat = serialize_for_js(
            session.query(Area).order_by(Area.name).all(), 'area'
        )
        all_steps_flat = serialize_for_js(
            session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step'
        )
        all_usecases_flat = serialize_for_js(
            session.query(UseCase).order_by(UseCase.name).all(), 'usecase'
        )

        return render_template(
            'area_detail.html',
            title=f"Area: {area.name}",
            area=area,
            current_area=area,
            current_item=area,
            current_step=None,
            current_usecase=None,
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
        )
    finally:
        session.close()


@area_routes.route('/<int:area_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_area(area_id):
    # This function can be refactored next using the same pattern
    session = SessionLocal()
    try:
        area = area_service.get_area_by_id(session, area_id)
        if not area:
            flash(f"Area with ID {area_id} not found.", "warning")
            return redirect(url_for('areas.list_areas'))

        if request.method == 'POST':
            # You could create an update_area(session, area, form_data) service function here
            area.name = request.form['name']
            area.description = request.form['description']
            session.commit()
            flash("Area updated successfully!", "success")
            return redirect(url_for('areas.view_area', area_id=area.id))

        all_areas_flat = serialize_for_js(
            session.query(Area).order_by(Area.name).all(), 'area'
        )
        return render_template(
            'edit_area.html',
            title=f"Edit Area: {area.name}",
            area=area,
            all_areas_flat=all_areas_flat
        )
    except Exception as e:
        session.rollback()
        flash(f"An error occurred: {e}", "danger")
        return redirect(url_for('areas.view_area', area_id=area_id))
    finally:
        session.close()


@area_routes.route('/<int:area_id>/delete', methods=['POST'])
@login_required
def delete_area(area_id):
    # This function can be refactored next using the same pattern
    session = SessionLocal()
    try:
        area = area_service.get_area_by_id(session, area_id)
        if area:
            session.delete(area)
            session.commit()
            flash(f"Area '{area.name}' deleted successfully.", "success")
        else:
            flash(f"Area with ID {area_id} not found.", "warning")
    except Exception as e:
        session.rollback()
        flash(f"Error deleting area: {e}", "danger")
    finally:
        session.close()
    return redirect(url_for('areas.list_areas'))