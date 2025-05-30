# backend/routes/injection_routes.py
import os
import traceback
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from flask_login import login_required
import json
from sqlalchemy.orm import joinedload # Import joinedload for fetching related data

from ..models import Area, ProcessStep, UseCase
from ..injection_service import (
    process_area_file,
    process_step_file, # This is now for preview
    process_usecase_file,
    process_ps_ps_relevance_file,
    process_usecase_area_relevance_file,
    process_usecase_step_relevance_file,
    process_usecase_usecase_relevance_file,
    import_database_from_json,
    finalize_step_import # NEW import for finalization
)
from ..db import SessionLocal # Import SessionLocal to fetch all_areas

injection_routes = Blueprint('injection', __name__,
                             template_folder='../templates',
                             url_prefix='/data-update') # CHANGED URL PREFIX

# Define fields for ProcessStep for dynamic rendering in modal template
STEP_DETAIL_FIELDS = {
    "step_description": "Short Description",
    "raw_content": "Raw Content",
    "summary": "Generic Summary",
    "vision_statement": "Vision Statement",
    "in_scope": "In Scope",
    "out_of_scope": "Out of Scope",
    "interfaces_text": "Interfaces",
    "what_is_actually_done": "What is Actually Done",
    "pain_points": "Pain Points",
    "targets_text": "Targets",
}

# Mapping of field names to their display labels, for use in the new edit_multiple_steps.html
# This makes it easy to iterate and display in the 3-column view.
PROCESS_STEP_EDITABLE_FIELDS = {
    "name": "Step Name",
    "bi_id": "Business ID (BI_ID)",
    "area_id": "Parent Area", # Special handling needed for dropdown
    "step_description": "Short Description",
    "raw_content": "Raw Content",
    "summary": "Generic Summary",
    "vision_statement": "Vision Statement",
    "in_scope": "In Scope",
    "out_of_scope": "Out of Scope",
    "interfaces_text": "Interfaces",
    "what_is_actually_done": "What is Actually Done",
    "pain_points": "Pain Points",
    "targets_text": "Targets",
}


@injection_routes.route('/', methods=['GET', 'POST'])
@login_required
def data_update_page(): # RENAMED FUNCTION
    session_db = SessionLocal()
    all_areas = []
    all_steps = []
    all_usecases = []

    try:
        all_areas = session_db.query(Area).order_by(Area.name).all()
        # Eager load area for steps to display area name in select option
        all_steps = session_db.query(ProcessStep).options(joinedload(ProcessStep.area)).order_by(ProcessStep.name).all()
        # Eager load process_step and area for use cases to display them in select option
        all_usecases = session_db.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area)
        ).order_by(UseCase.name).all()
    except Exception as e:
        print(f"Error loading initial data for data_update_page: {e}")
        flash("Error loading data for selection. Please try again.", "danger")
    finally:
        SessionLocal.remove()

    if request.method == 'POST':
        try:
            # The file upload logic remains largely the same, just adjust the flash messages
            # and redirects as needed for the new context.
            if 'area_file' in request.files:
                file = request.files['area_file']
                if file.filename == '' or not file:
                    flash('No selected file for Areas.', 'warning')
                    return redirect(request.url)
                if file and '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() == 'json':
                    result = process_area_file(file.stream)
                    flash_category = 'success' if result['success'] else 'danger'
                    if not result['success'] and result['added_count'] == 0 and result['skipped_count'] > 0 :
                        flash_category = 'warning'
                    flash(result['message'], flash_category)
                    return redirect(request.url)
                else:
                    flash('Invalid file type or name for Areas. Please upload a .json file.', 'danger')
                    return redirect(request.url)

            elif 'step_file' in request.files:
                file = request.files['step_file']
                if file.filename == '' or not file:
                    flash('No selected file for Process Steps.', 'warning')
                    return redirect(request.url)
                if file and '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() == 'json':
                    file_content_str = file.read().decode('utf-8')
                    try:
                        parsed_json_data = json.loads(file_content_str)
                    except json.JSONDecodeError:
                        flash('Invalid JSON format in the uploaded file.', 'danger')
                        return redirect(request.url)
                    result = process_step_file(parsed_json_data)
                    
                    if result['success']:
                        session['step_import_preview_data'] = result['preview_data']
                        flash('Step file uploaded. Please review changes before finalizing import.', 'info')
                        return redirect(url_for('injection.preview_steps_injection'))
                    else:
                        flash(result['message'], 'danger')
                        return redirect(request.url)
                else:
                    flash('Invalid file type or name for Process Steps. Please upload a .json file.', 'danger')
                    return redirect(request.url)
            
            elif 'usecase_file' in request.files:
                file = request.files['usecase_file']
                if file.filename == '' or not file:
                    flash('No selected file for Use Cases.', 'warning')
                    return redirect(request.url)
                if file and '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() == 'json':
                    result = process_usecase_file(file.stream)
                    flash_category = 'danger'
                    if result['success'] and result['added_count'] > 0:
                        flash_category = 'success'
                    elif result['success'] and result['added_count'] == 0 and result['skipped_count'] > 0:
                        flash_category = 'warning'
                    elif not result['success'] and 'Error:' not in result.get('message', ''):
                         flash_category = 'warning'
                    flash(result['message'], flash_category)
                    return redirect(request.url)
                else:
                     flash('Invalid file type or name for Use Cases. Please upload a .json file.', 'danger')
                     return redirect(request.url)

            elif 'ps_ps_relevance_file' in request.files:
                file = request.files['ps_ps_relevance_file']
                if file.filename == '' or not file:
                    flash('No selected file for Process Step Relevance.', 'warning')
                    return redirect(request.url)
                if file and '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() == 'json':
                    result = process_ps_ps_relevance_file(file.stream)
                    flash_category = 'danger'
                    if result['success'] and result['added_count'] > 0:
                        flash_category = 'success'
                    elif result['success'] and result['added_count'] == 0 and result['skipped_count'] > 0:
                        flash_category = 'warning'
                    elif not result['success'] and 'Error:' not in result.get('message', ''):
                         flash_category = 'warning'
                    flash(result['message'], flash_category)
                    if result.get('skipped_errors'):
                        for err_msg in result['skipped_errors']:
                            pass
                    return redirect(request.url)
                else:
                     flash('Invalid file type or name for Process Step Relevance. Please upload a .json file.', 'danger')
                     return redirect(request.url)

            elif 'usecase_area_relevance_file' in request.files:
                file = request.files['usecase_area_relevance_file']
                if file.filename == '' or not file:
                    flash('No selected file for Use Case-Area Relevance.', 'warning')
                    return redirect(request.url)
                if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() == 'json':
                    result = process_usecase_area_relevance_file(file.stream)
                    flash_category = 'success' if result['success'] and result['added_count'] > 0 else 'danger'
                    if result['success'] and result['added_count'] == 0 and result['skipped_count'] > 0:
                        flash_category = 'warning'
                    flash(result['message'], flash_category)
                    return redirect(request.url)
                else:
                    flash('Invalid file type or name for Use Case-Area Relevance. Please upload a .json file.', 'danger')
                    return redirect(request.url)

            elif 'usecase_step_relevance_file' in request.files:
                file = request.files['usecase_step_relevance_file']
                if file.filename == '' or not file:
                    flash('No selected file for Use Case-Step Relevance.', 'warning')
                    return redirect(request.url)
                if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() == 'json':
                    result = process_usecase_step_relevance_file(file.stream)
                    flash_category = 'success' if result['success'] and result['added_count'] > 0 else 'danger'
                    if result['success'] and result['added_count'] == 0 and result['skipped_count'] > 0:
                        flash_category = 'warning'
                    flash(result['message'], flash_category)
                    return redirect(request.url)
                else:
                    flash('Invalid file type or name for Use Case-Step Relevance. Please upload a .json file.', 'danger')
                    return redirect(request.url)

            elif 'usecase_usecase_relevance_file' in request.files:
                file = request.files['usecase_usecase_relevance_file']
                if file.filename == '' or not file:
                    flash('No selected file for Use Case-Use Case Relevance.', 'warning')
                    return redirect(request.url)
                if file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() == 'json':
                    result = process_usecase_usecase_relevance_file(file.stream)
                    flash_category = 'success' if result['success'] and result['added_count'] > 0 else 'danger'
                    if result['success'] and result['added_count'] == 0 and result['skipped_count'] > 0:
                        flash_category = 'warning'
                    flash(result['message'], flash_category)
                    return redirect(request.url)
                else:
                    flash('Invalid file type or name for Use Case-Use Case Relevance. Please upload a .json file.', 'danger')
                    return redirect(request.url)

            elif 'database_file' in request.files:
                file = request.files['database_file']
                if file.filename == '':
                    flash('No selected database file.', 'warning')
                    return redirect(request.url)
                if file and '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() == 'json':
                    clear_data = request.form.get('clear_existing_data') == 'on'
                    try:
                        result = import_database_from_json(file.stream, clear_existing_data=clear_data)
                        flash_category = 'success' if result['success'] else 'danger'
                        flash(result['message'], flash_category)
                    except Exception as e:
                        traceback.print_exc()
                        flash(f"An error occurred during database import: {str(e)}", 'danger')
                else:
                    flash('Invalid file type for database import. Please upload a .json file.', 'danger')
                return redirect(request.url)

            else:
                flash('No file submitted or unknown form field.', 'warning')
                return redirect(request.url)

        except Exception as e:
            traceback.print_exc()
            flash(f"An unexpected error occurred: {str(e)}", 'danger')
            return redirect(request.url)

    # --- GET Logic ---
    return render_template(
        'data_update.html', # RENAMED TEMPLATE
        title='Data Update',
        all_areas=all_areas,
        all_steps=all_steps,
        all_usecases=all_usecases
    )

# NEW ROUTE: Endpoint to prepare selected steps for bulk editing
@injection_routes.route('/steps/prepare-for-edit', methods=['POST'])
@login_required
def prepare_steps_for_edit():
    selected_step_ids_str = request.form.getlist('selected_update_steps')
    if not selected_step_ids_str:
        flash("No process steps selected for editing.", "warning")
        return redirect(url_for('injection.data_update_page'))

    selected_step_ids = [int(sid) for sid in selected_step_ids_str if sid.isdigit()]
    
    session_db = SessionLocal()
    try:
        steps_to_edit_raw = session_db.query(ProcessStep).options(joinedload(ProcessStep.area)).filter(ProcessStep.id.in_(selected_step_ids)).all()
        
        # Convert SQLAlchemy objects to serializable dictionaries for session storage
        # and to simplify JS processing.
        steps_to_edit_serializable = []
        for step in steps_to_edit_raw:
            step_dict = {
                'id': step.id,
                'bi_id': step.bi_id,
                'name': step.name,
                'area_id': step.area_id,
                'area_name': step.area.name if step.area else 'N/A', # For display
                # Include all editable fields with their current values
            }
            for field_key in PROCESS_STEP_EDITABLE_FIELDS.keys():
                # Special handling for 'area_id' as it's a FK and displayed differently
                if field_key == 'area_id':
                    # Value for input should be the ID, display name separately
                    step_dict['current_area_id'] = step.area_id
                    step_dict['current_area_name'] = step.area.name if step.area else 'N/A'
                else:
                    value = getattr(step, field_key)
                    step_dict[f'current_{field_key}'] = value if value is not None else '' # Ensure empty string for input fields

            # This 'new_values' dict will store the *proposed* changes from the user
            # It starts as a copy of current values.
            step_dict['new_values'] = {k: step_dict[f'current_{k}'] for k in PROCESS_STEP_EDITABLE_FIELDS.keys()}
            # For area_id in new_values, store the ID, not the name
            step_dict['new_values']['area_id'] = step.area_id

            steps_to_edit_serializable.append(step_dict)

        session['steps_to_edit'] = steps_to_edit_serializable
        flash(f"Prepared {len(steps_to_edit_serializable)} process step(s) for editing.", "info")
        return redirect(url_for('injection.edit_selected_steps'))

    except Exception as e:
        traceback.print_exc()
        flash(f"Error preparing steps for edit: {e}", "danger")
        return redirect(url_for('injection.data_update_page'))
    finally:
        SessionLocal.remove()

# NEW ROUTE: Page for bulk editing selected steps
@injection_routes.route('/steps/edit-selected-steps', methods=['GET'])
@login_required
def edit_selected_steps():
    steps_data = session.get('steps_to_edit', [])
    if not steps_data:
        flash("No process steps to edit. Please select some from the Data Update page.", "warning")
        return redirect(url_for('injection.data_update_page'))
    
    session_db = SessionLocal()
    all_areas_for_dropdown = []
    try:
        all_areas_for_dropdown = session_db.query(Area).order_by(Area.name).all()
        # Convert to serializable dicts if not already (for passing to JS)
        all_areas_for_dropdown = [{'id': a.id, 'name': a.name} for a in all_areas_for_dropdown]
    except Exception as e:
        print(f"Error loading areas for dropdown in edit_selected_steps: {e}")
        flash("Error loading areas for dropdowns. Area selection might be limited.", "danger")
    finally:
        SessionLocal.remove()

    return render_template(
        'edit_multiple_steps.html',
        title='Bulk Edit Process Steps',
        steps_data=steps_data,
        editable_fields=PROCESS_STEP_EDITABLE_FIELDS,
        all_areas=all_areas_for_dropdown # Pass areas for the dropdowns
    )

# NEW ROUTE: AJAX endpoint for saving all pending changes from edit_multiple_steps.html
@injection_routes.route('/steps/save-all-changes', methods=['POST'])
@login_required
def save_all_step_changes():
    changes_to_apply = request.get_json()
    if not changes_to_apply:
        return jsonify({"success": False, "message": "No changes received."}), 400

    session_db = SessionLocal()
    updated_count = 0
    failed_updates = []

    try:
        for change_item in changes_to_apply:
            step_id = change_item.get('id')
            updated_fields = change_item.get('updated_fields', {})

            if not step_id or not updated_fields:
                failed_updates.append({"id": step_id, "error": "Missing step_id or updated_fields."})
                continue

            step = session_db.query(ProcessStep).get(step_id)
            if not step:
                failed_updates.append({"id": step_id, "error": f"Process Step {step_id} not found."})
                continue

            for field_name, new_value in updated_fields.items():
                if hasattr(step, field_name):
                    # Handle empty strings from form inputs, convert to None for nullable fields
                    final_value = new_value.strip() if isinstance(new_value, str) and new_value.strip() else None
                    if field_name == 'area_id' and final_value is not None:
                        # Ensure area_id is an integer
                        try:
                            final_value = int(final_value)
                        except ValueError:
                            failed_updates.append({"id": step_id, "field": field_name, "error": "Invalid area ID format."})
                            continue
                    
                    setattr(step, field_name, final_value)
            updated_count += 1
        
        session_db.commit()
        session.pop('steps_to_edit', None) # Clear session data after successful save
        return jsonify({
            "success": True,
            "message": f"Successfully updated {updated_count} process step(s).",
            "updated_count": updated_count,
            "failed_updates": failed_updates
        })

    except IntegrityError as e:
        session_db.rollback()
        print(f"Integrity Error during bulk update: {e}")
        return jsonify({
            "success": False,
            "message": f"Database integrity error during bulk update. Changes rolled back. Error: {str(e)}",
            "failed_updates": failed_updates # Include any previous failures
        }), 500
    except Exception as e:
        session_db.rollback()
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"An unexpected error occurred during bulk update: {str(e)}",
            "failed_updates": failed_updates # Include any previous failures
        }), 500
    finally:
        SessionLocal.remove()

# This route remains for file injection preview only
@injection_routes.route('/steps/preview', methods=['GET'])
@login_required
def preview_steps_injection():
    # ... (existing content of preview_steps_injection) ...
    """
    Displays a preview of Process Step changes for user review and resolution.
    Data is retrieved from the Flask session.
    """
    preview_data = session.get('step_import_preview_data', [])
    if not preview_data:
        flash("No process step data to preview. Please upload a file first.", "warning")
        return redirect(url_for('injection.data_update_page')) # Redirect to new data_update_page

    db_session = SessionLocal()
    
    # Convert SQLAlchemy Area objects to dictionaries for JSON serialization
    serializable_areas = []
    try:
        areas_from_db = db_session.query(Area).order_by(Area.name).all()
        for area in areas_from_db:
            serializable_areas.append({
                'id': area.id,
                'name': area.name,
                'description': area.description # Include other relevant fields if needed in JS
            })
    except Exception as e:
        flash("Error loading areas for preview. Some area selections might be missing.", "danger")
        print(f"Error converting areas for JSON serialization: {e}")
    finally:
        SessionLocal.remove()

    return render_template(
        'step_injection_preview.html',
        title='Process Step Injection Preview',
        preview_data=preview_data,
        step_detail_fields=STEP_DETAIL_FIELDS, # RENAMED context variable
        all_areas=serializable_areas # Pass the serializable list
    )

# This route remains for file injection finalization
@injection_routes.route('/steps/finalize', methods=['POST'])
@login_required
def finalize_steps_injection():
    # ... (existing content of finalize_steps_injection) ...
    """
    Receives user-resolved step data from the frontend and performs database updates.
    """
    resolved_steps_json = request.get_json()
    
    if not resolved_steps_json:
        return jsonify({"success": False, "message": "No data received for finalization."}), 400

    result = finalize_step_import(resolved_steps_json)

    if result['success']:
        session.pop('step_import_preview_data', None)
        flash(f"Process Step import complete: Added {result['added_count']}, Updated {result['updated_count']}, Failed {result['failed_count']}. See server logs for details.", "success")
        return jsonify(result), 200
    else:
        flash(f"Process Step import failed: {result['messages'][-1] if result['messages'] else 'Unknown error'}", "danger")
        return jsonify(result), 500

# This route remains for full database import
@injection_routes.route('/database/json', methods=['POST'])
@login_required
def import_db_json_route():
    # ... (existing content of import_db_json_route) ...
    if 'database_file' not in request.files:
        flash('No database file part in the request.', 'danger')
        return redirect(request.referrer or url_for('injection.data_update_page')) # Redirect to new data_update_page

    file = request.files['database_file']
    if file.filename == '':
        flash('No selected database file.', 'warning')
        return redirect(request.referrer or url_for('injection.data_update_page')) # Redirect to new data_update_page

    if file and '.' in file.filename and \
       file.filename.rsplit('.', 1)[1].lower() == 'json':
        
        clear_data = request.form.get('clear_existing_data') == 'on'
        
        try:
            result = import_database_from_json(file.stream, clear_existing_data=clear_data)
            flash_category = 'success' if result['success'] else 'danger'
            flash(result['message'], flash_category)
        except Exception as e:
            traceback.print_exc()
            flash(f"An error occurred during database import: {str(e)}", 'danger')
    else:
        flash('Invalid file type for database import. Please upload a .json file.', 'danger')
    
    return redirect(request.referrer or url_for('injection.data_update_page')) # Redirect to new data_update_page