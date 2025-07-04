# backend/routes/usecase_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, g
from flask_login import login_required
from sqlalchemy.exc import IntegrityError
from ..models import UseCase, ProcessStep, Area
from ..utils import serialize_for_js
from ..services.llm_service import get_all_available_llm_models
from ..routes.llm_routes import AI_ASSIST_IMAGE_SYSTEM_PROMPT_TEMPLATE
from ..services import usecase_service, step_service, area_service

usecase_routes = Blueprint('usecases', __name__, template_folder='../templates', url_prefix='/usecases')

PROCESS_USECASE_EDITABLE_FIELDS_FOR_AI_SUGGESTIONS = [ "name", "summary", "business_problem_solved", "target_solution_description", "pilot_site_factory_text", "usecase_type_category", "effort_quantification", "potential_quantification", "dependencies_text" ]

@usecase_routes.route('/')
@login_required
def list_usecases():
    usecases = usecase_service.get_all_usecases_with_details(g.db_session)
    all_areas_for_filters = g.db_session.query(Area).order_by(Area.name).all()
    all_steps_for_filters = g.db_session.query(ProcessStep).order_by(ProcessStep.name).all()
    
    all_usecases_for_js_filtering = [ { 'id': uc.id, 'name': uc.name, 'bi_id': uc.bi_id, 'process_step_id': uc.process_step_id, 'area_id': uc.process_step.area.id if uc.process_step and uc.process_step.area else None, 'wave': uc.wave, 'effort_level': uc.effort_level, 'priority': uc.priority, 'quality_improvement_quant': uc.quality_improvement_quant } for uc in usecases ]
    all_areas_flat = serialize_for_js(all_areas_for_filters, 'area')
    all_steps_flat = serialize_for_js(all_steps_for_filters, 'step')
    all_usecases_flat = serialize_for_js(usecases, 'usecase')

    return render_template( 'usecase_overview.html', title="All Use Cases", usecases=usecases, all_areas_for_filters=all_areas_for_filters, all_steps_for_js=all_steps_flat, all_usecases_for_js_filtering=all_usecases_for_js_filtering, current_item=None, current_area=None, current_step=None, current_usecase=None, all_areas_flat=all_areas_flat, all_steps_flat=all_steps_flat, all_usecases_flat=all_usecases_flat )

@usecase_routes.route('/<int:usecase_id>')
@login_required
def view_usecase(usecase_id):
    usecase = usecase_service.get_usecase_by_id(g.db_session, usecase_id)
    if not usecase:
        flash(f"Use Case with ID {usecase_id} not found.", "warning")
        return redirect(url_for('dashboard'))

    all_areas_db = g.db_session.query(Area).order_by(Area.name).all()
    all_steps_db = g.db_session.query(ProcessStep).order_by(ProcessStep.name).all()
    other_usecases = usecase_service.get_all_other_usecases(g.db_session, usecase_id)
    all_areas_flat = serialize_for_js(all_areas_db, 'area')
    all_steps_flat = serialize_for_js(all_steps_db, 'step')
    all_usecases_flat = serialize_for_js(g.db_session.query(UseCase).order_by(UseCase.name).all(), 'usecase')

    return render_template('usecase_detail.html', title=f"Use Case: {usecase.name}", usecase=usecase, all_areas=all_areas_db, all_steps=all_steps_db, other_usecases=other_usecases, current_usecase=usecase, current_step=usecase.process_step, current_area=usecase.process_step.area, current_item=usecase, all_areas_flat=all_areas_flat, all_steps_flat=all_steps_flat, all_usecases_flat=all_usecases_flat)

@usecase_routes.route('/<int:usecase_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_usecase(usecase_id):
    try:
        usecase = usecase_service.get_usecase_by_id(g.db_session, usecase_id)
        if not usecase:
            flash(f"Use Case with ID {usecase_id} not found.", "warning")
            return redirect(url_for('usecases.list_usecases'))

        if request.method == 'POST':
            success, message = usecase_service.update_usecase_from_form(g.db_session, usecase, request.form)
            flash(message, 'success' if success else 'danger')
            if success:
                return redirect(url_for('usecases.list_usecases'))

        all_steps_db = g.db_session.query(ProcessStep).order_by(ProcessStep.name).all()
        all_areas_flat = serialize_for_js(g.db_session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(all_steps_db, 'step')
        all_usecases_flat = serialize_for_js(g.db_session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        
        return render_template('edit_usecase.html', title=f"Edit Use Case: {usecase.name}", usecase=usecase, all_steps=all_steps_db, current_usecase=usecase, current_step=usecase.process_step, current_area=usecase.process_step.area, current_item=usecase, all_areas_flat=all_areas_flat, all_steps_flat=all_steps_flat, all_usecases_flat=all_usecases_flat)
    except Exception as e:
        g.db_session.rollback()
        flash(f"An unexpected error occurred: {e}", "danger")
        return redirect(url_for('usecases.view_usecase', usecase_id=usecase_id))

@usecase_routes.route('/<int:usecase_id>/delete', methods=['POST'])
@login_required
def delete_usecase(usecase_id):
    redirect_url = url_for('usecases.list_usecases')
    try:
        step_id_for_redirect = request.form.get('process_step_id_for_redirect', type=int)
        uc_name, message = usecase_service.delete_usecase_by_id(g.db_session, usecase_id)
        flash(message, 'success' if uc_name else 'warning')
        if uc_name and step_id_for_redirect:
            redirect_url = url_for('steps.view_step', step_id=step_id_for_redirect)
    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
    return redirect(redirect_url)

@usecase_routes.route('/api/usecases/<int:usecase_id>/inline-update', methods=['PUT'])
@login_required
def inline_update_usecase(usecase_id):
    try:
        usecase = g.db_session.query(UseCase).get(usecase_id)
        if not usecase: return jsonify(success=False, message="Use Case not found"), 404
        data = request.json
        if not data or len(data) != 1: return jsonify(success=False, message="Invalid update data."), 400
        field, value = list(data.items())[0]

        updated_usecase, message, updated_data = usecase_service.inline_update_usecase_field(g.db_session, usecase, field, value)
        if updated_usecase:
            return jsonify(success=True, message=message, usecase=updated_data)
        else:
            return jsonify(success=False, message=message), 400
    except IntegrityError as e:
        g.db_session.rollback()
        return jsonify(success=False, message=f"Database error: {e.orig}"), 500
    except Exception as e:
        g.db_session.rollback()
        return jsonify(success=False, message=str(e)), 500

@usecase_routes.route('/<int:usecase_id>/edit-with-ai', methods=['GET'])
@login_required
def edit_usecase_with_ai(usecase_id):
    usecase = usecase_service.get_usecase_by_id(g.db_session, usecase_id)
    if not usecase:
        flash(f"Use Case with ID {usecase_id} not found.", "warning")
        return redirect(url_for('usecases.list_usecases'))

    all_steps_db = g.db_session.query(ProcessStep).order_by(ProcessStep.name).all()
    # ... (rest of data prep for template is fine) ...
    usecase_data_for_js = { "id": usecase.id, "name": usecase.name, "bi_id": usecase.bi_id, "process_step_id": usecase.process_step_id, "priority": usecase.priority, "raw_content": usecase.raw_content, "summary": usecase.summary, "inspiration": usecase.inspiration, "wave": usecase.wave, "effort_level": usecase.effort_level, "status": usecase.status, "business_problem_solved": usecase.business_problem_solved, "target_solution_description": usecase.target_solution_description, "technologies_text": usecase.technologies_text, "requirements": usecase.requirements, "relevants_text": usecase.relevants_text, "reduction_time_transfer": usecase.reduction_time_transfer, "reduction_time_launches": usecase.reduction_time_launches, "reduction_costs_supply": usecase.reduction_costs_supply, "quality_improvement_quant": usecase.quality_improvement_quant, "ideation_notes": usecase.ideation_notes, "further_ideas": usecase.further_ideas, "effort_quantification": usecase.effort_quantification, "potential_quantification": usecase.potential_quantification, "dependencies_text": usecase.dependencies_text, "contact_persons_text": usecase.contact_persons_text, "related_projects_text": usecase.related_projects_text, "process_step_name": usecase.process_step.name if usecase.process_step else "N/A", "area_name": usecase.process_step.area.name if usecase.process_step and usecase.process_step.area else "N/A", "pilot_site_factory_text": usecase.pilot_site_factory_text, "usecase_type_category": usecase.usecase_type_category, }
    
    return render_template( 'edit_usecase_with_ai.html', title=f"AI Edit: {usecase.name}", usecase=usecase, usecase_data_for_js=usecase_data_for_js, all_steps=all_steps_db, default_ai_system_prompt=AI_ASSIST_IMAGE_SYSTEM_PROMPT_TEMPLATE, ai_suggestible_fields=PROCESS_USECASE_EDITABLE_FIELDS_FOR_AI_SUGGESTIONS, current_usecase=usecase, current_step=usecase.process_step, current_area=usecase.process_step.area, current_item=usecase, all_areas_flat=serialize_for_js(g.db_session.query(Area).order_by(Area.name).all(), 'area'), all_steps_flat=serialize_for_js(all_steps_db, 'step'), all_usecases_flat=serialize_for_js(g.db_session.query(UseCase).order_by(UseCase.name).all(), 'usecase'), available_llm_models=get_all_available_llm_models() )