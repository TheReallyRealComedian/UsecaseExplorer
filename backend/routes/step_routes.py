# backend/routes/step_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy.orm import joinedload, selectinload

from ..app import SessionLocal
# Ensure all necessary models are imported
from ..models import ProcessStep, UseCase, Area, UsecaseStepRelevance

# Define the blueprint IN THIS FILE
step_routes = Blueprint('steps', __name__,
                        template_folder='../templates', # Points to backend/templates
                        url_prefix='/steps') # User-facing pages, so /steps not /api/steps

@step_routes.route('/<int:step_id>')
@login_required
def view_step(step_id):
    session = SessionLocal()
    try:
        step = session.query(ProcessStep).options(
            # Load parent Area for breadcrumbs/info
            joinedload(ProcessStep.area),
            # Load UseCases directly under this ProcessStep
            selectinload(ProcessStep.use_cases),
            # Load UsecaseStepRelevance records where this Step is the target,
            # and also load the source UseCase for each of those relevance links.
            selectinload(ProcessStep.usecase_relevance)
                .joinedload(UsecaseStepRelevance.source_usecase)
        ).get(step_id)

        if step is None:
            flash(f"Process Step with ID {step_id} not found.", "warning")
            return redirect(url_for('index'))

        # The step object now contains:
        # - step.area (the parent Area object)
        # - step.use_cases (list of UseCase objects directly under this step)
        # - step.usecase_relevance (list of UsecaseStepRelevance objects)
        #   - each rel in step.usecase_relevance has rel.source_usecase (the UseCase relevant to this step)

        return render_template(
            'step_detail.html',
            title=f"Process Step: {step.name}",
            step=step
        )
    except Exception as e:
        print(f"Error fetching step {step_id}: {e}")
        flash("An error occurred while fetching step details.", "danger")
        return redirect(url_for('index'))
    finally:
        SessionLocal.remove()