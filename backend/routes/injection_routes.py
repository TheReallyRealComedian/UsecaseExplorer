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
    import_database_from_json,
    finalize_step_import # Import the new finalize service function
)
from ..db import SessionLocal
from ..utils import serialize_for_js

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
    "out_of_scope": "Out of_scope",
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
    print("---------- DEBUG: Data Update Page Route Entered ----------")
    print(f"Request Method: {request.method}")
    print(f"Request Form Keys: {request.form.keys()}")
    print(f"Request Files Keys: {request.files.keys()}")
    print("---------------------------------------------------------")

    session_db = SessionLocal()
    all_areas = []
    all_steps = []
    all_usecases = []

    all_area_names = []
    all_step_names = []
    all_usecase_names = []

    all_areas_flat = []
    all_steps_flat = []
    all_usecases_flat = []

    try:
        all_areas = session_db.query(Area).order_by(Area.name).all()
        all_steps = session_db.query(ProcessStep).options(joinedload(ProcessStep.area)).order_by(ProcessStep.id).all()
        all_usecases = session_db.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area)
        ).order_by(UseCase.id).all()

        all_area_names = sorted(list(set([area.name for area in all_areas])))
        all_step_names = sorted(list(set([step.name for step in all_steps])))
        all_usecase_names = sorted(list(set([uc.name for uc in all_usecases])))

        all_areas_flat = serialize_for_js(session_db.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session_db.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session_db.query(UseCase).order_by(UseCase.name).all(), 'usecase')

    except Exception as e:
        print(f"Error loading initial data for data_update_page: {e}")
        flash("Error loading data for selection. Please try again.", "danger")
    finally:
        # SessionLocal.remove() # Handled by app.teardown_request
        pass

    if request.method == 'POST':
        try:
            if 'area_file' in request.files:
                file = request.files['area_file']
                if file.filename == '' or not file:
                    flash('No selected file for Areas.', 'warning')
                    return redirect(request.url)
                if file and '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() == 'json':
                    result = process_area_file(file.stream)
                    # Flash main message
                    flash(result['message'], 'success' if result['success'] else 'danger')
                    # Flash detailed messages for skipped items if any
                    if result.get('skipped_errors_details'):
                        for i, detail in enumerate(result['skipped_errors_details']):
                            if i < 5: # Limit to first 5 for brevity in flash, prompt to check logs
                                flash(f"Skipped Area: {detail}", "warning")
                            else:
                                flash(f"And {len(result['skipped_errors_details']) - i} more. Check server logs for full details on skipped areas.", "warning")
                                break
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
                    except json.JSONDecodeError as e: # Catch JSONDecodeError specifically here
                        flash(f'Invalid JSON format in the uploaded file: {e}.', 'danger')
                        return redirect(request.url)
                    
                    result = process_step_file(parsed_json_data)

                    if result['success']:
                        if result['preview_data']:
                            session['step_import_preview_data'] = result['preview_data']
                            flash('Step file uploaded. Please review changes before finalizing import.', 'info')
                            return redirect(url_for('injection.preview_steps_injection'))
                        else:
                            flash('Step file uploaded but no process steps were found or valid for import. No preview generated.', 'warning')
                            return redirect(request.url)
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
                    # Flash main message based on overall outcome
                    flash_category = 'success'
                    if not result['success']:
                        flash_category = 'danger'
                    elif result['skipped_count'] > 0: # If there are any skips, it's at least a warning
                        flash_category = 'warning'
                    flash(result['message'], flash_category)
                    
                    # Flash detailed skipped messages
                    if result.get('skipped_invalid_format') > 0:
                        flash(f"Invalid format or missing required fields: {result['skipped_invalid_format']} items skipped.", "warning")
                    if result.get('skipped_missing_step') > 0:
                        flash(f"Missing parent process step: {result['skipped_missing_step']} items skipped. Check BI_IDs: {', '.join(result['missing_step_bi_ids'][:5])}{'...' if len(result['missing_step_bi_ids']) > 5 else ''}", "warning")
                    if result.get('skipped_existing_no_update_uc_bi_id_count') > 0:
                        flash(f"Existing use case with no empty fields to fill: {result['skipped_existing_no_update_uc_bi_id_count']} items skipped. BI_IDs: {', '.join(result['uc_bi_ids_existing_no_update'][:5])}{'...' if len(result['uc_bi_ids_existing_no_update']) > 5 else ''}", "warning")
                    if result.get('skipped_invalid_priority') > 0:
                        flash(f"Invalid priority values: {result['skipped_invalid_priority']} items affected. Priority not set for these.", "warning")
                    if result.get('skipped_errors_details'):
                        for i, detail in enumerate(result['skipped_errors_details']):
                            if i < 5:
                                flash(f"Skipped Use Case detail: {detail}", "info") # Use 'info' for less critical per-item details
                            else:
                                flash(f"And {len(result['skipped_errors_details']) - i} more. Check server logs for full details on skipped use cases.", "info")
                                break
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
                    flash_category = 'success'
                    if not result['success']:
                        flash_category = 'danger'
                    elif result['skipped_count'] > 0:
                        flash_category = 'warning'
                    flash(result['message'], flash_category)
                    
                    if result.get('skipped_invalid_format') > 0:
                        flash(f"Invalid format/score: {result['skipped_invalid_format']} links skipped.", "warning")
                    if result.get('skipped_existing_link') > 0:
                        flash(f"Existing links: {result['skipped_existing_link']} links skipped.", "warning")
                    if result.get('skipped_missing_step') > 0:
                        flash(f"Missing source/target steps: {result['skipped_missing_step']} links skipped.", "warning")
                    if result.get('skipped_self_link') > 0:
                        flash(f"Self-referencing links: {result['skipped_self_link']} links skipped.", "warning")
                    if result.get('skipped_errors_details'):
                        for i, detail in enumerate(result['skipped_errors_details']):
                            if i < 5:
                                flash(f"Skipped PS-PS link detail: {detail}", "info")
                            else:
                                flash(f"And {len(result['skipped_errors_details']) - i} more. Check server logs for full details on skipped PS-PS links.", "info")
                                break
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
                    flash_category = 'success'
                    if not result['success']:
                        flash_category = 'danger'
                    elif result['skipped_count'] > 0:
                        flash_category = 'warning'
                    flash(result['message'], flash_category)

                    if result.get('skipped_errors_details'):
                        for i, detail in enumerate(result['skipped_errors_details']):
                            if i < 5:
                                flash(f"Skipped UC-Area link detail: {detail}", "info")
                            else:
                                flash(f"And {len(result['skipped_errors_details']) - i} more. Check server logs for full details on skipped UC-Area links.", "info")
                                break
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
                    flash_category = 'success'
                    if not result['success']:
                        flash_category = 'danger'
                    elif result['skipped_count'] > 0:
                        flash_category = 'warning'
                    flash(result['message'], flash_category)

                    if result.get('skipped_errors_details'):
                        for i, detail in enumerate(result['skipped_errors_details']):
                            if i < 5:
                                flash(f"Skipped UC-Step link detail: {detail}", "info")
                            else:
                                flash(f"And {len(result['skipped_errors_details']) - i} more. Check server logs for full details on skipped UC-Step links.", "info")
                                break
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
                    flash_category = 'success'
                    if not result['success']:
                        flash_category = 'danger'
                    elif result['skipped_count'] > 0:
                        flash_category = 'warning'
                    flash(result['message'], flash_category)

                    if result.get('skipped_errors_details'):
                        for i, detail in enumerate(result['skipped_errors_details']):
                            if i < 5:
                                flash(f"Skipped UC-UC link detail: {detail}", "info")
                            else:
                                flash(f"And {len(result['skipped_errors_details']) - i} more. Check server logs for full details on skipped UC-UC links.", "info")
                                break
                    return redirect(request.url)
                else:
                    flash('Invalid file type or name for Use Case-Use Case Relevance. Please upload a .json file.', 'danger')
                    return redirect(request.url)

            elif 'database_file' in request.files:
                file = request.files['database_file']
                print(f"DEBUG: database_file detected. Filename: {file.filename}")
                if file.filename == '':
                    flash('No selected database file.', 'warning')
                    return redirect(request.url)
                if file and '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() == 'json':
                    clear_data = request.form.get('clear_existing_data') == 'on'

                    print("DEBUG: database_file upload detected in data_update_page POST.")
                    print(f"DEBUG: Clear existing data: {clear_data}")

                    try:
                        file_content = file.read().decode('utf-8')
                        print(f"DEBUG: File content for database import read. Length: {len(file_content)} characters.")

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
        all_area_names=all_area_names,
        all_step_names=all_step_names,
        all_usecase_names=all_usecase_names,
        current_item=None,
        current_area=None,
        current_step=None,
        current_usecase=None,
        all_areas_flat=all_areas_flat,
        all_steps_flat=all_steps_flat,
        all_usecases_flat=all_usecases_flat
    )

# --- NEW ROUTES FOR BULK EDITING STEPS ---

@injection_routes.route('/steps/prepare-for-edit', methods=['POST'])
@login_required
def prepare_steps_for_edit():
    selected_step_ids = request.form.getlist('selected_update_steps')
    if not selected_step_ids:
        flash("No process steps selected for update.", "warning")
        return redirect(url_for('injection.data_update_page'))

    session_db = SessionLocal()
    try:
        steps_to_edit = session_db.query(ProcessStep).options(
            joinedload(ProcessStep.area)
        ).filter(ProcessStep.id.in_(selected_step_ids)).all()

        if not steps_to_edit:
            flash("Selected process steps not found.", "warning")
            return redirect(url_for('injection.data_update_page'))

        # Prepare data structure for the frontend
        prepared_data_for_edit = []
        for step in steps_to_edit:
            item_data = {
                'id': step.id,
                'name': step.name,
                'bi_id': step.bi_id,
                'current_area_id': step.area_id,
                'current_area_name': step.area.name if step.area else 'N/A',
                # Initialize current values for all editable fields
                **{f'current_{key}': getattr(step, key) for key in PROCESS_STEP_EDITABLE_FIELDS if key not in ['name', 'bi_id', 'area_id']},
                'new_values': {
                    'name': step.name, # Default new value to current value
                    'bi_id': step.bi_id,
                    'area_id': step.area_id,
                    **{key: getattr(step, key) for key in PROCESS_STEP_EDITABLE_FIELDS if key not in ['name', 'bi_id', 'area_id']}
                }
            }
            # Clean up new_values: replace empty strings with None, and strip whitespace from strings
            for key, value in item_data['new_values'].items():
                if isinstance(value, str):
                    item_data['new_values'][key] = value.strip() or None
                if value == "": # Handle explicit empty string becoming None
                     item_data['new_values'][key] = None
            
            # Clean up current_ values similarly for consistent comparison in JS
            for key, value in item_data.items():
                if key.startswith('current_') and isinstance(value, str):
                    item_data[key] = value.strip() or None

            prepared_data_for_edit.append(item_data)
        
        session['steps_to_edit'] = prepared_data_for_edit
        flash(f"Loaded {len(steps_to_edit)} steps for bulk editing.", "info")
        return redirect(url_for('injection.edit_multiple_steps'))
    except Exception as e:
        session_db.rollback()
        flash(f"Error preparing steps for edit: {e}", "danger")
        print(f"Error preparing steps for edit: {e}")
        return redirect(url_for('injection.data_update_page'))
    finally:
        SessionLocal.remove()

@injection_routes.route('/steps/edit-multiple', methods=['GET'])
@login_required
def edit_multiple_steps():
    steps_data = session.get('steps_to_edit', [])
    if not steps_data:
        flash("No steps found in session for editing. Please select them again.", "warning")
        return redirect(url_for('injection.data_update_page'))

    session_db = SessionLocal()
    try:
        all_areas = session_db.query(Area).order_by(Area.name).all()
        # NEW BREADCRUMB DATA FETCHING (for consistency across all routes)
        all_areas_flat = serialize_for_js(session_db.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session_db.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session_db.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        # END NEW BREADCRUMB DATA FETCHING
        
        return render_template(
            'edit_multiple_steps.html',
            title='Bulk Edit Process Steps',
            steps_data=steps_data,
            all_areas=all_areas,
            editable_fields=PROCESS_STEP_EDITABLE_FIELDS,
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
        )
    except Exception as e:
        flash(f"Error loading bulk edit page: {e}", "danger")
        print(f"Error loading bulk edit page: {e}")
        return redirect(url_for('injection.data_update_page'))
    finally:
        SessionLocal.remove()


@injection_routes.route('/steps/save-all-changes', methods=['POST'])
@login_required
def save_all_steps_changes():
    changes_payload = request.get_json()
    if not changes_payload:
        return jsonify(success=False, message="No changes received."), 400

    session_db = SessionLocal()
    successful_updates = 0
    failed_updates = []

    try:
        for change_item in changes_payload:
            step_id = change_item.get('id')
            updated_fields = change_item.get('updated_fields', {})

            step = session_db.query(ProcessStep).get(step_id)
            if not step:
                failed_updates.append({"id": step_id, "error": "Step not found."})
                continue
            
            # Keep track of original values for comparison in flash messages
            # original_values = {field: getattr(step, field) for field in updated_fields.keys()} # Not used in final response

            for field, new_value in updated_fields.items():
                if field == 'area_id':
                    # Ensure area exists before assigning
                    area_exists = session_db.query(Area).filter_by(id=new_value).first()
                    if not area_exists:
                        failed_updates.append({"id": step_id, "field": field, "value": new_value, "error": f"Area ID {new_value} not found."})
                        continue
                elif field == 'bi_id':
                     # Ensure BI_ID uniqueness if changed
                    existing_bi_id_step = session_db.query(ProcessStep).filter(
                        ProcessStep.bi_id == new_value,
                        ProcessStep.id != step_id
                    ).first()
                    if existing_bi_id_step:
                        failed_updates.append({"id": step_id, "field": field, "value": new_value, "error": f"BI_ID '{new_value}' already exists for another step."})
                        continue

                setattr(step, field, new_value)
            
            session_db.add(step) # Add to session if not already tracked or to mark as dirty
            successful_updates += 1
        
        session_db.commit()
        
        message = f"Successfully saved {successful_updates} changes."
        if failed_updates:
            message += f" {len(failed_updates)} updates failed."
            flash(f"{message} See details below.", "warning")
            return jsonify(success=False, message=message, failed_updates=failed_updates), 200
        else:
            flash(message, "success")
            return jsonify(success=True, message=message), 200

    except IntegrityError as e:
        session_db.rollback()
        return jsonify(success=False, message=f"Database integrity error: {e}. Changes rolled back."), 500
    except Exception as e:
        session_db.rollback()
        print(f"Error saving bulk step changes: {e}")
        traceback.print_exc()
        return jsonify(success=False, message=f"An unexpected error occurred: {e}. Changes rolled back."), 500
    finally:
        SessionLocal.remove()


# --- NEW ROUTES FOR BULK EDITING USE CASES ---

@injection_routes.route('/usecases/prepare-for-edit', methods=['POST'])
@login_required
def prepare_usecases_for_edit():
    selected_usecase_ids = request.form.getlist('selected_update_usecases')
    if not selected_usecase_ids:
        flash("No use cases selected for update.", "warning")
        return redirect(url_for('injection.data_update_page'))

    session_db = SessionLocal()
    try:
        usecases_to_edit = session_db.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area)
        ).filter(UseCase.id.in_(selected_usecase_ids)).all()

        if not usecases_to_edit:
            flash("Selected use cases not found.", "warning")
            return redirect(url_for('injection.data_update_page'))

        prepared_data_for_edit = []
        for uc in usecases_to_edit:
            item_data = {
                'id': uc.id,
                'name': uc.name,
                'bi_id': uc.bi_id,
                'current_process_step_id': uc.process_step_id,
                'current_process_step_name': uc.process_step.name if uc.process_step else 'N/A',
                'area_name': uc.process_step.area.name if uc.process_step and uc.process_step.area else 'N/A',
                # Initialize current values for all editable fields
                **{f'current_{key}': getattr(uc, key) for key in PROCESS_USECASE_EDITABLE_FIELDS if key not in ['name', 'bi_id', 'process_step_id']},
                'new_values': {
                    'name': uc.name,
                    'bi_id': uc.bi_id,
                    'process_step_id': uc.process_step_id,
                    **{key: getattr(uc, key) for key in PROCESS_USECASE_EDITABLE_FIELDS if key not in ['name', 'bi_id', 'process_step_id']}
                }
            }
            # Clean up new_values and current_ values
            for key, value in item_data['new_values'].items():
                if isinstance(value, str):
                    item_data['new_values'][key] = value.strip() or None
                elif value == "":
                    item_data['new_values'][key] = None
            
            for key, value in item_data.items():
                if key.startswith('current_') and isinstance(value, str):
                    item_data[key] = value.strip() or None

            prepared_data_for_edit.append(item_data)
        
        session['usecases_to_edit'] = prepared_data_for_edit
        flash(f"Loaded {len(usecases_to_edit)} use cases for bulk editing.", "info")
        return redirect(url_for('injection.edit_multiple_usecases'))
    except Exception as e:
        session_db.rollback()
        flash(f"Error preparing use cases for edit: {e}", "danger")
        print(f"Error preparing use cases for edit: {e}")
        return redirect(url_for('injection.data_update_page'))
    finally:
        SessionLocal.remove()

@injection_routes.route('/usecases/edit-multiple', methods=['GET'])
@login_required
def edit_multiple_usecases():
    usecases_data = session.get('usecases_to_edit', [])
    if not usecases_data:
        flash("No use cases found in session for editing. Please select them again.", "warning")
        return redirect(url_for('injection.data_update_page'))

    session_db = SessionLocal()
    try:
        all_steps = session_db.query(ProcessStep).options(joinedload(ProcessStep.area)).order_by(ProcessStep.name).all()
        # NEW BREADCRUMB DATA FETCHING (for consistency)
        all_areas_flat = serialize_for_js(session_db.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session_db.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session_db.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        # END NEW BREADCRUMB DATA FETCHING
        
        return render_template(
            'edit_multiple_usecases.html',
            title='Bulk Edit Use Cases',
            usecases_data=usecases_data,
            all_steps=all_steps,
            editable_fields=PROCESS_USECASE_EDITABLE_FIELDS,
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
        )
    except Exception as e:
        flash(f"Error loading bulk edit use cases page: {e}", "danger")
        print(f"Error loading bulk edit use cases page: {e}")
        return redirect(url_for('injection.data_update_page'))
    finally:
        SessionLocal.remove()


@injection_routes.route('/usecases/save-all-changes', methods=['POST'])
@login_required
def save_all_usecases_changes():
    changes_payload = request.get_json()
    if not changes_payload:
        return jsonify(success=False, message="No changes received."), 400

    session_db = SessionLocal()
    successful_updates = 0
    failed_updates = []

    try:
        for change_item in changes_payload:
            uc_id = change_item.get('id')
            updated_fields = change_item.get('updated_fields', {})

            uc = session_db.query(UseCase).get(uc_id)
            if not uc:
                failed_updates.append({"id": uc_id, "error": "Use Case not found."})
                continue
            
            for field, new_value in updated_fields.items():
                if field == 'process_step_id':
                    # Ensure process step exists before assigning
                    step_exists = session_db.query(ProcessStep).filter_by(id=new_value).first()
                    if not step_exists:
                        failed_updates.append({"id": uc_id, "field": field, "value": new_value, "error": f"Process Step ID {new_value} not found."})
                        continue
                elif field == 'bi_id':
                     # Ensure BI_ID uniqueness if changed
                    existing_bi_id_uc = session_db.query(UseCase).filter(
                        UseCase.bi_id == new_value,
                        UseCase.id != uc_id
                    ).first()
                    if existing_bi_id_uc:
                        failed_updates.append({"id": uc_id, "field": field, "value": new_value, "error": f"BI_ID '{new_value}' already exists for another use case."})
                        continue
                elif field == 'priority':
                    if new_value is not None:
                        try:
                            priority_int = int(new_value)
                            if not (1 <= priority_int <= 4):
                                failed_updates.append({"id": uc_id, "field": field, "value": new_value, "error": "Priority must be between 1 and 4, or empty."})
                                continue
                            setattr(uc, field, priority_int)
                        except ValueError:
                            failed_updates.append({"id": uc_id, "field": field, "value": new_value, "error": "Invalid priority format (not an integer)."})
                            continue
                    else:
                        setattr(uc, field, None) # Allow setting to null/None
                    continue # Skip general setattr below for priority

                setattr(uc, field, new_value)
            
            session_db.add(uc)
            successful_updates += 1
        
        session_db.commit()
        
        message = f"Successfully saved {successful_updates} changes."
        if failed_updates:
            message += f" {len(failed_updates)} updates failed."
            flash(f"{message} See details below.", "warning")
            return jsonify(success=False, message=message, failed_updates=failed_updates), 200
        else:
            flash(message, "success")
            return jsonify(success=True, message=message), 200

    except IntegrityError as e:
        session_db.rollback()
        # Check specific constraints for more user-friendly messages
        if 'priority_range_check' in str(e):
            return jsonify(success=False, message="Database error: Priority must be between 1 and 4, or empty.", failed_updates=failed_updates), 500
        return jsonify(success=False, message=f"Database integrity error: {e}. Changes rolled back.", failed_updates=failed_updates), 500
    except Exception as e:
        session_db.rollback()
        print(f"Error saving bulk use case changes: {e}")
        traceback.print_exc()
        return jsonify(success=False, message=f"An unexpected error occurred: {e}. Changes rolled back."), 500
    finally:
        SessionLocal.remove()


# --- NEW ROUTES FOR STEP INJECTION PREVIEW AND FINALIZATION ---

# Route to display the preview of step injections
@injection_routes.route('/steps/injection-preview')
@login_required
def preview_steps_injection():
    preview_data = session.get('step_import_preview_data')
    if not preview_data:
        flash("No process step data found for preview. Please upload a file.", "warning")
        return redirect(url_for('injection.data_update_page'))

    session_db = SessionLocal()
    try:
        all_areas = session_db.query(Area).order_by(Area.name).all()
        # NEW BREADCRUMB DATA FETCHING (for consistency)
        all_areas_flat = serialize_for_js(session_db.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session_db.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session_db.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        # END NEW BREADCRUMB DATA FETCHING

        return render_template(
            'step_injection_preview.html',
            title='Process Step Import Preview',
            preview_data=preview_data,
            all_areas=all_areas,
            step_detail_fields=STEP_DETAIL_FIELDS, # For the modal
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
        )
    except Exception as e:
        flash(f"Error loading step injection preview: {e}", "danger")
        print(f"Error loading step injection preview: {e}")
        return redirect(url_for('injection.data_update_page'))
    finally:
        SessionLocal.remove()

# API endpoint to finalize the step import (called by JS from preview page)
@injection_routes.route('/steps/finalize', methods=['POST'])
@login_required
def finalize_steps_import():
    resolved_steps_data = request.get_json()
    if not resolved_steps_data:
        return jsonify(success=False, message="No data received for finalization."), 400

    result = finalize_step_import(resolved_steps_data)
    if result['success']:
        # Clear the session data after successful finalization
        session.pop('step_import_preview_data', None)
        flash(f"Process Step import complete: Added {result.get('added_count', 0)}, Updated {result.get('updated_count', 0)}, Skipped {result.get('skipped_count', 0)}, Failed {result.get('failed_count', 0)}.", "success")
        return jsonify(result), 200
    else:
        # If there was an overall failure in the service, keep data in session
        # And flash specific message for the user.
        flash(f"Finalizing import failed: {result['message']}", "danger")
        return jsonify(result), 500
