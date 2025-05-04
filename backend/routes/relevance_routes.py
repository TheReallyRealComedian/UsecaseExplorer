# backend/routes/relevance_routes.py
from flask import Blueprint, request, flash, redirect, url_for
from flask_login import login_required
from ..app import SessionLocal
from ..models import UsecaseAreaRelevance, UsecaseStepRelevance, UsecaseUsecaseRelevance
from sqlalchemy.exc import IntegrityError

relevance_routes = Blueprint('relevance', __name__, url_prefix='/relevance')

@relevance_routes.route('/add/area', methods=['POST'])
@login_required
def add_area_relevance():
    """Handles the form submission for adding UseCase-Area relevance."""
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    target_area_id = request.form.get('target_area_id', type=int)
    score = request.form.get('relevance_score', type=int)
    content = request.form.get('relevance_content', '').strip() # Get content, strip whitespace

    if not all([source_usecase_id, target_area_id, score is not None]):
        flash("Missing required fields (Source UC ID, Target Area, Score).", "danger")
        # Redirect back to previous page or a sensible default
        redirect_url = (
            url_for('usecases.view_usecase', usecase_id=source_usecase_id)
            if source_usecase_id
            else url_for('index')
        )
        return redirect(request.referrer or redirect_url)

    if not (0 <= score <= 100):
         flash("Score must be between 0 and 100.", "danger")
         redirect_url = (
             url_for('usecases.view_usecase', usecase_id=source_usecase_id)
             if source_usecase_id
             else url_for('index')
         )
         return redirect(request.referrer or redirect_url)

    session = SessionLocal()
    try:
        # Check if this specific link already exists
        existing_link = session.query(UsecaseAreaRelevance).filter_by(
            source_usecase_id=source_usecase_id,
            target_area_id=target_area_id
        ).first()

        if existing_link:
            flash("Relevance link between this Use Case and Area already exists.", "warning")
        else:
            # Create and add the new link
            new_link = UsecaseAreaRelevance(
                source_usecase_id=source_usecase_id,
                target_area_id=target_area_id,
                relevance_score=score,
                relevance_content=content if content else None # Store None if empty
            )
            session.add(new_link)
            session.commit()
            flash("Area relevance link added successfully!", "success")

    except IntegrityError:
         session.rollback()
         flash("Database error: Could not add link. It might already exist.", "danger")
    except Exception as e:
        session.rollback()
        flash(f"An unexpected error occurred: {e}", "danger")
        print(f"Error adding area relevance: {e}") # Log the error
    finally:
        SessionLocal.remove()

    # Redirect back to the source use case detail page
    if source_usecase_id:
        return redirect(url_for('usecases.view_usecase', usecase_id=source_usecase_id))
    else:
        # Fallback if source_usecase_id was somehow missing
        return redirect(url_for('index'))

@relevance_routes.route('/add/step', methods=['POST'])
@login_required
def add_step_relevance():
    """Handles the form submission for adding UseCase-Step relevance."""
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    target_process_step_id = request.form.get('target_process_step_id', type=int) # Get step ID
    score = request.form.get('relevance_score', type=int)
    content = request.form.get('relevance_content', '').strip()

    if not all([source_usecase_id, target_process_step_id, score is not None]):
        flash("Missing required fields (Source UC ID, Target Step, Score).", "danger")
        redirect_url = (
            url_for('usecases.view_usecase', usecase_id=source_usecase_id)
            if source_usecase_id
            else url_for('index')
        )
        return redirect(request.referrer or redirect_url)

    if not (0 <= score <= 100):
         flash("Score must be between 0 and 100.", "danger")
         redirect_url = (
             url_for('usecases.view_usecase', usecase_id=source_usecase_id)
             if source_usecase_id
             else url_for('index')
         )
         return redirect(request.referrer or redirect_url)

    session = SessionLocal()
    try:
        # Check for existing link
        existing_link = session.query(UsecaseStepRelevance).filter_by(
            source_usecase_id=source_usecase_id,
            target_process_step_id=target_process_step_id
        ).first()

        if existing_link:
            flash("Relevance link between this Use Case and Process Step already exists.", "warning")
        else:
            # Create and add new link
            new_link = UsecaseStepRelevance(
                source_usecase_id=source_usecase_id,
                target_process_step_id=target_process_step_id, # Use correct column name
                relevance_score=score,
                relevance_content=content if content else None
            )
            session.add(new_link)
            session.commit()
            flash("Step relevance link added successfully!", "success")

    except IntegrityError:
         session.rollback()
         flash("Database error: Could not add link. It might already exist.", "danger")
    except Exception as e:
        session.rollback()
        flash(f"An unexpected error occurred: {e}", "danger")
        print(f"Error adding step relevance: {e}")
    finally:
        SessionLocal.remove()

    # Redirect back to the source use case detail page
    if source_usecase_id:
        return redirect(url_for('usecases.view_usecase', usecase_id=source_usecase_id))
    else:
        return redirect(url_for('index'))


@relevance_routes.route('/add/usecase', methods=['POST'])
@login_required
def add_usecase_relevance():
    """Handles the form submission for adding UseCase-UseCase relevance."""
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    target_usecase_id = request.form.get('target_usecase_id', type=int) # Get target UC ID
    score = request.form.get('relevance_score', type=int)
    content = request.form.get('relevance_content', '').strip()

    redirect_url_fallback = url_for('index')
    if source_usecase_id:
        redirect_url_fallback = url_for('usecases.view_usecase', usecase_id=source_usecase_id)

    if not all([source_usecase_id, target_usecase_id, score is not None]):
        flash("Missing required fields (Source UC ID, Target UC ID, Score).", "danger")
        return redirect(request.referrer or redirect_url_fallback)

    # Prevent linking a Use Case to itself
    if source_usecase_id == target_usecase_id:
        flash("Cannot link a Use Case to itself.", "warning")
        return redirect(redirect_url_fallback)

    if not (0 <= score <= 100):
         flash("Score must be between 0 and 100.", "danger")
         return redirect(redirect_url_fallback)

    session = SessionLocal()
    try:
        # Check for existing link (in this specific direction)
        existing_link = session.query(UsecaseUsecaseRelevance).filter_by(
            source_usecase_id=source_usecase_id,
            target_usecase_id=target_usecase_id
        ).first()

        if existing_link:
            flash("Relevance link between these Use Cases already exists.", "warning")
        else:
            # Create and add new link
            new_link = UsecaseUsecaseRelevance(
                source_usecase_id=source_usecase_id,
                target_usecase_id=target_usecase_id, # Use correct column name
                relevance_score=score,
                relevance_content=content if content else None
            )
            session.add(new_link)
            session.commit()
            flash("Use Case relevance link added successfully!", "success")

    except IntegrityError as ie:
         session.rollback()
         # Check if it's the self-relevance constraint violation
         if 'no_self_relevance' in str(ie).lower():
             flash("Database error: Cannot link a Use Case to itself.", "danger")
         else:
             flash("Database error: Could not add link. It might already exist or violate constraints.", "danger")
             print(f"IntegrityError adding use case relevance: {ie}") # Log specific error
    except Exception as e:
        session.rollback()
        flash(f"An unexpected error occurred: {e}", "danger")
        print(f"Error adding use case relevance: {e}")
    finally:
        SessionLocal.remove()

    # Redirect back to the source use case detail page
    return redirect(redirect_url_fallback)