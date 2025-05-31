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
        current_item_for_bc = usecase # The specific item for "active" breadcrumb logic

        return render_template(
            'usecase_detail.html',
            title=f"Use Case: {usecase.name}",
            usecase=usecase,
            all_areas=all_areas,
            all_steps=all_steps,
            other_usecases=other_usecases, # For the 'add relevance' forms
            current_usecase=usecase, # For breadcrumbs (the usecase itself)
            current_step=current_step_for_bc, # For breadcrumbs (the parent step)
            current_area=current_area_for_bc, # For breadcrumbs (the parent area)
            current_item=current_item_for_bc
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
    usecase = session.query(UseCase).options(
        joinedload(UseCase.process_step).joinedload(ProcessStep.area)
    ).get(usecase_id)
    all_steps = session.query(ProcessStep).order_by(ProcessStep.name).all()

    if usecase is None:
        flash(f"Use Case with ID {usecase_id} not found.", "warning")
        SessionLocal.remove()
        return redirect(url_for('index'))

    current_step_for_bc = usecase.process_step
    current_area_for_bc = current_step_for_bc.area if current_step_for_bc else None
    current_item_for_bc = usecase # For "active" breadcrumb logic

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
                    SessionLocal.remove()
                    return render_template(
                        'edit_usecase.html',
                        title=f"Edit Use Case: {usecase.name}",
                        usecase=usecase, # For the page's data
                        all_steps=all_steps, # For the dropdown
                        current_usecase=usecase, # For breadcrumbs
                        current_step=current_step_for_bc, # For breadcrumbs
                        current_area=current_area_for_bc, # For breadcrumbs
                        current_item=current_item_for_bc # For "active" breadcrumb logic
                    )
            else:
                 flash("Invalid priority format. Must be a number (1-4) or empty.", "danger")
                 SessionLocal.remove()
                 return render_template(
                     'edit_usecase.html',
                     title=f"Edit Use Case: {usecase.name}",
                     usecase=usecase, # For the page's data
                     all_steps=all_steps, # For the dropdown
                     current_usecase=usecase, # For breadcrumbs
                     current_step=current_step_for_bc, # For breadcrumbs
                     current_area=current_area_for_bc, # For breadcrumbs
                     current_item=current_item_for_bc # For "active" breadcrumb logic
                 )
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
            SessionLocal.remove()
            return render_template(
                'edit_usecase.html',
                title=f"Edit Use Case: {usecase.name}",
                usecase=usecase, # For the page's data
                all_steps=all_steps, # For the dropdown
                current_usecase=usecase, # For breadcrumbs
                current_step=current_step_for_bc, # For breadcrumbs
                current_area=current_area_for_bc, # For breadcrumbs
                current_item=current_item_for_bc # For "active" breadcrumb logic
            )

        if usecase.bi_id != original_bi_id:
            existing_uc = session.query(UseCase)\
                .filter(UseCase.bi_id == usecase.bi_id, UseCase.id != usecase_id)\
                .first()
            if existing_uc:
                flash(f"Another use case with BI_ID '{usecase.bi_id}' already exists.", "danger")
                SessionLocal.remove()
                return render_template(
                    'edit_usecase.html',
                    title=f"Edit Use Case: {usecase.name}",
                    usecase=usecase, # For the page's data
                    all_steps=all_steps, # For the dropdown
                    current_usecase=usecase, # For breadcrumbs
                    current_step=current_step_for_bc, # For breadcrumbs
                    current_area=current_area_for_bc, # For breadcrumbs
                    current_item=current_item_for_bc # For "active" breadcrumb logic
                )

        try:
            session.commit()
            flash("Use Case updated successfully!", "success")
            return redirect(url_for('usecases.view_usecase', usecase_id=usecase.id))
        except IntegrityError as e:
            session.rollback()
            if 'priority_range_check' in str(e):
                 flash("Database error: Priority must be between 1 and 4, or empty.", "danger")
            else:
                flash("Database error: Could not update use case. BI_ID might already exist or step is invalid.", "danger")
                print(f"Integrity Error updating use case {usecase_id}: {e}")
            return render_template(
                'edit_usecase.html',
                title=f"Edit Use Case: {usecase.name}",
                usecase=usecase, # For the page's data
                all_steps=all_steps, # For the dropdown
                current_usecase=usecase, # For breadcrumbs
                current_step=current_step_for_bc, # For breadcrumbs
                current_area=current_area_for_bc, # For breadcrumbs
                current_item=current_item_for_bc # For "active" breadcrumb logic
            )
        except Exception as e:
            session.rollback()
            flash(f"An unexpected error occurred: {e}", "danger")
            print(f"Error updating use case {usecase_id}: {e}")
            SessionLocal.remove()
            return render_template(
                'edit_usecase.html',
                title=f"Edit Use Case: {usecase.name}", # Page title
                usecase=usecase, # For the page's data
                all_steps=all_steps, # For the dropdown
                current_usecase=usecase, # For breadcrumbs
                current_step=current_step_for_bc, # For breadcrumbs
                current_area=current_area_for_bc, # For breadcrumbs
                current_item=current_item_for_bc # For "active" breadcrumb logic
            )

    # For GET or re-render on error (if not handled by POST's error returns)
    SessionLocal.remove()
    return render_template(
        'edit_usecase.html',
        title=f"Edit Use Case: {usecase.name}",
        usecase=usecase,
        all_steps=all_steps,
        current_usecase=usecase,
        current_step=current_step_for_bc,
        current_area=current_area_for_bc,
        current_item=current_item_for_bc
    )


@usecase_routes.route('/<int:usecase_id>/delete', methods=['POST'])
@login_required
def delete_usecase(usecase_id):
    session = SessionLocal()
    usecase = session.query(UseCase).options(joinedload(UseCase.process_step)).get(usecase_id)
    # Check if the deletion request came from a step detail page and store the step ID for redirect
    step_id_for_redirect = request.form.get('process_step_id_for_redirect', type=int)
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
            if step_id_for_redirect is not None: # Prioritize redirecting back to the step page
                redirect_url = url_for('steps.view_step', step_id=step_id_for_redirect)
        except Exception as e:
            session.rollback()
            flash(f"Error deleting use case: {e}", "danger")
            print(f"Error deleting use case {usecase_id}: {e}")
            # If deletion failed, try to redirect back to where we came from, if possible
            if step_id_for_redirect is not None:
                 redirect_url = url_for('steps.view_step', step_id=usecase.process_step_id)

    SessionLocal.remove()
    return redirect(redirect_url)