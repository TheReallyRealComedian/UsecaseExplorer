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
    """Displays the detail page for a specific Use Case."""
    session = SessionLocal()
    # try: # <<< COMMENTED OUT
    # Query for the specific Use Case, preloading related data
    usecase = session.query(UseCase).options(
        # Load the process step and its associated area
        joinedload(UseCase.process_step).joinedload(ProcessStep.area),
        # Load outgoing Area relevance links and the target Area
        selectinload(UseCase.relevant_to_areas)
            .joinedload(UsecaseAreaRelevance.target_area),
        # Load outgoing Step relevance links and the target Step
        selectinload(UseCase.relevant_to_steps)
            .joinedload(UsecaseStepRelevance.target_process_step),
        # Load outgoing Use Case relevance links (where this UC is source) and the target UC
        selectinload(UseCase.relevant_to_usecases_as_source)
            .joinedload(UsecaseUsecaseRelevance.target_usecase),
        # Load incoming Use Case relevance links (where this UC is target) and the source UC
        selectinload(UseCase.relevant_to_usecases_as_target)
            .joinedload(UsecaseUsecaseRelevance.source_usecase)
    ).get(usecase_id) # Use get() for primary key lookup

    if usecase is None:
        flash(f"Use Case with ID {usecase_id} not found.", "warning")
        SessionLocal.remove() # Manually remove if redirecting early
        return redirect(url_for('index'))

    # Query data needed for dropdowns/selectors in the template
    all_areas = session.query(Area).order_by(Area.name).all()
    all_steps = session.query(ProcessStep).order_by(ProcessStep.name).all()
    # Query other use cases, excluding the current one
    other_usecases = session.query(UseCase)\
        .filter(UseCase.id != usecase_id)\
        .order_by(UseCase.name)\
        .all()

    # Render the detail template
    response = render_template(
        'usecase_detail.html',
        title=f"Use Case: {usecase.name}",
        usecase=usecase,
        all_areas=all_areas,
        all_steps=all_steps,
        other_usecases=other_usecases
    )
    SessionLocal.remove() # Ensure removal before returning response
    return response

    # except Exception as e: # <<< COMMENTED OUT Start
    #     # Log the error for debugging
    #     print(f"Error fetching use case {usecase_id} or related data: {e}")
    #     flash("An error occurred while fetching details.", "danger")
    #     # Ensure session is removed even on error before redirect
    #     SessionLocal.remove()
    #     return redirect(url_for('index'))
    # --- COMMENTED OUT End
    # finally: # <<< COMMENTED OUT Start (as try is commented out)
    #     # Ensure the session is closed properly, even if an error occurred above
    #     # before the explicit removal calls (e.g., during query building).
    #     # This might run redundantly if no exception, but it's safe.
    #     SessionLocal.remove()
    # --- COMMENTED OUT End

# Add other use case related routes below (e.g., list, create, edit, delete)
# ...