import os
import traceback
from flask import Blueprint, render_template, request, flash, redirect, url_for, session, jsonify
from flask_login import login_required
import json

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
                             url_prefix='/injection')

# Define fields for ProcessStep for dynamic rendering in preview template
STEP_PREVIEW_FIELDS = {
    "name": "Name",
    "step_description": "Description",
    "raw_content": "Raw Content",
    "summary": "Summary",
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
def handle_injection():
    if request.method == 'POST':
        try:
            if 'area_file' not in request.files and \
               'step_file' not in request.files and \
               'usecase_file' not in request.files and \
               'ps_ps_relevance_file' not in request.files and \
               'usecase_area_relevance_file' not in request.files and \
               'usecase_step_relevance_file' not in request.files and \
               'usecase_usecase_relevance_file' not in request.files and \
               'database_file' not in request.files:
                flash('No file part in the request.', 'danger')
                return redirect(request.url)

            # --- Process Step File Processing (MODIFIED) ---
            if 'step_file' in request.files:
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

            # --- Area File Processing (existing) ---
            elif 'area_file' in request.files:
                file = request.files['area_file']
                if file.filename == '' or not file:
                    flash('No selected file.', 'warning')
                    return redirect(request.url)

                if file and '.' in file.filename and \
                   file.filename.rsplit('.', 1)[1].lower() == 'json':
                    result = process_area_file(file.stream)
                    flash_category = 'success' if result['success'] else 'danger'
                    if not result['success'] and result['added_count'] == 0 and result['skipped_count'] > 0 :
                        flash_category = 'warning'
                    flash(result['message'], flash_category)
                    return redirect(url_for('injection.handle_injection'))
                else:
                    flash('Invalid file type or name for Areas. Please upload a .json file.', 'danger')
                    return redirect(request.url)

            # --- Use Case File Processing (existing) ---
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
                    return redirect(url_for('injection.handle_injection'))
                else:
                     flash('Invalid file type or name for Use Cases. Please upload a .json file.', 'danger')
                     return redirect(request.url)
            # --- END Use Case File Processing ---

            # NEW: Process Step-to-Step Relevance File Processing
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
                    return redirect(url_for('injection.handle_injection'))
                else:
                     flash('Invalid file type or name for Process Step Relevance. Please upload a .json file.', 'danger')
                     return redirect(request.url)
            # END NEW Process Step-to-Step Relevance File Processing

            # NEW: Process Use Case-Area Relevance File Processing
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
                    return redirect(url_for('injection.handle_injection'))
                else:
                    flash('Invalid file type or name for Use Case-Area Relevance. Please upload a .json file.', 'danger')
                    return redirect(request.url)

            # NEW: Process Use Case-Step Relevance File Processing
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
                    return redirect(url_for('injection.handle_injection'))
                else:
                    flash('Invalid file type or name for Use Case-Step Relevance. Please upload a .json file.', 'danger')
                    return redirect(request.url)

            # NEW: Process Use Case-Use Case Relevance File Processing
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
                    return redirect(url_for('injection.handle_injection'))
                else:
                    flash('Invalid file type or name for Use Case-Use Case Relevance. Please upload a .json file.', 'danger')
                    return redirect(request.url)

            # Handle database import as a fallback
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
    return render_template('injection.html', title='Data Injection')


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
        return redirect(url_for('injection.handle_injection'))

    # Fetch all areas to populate the dropdown for area conflict resolution
    db_session = SessionLocal()
    all_areas = []
    try:
        all_areas = db_session.query(Area).order_by(Area.name).all()
    except Exception as e:
        flash("Error loading areas for preview. Some area selections might be missing.", "danger")
    finally:
        SessionLocal.remove() # Ensure session is closed

    return render_template(
        'step_injection_preview.html',
        title='Process Step Injection Preview',
        preview_data=preview_data,
        step_fields=STEP_PREVIEW_FIELDS,
        all_areas=all_areas
    )

@injection_routes.route('/steps/finalize', methods=['POST'])
@login_required
def finalize_steps_injection():
    """
    Receives user-resolved step data from the frontend and initiates database updates.
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

@injection_routes.route('/database/json', methods=['POST'])
@login_required
def import_db_json_route():
    if 'database_file' not in request.files:
        flash('No database file part in the request.', 'danger')
        return redirect(request.referrer or url_for('injection.handle_injection'))

    file = request.files['database_file']
    if file.filename == '':
        flash('No selected database file.', 'warning')
        return redirect(request.referrer or url_for('injection.handle_injection'))

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
    
    return redirect(request.referrer or url_for('injection.handle_injection'))