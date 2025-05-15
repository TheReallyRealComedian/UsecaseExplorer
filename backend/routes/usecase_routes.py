# backend/routes/usecase_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal
from ..models import (
    UseCase, ProcessStep, Area,
    UsecaseAreaRelevance, UsecaseStepRelevance, UsecaseUsecaseRelevance
)

usecase_routes = Blueprint(
    'usecases',
    __name__,
    template_folder='../templates',
    url_prefix='/usecases'
)

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

        all_areas = session.query(Area).order_by(Area.name).all()
        all_steps = session.query(ProcessStep).order_by(ProcessStep.name).all()
        other_usecases = session.query(UseCase)\
            .filter(UseCase.id != usecase_id)\
            .order_by(UseCase.name)\
            .all()

        current_step_for_bc = usecase.process_step
        current_area_for_bc = current_step_for_bc.area if current_step_for_bc else None

        return render_template(
            'usecase_detail.html',
            title=f"Use Case: {usecase.name}",
            usecase=usecase,
            all_areas=all_areas,
            all_steps=all_steps,
            other_usecases=other_usecases,
            current_usecase=usecase,
            current_step=current_step_for_bc,
            current_area=current_area_for_bc
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
    # Load usecase with joinedload for quick access to step/area for breadcrumbs if needed on error
    usecase = session.query(UseCase).options(joinedload(UseCase.process_step).joinedload(ProcessStep.area)).get(usecase_id)
    all_steps = session.query(ProcessStep).order_by(ProcessStep.name).all()

    if usecase is None:
        flash(f"Use Case with ID {usecase_id} not found.", "warning")
        SessionLocal.remove()
        return redirect(url_for('index'))

    # Need current step/area for breadcrumbs before handling POST data
    current_step_for_bc = usecase.process_step
    current_area_for_bc = current_step_for_bc.area if current_step_for_bc else None

    if request.method == 'POST':
        original_bi_id = usecase.bi_id
        # Update basic fields first
        usecase.name = request.form.get('name', '').strip()
        usecase.bi_id = request.form.get('bi_id', '').strip()
        # Process step might be None if dropdown is empty (shouldn't happen with required field in template)
        usecase.process_step_id = request.form.get('process_step_id', type=int)

        # --- Handle Priority field ---
        priority_str = request.form.get('priority')
        if priority_str: # If a value was provided
            if priority_str.isdigit(): # Check if it's a valid number string
                priority_val = int(priority_str)
                if 1 <= priority_val <= 4: # Check if number is in range 1-4
                    usecase.priority = priority_val
                else: # Number is outside 1-4 range
                    flash("Invalid priority value. Must be a number between 1 and 4, or empty.", "danger")
                    SessionLocal.remove()
                    # Pass current (unsaved) usecase object back to template
                    return render_template('edit_usecase.html', title=f"Edit Use Case: {usecase.name}", usecase=usecase, all_steps=all_steps, current_usecase=usecase, current_step=current_step_for_bc, current_area=current_area_for_bc)
            else: # Value provided but not a digit string
                 flash("Invalid priority format. Must be a number (1-4) or empty.", "danger")
                 SessionLocal.remove()
                 # Pass current (unsaved) usecase object back to template
                 return render_template('edit_usecase.html', title=f"Edit Use Case: {usecase.name}", usecase=usecase, all_steps=all_steps, current_usecase=usecase, current_step=current_step_for_bc, current_area=current_area_for_bc)
        else: # Value was not provided (empty string)
            usecase.priority = None
        # --- End Handle Priority field ---


        # --- Update New Fields from Form ---
        usecase.raw_content = request.form.get('raw_content', '').strip() or None
        usecase.summary = request.form.get('summary', '').strip() or None
        usecase.inspiration = request.form.get('inspiration', '').strip() or None
        usecase.wave = request.form.get('wave', '').strip() or None
        usecase.effort_level = request.form.get('effort_level', '').strip() or None
        usecase.status = request.form.get('status', '').strip() or None # Needs updating if you add a select/dropdown later
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
        # --- End Update New Fields ---


        # Check for mandatory fields AFTER updating all fields, but before commit
        if not usecase.name or not usecase.bi_id or not usecase.process_step_id:
            flash("Use Case Name, BI_ID, and Process Step are required.", "danger")
            SessionLocal.remove()
            # Pass current (unsaved) usecase object back to template
            return render_template('edit_usecase.html', title=f"Edit Use Case: {usecase.name}", usecase=usecase, all_steps=all_steps, current_usecase=usecase, current_step=current_step_for_bc, current_area=current_area_for_bc)

        # Check for BI_ID uniqueness only if it changed
        if usecase.bi_id != original_bi_id:
            existing_uc = session.query(UseCase)\
                .filter(UseCase.bi_id == usecase.bi_id, UseCase.id != usecase_id)\
                .first()
            if existing_uc:
                flash(f"Another use case with BI_ID '{usecase.bi_id}' already exists.", "danger")
                SessionLocal.remove()
                # Pass current (unsaved) usecase object back to template
                return render_template('edit_usecase.html', title=f"Edit Use Case: {usecase.name}", usecase=usecase, all_steps=all_steps, current_usecase=usecase, current_step=current_step_for_bc, current_area=current_area_for_bc)

        # If all validations pass, commit
        try:
            session.commit()
            flash("Use Case updated successfully!", "success")
            SessionLocal.remove()
            return redirect(url_for('usecases.view_usecase', usecase_id=usecase.id))
        except IntegrityError as e:
            session.rollback()
            # Check for specific constraint violations if needed, though priority is handled above
            # The DB check might still trigger if priority is manipulated outside the form
            if 'priority_range_check' in str(e):
                 flash("Database error: Priority must be between 1 and 4, or empty.", "danger")
            else:
                flash("Database error: Could not update use case. BI_ID might already exist or step is invalid.", "danger")
                print(f"Integrity Error updating use case {usecase_id}: {e}")
            SessionLocal.remove()
            # Render form again with error
            return render_template('edit_usecase.html', title=f"Edit Use Case: {usecase.name}", usecase=usecase, all_steps=all_steps, current_usecase=usecase, current_step=current_step_for_bc, current_area=current_area_for_bc)
        except Exception as e:
            session.rollback()
            flash(f"An unexpected error occurred: {e}", "danger")
            print(f"Error updating use case {usecase_id}: {e}")
            SessionLocal.remove()
            # Render form again with error
            return render_template('edit_usecase.html', title=f"Edit Use Case: {usecase.name}", usecase=usecase, all_steps=all_steps, current_usecase=usecase, current_step=current_step_for_bc, current_area=current_area_for_bc)

    # GET request or validation failed and rendered template above
    # If it was a validation failure above, the session would have been removed
    # Need to remove the session here if it was a successful GET request
    SessionLocal.remove()
    # For GET, usecase and its step/area are already loaded.
    # For POST render (due to validation error), usecase object holds the unsaved form data.
    return render_template('edit_usecase.html', title=f"Edit Use Case: {usecase.name}", usecase=usecase, all_steps=all_steps, current_usecase=usecase, current_step=current_step_for_bc, current_area=current_area_for_bc)


@usecase_routes.route('/<int:usecase_id>/delete', methods=['POST'])
@login_required
def delete_usecase(usecase_id):
    session = SessionLocal()
    usecase = session.query(UseCase).options(joinedload(UseCase.process_step)).get(usecase_id)
    redirect_url = url_for('index')

    if usecase is None:
        flash(f"Use Case with ID {usecase_id} not found.", "warning")
    else:
        step_id_for_redirect = usecase.process_step_id
        uc_name = usecase.name
        try:
            session.delete(usecase)
            session.commit()
            flash(f"Use Case '{uc_name}' deleted successfully.", "success")
            if step_id_for_redirect:
                redirect_url = url_for('steps.view_step', step_id=step_id_for_redirect)
        except Exception as e:
            session.rollback()
            flash(f"Error deleting use case: {e}", "danger")
            print(f"Error deleting use case {usecase_id}: {e}")
            # If delete fails, stay on the current usecase view or redirect to index as a fallback
            if usecase.process_step_id: # Use the original step_id if available
                 redirect_url = url_for('steps.view_step', step_id=usecase.process_step_id)

    SessionLocal.remove()
    return redirect(redirect_url)