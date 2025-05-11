# backend/routes/area_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy.orm import joinedload, selectinload

from ..app import SessionLocal
# Ensure all necessary models are imported
from ..models import Area, ProcessStep, UseCase, UsecaseAreaRelevance

# Define the blueprint IN THIS FILE
area_routes = Blueprint('areas', __name__,
                        template_folder='../templates', # Points to backend/templates
                        url_prefix='/areas') # User-facing pages, so /areas not /api/areas

@area_routes.route('/<int:area_id>')
@login_required
def view_area(area_id):
    session = SessionLocal()
    try:
        area = session.query(Area).options(
            # Load ProcessSteps under this Area, and UseCases under those ProcessSteps
            selectinload(Area.process_steps).selectinload(ProcessStep.use_cases),
            # Load UsecaseAreaRelevance records where this Area is the target,
            # and also load the source UseCase for each of those relevance links.
            selectinload(Area.usecase_relevance)
                .joinedload(UsecaseAreaRelevance.source_usecase)
        ).get(area_id)

        if area is None:
            flash(f"Area with ID {area_id} not found.", "warning")
            return redirect(url_for('index'))

        # The area object now contains:
        # - area.process_steps (list of ProcessStep objects)
        #   - each step in area.process_steps has step.use_cases (list of UseCase objects)
        # - area.usecase_relevance (list of UsecaseAreaRelevance objects)
        #   - each rel in area.usecase_relevance has rel.source_usecase (the UseCase relevant to this area)

        return render_template(
            'area_detail.html',
            title=f"Area: {area.name}",
            area=area,
            current_area=area  # For breadcrumbs
        )
    except Exception as e:
        print(f"Error fetching area {area_id}: {e}")
        flash("An error occurred while fetching area details.", "danger")
        return redirect(url_for('index'))
    finally:
        SessionLocal.remove()