# backend/routes/injection_routes.py

import os
import traceback
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify # session is used
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
    finalize_step_import
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
    # ... (rest of the function remains the same)
    print("---------- DEBUG: Data Update Page Route Entered ----------")
    print(f"Request Method: {request.method}")
    print(f"Request Form Keys: {request.form.keys()}")
    print(f"Request Files Keys: {request.files.keys()}")
    print("---------------------------------------------------------")

    session_db = SessionLocal()
    all_steps_for_table_objects = []
    all_usecases_for_table = []
    all_areas_for_filters_list = []

    all_areas_flat = []
    all_steps_flat_for_js = []
    detailed_usecases_for_js_filtering = []
    all_usecases_flat_for_breadcrumbs = []

    try:
        all_steps_for_table_objects = session_db.query(ProcessStep).options(
            joinedload(ProcessStep.area),
            joinedload(ProcessStep.use_cases)
        ).order_by(ProcessStep.area_id, ProcessStep.name).all()

        all_usecases_for_table = session_db.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area)
        ).order_by(UseCase.process_step_id, UseCase.name).all()
        
        all_areas_for_filters_list = session_db.query(Area).order_by(Area.name).all()

        detailed_usecases_for_js_filtering = [] 
        for uc in all_usecases_for_table:
            detailed_usecases_for_js_filtering.append({
                'id': uc.id,
                'name': uc.name,
                'bi_id': uc.bi_id,
                'process_step_id': uc.process_step_id,
                'area_id': uc.process_step.area_id if uc.process_step and uc.process_step.area else None,
                'wave': uc.wave,
                'effort_level': uc.effort_level,
                'priority': uc.priority,
                'quality_improvement_quant': uc.quality_improvement_quant
            })

        all_areas_flat = serialize_for_js(all_areas_for_filters_list, 'area')
        all_steps_flat_for_js = serialize_for_js(all_steps_for_table_objects, 'step')
        all_usecases_flat_for_breadcrumbs = serialize_for_js(all_usecases_for_table, 'usecase')

    except Exception as e:
        print(f"Error loading initial data for data_update_page: {e}")
        flash("Error loading data. Please try again.", "danger")
        detailed_usecases_for_js_filtering = []
        all_usecases_flat_for_breadcrumbs = []
    finally:
        SessionLocal.remove()

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
                    flash(result['message'], 'success' if result['success'] else 'danger')
                    if result.get('skipped_errors_details'):
                        for i, detail in enumerate(result['skipped_errors_details']):
                            if i < 5:
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
                    except json.JSONDecodeError as e:
                        flash(f'Invalid JSON format in the uploaded file: {e}.', 'danger')
                        return redirect(request.url)
                    
                    result = process_step_file(parsed_json_data) # This function in injection_service.py generates the preview_data

                    if result['success']:
                        if result['preview_data']:
                            # Store the preview_data (which should be JSON serializable) in the session
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

            # ... (other elif blocks for usecase_file, relevance files, database_file remain the same)
            elif 'usecase_file' in request.files:
                file = request.files['usecase_file']
                if file.filename == '' or not file:
                    flash('No selected file for Use Cases.', 'warning')
                    return redirect(request.url)
                if file and '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() == 'json':
                    result = process_usecase_file(file.stream)
                    flash_category = 'success'
                    if not result['success']:
                        flash_category = 'danger'
                    elif result['skipped_count'] > 0:
                        flash_category = 'warning'
                    flash(result['message'], flash_category)
                    
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
                                flash(f"Skipped Use Case detail: {detail}", "info")
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
                flash('No file submitted or unknown action.', 'warning')
                return redirect(request.url)

        except Exception as e:
            traceback.print_exc()
            flash(f"An unexpected error occurred: {str(e)}", "danger")
            return redirect(request.url)
        finally:
            SessionLocal.remove() # This was correct, it's a new session per request
    
    return render_template(
        'data_update.html',
        title='Data Update & Management',
        all_steps=all_steps_for_table_objects,
        all_usecases=all_usecases_for_table,
        all_areas_for_filters=all_areas_for_filters_list,
        current_item=None,
        current_area=None,
        current_step=None,
        current_usecase=None,
        all_areas_flat=all_areas_flat,
        all_steps_flat=all_steps_flat_for_js,
        all_usecases_for_js_filtering=detailed_usecases_for_js_filtering,
        all_usecases_flat=all_usecases_flat_for_breadcrumbs
    )
# ... (rest of the file remains the same for prepare_steps_for_edit, edit_multiple_steps, etc.)

@injection_routes.route('/steps/prepare-for-edit', methods=['POST'])
@login_required
def prepare_steps_for_edit():
    selected_step_ids_str = request.form.get('selected_update_steps_ids')
    if not selected_step_ids_str:
        flash("No process steps selected for update.", "warning")
        return redirect(url_for('injection.data_update_page'))

    selected_step_ids = [int(id_val) for id_val in selected_step_ids_str.split(',') if id_val.isdigit()]
    if not selected_step_ids:
        flash("Invalid selection of process steps.", "warning")
        return redirect(url_for('injection.data_update_page'))

    session_db = SessionLocal()
    try:
        steps_to_edit = session_db.query(ProcessStep).options(
            joinedload(ProcessStep.area)
        ).filter(ProcessStep.id.in_(selected_step_ids)).all()

        if not steps_to_edit:
            flash("Selected process steps not found.", "warning")
            return redirect(url_for('injection.data_update_page'))

        prepared_data_for_edit = []
        for step in steps_to_edit:
            item_data = {
                'id': step.id,
                'name': step.name,
                'bi_id': step.bi_id,
                'current_area_id': step.area_id,
                'current_area_name': step.area.name if step.area else 'N/A',
                **{f'current_{key}': getattr(step, key) for key in PROCESS_STEP_EDITABLE_FIELDS if key not in ['name', 'bi_id', 'area_id']},
                'new_values': {
                    'name': step.name,
                    'bi_id': step.bi_id,
                    'area_id': step.area_id,
                    **{key: getattr(step, key) for key in PROCESS_STEP_EDITABLE_FIELDS if key not in ['name', 'bi_id', 'area_id']}
                }
            }
            for key, value in item_data['new_values'].items():
                if isinstance(value, str):
                    item_data['new_values'][key] = value.strip() or None
                if value == "":
                     item_data['new_values'][key] = None
            
            for key, value in item_data.items():
                if key.startswith('current_') and isinstance(value, str):
                    item_data[key] = value.strip() or None

            prepared_data_for_edit.append(item_data)
        
        session['steps_to_edit'] = prepared_data_for_edit # This should be JSON serializable
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
        all_areas_objs = session_db.query(Area).order_by(Area.name).all()
        all_areas_flat_js = serialize_for_js(all_areas_objs, 'area') # Used for breadcrumbs
        
        # For the dropdown in the form, we need a list of dicts {id, name}
        all_areas_for_select = [{'id': area.id, 'name': area.name} for area in all_areas_objs]


        all_steps_flat_js = serialize_for_js(session_db.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat_js = serialize_for_js(session_db.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        
        return render_template(
            'edit_multiple_steps.html',
            title='Bulk Edit Process Steps',
            steps_data=steps_data,
            all_areas=all_areas_for_select, # Pass the list of dicts
            editable_fields=PROCESS_STEP_EDITABLE_FIELDS,
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            all_areas_flat=all_areas_flat_js,
            all_steps_flat=all_steps_flat_js,
            all_usecases_flat=all_usecases_flat_js
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
            
            for field, new_value in updated_fields.items():
                if field == 'area_id':
                    area_exists = session_db.query(Area).filter_by(id=new_value).first()
                    if not area_exists:
                        failed_updates.append({"id": step_id, "field": field, "value": new_value, "error": f"Area ID {new_value} not found."})
                        continue
                elif field == 'bi_id':
                    existing_bi_id_step = session_db.query(ProcessStep).filter(
                        ProcessStep.bi_id == new_value,
                        ProcessStep.id != step_id
                    ).first()
                    if existing_bi_id_step:
                        failed_updates.append({"id": step_id, "field": field, "value": new_value, "error": f"BI_ID '{new_value}' already exists for another step."})
                        continue

                setattr(step, field, new_value)
            
            session_db.add(step)
            # No commit per item, commit once after all updates
        
        session_db.commit() # Commit all successful changes at once
        
        message = f"Successfully saved changes for {successful_updates} steps." # successful_updates was not incremented
        if successful_updates == 0 and not failed_updates: # If nothing was actually changed but no errors
            message = "No actual changes were applied."
            flash(message, "info")
            return jsonify(success=True, message=message), 200

        if failed_updates:
            message += f" {len(failed_updates)} updates failed."
            flash(f"{message} See console or server logs for details.", "warning")
            return jsonify(success=False, message=message, failed_updates=failed_updates), 200 # Still 200 if some succeeded
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


# --- ROUTES FOR BULK EDITING USE CASES ---
@injection_routes.route('/usecases/prepare-for-edit', methods=['POST'])
@login_required
def prepare_usecases_for_edit():
    selected_usecase_ids_str = request.form.get('selected_update_usecases_ids')
    if not selected_usecase_ids_str:
        flash("No use cases selected for update.", "warning")
        return redirect(url_for('injection.data_update_page'))
    
    selected_usecase_ids = [int(id_val) for id_val in selected_usecase_ids_str.split(',') if id_val.isdigit()]
    if not selected_usecase_ids:
        flash("Invalid selection of use cases.", "warning")
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
                **{f'current_{key}': getattr(uc, key) for key in PROCESS_USECASE_EDITABLE_FIELDS if key not in ['name', 'bi_id', 'process_step_id']},
                'new_values': {
                    'name': uc.name,
                    'bi_id': uc.bi_id,
                    'process_step_id': uc.process_step_id,
                    **{key: getattr(uc, key) for key in PROCESS_USECASE_EDITABLE_FIELDS if key not in ['name', 'bi_id', 'process_step_id']}
                }
            }
            for key, value in item_data['new_values'].items():
                if isinstance(value, str):
                    item_data['new_values'][key] = value.strip() or None
                elif value == "": # Explicitly handle empty string for non-string fields that might become empty
                    item_data['new_values'][key] = None
            
            for key, value in item_data.items(): # Normalize current_ values as well
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
        all_steps_objs = session_db.query(ProcessStep).options(joinedload(ProcessStep.area)).order_by(ProcessStep.name).all()
        all_steps_for_select = [{'id': step.id, 'name': step.name, 'bi_id': step.bi_id} for step in all_steps_objs]


        all_areas_flat_js = serialize_for_js(session_db.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat_js = serialize_for_js(all_steps_objs, 'step') # For breadcrumbs
        all_usecases_flat_js = serialize_for_js(session_db.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        
        return render_template(
            'edit_multiple_usecases.html',
            title='Bulk Edit Use Cases',
            usecases_data=usecases_data,
            all_steps=all_steps_for_select, # Pass list of dicts for dropdown
            editable_fields=PROCESS_USECASE_EDITABLE_FIELDS,
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            all_areas_flat=all_areas_flat_js,
            all_steps_flat=all_steps_flat_js,
            all_usecases_flat=all_usecases_flat_js
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
    successful_updates_count = 0 # Renamed for clarity
    failed_updates_details = [] # Renamed for clarity

    try:
        for change_item in changes_payload:
            uc_id = change_item.get('id')
            updated_fields = change_item.get('updated_fields', {})

            uc = session_db.query(UseCase).get(uc_id)
            if not uc:
                failed_updates_details.append({"id": uc_id, "error": "Use Case not found."})
                continue
            
            has_failed_field_update = False # Flag for this specific UC
            for field, new_value in updated_fields.items():
                if field == 'process_step_id':
                    step_exists = session_db.query(ProcessStep).filter_by(id=new_value).first()
                    if not step_exists:
                        failed_updates_details.append({"id": uc_id, "field": field, "value": new_value, "error": f"Process Step ID {new_value} not found."})
                        has_failed_field_update = True
                        break 
                elif field == 'bi_id':
                    existing_bi_id_uc = session_db.query(UseCase).filter(
                        UseCase.bi_id == new_value,
                        UseCase.id != uc_id
                    ).first()
                    if existing_bi_id_uc:
                        failed_updates_details.append({"id": uc_id, "field": field, "value": new_value, "error": f"BI_ID '{new_value}' already exists for another use case."})
                        has_failed_field_update = True
                        break
                elif field == 'priority':
                    if new_value is not None:
                        try:
                            priority_int = int(new_value)
                            if not (1 <= priority_int <= 4):
                                failed_updates_details.append({"id": uc_id, "field": field, "value": new_value, "error": "Priority must be between 1 and 4, or empty."})
                                has_failed_field_update = True
                                break
                            setattr(uc, field, priority_int)
                        except ValueError:
                            failed_updates_details.append({"id": uc_id, "field": field, "value": new_value, "error": "Invalid priority format (not an integer)."})
                            has_failed_field_update = True
                            break
                    else:
                        setattr(uc, field, None) 
                    continue # Skip default setattr for priority

                setattr(uc, field, new_value)
            
            if not has_failed_field_update: # Only add if no field update failed for this UC
                session_db.add(uc)
                successful_updates_count += 1 # Increment here
        
        if successful_updates_count > 0: # Only commit if there were successful updates to attempt
            session_db.commit()
        else:
            session_db.rollback() # Rollback if no successful updates to prevent empty transaction
        
        message = f"Successfully saved changes for {successful_updates_count} use cases."
        if not failed_updates_details and successful_updates_count == 0:
             message = "No actual changes were applied to any use case."
             flash(message, "info")
             return jsonify(success=True, message=message), 200

        if failed_updates_details:
            message += f" {len(failed_updates_details)} use case updates failed or had field errors."
            flash(f"{message} See console or server logs for details.", "warning")
            return jsonify(success=False, message=message, failed_updates=failed_updates_details), 200
        else:
            flash(message, "success")
            return jsonify(success=True, message=message), 200

    except IntegrityError as e:
        session_db.rollback()
        if 'priority_range_check' in str(e).lower():
            return jsonify(success=False, message="Database error: Priority must be between 1 and 4, or empty.", failed_updates=failed_updates_details), 500
        return jsonify(success=False, message=f"Database integrity error: {e}. Changes rolled back.", failed_updates=failed_updates_details), 500
    except Exception as e:
        session_db.rollback()
        print(f"Error saving bulk use case changes: {e}")
        traceback.print_exc()
        return jsonify(success=False, message=f"An unexpected error occurred: {e}. Changes rolled back."), 500
    finally:
        SessionLocal.remove()


# --- ROUTES FOR STEP INJECTION PREVIEW AND FINALIZATION ---
@injection_routes.route('/steps/injection-preview')
@login_required
def preview_steps_injection():
    preview_data = session.get('step_import_preview_data')
    if not preview_data:
        flash("No process step data found for preview. Please upload a file.", "warning")
        return redirect(url_for('injection.data_update_page'))

    session_db = SessionLocal()
    try:
        all_areas_objs = session_db.query(Area).order_by(Area.name).all()
        # CORRECTED: Create a list of dicts for all_areas, not Area objects
        all_areas_for_template = [{'id': area.id, 'name': area.name, 'description': area.description} for area in all_areas_objs]

        all_areas_flat_js = serialize_for_js(all_areas_objs, 'area')
        all_steps_flat_js = serialize_for_js(session_db.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat_js = serialize_for_js(session_db.query(UseCase).order_by(UseCase.name).all(), 'usecase')

        return render_template(
            'step_injection_preview.html',
            title='Process Step Import Preview',
            preview_data=preview_data,
            all_areas=all_areas_for_template, # Pass the JSON-serializable list
            step_detail_fields=STEP_DETAIL_FIELDS,
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            all_areas_flat=all_areas_flat_js,
            all_steps_flat=all_steps_flat_js,
            all_usecases_flat=all_usecases_flat_js
        )
    except Exception as e:
        # Print the error to the console for debugging
        print(f"Error loading step injection preview: {e}")
        traceback.print_exc() # Print full traceback
        flash(f"Error loading step injection preview: {e}", "danger")
        # Redirect to data_update_page on error
        return redirect(url_for('injection.data_update_page'))
    finally:
        SessionLocal.remove()


@injection_routes.route('/steps/finalize', methods=['POST'])
@login_required
def finalize_steps_import():
    resolved_steps_data = request.get_json()
    if not resolved_steps_data:
        return jsonify(success=False, message="No data received for finalization."), 400

    result = finalize_step_import(resolved_steps_data)
    if result['success']:
        session.pop('step_import_preview_data', None) # Clear session data
        flash(f"Process Step import complete: Added {result.get('added_count', 0)}, Updated {result.get('updated_count', 0)}, Skipped {result.get('skipped_count', 0)}, Failed {result.get('failed_count', 0)}.", "success")
        # Return the full result object for better JS handling
        return jsonify(result), 200 
    else:
        flash(f"Finalizing import failed: {result.get('message', 'Unknown error')}", "danger")
         # Return the full result object for better JS handling
        return jsonify(result), 500