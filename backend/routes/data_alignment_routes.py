# backend/routes/data_alignment_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required
from sqlalchemy.orm import joinedload # Using joinedload for efficiency
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal
from ..models import Area, ProcessStep, UseCase

data_alignment_routes = Blueprint('data_alignment', __name__,
                                   template_folder='../templates',
                                   url_prefix='/data-alignment')

@data_alignment_routes.route('/')
@login_required
def data_alignment_page():
    session = SessionLocal()
    try:
        # Section 1: Areas & Steps
        # Load all areas with their process steps, and eager load the area for each step
        # to ensure area.name is available for the step's current area display.
        areas_with_steps = session.query(Area).options(
            joinedload(Area.process_steps)
        ).order_by(Area.name).all()

        # Load all areas for the 'assign new area' dropdown in Section 1
        all_areas = session.query(Area).order_by(Area.name).all()

        # Section 2: Steps & Use-Cases
        # Load all areas, then their steps, then their use cases.
        # Also eager load the area for each step, and the process_step for each use_case,
        # to get names and BI_IDs for display.
        areas_steps_usecases = session.query(Area).options(
            joinedload(Area.process_steps).joinedload(ProcessStep.use_cases)
        ).order_by(Area.name).all()

        # Load all process steps for the 'assign new step' dropdown in Section 2
        # Eager load the area for each step for displaying (Area Name - BI_ID) in dropdown
        all_steps = session.query(ProcessStep).options(joinedload(ProcessStep.area)).order_by(ProcessStep.name).all()

        return render_template(
            'data_alignment.html',
            title='Data Alignment',
            areas_with_steps=areas_with_steps,
            all_areas=all_areas,
            areas_steps_usecases=areas_steps_usecases,
            all_steps=all_steps,
            current_area=None, # No specific area context for breadcrumbs
            current_step=None, # No specific step context for breadcrumbs
            current_usecase=None # No specific usecase context for breadcrumbs
        )
    except Exception as e:
        flash(f"An error occurred while loading data: {e}", "danger")
        print(f"Error loading data for alignment: {e}")
        return redirect(url_for('index'))
    finally:
        SessionLocal.remove()

@data_alignment_routes.route('/update_step_area', methods=['POST'])
@login_required
def update_step_area():
    step_id = request.form.get('step_id', type=int)
    new_area_id = request.form.get('new_area_id', type=int)

    if not all([step_id, new_area_id]):
        return jsonify(success=False, message="Missing step ID or new area ID."), 400

    session = SessionLocal()
    try:
        step = session.query(ProcessStep).options(joinedload(ProcessStep.area)).get(step_id)
        area = session.query(Area).get(new_area_id)

        if not step:
            return jsonify(success=False, message="Process Step not found."), 404
        if not area:
            return jsonify(success=False, message="Target Area not found."), 404

        original_area_name = step.area.name if step.area else "N/A"
        step.area_id = new_area_id
        session.commit()
        # Flash message for user feedback on page reload
        flash(f"Process Step '{step.name}' (BI_ID: {step.bi_id}) moved from '{original_area_name}' to '{area.name}' successfully.", "success")
        return jsonify(success=True, message="Process Step area updated."), 200
    except IntegrityError:
        session.rollback()
        # More specific error for integrity issues
        flash("A database integrity error occurred. The step might already exist under the target area with the same BI_ID if that constraint exists, or a foreign key was violated.", "danger")
        return jsonify(success=False, message="Database integrity error."), 500
    except Exception as e:
        session.rollback()
        print(f"Error updating step area for step {step_id}: {e}")
        flash(f"An unexpected error occurred: {e}", "danger")
        return jsonify(success=False, message=f"An unexpected error occurred: {e}"), 500
    finally:
        SessionLocal.remove()

@data_alignment_routes.route('/update_usecase_step', methods=['POST'])
@login_required
def update_usecase_step():
    usecase_id = request.form.get('usecase_id', type=int)
    new_process_step_id = request.form.get('new_process_step_id', type=int)

    if not all([usecase_id, new_process_step_id]):
        return jsonify(success=False, message="Missing use case ID or new process step ID."), 400

    session = SessionLocal()
    try:
        usecase = session.query(UseCase).options(joinedload(UseCase.process_step)).get(usecase_id)
        new_step = session.query(ProcessStep).get(new_process_step_id)

        if not usecase:
            return jsonify(success=False, message="Use Case not found."), 404
        if not new_step:
            return jsonify(success=False, message="Target Process Step not found."), 404

        original_step_name = usecase.process_step.name if usecase.process_step else "N/A"
        usecase.process_step_id = new_process_step_id
        session.commit()
        # Flash message for user feedback on page reload
        flash(f"Use Case '{usecase.name}' (BI_ID: {usecase.bi_id}) moved from '{original_step_name}' to '{new_step.name}' successfully.", "success")
        return jsonify(success=True, message="Use Case process step updated."), 200
    except IntegrityError:
        session.rollback()
        # More specific error for integrity issues
        flash("A database integrity error occurred. The use case might already exist under the target step with the same BI_ID if that constraint exists, or a foreign key was violated.", "danger")
        return jsonify(success=False, message="Database integrity error."), 500
    except Exception as e:
        session.rollback()
        print(f"Error updating use case step for usecase {usecase_id}: {e}")
        flash(f"An unexpected error occurred: {e}", "danger")
        return jsonify(success=False, message=f"An unexpected error occurred: {e}"), 500
    finally:
        SessionLocal.remove()