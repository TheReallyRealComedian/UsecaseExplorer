import os
import traceback
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from flask_login import login_required
import json
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

from ..models import Area, ProcessStep, UseCase
from ..injection_service import (
    process_area_file,
    process_step_file,
    process_usecase_file,
    process_ps_ps_relevance_file,
    process_usecase_area_relevance_file,
    process_usecase_step_relevance_file,
    process_usecase_usecase_relevance_file,
    import_database_from_json, # This function will now accept a string
    finalize_step_import
)
from ..db import SessionLocal

injection_routes = Blueprint('injection', __name__,
                             template_folder='../templates',
                             url_prefix='/data-update')

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

PROCESS_STEP_EDITABLE_FIELDS = {
    "name": "Step Name",
    "bi_id": "Business ID (BI_ID)",
    "area_id": "Parent Area",
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

PROCESS_USECASE_EDITABLE_FIELDS = {
    "name": "Use Case Name",
    "bi_id": "Business ID (BI_ID)",
    "process_step_id": "Parent Process Step",
    "priority": "Priority (1-4)",
    "raw_content": "Raw Content",
    "summary": "Summary",
    "inspiration": "Inspiration",
    "wave": "Wave",
    "effort_level": "Effort Level",
    "status": "Status",
    "business_problem_solved": "Business Problem Solved",
    "target_solution_description": "Target / Solution Description",
    "technologies_text": "Technologies",
    "requirements": "Requirements",
    "relevants_text": "Relevants (Tags)",
    "reduction_time_transfer": "Time Reduction (Transfer)",
    "reduction_time_launches": "Time Reduction (Launches)",
    "reduction_costs_supply": "Cost Reduction (Supply)",
    "quality_improvement_quant": "Quality Improvement",
    "ideation_notes": "Ideation Notes",
    "further_ideas": "Further Ideas",
    "effort_quantification": "Effort Quantification",
    "potential_quantification": "Potential Quantification",
    "dependencies_text": "Redundancies & Dependencies",
    "contact_persons_text": "Contact Persons",
    "related_projects_text": "Related Projects",
}

DEFAULT_SELECT_SIZE = 15

@injection_routes.route('/', methods=['GET', 'POST'])
@login_required
def data_update_page():
    # --- ADD THESE LINES HERE ---
    print("---------- DEBUG: Data Update Page Route Entered ----------")
    print(f"Request Method: {request.method}")
    print(f"Request Form Keys: {request.form.keys()}")
    print(f"Request Files Keys: {request.files.keys()}")
    print("---------------------------------------------------------")
    # --- END ADDITION ---

    session_db = SessionLocal()
    all_areas = []
    all_steps = []
    all_usecases = []

    # NEW: Data for datalists
    all_area_names = []
    all_step_names = []
    all_usecase_names = []

    try:
        all_areas = session_db.query(Area).order_by(Area.name).all() # Keep order by name for datalist suggestions
        all_steps = session_db.query(ProcessStep).options(joinedload(ProcessStep.area)).order_by(ProcessStep.id).all()
        all_usecases = session_db.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area)
        ).order_by(UseCase.id).all()

        # Populate datalist names
        all_area_names = sorted(list(set([area.name for area in all_areas]))) # Get unique names
        all_step_names = sorted(list(set([step.name for step in all_steps]))) # Get unique names
        all_usecase_names = sorted(list(set([uc.name for uc in all_usecases]))) # Get unique names

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

            # This is the /database/json route, but now handled directly by this function for simpler POST
            elif 'database_file' in request.files:
                file = request.files['database_file']
                print(f"DEBUG: database_file detected. Filename: {file.filename}") # ADDED PRINT STATEMENT
                if file.filename == '':
                    flash('No selected database file.', 'warning')
                    return redirect(request.url)
                if file and '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() == 'json':
                    clear_data = request.form.get('clear_existing_data') == 'on'

                    # START OF ADDITION FOR DEBUGGING DATABASE IMPORT
                    print("DEBUG: database_file upload detected in data_update_page POST.")
                    print(f"DEBUG: Clear existing data: {clear_data}")

                    try:
                        # Read the entire file content into memory first
                        # This can be memory intensive for very large files, but is more robust
                        # against issues with `file.stream` directly with json.load/loads.
                        file_content = file.read().decode('utf-8')
                        print(f"DEBUG: File content for database import read. Length: {len(file_content)} characters.")

                        # Pass the string content to the service function
                        result = import_database_from_json(file_content, clear_existing_data=clear_data)
                        flash_category = 'success' if result['success'] else 'danger'
                        flash(result['message'], flash_category)
                        print(f"DEBUG: Database import result: {result['message']}")
                    except UnicodeDecodeError:
                        flash("Error: Could not decode database file content. Ensure it's UTF-8.", 'danger')
                        print("ERROR: UnicodeDecodeError during database file read.")
                    except json.JSONDecodeError as e:
                        flash(f"Invalid JSON format in the uploaded database file: {e}", 'danger')
                        print(f"ERROR: JSONDecodeError during database file import: {e}")
                    except Exception as e:
                        traceback.print_exc()
                        flash(f"An unexpected error occurred during database import: {str(e)}", 'danger')
                        print(f"ERROR: Unexpected exception during database import: {e}")
                    # END OF ADDITION FOR DEBUGGING DATABASE IMPORT
                else:
                    flash('Invalid file type for database import. Please upload a .json file.', 'danger')
                    print("DEBUG: Invalid file type for database import.")
                return redirect(request.url)

            else:
                flash('No file submitted or unknown form field.', 'warning')
                return redirect(request.url)

        except Exception as e:
            traceback.print_exc()
            flash(f"An unexpected error occurred: {str(e)}", "danger")
            return redirect(request.url)

    return render_template(
        'data_update.html',
        title='Data Update',
        all_areas=all_areas,
        all_steps=all_steps,
        all_usecases=all_usecases,
        default_select_size=DEFAULT_SELECT_SIZE,
        # NEW: Pass datalist names
        all_area_names=all_area_names,
        all_step_names=all_step_names,
        all_usecase_names=all_usecase_names,
        current_item=None # Indicates this is a top-level page
    )

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

@injection_routes.route('/usecases/prepare-for-edit', methods=['POST'])
@login_required
def prepare_usecases_for_edit():
    selected_usecase_ids_str = request.form.getlist('selected_update_usecases')
    if not selected_usecase_ids_str:
        flash("No use cases selected for editing.", "warning")
        return redirect(url_for('injection.data_update_page'))

    selected_usecase_ids = [int(uid) for uid in selected_usecase_ids_str if uid.isdigit()]

    session_db = SessionLocal()
    try:
        usecases_to_edit_raw = session_db.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area)
        ).filter(UseCase.id.in_(selected_usecase_ids)).all()

        usecases_to_edit_serializable = []
        for uc in usecases_to_edit_raw:
            uc_dict = {
                'id': uc.id,
                'bi_id': uc.bi_id,
                'name': uc.name,
                'process_step_id': uc.process_step_id,
                'process_step_name': uc.process_step.name if uc.process_step else 'N/A', # For display
                'area_name': uc.process_step.area.name if uc.process_step and uc.process_step.area else 'N/A', # For display
            }
            # Populate current_ values for all editable fields
            for field_key in PROCESS_USECASE_EDITABLE_FIELDS.keys():
                if field_key == 'process_step_id':
                    uc_dict['current_process_step_id'] = uc.process_step_id
                    uc_dict['current_process_step_name'] = uc.process_step.name if uc.process_step else 'N/A'
                elif field_key == 'priority':
                    uc_dict['current_priority'] = uc.priority # Allow None for priority
                else:
                    value = getattr(uc, field_key)
                    uc_dict[f'current_{field_key}'] = value if value is not None else '' # Ensure empty string for text fields

            # Initialize new_values with current values
            uc_dict['new_values'] = {k: uc_dict[f'current_{k}'] for k in PROCESS_USECASE_EDITABLE_FIELDS.keys()}
            uc_dict['new_values']['process_step_id'] = uc.process_step_id # Ensure ID is stored for dropdown

            usecases_to_edit_serializable.append(uc_dict)

        session['usecases_to_edit'] = usecases_to_edit_serializable
        flash(f"Prepared {len(usecases_to_edit_serializable)} use case(s) for editing.", "info")
        return redirect(url_for('injection.edit_selected_usecases'))

    except Exception as e:
        traceback.print_exc()
        flash(f"Error preparing use cases for edit: {e}", "danger")
        return redirect(url_for('injection.data_update_page'))
    finally:
        SessionLocal.remove()

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
        steps_data=steps_data, # The data being edited
        editable_fields=PROCESS_STEP_EDITABLE_FIELDS, # Config for fields
        all_areas=all_areas_for_dropdown, # For area dropdowns in the edit form
        current_item=None # Indicates this is a top-level page
    )

@injection_routes.route('/usecases/edit-selected-usecases', methods=['GET'])
@login_required
def edit_selected_usecases():
    usecases_data = session.get('usecases_to_edit', [])
    if not usecases_data:
        flash("No use cases to edit. Please select some from the Data Update page.", "warning")
        return redirect(url_for('injection.data_update_page'))

    session_db = SessionLocal()
    all_steps_for_dropdown = []
    try:
        all_steps_for_dropdown = session_db.query(ProcessStep).order_by(ProcessStep.name).all()
        # Convert to serializable dicts (for passing to JS)
        all_steps_for_dropdown = [{'id': ps.id, 'name': ps.name, 'bi_id': ps.bi_id} for ps in all_steps_for_dropdown]
    except Exception as e:
        print(f"Error loading steps for dropdown in edit_selected_usecases: {e}")
        flash("Error loading steps for dropdowns. Step selection might be limited.", "danger")
    finally:
        SessionLocal.remove()

    return render_template(
        'edit_multiple_usecases.html',
        title='Bulk Edit Use Cases',
        usecases_data=usecases_data, # The data being edited
        editable_fields=PROCESS_USECASE_EDITABLE_FIELDS, # Config for fields
        all_steps=all_steps_for_dropdown, # For process step dropdowns in the edit form
        current_item=None # Indicates this is a top-level page
    )

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

@injection_routes.route('/usecases/save-all-changes', methods=['POST'])
@login_required
def save_all_usecase_changes():
    changes_to_apply = request.get_json()
    if not changes_to_apply:
        return jsonify({"success": False, "message": "No changes received."}), 400

    session_db = SessionLocal()
    updated_count = 0
    failed_updates = []

    try:
        for change_item in changes_to_apply:
            uc_id = change_item.get('id')
            updated_fields = change_item.get('updated_fields', {})

            if not uc_id or not updated_fields:
                failed_updates.append({"id": uc_id, "error": "Missing usecase_id or updated_fields."})
                continue

            usecase = session_db.query(UseCase).get(uc_id)
            if not usecase:
                failed_updates.append({"id": uc_id, "error": f"Use Case {uc_id} not found."})
                continue

            for field_name, new_value in updated_fields.items():
                if hasattr(usecase, field_name):
                    final_value = None
                    if isinstance(new_value, str):
                        final_value = new_value.strip() if new_value.strip() else None
                    elif new_value is not None:
                        final_value = new_value # Keep non-string, non-None values as is (e.g. integer 0, False)

                    # Special handling for integer fields
                    if field_name in ['priority', 'process_step_id']:
                        if final_value is None: # Allow None if field is nullable
                            setattr(usecase, field_name, None)
                        else:
                            try:
                                # Ensure it's an integer for DB, then validate range for priority
                                int_value = int(final_value)
                                if field_name == 'priority' and not (1 <= int_value <= 4):
                                    raise ValueError("Priority must be between 1 and 4.")
                                setattr(usecase, field_name, int_value)
                            except (ValueError, TypeError):
                                failed_updates.append({"id": uc_id, "field": field_name, "error": f"Invalid format for {field_name}. Must be an integer."})
                                continue # Skip this field, try next one
                    else:
                        setattr(usecase, field_name, final_value)
            updated_count += 1

        session_db.commit()
        session.pop('usecases_to_edit', None) # Clear session data after successful save
        return jsonify({
            "success": True,
            "message": f"Successfully updated {updated_count} use case(s).",
            "updated_count": updated_count,
            "failed_updates": failed_updates
        })

    except IntegrityError as e:
        session_db.rollback()
        print(f"Integrity Error during bulk usecase update: {e}")
        # Extract specific error details for user if possible (e.g., duplicate BI_ID, invalid FK)
        if 'bi_id' in str(e).lower() and 'unique' in str(e).lower():
            error_message = "Duplicate Business ID (BI_ID) detected for one or more use cases."
        elif 'priority_range_check' in str(e).lower():
            error_message = "Priority must be between 1 and 4 for one or more use cases."
        elif 'process_step_id' in str(e).lower() and 'foreign key' in str(e).lower():
            error_message = "Invalid Process Step ID for one or more use cases."
        else:
            error_message = f"Database integrity error during bulk update. Changes rolled back. Error: {str(e)}"

        return jsonify({
            "success": False,
            "message": error_message,
            "failed_updates": failed_updates # Include any previous failures
        }), 500
    except Exception as e:
        session_db.rollback()
        traceback.print_exc()
        return jsonify({
            "success": False,
            "message": f"An unexpected error occurred during bulk usecase update: {str(e)}",
            "failed_updates": failed_updates # Include any previous failures
        }), 500
    finally:
        SessionLocal.remove()

@injection_routes.route('/steps/preview', methods=['GET'])
@login_required
def preview_steps_injection():
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
        all_areas=serializable_areas, # Pass the serializable list for dropdowns
        current_item=None # Indicates this is a top-level page
    )

@injection_routes.route('/steps/finalize', methods=['POST'])
@login_required
def finalize_steps_injection():
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