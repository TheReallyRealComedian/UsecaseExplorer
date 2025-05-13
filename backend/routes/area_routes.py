# backend/routes/area_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for, request
from flask_login import login_required
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal # CHANGED
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
            selectinload(Area.process_steps).selectinload(ProcessStep.use_cases),
            selectinload(Area.usecase_relevance)
                .joinedload(UsecaseAreaRelevance.source_usecase)
        ).get(area_id)

        if area is None:
            flash(f"Area with ID {area_id} not found.", "warning")
            return redirect(url_for('index'))

        return render_template(
            'area_detail.html',
            title=f"Area: {area.name}",
            area=area,
            current_area=area
        )
    except Exception as e:
        print(f"Error fetching area {area_id}: {e}")
        flash("An error occurred while fetching area details.", "danger")
        return redirect(url_for('index'))
    finally:
        SessionLocal.remove()


@area_routes.route('/<int:area_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_area(area_id):
    session = SessionLocal()
    area = session.query(Area).get(area_id)

    if area is None:
        flash(f"Area with ID {area_id} not found.", "warning")
        SessionLocal.remove()
        return redirect(url_for('index'))

    if request.method == 'POST':
        new_name = request.form.get('name', '').strip()
        new_description = request.form.get('description', '').strip()

        if not new_name:
            flash("Area name cannot be empty.", "danger")
        else:
            # Check for name uniqueness if changed
            if new_name != area.name:
                existing_area = session.query(Area).filter(Area.name == new_name, Area.id != area_id).first()
                if existing_area:
                    flash(f"Another area with the name '{new_name}' already exists.", "danger")
                    # Return to form with current (unsaved) data
                    area.name = new_name # To show the problematic name in the form
                    area.description = new_description
                    SessionLocal.remove()
                    return render_template('edit_area.html', title=f"Edit Area: {area.name}", area=area, current_area=area)
            
            area.name = new_name
            area.description = new_description if new_description else None
            try:
                session.commit()
                flash("Area updated successfully!", "success")
                SessionLocal.remove()
                return redirect(url_for('areas.view_area', area_id=area.id))
            except IntegrityError: # Should be caught by the explicit check above, but as a fallback
                session.rollback()
                flash("Database error: Could not update area. The name might already exist.", "danger")
            except Exception as e:
                session.rollback()
                flash(f"An unexpected error occurred: {e}", "danger")
                print(f"Error updating area {area_id}: {e}")
    
    # For GET request or if POST had errors and needs to re-render
    SessionLocal.remove() # Remove session if it wasn't already (e.g. on GET)
    return render_template('edit_area.html', title=f"Edit Area: {area.name}", area=area, current_area=area)


@area_routes.route('/<int:area_id>/delete', methods=['POST'])
@login_required
def delete_area(area_id):
    session = SessionLocal()
    area = session.query(Area).get(area_id)

    if area is None:
        flash(f"Area with ID {area_id} not found.", "warning")
    else:
        try:
            session.delete(area)
            session.commit()
            flash(f"Area '{area.name}' and all its contents deleted successfully.", "success")
        except Exception as e:
            session.rollback()
            flash(f"Error deleting area: {e}", "danger")
            print(f"Error deleting area {area_id}: {e}")
    
    SessionLocal.remove()
    return redirect(url_for('index'))