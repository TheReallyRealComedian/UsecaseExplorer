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
            joinedload(ProcessStep.area),
            selectinload(ProcessStep.use_cases),
            selectinload(ProcessStep.usecase_relevance)
                .joinedload(UsecaseStepRelevance.source_usecase)
        ).get(step_id)

        if step is None:
            flash(f"Process Step with ID {step_id} not found.", "warning")
            return redirect(url_for('index'))

        return render_template(
            'step_detail.html',
            title=f"Process Step: {step.name}",
            step=step,
            current_step=step,        # For breadcrumbs
            current_area=step.area    # For breadcrumbs
        )
    except Exception as e:
        print(f"Error fetching step {step_id}: {e}")
        flash("An error occurred while fetching step details.", "danger")
        return redirect(url_for('index'))
    finally:
        SessionLocal.remove()