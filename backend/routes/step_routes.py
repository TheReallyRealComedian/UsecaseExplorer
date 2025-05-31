# backend/routes/step_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal
from ..models import ProcessStep, UseCase, Area, UsecaseStepRelevance, ProcessStepProcessStepRelevance # NEW Import
# NEW IMPORT FOR BREADCRUMBS DATA
from ..app import serialize_for_js
# END NEW IMPORT

step_routes = Blueprint('steps', __name__,
                        template_folder='../templates',
                        url_prefix='/steps')

@step_routes.route('/<int:step_id>')
@login_required
def view_step(step_id):
    session = SessionLocal()

    # NEW BREADCRUMB DATA FETCHING
    all_areas_flat = []
    all_steps_flat = []
    all_usecases_flat = []
    # END NEW BREADCRUMB DATA FETCHING

    try:
        step = session.query(ProcessStep).options(
            joinedload(ProcessStep.area),
            selectinload(ProcessStep.use_cases),
            selectinload(ProcessStep.usecase_relevance)
                .joinedload(UsecaseStepRelevance.source_usecase),
            # NEW: Load ProcessStep-ProcessStep relevance links (as source and target)
            selectinload(ProcessStep.relevant_to_steps_as_source)
                .joinedload(ProcessStepProcessStepRelevance.target_process_step),
            selectinload(ProcessStep.relevant_to_steps_as_target)
                .joinedload(ProcessStepProcessStepRelevance.source_process_step)
        ).get(step_id)

        if step is None:
            flash(f"Process Step with ID {step_id} not found.", "warning")
            return redirect(url_for('index'))

        # NEW: Fetch other steps for the "Add Relevance Link" form
        other_steps = session.query(ProcessStep)\
            .filter(ProcessStep.id != step_id)\
            .order_by(ProcessStep.name)\
            .all()

        # NEW BREADCRUMB DATA FETCHING
        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        # END NEW BREADCRUMB DATA FETCHING

        return render_template(
            'step_detail.html',
            title=f"Process Step: {step.name}",
            step=step,
            other_steps=other_steps, # Pass other steps to the template for the 'add relevance' form
            current_step=step, # For breadcrumbs (the step itself)
            current_area=step.area, # For breadcrumbs (the parent area)
            current_usecase=None, # Ensure consistency
            current_item=step, # The specific item for "active" breadcrumb logic
            # NEW BREADCRUMB DATA PASSING
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
            # END NEW BREADCRUMB DATA PASSING
        )
    except Exception as e:
        print(f"Error fetching step {step_id}: {e}")
        flash("An error occurred while fetching step details. Please check server logs.", "danger")
        return redirect(url_for('index'))
    finally:
        # REMOVE THIS LINE: SessionLocal.remove()
        pass


@step_routes.route('/<int:step_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_step(step_id):
    session = SessionLocal()
    step = session.query(ProcessStep).options(joinedload(ProcessStep.area)).get(step_id)
    all_areas = session.query(Area).order_by(Area.name).all()

    # NEW BREADCRUMB DATA FETCHING
    all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
    all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
    all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
    # END NEW BREADCRUMB DATA FETCHING

    if step is None:
        flash(f"Process Step with ID {step_id} not found.", "warning")
        # REMOVE THIS LINE: SessionLocal.remove()
        return redirect(url_for('index'))

    if request.method == 'POST':
        original_bi_id = step.bi_id
        step.name = request.form.get('name', '').strip()
        step.bi_id = request.form.get('bi_id', '').strip()
        step.area_id = request.form.get('area_id', type=int)
        
        step.step_description = request.form.get('step_description', '').strip() or None
        step.raw_content = request.form.get('raw_content', '').strip() or None
        step.summary = request.form.get('summary', '').strip() or None
        step.vision_statement = request.form.get('vision_statement', '').strip() or None
        step.in_scope = request.form.get('in_scope', '').strip() or None
        step.out_of_scope = request.form.get('out_of_scope', '').strip() or None
        step.interfaces_text = request.form.get('interfaces_text', '').strip() or None
        step.what_is_actually_done = request.form.get('what_is_actually_done', '').strip() or None
        step.pain_points = request.form.get('pain_points', '').strip() or None
        step.targets_text = request.form.get('targets_text', '').strip() or None

        if not step.name or not step.bi_id or not step.area_id:
            flash("Step Name, BI_ID, and Area are required.", "danger")
            # Fall through to render_template at the end of the function
        else:
            if step.bi_id != original_bi_id:
                existing_step = session.query(ProcessStep).filter(
                    ProcessStep.bi_id == step.bi_id, 
                    ProcessStep.id != step_id
                ).first()
                if existing_step:
                    flash(f"Another process step with BI_ID '{step.bi_id}' already exists.", "danger")
                    return render_template(
                        'edit_step.html',
                        title=f"Edit Step: {step.name}",
                        step=step, # The object for the page's data
                        all_areas=all_areas, # For the dropdown
                        current_step=step, # For breadcrumbs (the step itself)
                        current_area=step.area, # For breadcrumbs (the parent area)
                        current_usecase=None, # Ensure consistency
                        current_item=step, # The specific item for "active" breadcrumb logic
                        # NEW BREADCRUMB DATA PASSING
                        all_areas_flat=all_areas_flat,
                        all_steps_flat=all_steps_flat,
                        all_usecases_flat=all_usecases_flat
                        # END NEW BREADCRUMB DATA PASSING
                    )
            
            try:
                session.commit()
                flash("Process Step updated successfully!", "success")
                # REMOVE THIS LINE: SessionLocal.remove() # Close session before redirect
                return redirect(url_for('steps.view_step', step_id=step.id))
            except IntegrityError:
                session.rollback()
                flash("Database error: Could not update step. BI_ID might already exist or area is invalid.", "danger")
                # REMOVE THIS LINE: SessionLocal.remove() 
                return render_template(
                    'edit_step.html',
                    title=f"Edit Step: {step.name}",
                    step=step, # The object for the page's data
                    all_areas=all_areas, # For the dropdown
                    current_step=step, # For breadcrumbs (the step itself)
                    current_area=step.area, # For breadcrumbs (the parent area)
                    current_usecase=None, # Ensure consistency
                    current_item=step, # The specific item for "active" breadcrumb logic
                    # NEW BREADCRUMB DATA PASSING
                    all_areas_flat=all_areas_flat,
                    all_steps_flat=all_steps_flat,
                    all_usecases_flat=all_usecases_flat
                    # END NEW BREADCRUMB DATA PASSING
                )
            except Exception as e:
                session.rollback()
                flash(f"An unexpected error occurred: {e}", "danger")
                print(f"Error updating step {step_id}: {e}")
                # Fall through to render_template below
                # REMOVE THIS LINE: SessionLocal.remove()
                return render_template(
                    'edit_step.html',
                    title=f"Edit Step: {step.name}",
                    step=step, # The object for the page's data
                    all_areas=all_areas, # For the dropdown
                    current_step=step, # For breadcrumbs (the step itself)
                    current_area=step.area, # For breadcrumbs (the parent area)
                    current_usecase=None, # Ensure consistency
                    current_item=step, # The specific item for "active" breadcrumb logic
                    # NEW BREADCRUMB DATA PASSING
                    all_areas_flat=all_areas_flat,
                    all_steps_flat=all_steps_flat,
                    all_usecases_flat=all_usecases_flat
                    # END NEW BREADCRUMB DATA PASSING
                )
    
    # REMOVE THIS LINE: SessionLocal.remove() 
    return render_template(
        'edit_step.html',
        title=f"Edit Step: {step.name}", # Page title
        step=step, # The object for the page's data
        all_areas=all_areas, # For the dropdown
        current_step=step, # For breadcrumbs (the step itself)
        current_area=step.area, # For breadcrumbs (the parent area)
        current_usecase=None, # Ensure consistency
        current_item=step, # The specific item for "active" breadcrumb logic
        # NEW BREADCRUMB DATA PASSING
        all_areas_flat=all_areas_flat,
        all_steps_flat=all_steps_flat,
        all_usecases_flat=all_usecases_flat
        # END NEW BREADCRUMB DATA PASSING
    )


@step_routes.route('/<int:step_id>/delete', methods=['POST'])
@login_required
def delete_step(step_id):
    session = SessionLocal()
    step = session.query(ProcessStep).options(joinedload(ProcessStep.area)).get(step_id)
    redirect_url = url_for('index')

    if step is None:
        flash(f"Process Step with ID {step_id} not found.", "warning")
    else:
        area_id_for_redirect = step.area_id
        step_name = step.name
        try:
            session.delete(step)
            session.commit()
            flash(f"Process Step '{step_name}' and its use cases deleted successfully.", "success")
            if area_id_for_redirect:
                 redirect_url = url_for('areas.view_area', area_id=area_id_for_redirect)
        except Exception as e:
            session.rollback()
            flash(f"Error deleting process step: {e}", "danger")
            print(f"Error deleting step {step_id}: {e}")
            if step.area_id: 
                 redirect_url = url_for('areas.view_area', area_id=step.area_id)

    # REMOVE THIS LINE: SessionLocal.remove()
    return redirect(redirect_url)