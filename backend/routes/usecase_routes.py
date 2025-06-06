# backend/routes/usecase_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify
from flask_login import login_required
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal
from ..models import (
    UseCase, ProcessStep, Area,
    UsecaseAreaRelevance, UsecaseStepRelevance, UsecaseUsecaseRelevance
)
from ..utils import serialize_for_js
from ..llm_service import get_all_available_llm_models # Moved import

usecase_routes = Blueprint(
    'usecases',
    __name__,
    template_folder='../templates',
    url_prefix='/usecases'
)


@usecase_routes.route('/')
@login_required
def list_usecases():
    session = SessionLocal()
    try:
        usecases = session.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area)
        ).order_by(UseCase.name).all()

        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        
        return render_template(
            'usecase_overview.html', 
            title="All Use Cases",
            usecases=usecases,
            current_item=None, 
            current_area=None, 
            current_step=None, 
            current_usecase=None, 
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
        )
    except Exception as e:
        print(f"Error fetching all use cases for overview: {e}")
        flash("An error occurred while fetching use case overview.", "danger")
        return redirect(url_for('index'))
    finally:
        SessionLocal.remove()


@usecase_routes.route('/<int:usecase_id>')
@login_required
def view_usecase(usecase_id):
    session = SessionLocal()
    try:
        usecase = session.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area),
            selectinload(UseCase.relevant_to_areas)
                .joinedload(UsecaseAreaRelevance.target_area),
            selectinload(UseCase.relevant_to_steps)
                .joinedload(UsecaseStepRelevance.target_process_step),
            selectinload(UseCase.relevant_to_usecases_as_source)
                .joinedload(UsecaseUsecaseRelevance.target_usecase),
            selectinload(UseCase.relevant_to_usecases_as_target)
                .joinedload(UsecaseUsecaseRelevance.source_usecase)
        ).get(usecase_id)

        if usecase is None:
            flash(f"Use Case with ID {usecase_id} not found.", "warning")
            return redirect(url_for('index'))

        all_areas_db = session.query(Area).order_by(Area.name).all()
        all_steps_db = session.query(ProcessStep).order_by(ProcessStep.name).all()
        other_usecases = session.query(UseCase)\
            .filter(UseCase.id != usecase_id)\
            .order_by(UseCase.name)\
            .all()

        current_step_for_bc = usecase.process_step
        current_area_for_bc = current_step_for_bc.area if current_step_for_bc else None
        current_item_for_bc = usecase 

        all_areas_flat = serialize_for_js(all_areas_db, 'area')
        all_steps_flat = serialize_for_js(all_steps_db, 'step')
        all_usecases_list = session.query(UseCase).order_by(UseCase.name).all()
        all_usecases_flat = serialize_for_js(all_usecases_list, 'usecase')

        return render_template(
            'usecase_detail.html',
            title=f"Use Case: {usecase.name}",
            usecase=usecase,
            all_areas=all_areas_db,
            all_steps=all_steps_db,
            other_usecases=other_usecases, 
            current_usecase=usecase, 
            current_step=current_step_for_bc, 
            current_area=current_area_for_bc, 
            current_item=current_item_for_bc,
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
        )
    except Exception as e:
        print(f"Error fetching usecase {usecase_id}: {e}")
        flash("An error occurred while fetching usecase details.", "danger")
        return redirect(url_for('index'))
    finally:
        SessionLocal.remove()


@usecase_routes.route('/<int:usecase_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_usecase(usecase_id):
    session = SessionLocal()
    try:
        usecase = session.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area)
        ).get(usecase_id)
        
        if usecase is None:
            flash(f"Use Case with ID {usecase_id} not found.", "warning")
            return redirect(url_for('index'))

        all_steps_db = session.query(ProcessStep).order_by(ProcessStep.name).all()
        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(all_steps_db, 'step')
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')

        current_step_for_bc = usecase.process_step
        current_area_for_bc = current_step_for_bc.area if current_step_for_bc else None
        current_item_for_bc = usecase 

        if request.method == 'POST':
            original_bi_id = usecase.bi_id
            usecase.name = request.form.get('name', '').strip()
            usecase.bi_id = request.form.get('bi_id', '').strip()
            usecase.process_step_id = request.form.get('process_step_id', type=int)

            priority_str = request.form.get('priority')
            if priority_str:
                if priority_str.isdigit():
                    priority_val = int(priority_str)
                    if 1 <= priority_val <= 4:
                        usecase.priority = priority_val
                    else:
                        flash("Invalid priority value. Must be a number between 1 and 4, or empty.", "danger")
                else:
                     flash("Invalid priority format. Must be a number (1-4) or empty.", "danger")
            else:
                usecase.priority = None

            usecase.raw_content = request.form.get('raw_content', '').strip() or None
            usecase.summary = request.form.get('summary', '').strip() or None
            usecase.inspiration = request.form.get('inspiration', '').strip() or None
            usecase.wave = request.form.get('wave', '').strip() or None
            usecase.effort_level = request.form.get('effort_level', '').strip() or None
            usecase.status = request.form.get('status', '').strip() or None
            usecase.business_problem_solved = request.form.get('business_problem_solved', '').strip() or None
            usecase.target_solution_description = request.form.get('target_solution_description', '').strip() or None
            usecase.technologies_text = request.form.get('technologies_text', '').strip() or None
            usecase.requirements = request.form.get('requirements', '').strip() or None
            usecase.relevants_text = request.form.get('relevants_text', '').strip() or None
            usecase.reduction_time_transfer = request.form.get('reduction_time_transfer', '').strip() or None
            usecase.reduction_time_launches = request.form.get('reduction_time_launches', '').strip() or None
            usecase.reduction_costs_supply = request.form.get('reduction_costs_supply', '').strip() or None
            usecase.quality_improvement_quant = request.form.get('quality_improvement_quant', '').strip() or None
            usecase.ideation_notes = request.form.get('ideation_notes', '').strip() or None
            usecase.further_ideas = request.form.get('further_ideas', '').strip() or None
            usecase.effort_quantification = request.form.get('effort_quantification', '').strip() or None
            usecase.potential_quantification = request.form.get('potential_quantification', '').strip() or None
            usecase.dependencies_text = request.form.get('dependencies_text', '').strip() or None
            usecase.contact_persons_text = request.form.get('contact_persons_text', '').strip() or None
            usecase.related_projects_text = request.form.get('related_projects_text', '').strip() or None

            if not usecase.name or not usecase.bi_id or not usecase.process_step_id:
                flash("Use Case Name, BI_ID, and Process Step are required.", "danger")
            elif usecase.bi_id != original_bi_id and session.query(UseCase).filter(UseCase.bi_id == usecase.bi_id, UseCase.id != usecase_id).first():
                flash(f"Another use case with BI_ID '{usecase.bi_id}' already exists.", "danger")
            else:
                try:
                    session.commit()
                    flash("Use Case updated successfully!", "success")
                    return redirect(url_for('usecases.view_usecase', usecase_id=usecase.id))
                except IntegrityError as e: 
                    session.rollback()
                    if 'priority_range_check' in str(e).lower():
                         flash("Database error: Priority must be between 1 and 4, or empty.", "danger")
                    elif 'use_cases_bi_id_key' in str(e).lower() or \
                       ('unique constraint' in str(e).lower() and 'bi_id' in str(e).lower()):
                        flash(f"Database error: BI_ID '{usecase.bi_id}' might already exist.", "danger")
                    elif 'use_cases_process_step_id_fkey' in str(e).lower() or \
                         ('foreign key constraint' in str(e).lower() and 'process_step_id' in str(e).lower()):
                        flash("Database error: Invalid Process Step selected.", "danger")
                    else:
                        flash("Database error: Could not update use case. Please check your input.", "danger")
                    print(f"Integrity Error updating use case {usecase_id}: {e}")
                except Exception as e: 
                    session.rollback()
                    flash(f"An unexpected error occurred during save: {e}", "danger")
                    print(f"Error updating use case {usecase_id}: {e}")
        
        return render_template(
            'edit_usecase.html',
            title=f"Edit Use Case: {usecase.name}",
            usecase=usecase,
            all_steps=all_steps_db,
            current_usecase=usecase,
            current_step=current_step_for_bc,
            current_area=current_area_for_bc,
            current_item=current_item_for_bc,
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
        )
    finally:
        SessionLocal.remove() 


@usecase_routes.route('/<int:usecase_id>/delete', methods=['POST'])
@login_required
def delete_usecase(usecase_id):
    session = SessionLocal()
    redirect_url = url_for('index') 
    try:
        usecase = session.query(UseCase).options(joinedload(UseCase.process_step)).get(usecase_id)
        step_id_for_redirect = request.form.get('process_step_id_for_redirect', type=int)
        redirect_to_area_overview_id = request.form.get('redirect_to_area_overview', type=int)

        if usecase is None:
            flash(f"Use Case with ID {usecase_id} not found.", "warning")
        else:
            original_step_id = usecase.process_step_id 
            uc_name = usecase.name
            try:
                session.delete(usecase)
                session.commit()
                flash(f"Use Case '{uc_name}' deleted successfully.", "success")
                if redirect_to_area_overview_id is not None:
                     redirect_url = url_for('areas.list_areas') 
                elif step_id_for_redirect is not None: 
                    redirect_url = url_for('steps.view_step', step_id=step_id_for_redirect)
                elif original_step_id: 
                     redirect_url = url_for('steps.view_step', step_id=original_step_id)
            except Exception as e:
                session.rollback()
                flash(f"Error deleting use case: {e}", "danger")
                print(f"Error deleting use case {usecase_id}: {e}")
                # Determine redirect URL even on error, based on available info
                if redirect_to_area_overview_id is not None:
                     redirect_url = url_for('areas.list_areas')
                elif step_id_for_redirect is not None:
                     redirect_url = url_for('steps.view_step', step_id=step_id_for_redirect)
                elif usecase and usecase.process_step_id: # Check if usecase object still has data
                     redirect_url = url_for('steps.view_step', step_id=usecase.process_step_id)
                else: # Fallback if usecase object is gone or step_id is null
                    redirect_url = url_for('usecases.list_usecases')

    except Exception as e:
        flash(f"An unexpected error occurred: {e}", "danger")
        print(f"Outer error in delete_usecase for {usecase_id}: {e}")
        # redirect_url remains url_for('index') or as set before this outer exception
    finally:
        SessionLocal.remove()
    
    return redirect(redirect_url)


@usecase_routes.route('/api/usecases/<int:usecase_id>/inline-update', methods=['PUT'])
@login_required
def inline_update_usecase(usecase_id):
    session_db = SessionLocal()
    new_value_stripped_for_error = None 
    try:
        usecase = session_db.query(UseCase).get(usecase_id)

        if not usecase:
            return jsonify(success=False, message="Use Case not found"), 404

        data = request.json
        if not data or len(data) != 1:
            return jsonify(success=False, message="Invalid update data. Expecting a single field to update."), 400

        field_to_update = list(data.keys())[0]
        new_value = data[field_to_update]

        allowed_fields = ['name', 'bi_id', 'quality_improvement_quant', 'effort_level', 'wave']
        if field_to_update not in allowed_fields:
            return jsonify(success=False, message=f"Field '{field_to_update}' cannot be updated inline."), 400

        if field_to_update == 'name':
            new_value_stripped = new_value.strip() if isinstance(new_value, str) else ''
            if not new_value_stripped:
                return jsonify(success=False, message="Use Case Name cannot be empty."), 400
            new_value = new_value_stripped
        
        if field_to_update == 'bi_id':
            new_value_stripped = new_value.strip() if isinstance(new_value, str) else ''
            new_value_stripped_for_error = new_value_stripped 
            if not new_value_stripped:
                return jsonify(success=False, message="UC BI_ID cannot be empty."), 400
            existing_uc = session_db.query(UseCase).filter(UseCase.bi_id == new_value_stripped, UseCase.id != usecase_id).first()
            if existing_uc:
                return jsonify(success=False, message=f"UC BI_ID '{new_value_stripped}' already exists."), 409
            new_value = new_value_stripped

        if field_to_update in ['quality_improvement_quant', 'effort_level', 'wave'] and isinstance(new_value, str) and new_value.strip().upper() == "N/A":
            new_value = None
            
        setattr(usecase, field_to_update, new_value)
        session_db.commit()
        
        updated_data_for_js = {
            'id': usecase.id,
            'name': usecase.name,
            'bi_id': usecase.bi_id,
            'quality_improvement_quant': usecase.quality_improvement_quant,
            'priority': usecase.priority,
            'effort_level': usecase.effort_level,
            'wave': usecase.wave,
        }
        return jsonify(success=True, message="Use Case updated.", updated_field=field_to_update, new_value=new_value, usecase=updated_data_for_js)
    except IntegrityError as e:
        session_db.rollback()
        err_msg = str(e.orig) if hasattr(e, 'orig') and e.orig else str(e)
        
        bi_id_value_for_msg = new_value_stripped_for_error if field_to_update == 'bi_id' and new_value_stripped_for_error is not None else new_value

        if 'use_cases_bi_id_key' in err_msg.lower() or \
           ('unique constraint' in err_msg.lower() and 'bi_id' in err_msg.lower()):
             return jsonify(success=False, message=f"Error: BI_ID '{bi_id_value_for_msg}' likely already exists."), 409
        return jsonify(success=False, message=f"Database error during update: {err_msg}"), 500
    except Exception as e:
        session_db.rollback()
        return jsonify(success=False, message=f"An unexpected error occurred: {str(e)}"), 500
    finally:
        SessionLocal.remove()


@usecase_routes.route('/<int:usecase_id>/edit-with-ai', methods=['GET'])
@login_required
def edit_usecase_with_ai(usecase_id):
    session = SessionLocal()
    try:
        usecase = session.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area)
        ).get(usecase_id)

        if usecase is None:
            flash(f"Use Case with ID {usecase_id} not found.", "warning")
            return redirect(url_for('injection.data_update_page'))

        all_steps_db = session.query(ProcessStep).order_by(ProcessStep.name).all()

        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(all_steps_db, 'step') 
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        
        current_step_for_bc = usecase.process_step
        current_area_for_bc = current_step_for_bc.area if current_step_for_bc else None

        return render_template(
            'edit_usecase_with_ai.html', 
            title=f"AI Edit: {usecase.name}",
            usecase=usecase,
            all_steps=all_steps_db,
            current_usecase=usecase,
            current_step=current_step_for_bc,
            current_area=current_area_for_bc,
            current_item=usecase,
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
        )
    except Exception as e:
        print(f"Error loading AI edit page for usecase {usecase_id}: {e}")
        flash("An error occurred while loading the AI-assisted editing page.", "danger")
        return redirect(url_for('injection.data_update_page'))
    finally:
        SessionLocal.remove()