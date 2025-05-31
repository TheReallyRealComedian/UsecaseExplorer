# backend/routes/data_alignment_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal
from ..models import Area, ProcessStep, UseCase
# NEW IMPORT FOR BREADCRUMBS DATA
from ..app import serialize_for_js
# END NEW IMPORT

data_alignment_routes = Blueprint('data_alignment', __name__,
                                   template_folder='../templates',
                                   url_prefix='/data-alignment')

@data_alignment_routes.route('/')
@login_required
def data_alignment_page():
    session = SessionLocal()
    
    # NEW BREADCRUMB DATA FETCHING
    all_areas_flat = []
    all_steps_flat = []
    all_usecases_flat = []
    # END NEW BREADCRUMB DATA FETCHING

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

        # NEW BREADCRUMB DATA FETCHING
        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        # END NEW BREADCRUMB DATA FETCHING

        return render_template(
            'data_alignment.html',
            title='Data Alignment',
            areas_with_steps=areas_with_steps,
            all_areas=all_areas, # For the dropdown
            areas_steps_usecases=areas_steps_usecases, # For the accordion view
            all_steps=all_steps, # For the dropdown
            current_area=None, # No specific area context for breadcrumbs
            current_step=None, # No specific step context for breadcrumbs
            current_usecase=None, # No specific usecase context for breadcrumbs
            current_item=None, # Indicates this is a top-level page
            # NEW BREADCRUMB DATA PASSING
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
            # END NEW BREADCRUMB DATA PASSING
        )
    except Exception as e:
        flash(f"An error occurred while loading data: {e}", "danger")
        print(f"Error loading data for alignment: {e}")
        return redirect(url_for('index'))
    finally:
        SessionLocal.remove()

@data_alignment_routes.route('/batch-update', methods=['POST'])
@login_required
def batch_update():
    data = request.get_json() # Get JSON payload
    if not data:
        return jsonify(success=False, message="No data received."), 400

    step_area_updates = data.get('step_area_updates', [])
    usecase_step_updates = data.get('usecase_step_updates', [])

    session = SessionLocal()
    results = {
        "success": True,
        "total_updates": len(step_area_updates) + len(usecase_step_updates),
        "successful_updates": 0,
        "failed_updates": [],
        "messages": []
    }

    try:
        # Process Step-Area updates
        for update in step_area_updates:
            step_id = update.get('step_id')
            new_area_id = update.get('new_area_id')

            if not all([step_id, new_area_id]):
                results["failed_updates"].append({"type": "step_area", "data": update, "error": "Missing ID or new area ID."})
                results["success"] = False
                continue

            step = session.query(ProcessStep).options(joinedload(ProcessStep.area)).get(step_id)
            area = session.query(Area).get(new_area_id)

            if not step:
                results["failed_updates"].append({"type": "step_area", "data": update, "error": f"Process Step {step_id} not found."})
                results["success"] = False
                continue
            if not area:
                results["failed_updates"].append({"type": "step_area", "data": update, "error": f"Target Area {new_area_id} not found."})
                results["success"] = False
                continue

            original_area_name = step.area.name if step.area else "N/A"
            step.area_id = new_area_id
            results["successful_updates"] += 1
            results["messages"].append(f"Process Step '{step.name}' (BI_ID: {step.bi_id}) moved from '{original_area_name}' to '{area.name}'.")

        # Process UseCase-Step updates
        for update in usecase_step_updates:
            usecase_id = update.get('usecase_id')
            new_process_step_id = update.get('new_process_step_id')

            if not all([usecase_id, new_process_step_id]):
                results["failed_updates"].append({"type": "usecase_step", "data": update, "error": "Missing ID or new process step ID."})
                results["success"] = False
                continue

            usecase = session.query(UseCase).options(joinedload(UseCase.process_step)).get(usecase_id)
            new_step = session.query(ProcessStep).get(new_process_step_id)

            if not usecase:
                results["failed_updates"].append({"type": "usecase_step", "data": update, "error": f"Use Case {usecase_id} not found."})
                results["success"] = False
                continue
            if not new_step:
                results["failed_updates"].append({"type": "usecase_step", "data": update, "error": f"Target Process Step {new_process_step_id} not found."})
                results["success"] = False
                continue

            original_step_name = usecase.process_step.name if usecase.process_step else "N/A"
            usecase.process_step_id = new_process_step_id
            results["successful_updates"] += 1
            results["messages"].append(f"Use Case '{usecase.name}' (BI_ID: {usecase.bi_id}) moved from '{original_step_name}' to '{new_step.name}'.")

        session.commit()
        if results["successful_updates"] > 0:
            flash(f"Successfully applied {results['successful_updates']} changes.", "success")
        if results["failed_updates"]:
            flash(f"Failed to apply {len(results['failed_updates'])} changes. See console for details.", "danger")
            results["success"] = False # Mark overall as failure if any failed
        
        return jsonify(results), 200

    except IntegrityError as e:
        session.rollback()
        # Log specific integrity errors if necessary
        print(f"Integrity Error during batch update: {e}")
        flash(f"Database integrity error during batch update. Changes rolled back. Error: {str(e)}", "danger")
        results["success"] = False
        results["failed_updates"].append({"type": "database_integrity", "error": str(e)})
        return jsonify(results), 500
    except Exception as e:
        session.rollback()
        print(f"Unexpected error during batch update: {e}")
        flash(f"An unexpected error occurred during batch update. Changes rolled back. Error: {str(e)}", "danger")
        results["success"] = False
        results["failed_updates"].append({"type": "unexpected", "error": str(e)})
        return jsonify(results), 500
    finally:
        SessionLocal.remove()