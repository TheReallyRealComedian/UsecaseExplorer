# backend/routes/step_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy.orm import joinedload, selectinload

from ..app import SessionLocal
from ..models import ProcessStep, UseCase, Area, UsecaseStepRelevance # Ensure Area is imported

step_routes = Blueprint('steps', __name__,
                        template_folder='../templates',
                        url_prefix='/steps')

@step_routes.route('/<int:step_id>')
@login_required
def view_step(step_id):
    session = SessionLocal()
    try:
        print(f"--- Attempting to fetch ProcessStep with ID: {step_id} ---") # DEBUG
        step = session.query(ProcessStep).options(
            joinedload(ProcessStep.area),
            selectinload(ProcessStep.use_cases),
            selectinload(ProcessStep.usecase_relevance)
                .joinedload(UsecaseStepRelevance.source_usecase)
        ).get(step_id)

        if step is None:
            flash(f"Process Step with ID {step_id} not found.", "warning")
            print(f"--- ProcessStep with ID {step_id} NOT FOUND ---") # DEBUG
            return redirect(url_for('index'))

        # ---- DETAILED DEBUGGING ----
        print(f"--- Fetched Step: {step} ---")
        print(f"--- Step Name: {step.name} ---")
        print(f"--- Step Area Object: {step.area} ---")
        if step.area:
            print(f"--- Step Area Name: {step.area.name} ---")
        else:
            print(f"--- Step Area IS NONE ---") # IMPORTANT CHECK

        print(f"--- Step Use Cases Count: {len(step.use_cases) if step.use_cases else 0} ---")
        print(f"--- Step Relevance Count: {len(step.usecase_relevance) if step.usecase_relevance else 0} ---")
        # ---- END DETAILED DEBUGGING ----

        return render_template(
            'step_detail.html',
            title=f"Process Step: {step.name}",
            step=step,
            current_step=step,
            current_area=step.area # This is passed to base.html for breadcrumbs
        )
    except AttributeError as ae: # Catch AttributeError specifically
        print(f"!!! AttributeError in view_step for ID {step_id}: {ae} !!!") # DEBUG
        import traceback
        traceback.print_exc() # Print full traceback
        flash(f"An AttributeError occurred: {ae}. Please check the logs.", "danger")
        return redirect(url_for('index'))
    except Exception as e:
        print(f"!!! General Error fetching step {step_id}: {e} !!!") # DEBUG
        import traceback
        traceback.print_exc() # Print full traceback
        flash("An error occurred while fetching step details. Please check server logs.", "danger")
        return redirect(url_for('index'))
    finally:
        SessionLocal.remove()