# backend/routes/data_management_routes.py
import json
from flask import Blueprint, g, render_template, request, flash, redirect, url_for, session, jsonify
from flask_login import login_required
from sqlalchemy.orm import joinedload
from markupsafe import Markup, escape

# Import services
from ..services import data_management_service, bulk_edit_service
from ..models import Area, ProcessStep, UseCase
from ..services.data_management_service import analyze_json_import, finalize_import
from ..utils import serialize_for_js

data_management_bp = Blueprint('data_management', __name__,
                               template_folder='../templates',
                               url_prefix='/data-management')

# Configuration constants from old injection_routes.py
STEP_DETAIL_FIELDS = {
    "step_description": "Short Description", "raw_content": "Raw Content", "summary": "Generic Summary",
    "vision_statement": "Vision Statement", "in_scope": "In Scope", "out_of_scope": "Out of Scope",
    "interfaces_text": "Interfaces", "what_is_actually_done": "What is Actually Done",
    "pain_points": "Pain Points", "targets_text": "Targets",
}

PROCESS_STEP_EDITABLE_FIELDS = {
    "name": "Step Name", "bi_id": "Business ID (BI_ID)", "area_id": "Parent Area",
    **STEP_DETAIL_FIELDS
}

PROCESS_USECASE_EDITABLE_FIELDS = {
    "name": "Use Case Name", "bi_id": "Business ID (BI_ID)", "process_step_id": "Parent Process Step",
    "priority": "Priority (1-4)", "raw_content": "Raw Content", "summary": "Summary",
    "inspiration": "Inspiration", "wave": "Wave", "effort_level": "Effort Level",
    "status": "Status", "business_problem_solved": "Business Problem Solved",
    "target_solution_description": "Target / Solution Description", "technologies_text": "Technologies",
    "requirements": "Requirements", "relevants_text": "Relevants (Tags)",
    "reduction_time_transfer": "Time Reduction (Transfer)", "reduction_time_launches": "Time Reduction (Launches)",
    "reduction_costs_supply": "Cost Reduction (Supply)", "quality_improvement_quant": "Quality Improvement",
    "ideation_notes": "Ideation Notes", "further_ideas": "Further Ideas",
    "effort_quantification": "Effort Quantification", "potential_quantification": "Potential Quantification",
    "dependencies_text": "Redundancies & Dependencies", "contact_persons_text": "Contact Persons",
    "related_projects_text": "Related Projects", "pilot_site_factory_text": "Pilot Site, Factory",
    "usecase_type_category": "Use Case Type Category"
}

# Map string entity names to their SQLAlchemy models and unique keys
ENTITY_MAP = {
    'use_cases': {'model': UseCase, 'key': 'bi_id'},
    'process_steps': {'model': ProcessStep, 'key': 'bi_id'},
    'areas': {'model': Area, 'key': 'name'},
}


def flash_import_result(result):
    """Flashes a detailed message based on the import service result."""
    flash_category = 'success'
    if not result.get('success'):
        flash_category = 'danger'
    # Consider skipped/failed items as a warning, even if the overall process "succeeded"
    elif result.get('skipped_count', 0) > 0 or result.get('failed_count', 0) > 0 or result.get('skipped_errors_details'):
        flash_category = 'warning'

    message = result.get('message', 'File processed.')

    # Check for specific details to add to the message
    details_html = ""
    skipped_details = result.get('skipped_errors_details')
    if skipped_details:
        # Use set to avoid showing the exact same error message multiple times, then sort for consistent order
        unique_details = sorted(list(set(skipped_details)))
        details_html += "<h6>Details on Skipped/Failed Items:</h6><ul>"
        for detail in unique_details:
            details_html += f"<li>{escape(detail)}</li>"
        details_html += "</ul>"

    if details_html:
        # Construct the final HTML string, but do not wrap it in Markup().
        # This ensures a standard string is stored in the session.
        final_html_message = f"<p>{escape(message)}</p>{details_html}"
        flash(final_html_message, flash_category)
    else:
        flash(message, flash_category)


@data_management_bp.route('/', methods=['GET', 'POST'])
@login_required
def data_management_page():
    if request.method == 'POST':
        if 'database_file' in request.files:
            file = request.files['database_file']
            if file.filename == '':
                flash('No selected database file.', 'warning')
            elif file and '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() == 'json':
                clear_data = request.form.get('clear_existing_data') == 'on'
                try:
                    file_content = file.read().decode('utf-8')
                    result = data_management_service.import_database_from_json(file_content, clear_existing_data=clear_data)
                    flash_import_result(result)
                except Exception as e:
                    flash(f"An unexpected error occurred during database import: {str(e)}", 'danger')
            else:
                flash('Invalid file type for database import. Please upload a .json file.', 'danger')
            return redirect(url_for('data_management.data_management_page'))

        file_handlers = {
            'area_file': (data_management_service.process_area_file, {}),
            'step_file': (data_management_service.process_step_file, {'is_preview': True}),
            'usecase_file': (data_management_service.process_usecase_file, {}),
            'ps_ps_relevance_file': (data_management_service.process_ps_ps_relevance_file, {}),
            'usecase_area_relevance_file': (data_management_service.process_usecase_area_relevance_file, {}),
            'usecase_step_relevance_file': (data_management_service.process_usecase_step_relevance_file, {}),
            'usecase_usecase_relevance_file': (data_management_service.process_usecase_usecase_relevance_file, {})
        }

        for file_key, (handler, options) in file_handlers.items():
            if file_key in request.files:
                file = request.files[file_key]
                if file and file.filename != '':
                    if not file.filename.lower().endswith('.json'):
                        flash(f'Invalid file type for {file_key}. Please upload a .json file.', 'danger')
                        return redirect(request.url)

                    if file_key == 'step_file' and options.get('is_preview'):
                        try:
                            parsed_json_data = json.loads(file.read().decode('utf-8'))
                            result = handler(parsed_json_data)
                            if result.get('success') and result.get('preview_data'):
                                session['step_import_preview_data'] = result['preview_data']
                                flash('Step file uploaded. Please review changes before finalizing import.', 'info')
                                return redirect(url_for('data_management.preview_steps_injection'))
                            elif not result.get('preview_data'):
                                 flash('Step file uploaded but no valid steps were found for import.', 'warning')
                            else:
                                flash(result.get('message', 'Error processing step file.'), 'danger')
                        except json.JSONDecodeError as e:
                            flash(f'Invalid JSON in step file: {e}', 'danger')
                    else:
                        flash_import_result(handler(file.stream))

                    return redirect(request.url)

        flash('No file submitted or unknown action.', 'warning')
        return redirect(request.url)

    all_steps = g.db_session.query(ProcessStep).options(joinedload(ProcessStep.area), joinedload(ProcessStep.use_cases)).order_by(ProcessStep.area_id, ProcessStep.name).all()
    all_usecases = g.db_session.query(UseCase).options(joinedload(UseCase.process_step).joinedload(ProcessStep.area)).order_by(UseCase.process_step_id, UseCase.name).all()
    all_areas_for_filters = g.db_session.query(Area).order_by(Area.name).all()

    detailed_usecases_for_js = [{'id': uc.id, 'name': uc.name, 'bi_id': uc.bi_id, 'process_step_id': uc.process_step_id, 'area_id': uc.area.id if uc.area else None, 'wave': uc.wave, 'effort_level': uc.effort_level, 'priority': uc.priority, 'quality_improvement_quant': uc.quality_improvement_quant} for uc in all_usecases]

    all_areas_flat = serialize_for_js(all_areas_for_filters, 'area')
    all_steps_flat_js = serialize_for_js(all_steps, 'step')
    all_usecases_flat = serialize_for_js(all_usecases, 'usecase')

    return render_template(
        'data_management.html',
        title='Data Management',
        all_steps=all_steps,
        all_usecases=all_usecases,
        all_areas_for_filters=all_areas_for_filters,
        all_steps_flat=all_steps_flat_js,
        all_usecases_for_js_filtering=detailed_usecases_for_js,
        current_item=None, current_area=None, current_step=None, current_usecase=None,
        all_areas_flat=all_areas_flat, all_usecases_flat=all_usecases_flat
    )

@data_management_bp.route('/help', methods=['GET'])
@login_required
def data_help_page():
    all_areas = g.db_session.query(Area).order_by(Area.name).all()
    all_steps = g.db_session.query(ProcessStep).order_by(ProcessStep.name).all()

    area_names_list = "\n".join([area.name for area in all_areas])

    step_list_lines = ["BI_ID | Name", "--------------------------------------------------"]
    for step in all_steps:
        step_list_lines.append(f"{step.bi_id} | {step.name}")
    steps_text_block = "\n".join(step_list_lines)

    all_areas_flat = serialize_for_js(all_areas, 'area')
    all_steps_flat = serialize_for_js(all_steps, 'step')
    all_usecases_flat = serialize_for_js(g.db_session.query(UseCase).order_by(UseCase.name).all(), 'usecase')

    return render_template(
        'data_help.html',
        title='Data Import/Export Help',
        area_names_list=area_names_list,
        steps_text_block=steps_text_block,
        current_item=None,
        current_area=None,
        current_step=None,
        current_usecase=None,
        all_areas_flat=all_areas_flat,
        all_steps_flat=all_steps_flat,
        all_usecases_flat=all_usecases_flat
    )


@data_management_bp.route('/steps/prepare-for-edit', methods=['POST'])
@login_required
def prepare_steps_for_edit():
    selected_ids_str = request.form.get('selected_update_steps_ids')
    if not selected_ids_str:
        flash("No process steps selected for update.", "warning")
        return redirect(url_for('data_management.data_management_page'))
    selected_ids = [int(id_val) for id_val in selected_ids_str.split(',') if id_val.isdigit()]

    prepared_data = bulk_edit_service.prepare_steps_for_bulk_edit(g.db_session, selected_ids, PROCESS_STEP_EDITABLE_FIELDS)
    session['steps_to_edit'] = prepared_data
    return redirect(url_for('data_management.edit_multiple_steps'))


@data_management_bp.route('/steps/edit-multiple', methods=['GET'])
@login_required
def edit_multiple_steps():
    steps_data = session.get('steps_to_edit', [])
    if not steps_data:
        return redirect(url_for('data_management.data_management_page'))

    all_areas = g.db_session.query(Area).order_by(Area.name).all()
    return render_template(
        'edit_multiple_steps.html', title='Bulk Edit Process Steps', steps_data=steps_data,
        all_areas=all_areas, editable_fields=PROCESS_STEP_EDITABLE_FIELDS,
        all_areas_flat=serialize_for_js(all_areas, 'area'),
        all_steps_flat=serialize_for_js(g.db_session.query(ProcessStep).all(), 'step'),
        all_usecases_flat=serialize_for_js(g.db_session.query(UseCase).all(), 'usecase')
    )


@data_management_bp.route('/steps/save-all-changes', methods=['POST'])
@login_required
def save_all_steps_changes():
    changes = request.get_json()
    try:
        message = bulk_edit_service.save_bulk_step_changes(g.db_session, changes)
        session.pop('steps_to_edit', None)
        return jsonify(success=True, message=message)
    except Exception as e:
        g.db_session.rollback()
        return jsonify(success=False, message=str(e)), 500


@data_management_bp.route('/usecases/prepare-for-edit', methods=['POST'])
@login_required
def prepare_usecases_for_edit():
    selected_ids_str = request.form.get('selected_update_usecases_ids')
    if not selected_ids_str:
        flash("No use cases selected for update.", "warning")
        return redirect(url_for('data_management.data_management_page'))
    selected_ids = [int(id_val) for id_val in selected_ids_str.split(',') if id_val.isdigit()]

    prepared_data = bulk_edit_service.prepare_usecases_for_bulk_edit(g.db_session, selected_ids, PROCESS_USECASE_EDITABLE_FIELDS)
    session['usecases_to_edit'] = prepared_data
    return redirect(url_for('data_management.edit_multiple_usecases'))


@data_management_bp.route('/usecases/edit-multiple', methods=['GET'])
@login_required
def edit_multiple_usecases():
    usecases_data = session.get('usecases_to_edit', [])
    if not usecases_data:
        return redirect(url_for('data_management.data_management_page'))

    all_steps = g.db_session.query(ProcessStep).order_by(ProcessStep.name).all()
    return render_template(
        'edit_multiple_usecases.html', title='Bulk Edit Use Cases', usecases_data=usecases_data,
        all_steps=all_steps, editable_fields=PROCESS_USECASE_EDITABLE_FIELDS,
        all_areas_flat=serialize_for_js(g.db_session.query(Area).all(), 'area'),
        all_steps_flat=serialize_for_js(all_steps, 'step'),
        all_usecases_flat=serialize_for_js(g.db_session.query(UseCase).all(), 'usecase')
    )


@data_management_bp.route('/usecases/save-all-changes', methods=['POST'])
@login_required
def save_all_usecases_changes():
    changes = request.get_json()
    try:
        message = bulk_edit_service.save_bulk_usecase_changes(g.db_session, changes)
        session.pop('usecases_to_edit', None)
        return jsonify(success=True, message=message)
    except Exception as e:
        g.db_session.rollback()
        return jsonify(success=False, message=str(e)), 500


@data_management_bp.route('/steps/injection-preview')
@login_required
def preview_steps_injection():
    preview_data = session.get('step_import_preview_data')
    if not preview_data:
        flash("No step data found for preview. Please upload a file again.", "warning")
        return redirect(url_for('data_management.data_management_page'))

    all_areas = g.db_session.query(Area).order_by(Area.name).all()
    return render_template(
        'step_injection_preview.html', title='Process Step Import Preview',
        preview_data=preview_data, all_areas=all_areas, step_detail_fields=STEP_DETAIL_FIELDS,
        all_areas_flat=serialize_for_js(all_areas, 'area'),
        all_steps_flat=serialize_for_js(g.db_session.query(ProcessStep).all(), 'step'),
        all_usecases_flat=serialize_for_js(g.db_session.query(UseCase).all(), 'usecase')
    )


@data_management_bp.route('/steps/finalize', methods=['POST'])
@login_required
def finalize_steps_import():
    resolved_steps_data = request.get_json()
    if not resolved_steps_data:
        return jsonify(success=False, message="No data received for finalization."), 400

    result = data_management_service.finalize_step_import(resolved_steps_data)
    if result['success']:
        session.pop('step_import_preview_data', None)
    return jsonify(result)


@data_management_bp.route('/import/analyze', methods=['POST'])
@login_required
def analyze_json_upload():
    if 'json_file' not in request.files:
        flash('No file part in the request.', 'danger')
        return redirect(url_for('data_management.data_management_page'))

    file = request.files['json_file']
    entity_type = request.form.get('entity_type')

    if file.filename == '' or not entity_type:
        flash('No file selected or entity type missing.', 'warning')
        return redirect(url_for('data_management.data_management_page'))

    if entity_type not in ENTITY_MAP:
        flash(f"Invalid entity type '{entity_type}'.", 'danger')
        return redirect(url_for('data_management.data_management_page'))

    try:
        json_data = json.load(file.stream)
        if not isinstance(json_data, list):
            flash("Invalid JSON format. File must contain a list of objects.", "danger")
            return redirect(url_for('data_management.data_management_page'))

        analysis_result = analyze_json_import(
            json_data,
            ENTITY_MAP[entity_type]['model'],
            ENTITY_MAP[entity_type]['key']
        )

        if analysis_result['success']:
            session['import_preview_data'] = analysis_result['preview_data']
            session['import_entity_type'] = entity_type
            return redirect(url_for('data_management.import_preview'))
        else:
            flash(analysis_result.get('message', 'Analysis failed.'), 'danger')
            return redirect(url_for('data_management.data_management_page'))

    except json.JSONDecodeError:
        flash("Invalid JSON file. Please check the file content and format.", "danger")
        return redirect(url_for('data_management.data_management_page'))
    except Exception as e:
        flash(f"An unexpected error occurred during analysis: {e}", "danger")
        return redirect(url_for('data_management.data_management_page'))


@data_management_bp.route('/import/preview', methods=['GET'])
@login_required
def import_preview():
    preview_data = session.get('import_preview_data')
    entity_type = session.get('import_entity_type')

    if not preview_data or not entity_type:
        flash("No import preview data found. Please start a new import.", "warning")
        return redirect(url_for('data_management.data_management_page'))

    return render_template(
        'json_import_preview.html',
        title=f"Import Preview for {entity_type.replace('_', ' ').title()}",
        preview_data=preview_data,
        entity_type=entity_type
    )


@data_management_bp.route('/import/finalize', methods=['POST'])
@login_required
def finalize_json_import():
    resolved_data = request.get_json().get('resolved_data')
    entity_type = request.get_json().get('entity_type')

    if not resolved_data or not entity_type or entity_type not in ENTITY_MAP:
        return jsonify(success=False, message="Invalid request data."), 400

    result = finalize_import(
        resolved_data,
        ENTITY_MAP[entity_type]['model'],
        ENTITY_MAP[entity_type]['key']
    )

    if result['success']:
        session.pop('import_preview_data', None)
        session.pop('import_entity_type', None)

    return jsonify(result)