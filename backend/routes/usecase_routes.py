# backend/routes/usecase_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy.orm import joinedload, selectinload

# Import Session/Models needed
from ..app import SessionLocal
from ..models import (
    UseCase, ProcessStep, Area,
    UsecaseAreaRelevance, UsecaseStepRelevance, UsecaseUsecaseRelevance
)

# Define the blueprint
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
        SessionLocal.remove()
        return redirect(url_for('index'))

    all_areas = session.query(Area).order_by(Area.name).all()
    all_steps = session.query(ProcessStep).order_by(ProcessStep.name).all()
    other_usecases = session.query(UseCase)\
        .filter(UseCase.id != usecase_id)\
        .order_by(UseCase.name)\
        .all()

    # Context for breadcrumbs
    current_step_for_bc = usecase.process_step if usecase else None
    current_area_for_bc = current_step_for_bc.area if current_step_for_bc else None

    response = render_template(
        'usecase_detail.html',
        title=f"Use Case: {usecase.name}",
        usecase=usecase,
        all_areas=all_areas,
        all_steps=all_steps,
        other_usecases=other_usecases,
        current_usecase=usecase,           # For breadcrumbs
        current_step=current_step_for_bc,  # For breadcrumbs
        current_area=current_area_for_bc   # For breadcrumbs
    )
    SessionLocal.remove()
    return response

# Add other use case related routes below (e.g., list, create, edit, delete)
# ...