# backend/routes/usecase_routes.py
from flask import Blueprint, render_template, abort, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy.orm import joinedload, selectinload

# Import Session/Models needed
from ..app import SessionLocal
from ..models import (
    UseCase, ProcessStep, Area,
    UsecaseAreaRelevance, UsecaseStepRelevance, UsecaseUsecaseRelevance
)

# Define the blueprint
usecase_routes = Blueprint('usecases', __name__,
                           template_folder='../templates',
                           url_prefix='/usecases')

@usecase_routes.route('/<int:usecase_id>')
@login_required
def view_usecase(usecase_id):
    """Displays the detail page for a specific Use Case."""
    session = SessionLocal()
    try:
        # Query for the specific Use Case, preloading related data
        usecase = session.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area),
            selectinload(UseCase.relevant_to_areas).joinedload(UsecaseAreaRelevance.target_area),
            selectinload(UseCase.relevant_to_steps).joinedload(UsecaseStepRelevance.target_process_step),
            selectinload(UseCase.relevant_to_usecases_as_source).joinedload(UsecaseUsecaseRelevance.target_usecase)
        ).get(usecase_id) # .get() is efficient for primary key lookup

        if usecase is None:
            flash(f"Use Case with ID {usecase_id} not found.", "warning")
            return redirect(url_for('index'))

        # Query data needed for dropdowns/selectors in the template
        all_areas = session.query(Area).order_by(Area.name).all()
        all_steps = session.query(ProcessStep).order_by(ProcessStep.name).all()
        # Query other use cases, excluding the current one being viewed
        other_usecases = session.query(UseCase)\
            .filter(UseCase.id != usecase_id)\
            .order_by(UseCase.name)\
            .all()

        # Render the detail template, passing the main use case object
        # and the lists for selectors
        return render_template(
            'usecase_detail.html',
            title=f"Use Case: {usecase.name}",
            usecase=usecase,
            all_areas=all_areas,
            all_steps=all_steps,
            other_usecases=other_usecases
        )

    except Exception as e:
        print(f"Error fetching use case {usecase_id} or selector data: {e}")
        flash("An error occurred while fetching details.", "danger")
        return redirect(url_for('index'))
    finally:
        # Ensure the session is closed
        SessionLocal.remove()

# Add other use case related routes below (e.g., list, create, edit, delete)
# ...