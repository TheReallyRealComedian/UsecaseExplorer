# backend/routes/area_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal
from ..models import Area, ProcessStep, UseCase, UsecaseAreaRelevance
from ..utils import serialize_for_js

area_routes = Blueprint('areas', __name__,
                        template_folder='../templates',
                        url_prefix='/areas')

@area_routes.route('/<int:area_id>')
@login_required
def view_area(area_id):
    session = SessionLocal()
    try:
        area = session.query(Area).options(
            selectinload(Area.process_steps).selectinload(ProcessStep.use_cases),
            selectinload(Area.usecase_relevance)
                .joinedload(UsecaseAreaRelevance.source_usecase)
        ).get(area_id)

        if area is None:
            flash(f"Area with ID {area_id} not found.", "warning")
            return redirect(url_for('dashboard'))

        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')

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
    session = SessionLocal()
    area = session.query(Area).get(area_id)

    if area is None:
        flash(f"Area with ID {area_id} not found.", "warning")
        session.close()
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        new_name = request.form.get('name', '').strip()
        new_description = request.form.get('description', '').strip()

        if not new_name:
            flash("Area name cannot be empty.", "danger")
        else:
            # Check for name conflicts only if the name is actually changing
            if new_name != area.name:
                existing_area = session.query(Area).filter(Area.name == new_name, Area.id != area_id).first()
                if existing_area:
                    flash(f"Another area with the name '{new_name}' already exists.", "danger")
                    # Don't update the area object, just return the form with error
                    all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
                    all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
                    all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
                    session.close()
                    return render_template(
                        'edit_area.html',
                        title=f"Edit Area: {area.name}",
                        area=area,
                        current_area=area,
                        current_item=area,
                        current_step=None,
                        current_usecase=None,
                        all_areas_flat=all_areas_flat,
                        all_steps_flat=all_steps_flat,
                        all_usecases_flat=all_usecases_flat
                    )

            # If we reach here, no name conflict exists (or name didn't change)
            area.name = new_name
            area.description = new_description if new_description else None
            try:
                session.commit()
                flash("Area updated successfully!", "success")
                session.close()
                return redirect(url_for('areas.view_area', area_id=area.id))
            except IntegrityError:
                session.rollback()
                flash("Database error: Could not update area. The name might already exist.", "danger")
            except Exception as e:
                session.rollback()
                flash(f"An unexpected error occurred: {e}", "danger")
                print(f"Error updating area {area_id}: {e}")
    
    # GET request or POST with validation errors
    all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
    all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
    all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
    session.close()

    return render_template(
        'edit_area.html',
        title=f"Edit Area: {area.name}",
        area=area,
        current_area=area,
        current_item=area,
        current_step=None,
        current_usecase=None,
        all_areas_flat=all_areas_flat,
        all_steps_flat=all_steps_flat,
        all_usecases_flat=all_usecases_flat
    )


@area_routes.route('/<int:area_id>/delete', methods=['POST'])
@login_required
def delete_area(area_id):
    session = SessionLocal()
    area = session.query(Area).get(area_id)

    if area is None:
        flash(f"Area with ID {area_id} not found.", "warning")
        session.close() # Close the session here since finally won't be reached in this branch
        return redirect(url_for('dashboard'))
    else:
        try:
            session.delete(area)
            session.commit()
            flash(f"Area '{area.name}' and all its contents deleted successfully.", "success")
        except Exception as e:
            session.rollback()
            flash(f"Error deleting area: {e}", "danger")
            print(f"Error deleting area {area_id}: {e}")
        finally:
            # THIS IS THE FIX: Indent this block
            session.close()

    return redirect(url_for('dashboard'))