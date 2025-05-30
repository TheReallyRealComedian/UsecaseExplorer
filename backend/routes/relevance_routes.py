# backend/routes/relevance_routes.py
from flask import Blueprint, request, flash, redirect, url_for, abort, render_template, jsonify
from flask_login import login_required
from sqlalchemy.orm import joinedload
from ..db import SessionLocal
from ..models import (
    UsecaseAreaRelevance, UsecaseStepRelevance, UsecaseUsecaseRelevance,
    ProcessStepProcessStepRelevance,
    UseCase, ProcessStep, Area
)
from sqlalchemy.exc import IntegrityError

relevance_routes = Blueprint('relevance', __name__, url_prefix='/relevance')

@relevance_routes.route('/add/area', methods=['POST'])
@login_required
def add_area_relevance():
    """Handles the form submission for adding UseCase-Area relevance."""
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    target_area_id = request.form.get('target_area_id', type=int)
    score_str = request.form.get('relevance_score')
    content = request.form.get('relevance_content', '').strip()

    redirect_url = (
        url_for('usecases.view_usecase', usecase_id=source_usecase_id)
        if source_usecase_id
        else url_for('index')
    )

    if not all([source_usecase_id, target_area_id, score_str is not None]):
        flash("Missing required fields (Source UC ID, Target Area, Score).", "danger")
        return redirect(request.referrer or redirect_url)

    try:
        score = int(score_str)
        if not (0 <= score <= 100):
            flash("Score must be between 0 and 100.", "danger")
            return redirect(request.referrer or redirect_url)
    except ValueError:
        flash("Invalid score format. Score must be a number.", "danger")
        return redirect(request.referrer or redirect_url)

    session = SessionLocal()
    try:
        existing_link = session.query(UsecaseAreaRelevance).filter_by(
            source_usecase_id=source_usecase_id,
            target_area_id=target_area_id
        ).first()

        if existing_link:
            flash("Relevance link between this Use Case and Area already exists.", "warning")
        else:
            new_link = UsecaseAreaRelevance(
                source_usecase_id=source_usecase_id,
                target_area_id=target_area_id,
                relevance_score=score,
                relevance_content=content if content else None
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
        print(f"Error adding area relevance: {e}")
    finally:
        SessionLocal.remove()

    return redirect(redirect_url)

@relevance_routes.route('/add/step', methods=['POST'])
@login_required
def add_step_relevance():
    """Handles the form submission for adding UseCase-Step relevance."""
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    target_process_step_id = request.form.get('target_process_step_id', type=int)
    score_str = request.form.get('relevance_score')
    content = request.form.get('relevance_content', '').strip()

    redirect_url = (
        url_for('usecases.view_usecase', usecase_id=source_usecase_id)
        if source_usecase_id
        else url_for('index')
    )

    if not all([source_usecase_id, target_process_step_id, score_str is not None]):
        flash("Missing required fields (Source UC ID, Target Step, Score).", "danger")
        return redirect(request.referrer or redirect_url)

    try:
        score = int(score_str)
        if not (0 <= score <= 100):
            flash("Score must be between 0 and 100.", "danger")
            return redirect(request.referrer or redirect_url)
    except ValueError:
        flash("Invalid score format. Score must be a number.", "danger")
        return redirect(request.referrer or redirect_url)

    session = SessionLocal()
    try:
        existing_link = session.query(UsecaseStepRelevance).filter_by(
            source_usecase_id=source_usecase_id,
            target_process_step_id=target_process_step_id
        ).first()

        if existing_link:
            flash("Relevance link between this Use Case and Process Step already exists.", "warning")
        else:
            new_link = UsecaseStepRelevance(
                source_usecase_id=source_usecase_id,
                target_process_step_id=target_process_step_id,
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

    return redirect(redirect_url)


@relevance_routes.route('/add/usecase', methods=['POST'])
@login_required
def add_usecase_relevance():
    """Handles the form submission for adding UseCase-UseCase relevance."""
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    target_usecase_id = request.form.get('target_usecase_id', type=int)
    score_str = request.form.get('relevance_score')
    content = request.form.get('relevance_content', '').strip()

    redirect_url_fallback = url_for('index')
    if source_usecase_id:
        redirect_url_fallback = url_for('usecases.view_usecase', usecase_id=source_usecase_id)

    if not all([source_usecase_id, target_usecase_id, score_str is not None]):
        flash("Missing required fields (Source UC ID, Target UC ID, Score).", "danger")
        return redirect(request.referrer or redirect_url_fallback)

    if source_usecase_id == target_usecase_id:
        flash("Cannot link a Use Case to itself.", "warning")
        return redirect(redirect_url_fallback)

    try:
        score = int(score_str)
        if not (0 <= score <= 100):
            flash("Score must be between 0 and 100.", "danger")
            return redirect(redirect_url_fallback)
    except ValueError:
        flash("Invalid score format. Score must be a number.", "danger")
        return redirect(redirect_url_fallback)

    session = SessionLocal()
    try:
        existing_link = session.query(UsecaseUsecaseRelevance).filter_by(
            source_usecase_id=source_usecase_id,
            target_usecase_id=target_usecase_id
        ).first()

        if existing_link:
            flash("Relevance link between these Use Cases already exists.", "warning")
        else:
            new_link = UsecaseUsecaseRelevance(
                source_usecase_id=source_usecase_id,
                target_usecase_id=target_usecase_id,
                relevance_score=score,
                relevance_content=content if content else None
            )
            session.add(new_link)
            session.commit()
            flash("Use Case relevance link added successfully!", "success")

    except IntegrityError as ie:
        session.rollback()
        if 'no_self_relevance' in str(ie).lower() or 'chk_usecase_usecase_relevance_no_self_relevance' in str(ie).lower():
            flash("Database error: Cannot link a Use Case to itself.", "danger")
        else:
            flash("Database error: Could not add link. It might already exist or violate constraints.", "danger")
            print(f"IntegrityError adding use case relevance: {ie}")
    except Exception as e:
        session.rollback()
        flash(f"An unexpected error occurred: {e}", "danger")
        print(f"Error adding use case relevance: {e}")
    finally:
        SessionLocal.remove()

    return redirect(redirect_url_fallback)

@relevance_routes.route('/add/step_to_step', methods=['POST'])
@login_required
def add_step_to_step_relevance():
    """Handles the form submission for adding ProcessStep-ProcessStep relevance."""
    source_process_step_id = request.form.get('source_process_step_id', type=int)
    target_process_step_id = request.form.get('target_process_step_id', type=int)
    score_str = request.form.get('relevance_score')
    content = request.form.get('relevance_content', '').strip()

    redirect_url_fallback = url_for('index')
    if source_process_step_id:
        redirect_url_fallback = url_for('steps.view_step', step_id=source_process_step_id)

    if not all([source_process_step_id, target_process_step_id, score_str is not None]):
        flash("Missing required fields (Source Step ID, Target Step ID, Score).", "danger")
        return redirect(request.referrer or redirect_url_fallback)

    if source_process_step_id == target_process_step_id:
        flash("Cannot link a Process Step to itself.", "warning")
        return redirect(redirect_url_fallback)

    try:
        score = int(score_str)
        if not (0 <= score <= 100):
            flash("Score must be between 0 and 100.", "danger")
            return redirect(redirect_url_fallback)
    except ValueError:
        flash("Invalid score format. Score must be a number.", "danger")
        return redirect(redirect_url_fallback)

    session = SessionLocal()
    try:
        existing_link = session.query(ProcessStepProcessStepRelevance).filter_by(
            source_process_step_id=source_process_step_id,
            target_process_step_id=target_process_step_id
        ).first()

        if existing_link:
            flash("Relevance link between these Process Steps already exists.", "warning")
        else:
            new_link = ProcessStepProcessStepRelevance(
                source_process_step_id=source_process_step_id,
                target_process_step_id=target_process_step_id,
                relevance_score=score,
                relevance_content=content if content else None
            )
            session.add(new_link)
            session.commit()
            flash("Process Step relevance link added successfully!", "success")

    except IntegrityError as ie:
        session.rollback()
        if 'no_self_step_relevance' in str(ie).lower() or 'chk_process_step_process_step_relevance_no_self_step_relevance' in str(ie).lower():
            flash("Database error: Cannot link a Process Step to itself.", "danger")
        else:
            flash("Database error: Could not add link. It might already exist or violate constraints.", "danger")
            print(f"IntegrityError adding step-to-step relevance: {ie}")
    except Exception as e:
        session.rollback()
        flash(f"An unexpected error occurred: {e}", "danger")
        print(f"Error adding step-to-step relevance: {e}")
    finally:
        SessionLocal.remove()

    return redirect(redirect_url_fallback)

# --- DELETE ROUTES ---

@relevance_routes.route('/delete/area/<int:relevance_id>', methods=['POST'])
@login_required
def delete_area_relevance(relevance_id):
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    session = SessionLocal()
    try:
        link = session.query(UsecaseAreaRelevance).get(relevance_id)
        if link:
            if source_usecase_id is None and hasattr(link, 'source_usecase_id') and link.source_usecase_id:
                source_usecase_id = link.source_usecase_id

            session.delete(link)
            session.commit()
            flash("Area relevance link deleted successfully.", "success")
        else:
            flash("Area relevance link not found.", "warning")
    except Exception as e:
        session.rollback()
        flash(f"Error deleting area relevance link: {e}", "danger")
        print(f"Error deleting area relevance {relevance_id}: {e}")
    finally:
        SessionLocal.remove()

    if source_usecase_id:
        return redirect(url_for('usecases.view_usecase', usecase_id=source_usecase_id))
    return redirect(url_for('index'))


@relevance_routes.route('/delete/step/<int:relevance_id>', methods=['POST'])
@login_required
def delete_step_relevance(relevance_id):
    # Get the source use case ID from the form, if present. This is the page we came from.
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    # NEW: Get the step ID from the form, if present. This is the page we came from.
    referrer_step_id = request.form.get('referrer_step_id', type=int)
    session = SessionLocal()
    try:
        link = session.query(UsecaseStepRelevance).get(relevance_id)
        if link:
            # If source_usecase_id wasn't passed in the form, try to get it from the link object itself
            if source_usecase_id is None and hasattr(link, 'source_usecase_id') and link.source_usecase_id:
                source_usecase_id = link.source_usecase_id

            session.delete(link)
            session.commit()
            flash("Step relevance link deleted successfully.", "success")
        else:
            flash("Step relevance link not found.", "warning")
    except Exception as e:
        session.rollback()
        flash(f"Error deleting step relevance link: {e}", "danger")
        print(f"Error deleting step relevance {relevance_id}: {e}")
    finally:
        SessionLocal.remove()

    # Determine redirect URL based on what's available
    if referrer_step_id: # Prioritize redirecting back to the step page if it was the referrer
        return redirect(url_for('steps.view_step', step_id=referrer_step_id))
    elif source_usecase_id: # Fallback to usecase page
        return redirect(url_for('usecases.view_usecase', usecase_id=source_usecase_id))
    return redirect(url_for('index'))


@relevance_routes.route('/delete/usecase/<int:relevance_id>', methods=['POST'])
@login_required
def delete_usecase_relevance(relevance_id):
    source_usecase_id_form = request.form.get('source_usecase_id', type=int)
    session = SessionLocal()
    redirect_uc_id = source_usecase_id_form

    try:
        link = session.query(UsecaseUsecaseRelevance).get(relevance_id)
        if link:
            if not redirect_uc_id and hasattr(link, 'source_usecase_id') and link.source_usecase_id:
                redirect_uc_id = link.source_usecase_id

            session.delete(link)
            session.commit()
            flash("Use Case relevance link deleted successfully.", "success")
        else:
            flash("Use Case relevance link not found.", "warning")
    except Exception as e:
        session.rollback()
        flash(f"Error deleting use case relevance link: {e}", "danger")
        print(f"Error deleting usecase-usecase relevance {relevance_id}: {e}")
    finally:
        SessionLocal.remove()

    if redirect_uc_id:
        return redirect(url_for('usecases.view_usecase', usecase_id=redirect_uc_id))
    return redirect(url_for('index'))

@relevance_routes.route('/delete/step_to_step/<int:relevance_id>', methods=['POST'])
@login_required
def delete_step_to_step_relevance(relevance_id):
    source_process_step_id_form = request.form.get('source_process_step_id', type=int)
    session = SessionLocal()
    redirect_ps_id = source_process_step_id_form

    try:
        link = session.query(ProcessStepProcessStepRelevance).get(relevance_id)
        if link:
            if not redirect_ps_id and hasattr(link, 'source_process_step_id') and link.source_process_step_id:
                redirect_ps_id = link.source_process_step_id

            session.delete(link)
            session.commit()
            flash("Process Step relevance link deleted successfully.", "success")
        else:
            flash("Process Step relevance link not found.", "warning")
    except Exception as e:
        session.rollback()
        flash(f"Error deleting process step relevance link: {e}", "danger")
        print(f"Error deleting step-to-step relevance {relevance_id}: {e}")
    finally:
        SessionLocal.remove()

    if redirect_ps_id:
        return redirect(url_for('steps.view_step', step_id=redirect_ps_id))
    return redirect(url_for('index'))

# --- EDIT ROUTES ---

@relevance_routes.route('/edit/area/<int:relevance_id>', methods=['GET', 'POST'])
@login_required
def edit_area_relevance(relevance_id):
    session = SessionLocal()
    link = session.query(UsecaseAreaRelevance).options(
        joinedload(UsecaseAreaRelevance.source_usecase),
        joinedload(UsecaseAreaRelevance.target_area)
    ).get(relevance_id)

    if not link:
        flash("Area relevance link not found.", "danger")
        SessionLocal.remove()
        return redirect(url_for('index'))

    # Fetch all UCs and Areas for the dropdowns
    all_usecases = session.query(UseCase).order_by(UseCase.name).all()
    all_areas = session.query(Area).order_by(Area.name).all()

    if request.method == 'POST':
        new_source_usecase_id = request.form.get('source_id', type=int)
        new_target_area_id = request.form.get('target_id', type=int)
        score_str = request.form.get('relevance_score')
        content = request.form.get('relevance_content', '').strip()

        # Validate score
        try:
            score = int(score_str)
            if not (0 <= score <= 100):
                flash("Relevance score must be between 0 and 100.", "danger")
                SessionLocal.remove() # Close session before re-rendering template
                return render_template('edit_relevance.html', relevance_link=link, link_type='area', all_usecases=all_usecases, all_areas=all_areas)
        except (ValueError, TypeError):
            flash("Invalid score format. Relevance score must be a number.", "danger")
            SessionLocal.remove()
            return render_template('edit_relevance.html', relevance_link=link, link_type='area', all_usecases=all_usecases, all_areas=all_areas)

        # Check if source or target has actually changed
        if (link.source_usecase_id != new_source_usecase_id or
            link.target_area_id != new_target_area_id):

            # Check for duplicate link if source/target changed
            existing_duplicate_link = session.query(UsecaseAreaRelevance).filter(
                UsecaseAreaRelevance.source_usecase_id == new_source_usecase_id,
                UsecaseAreaRelevance.target_area_id == new_target_area_id,
                UsecaseAreaRelevance.id != relevance_id # Exclude current link being edited
            ).first()

            if existing_duplicate_link:
                flash("A relevance link between the selected Use Case and Area already exists.", "danger")
                SessionLocal.remove()
                return render_template('edit_relevance.html', relevance_link=link, link_type='area', all_usecases=all_usecases, all_areas=all_areas)
            
            # Update source and target IDs
            link.source_usecase_id = new_source_usecase_id
            link.target_area_id = new_target_area_id
            
            # Update the relationship objects if they were loaded to reflect the change for re-render
            # This is important if an error occurs and the template re-renders with the link object
            link.source_usecase = session.query(UseCase).get(new_source_usecase_id)
            link.target_area = session.query(Area).get(new_target_area_id)
            
        link.relevance_score = score
        link.relevance_content = content if content else None

        try:
            session.commit()
            flash("Area relevance link updated successfully!", "success")
        except IntegrityError as e: # Catch potential remaining integrity errors (e.g., if IDs somehow invalid)
            session.rollback()
            flash(f"Database error: Could not update link. Check IDs and try again. Error: {e}", "danger")
            print(f"IntegrityError updating area relevance {relevance_id}: {e}")
        except Exception as e:
            session.rollback()
            flash(f"An unexpected error occurred: {e}", "danger")
            print(f"Error updating area relevance {relevance_id}: {e}")
        finally:
            SessionLocal.remove()

        # Redirect back to the new source use case page
        return redirect(url_for('usecases.view_usecase', usecase_id=new_source_usecase_id))

    # GET request:
    SessionLocal.remove()
    return render_template('edit_relevance.html',
                           relevance_link=link,
                           link_type='area',
                           all_usecases=all_usecases,
                           all_areas=all_areas)


@relevance_routes.route('/edit/step/<int:relevance_id>', methods=['GET', 'POST'])
@login_required
def edit_step_relevance(relevance_id):
    session = SessionLocal()
    link = session.query(UsecaseStepRelevance).options(
        joinedload(UsecaseStepRelevance.source_usecase),
        joinedload(UsecaseStepRelevance.target_process_step)
    ).get(relevance_id)

    if not link:
        flash("Step relevance link not found.", "danger")
        SessionLocal.remove()
        return redirect(url_for('index'))

    # Fetch all UCs and Steps for the dropdowns
    all_usecases = session.query(UseCase).order_by(UseCase.name).all()
    all_steps = session.query(ProcessStep).order_by(ProcessStep.name).all()

    if request.method == 'POST':
        new_source_usecase_id = request.form.get('source_id', type=int)
        new_target_process_step_id = request.form.get('target_id', type=int)
        score_str = request.form.get('relevance_score')
        content = request.form.get('relevance_content', '').strip()

        try:
            score = int(score_str)
            if not (0 <= score <= 100):
                flash("Relevance score must be between 0 and 100.", "danger")
                SessionLocal.remove()
                return render_template('edit_relevance.html', relevance_link=link, link_type='step', all_usecases=all_usecases, all_steps=all_steps)
        except (ValueError, TypeError):
            flash("Invalid score format. Relevance score must be a number.", "danger")
            SessionLocal.remove()
            return render_template('edit_relevance.html', relevance_link=link, link_type='step', all_usecases=all_usecases, all_steps=all_steps)

        if (link.source_usecase_id != new_source_usecase_id or
            link.target_process_step_id != new_target_process_step_id):

            existing_duplicate_link = session.query(UsecaseStepRelevance).filter(
                UsecaseStepRelevance.source_usecase_id == new_source_usecase_id,
                UsecaseStepRelevance.target_process_step_id == new_target_process_step_id,
                UsecaseStepRelevance.id != relevance_id
            ).first()

            if existing_duplicate_link:
                flash("A relevance link between the selected Use Case and Process Step already exists.", "danger")
                SessionLocal.remove()
                return render_template('edit_relevance.html', relevance_link=link, link_type='step', all_usecases=all_usecases, all_steps=all_steps)
            
            link.source_usecase_id = new_source_usecase_id
            link.target_process_step_id = new_target_process_step_id

            link.source_usecase = session.query(UseCase).get(new_source_usecase_id)
            link.target_process_step = session.query(ProcessStep).get(new_target_process_step_id)

        link.relevance_score = score
        link.relevance_content = content if content else None
        try:
            session.commit()
            flash("Step relevance link updated successfully!", "success")
        except IntegrityError as e:
            session.rollback()
            flash(f"Database error: Could not update link. Check IDs and try again. Error: {e}", "danger")
            print(f"IntegrityError updating step relevance {relevance_id}: {e}")
        except Exception as e:
            session.rollback()
            flash(f"An unexpected error occurred: {e}", "danger")
            print(f"Error updating step relevance {relevance_id}: {e}")
        finally:
            SessionLocal.remove()

        return redirect(url_for('usecases.view_usecase', usecase_id=new_source_usecase_id))

    # GET request:
    SessionLocal.remove()
    return render_template('edit_relevance.html',
                           relevance_link=link,
                           link_type='step',
                           all_usecases=all_usecases,
                           all_steps=all_steps)


@relevance_routes.route('/edit/usecase/<int:relevance_id>', methods=['GET', 'POST'])
@login_required
def edit_usecase_relevance(relevance_id):
    session = SessionLocal()
    link = session.query(UsecaseUsecaseRelevance).options(
        joinedload(UsecaseUsecaseRelevance.source_usecase),
        joinedload(UsecaseUsecaseRelevance.target_usecase)
    ).get(relevance_id)

    if not link:
        flash("Use Case relevance link not found.", "danger")
        SessionLocal.remove()
        return redirect(url_for('index'))

    # Fetch all UCs for the dropdowns
    all_usecases = session.query(UseCase).order_by(UseCase.name).all()

    if request.method == 'POST':
        new_source_usecase_id = request.form.get('source_id', type=int)
        new_target_usecase_id = request.form.get('target_id', type=int)
        score_str = request.form.get('relevance_score')
        content = request.form.get('relevance_content', '').strip()

        if new_source_usecase_id == new_target_usecase_id:
            flash("Cannot link a Use Case to itself.", "warning")
            SessionLocal.remove()
            return render_template('edit_relevance.html', relevance_link=link, link_type='usecase', all_usecases=all_usecases)

        try:
            score = int(score_str)
            if not (0 <= score <= 100):
                flash("Relevance score must be between 0 and 100.", "danger")
                SessionLocal.remove()
                return render_template('edit_relevance.html', relevance_link=link, link_type='usecase', all_usecases=all_usecases)
        except (ValueError, TypeError):
            flash("Invalid score format. Relevance score must be a number.", "danger")
            SessionLocal.remove()
            return render_template('edit_relevance.html', relevance_link=link, link_type='usecase', all_usecases=all_usecases)

        if (link.source_usecase_id != new_source_usecase_id or
            link.target_usecase_id != new_target_usecase_id):

            existing_duplicate_link = session.query(UsecaseUsecaseRelevance).filter(
                UsecaseUsecaseRelevance.source_usecase_id == new_source_usecase_id,
                UsecaseUsecaseRelevance.target_usecase_id == new_target_usecase_id,
                UsecaseUsecaseRelevance.id != relevance_id
            ).first()

            if existing_duplicate_link:
                flash("A relevance link between the selected Use Cases already exists.", "danger")
                SessionLocal.remove()
                return render_template('edit_relevance.html', relevance_link=link, link_type='usecase', all_usecases=all_usecases)
            
            link.source_usecase_id = new_source_usecase_id
            link.target_usecase_id = new_target_usecase_id

            link.source_usecase = session.query(UseCase).get(new_source_usecase_id)
            link.target_usecase = session.query(UseCase).get(new_target_usecase_id)

        link.relevance_score = score
        link.relevance_content = content if content else None
        try:
            session.commit()
            flash("Use Case relevance link updated successfully!", "success")
        except IntegrityError as ie:
            session.rollback()
            if 'no_self_relevance' in str(ie).lower():
                flash("Database error: Cannot link a Use Case to itself.", "danger")
            else:
                flash("Database error: Could not update link. It might already exist or violate constraints.", "danger")
                print(f"IntegrityError updating usecase-usecase relevance {relevance_id}: {ie}")
        except Exception as e:
            session.rollback()
            flash(f"An unexpected error occurred: {e}", "danger")
            print(f"Error updating usecase-usecase relevance {relevance_id}: {e}")
        finally:
            SessionLocal.remove()

        return redirect(url_for('usecases.view_usecase', usecase_id=new_source_usecase_id))

    # GET request:
    SessionLocal.remove()
    return render_template('edit_relevance.html',
                           relevance_link=link,
                           link_type='usecase',
                           all_usecases=all_usecases)

@relevance_routes.route('/edit/step_to_step/<int:relevance_id>', methods=['GET', 'POST'])
@login_required
def edit_step_to_step_relevance(relevance_id):
    session = SessionLocal()
    link = session.query(ProcessStepProcessStepRelevance).options(
        joinedload(ProcessStepProcessStepRelevance.source_process_step),
        joinedload(ProcessStepProcessStepRelevance.target_process_step)
    ).get(relevance_id)

    if not link:
        flash("Process Step relevance link not found.", "danger")
        SessionLocal.remove()
        return redirect(url_for('index'))

    # Fetch all Steps for the dropdowns
    all_steps = session.query(ProcessStep).order_by(ProcessStep.name).all()

    if request.method == 'POST':
        new_source_process_step_id = request.form.get('source_id', type=int)
        new_target_process_step_id = request.form.get('target_id', type=int)
        score_str = request.form.get('relevance_score')
        content = request.form.get('relevance_content', '').strip()

        if new_source_process_step_id == new_target_process_step_id:
            flash("Cannot link a Process Step to itself.", "warning")
            SessionLocal.remove()
            return render_template('edit_relevance.html', relevance_link=link, link_type='step_to_step', all_steps=all_steps)

        try:
            score = int(score_str)
            if not (0 <= score <= 100):
                flash("Relevance score must be between 0 and 100.", "danger")
                SessionLocal.remove()
                return render_template('edit_relevance.html', relevance_link=link, link_type='step_to_step', all_steps=all_steps)
        except (ValueError, TypeError):
            flash("Invalid score format. Relevance score must be a number.", "danger")
            SessionLocal.remove()
            return render_template('edit_relevance.html', relevance_link=link, link_type='step_to_step', all_steps=all_steps)

        if (link.source_process_step_id != new_source_process_step_id or
            link.target_process_step_id != new_target_process_step_id):

            existing_duplicate_link = session.query(ProcessStepProcessStepRelevance).filter(
                ProcessStepProcessStepRelevance.source_process_step_id == new_source_process_step_id,
                ProcessStepProcessStepRelevance.target_process_step_id == new_target_process_step_id,
                ProcessStepProcessStepRelevance.id != relevance_id
            ).first()

            if existing_duplicate_link:
                flash("A relevance link between the selected Process Steps already exists.", "danger")
                SessionLocal.remove()
                return render_template('edit_relevance.html', relevance_link=link, link_type='step_to_step', all_steps=all_steps)
            
            link.source_process_step_id = new_source_process_step_id
            link.target_process_step_id = new_target_process_step_id

            link.source_process_step = session.query(ProcessStep).get(new_source_process_step_id)
            link.target_process_step = session.query(ProcessStep).get(new_target_process_step_id)
            
        link.relevance_score = score
        link.relevance_content = content if content else None
        try:
            session.commit()
            flash("Process Step relevance link updated successfully!", "success")
        except IntegrityError as ie:
            session.rollback()
            if 'no_self_step_relevance' in str(ie).lower():
                flash("Database error: Cannot link a Process Step to itself.", "danger")
            else:
                flash("Database error: Could not update link. It might already exist or violate constraints.", "danger")
                print(f"IntegrityError updating step-to-step relevance {relevance_id}: {ie}")
        except Exception as e:
            session.rollback()
            flash(f"An unexpected error occurred: {e}", "danger")
            print(f"Error updating step-to-step relevance {relevance_id}: {e}")
        finally:
            SessionLocal.remove()

        return redirect(url_for('steps.view_step', step_id=new_source_process_step_id))

    # GET request:
    SessionLocal.remove()
    return render_template('edit_relevance.html',
                           relevance_link=link,
                           link_type='step_to_step',
                           all_steps=all_steps)


@relevance_routes.route('/visualize')
@login_required
def visualize_relevance():
    session = SessionLocal()
    try:
        areas = session.query(Area).order_by(Area.name).all()
        steps = session.query(ProcessStep).options(
            joinedload(ProcessStep.area),
            joinedload(ProcessStep.use_cases)
        ).order_by(ProcessStep.area_id, ProcessStep.name).all()
        
        relevances = session.query(ProcessStepProcessStepRelevance).all()

        echarts_categories = []
        area_id_to_category_index = {}
        area_colors = [
            '#5D8C7B',
            '#4A7062',
            '#6c757d',
            '#78909C',
            '#A0A0A0',
            '#B5C4B1',
            '#8C9A8C',
            '#455A64',
            '#CFD8DC',
            '#FFB6C1',
            '#FFD700',
            '#FFA07A',
            '#87CEEB',
            '#DA70D6',
            '#CD5C5C',
            '#4682B4'
        ]

        for i, area in enumerate(areas):
            echarts_categories.append({
                'name': area.name,
                'itemStyle': {'color': area_colors[i % len(area_colors)]}
            })
            area_id_to_category_index[area.id] = i

        echarts_nodes = []
        for step in steps:
            category_index = area_id_to_category_index.get(step.area_id)
            if category_index is None:
                print(f"Warning: Process step {step.name} (ID: {step.id}) has no valid area or area not found. Skipping node.")
                continue

            num_use_cases = len(step.use_cases) if step.use_cases else 0
            symbol_size = 15 + (num_use_cases * 1.5) 

            node_display_name = step.name
            if len(node_display_name) > 25:
                node_display_name = node_display_name[:22] + '...'


            echarts_nodes.append({
                'id': str(step.id),
                'name': node_display_name,
                'value': num_use_cases,
                'category': category_index,
                'symbolSize': symbol_size,
                'tooltip': {
                    'formatter': (
                        f'<strong>{step.name}</strong><br>'
                        f'BI_ID: {step.bi_id}<br>'
                        f'Area: {step.area.name if step.area else "N/A"}<br>'
                        f'Use Cases: {num_use_cases}<br>'
                        f'<i>Click for details</i>'
                    )
                },
                'itemStyle': {
                    'color': echarts_categories[category_index]['itemStyle']['color']
                }
            })

        echarts_links = []
        for rel in relevances:
            source_node = next((node for node in echarts_nodes if node['id'] == str(rel.source_process_step_id)), None)
            target_node = next((node for node in echarts_nodes if node['id'] == str(rel.target_process_step_id)), None)

            if source_node and target_node:
                link_width = max(0.5, rel.relevance_score / 25) 
                echarts_links.append({
                    'source': str(rel.source_process_step_id),
                    'target': str(rel.target_process_step_id),
                    'value': rel.relevance_score,
                    'label': {
                        'show': True,
                        'formatter': '{c}',
                        'fontSize': 10,
                        'color': '#333',
                        'backgroundColor': 'rgba(255, 255, 255, 0.7)',
                        'padding': [2, 4],
                        'borderRadius': 2
                    },
                    'lineStyle': {
                        'width': link_width,
                        'opacity': 0.8,
                        'curveness': 0.3
                    },
                    'tooltip': {
                        'formatter': (
                            f'Relevance: <strong>{rel.relevance_score}/100</strong><br>'
                            f'Content: {rel.relevance_content or "N/A"}'
                        )
                    }
                })

        return render_template(
            'relevance_visualize.html',
            title='Process Relevance Map',
            echarts_data={
                'nodes': echarts_nodes,
                'links': echarts_links,
                'categories': echarts_categories
            }
        )

    except Exception as e:
        print(f"Error fetching data for ECharts visualization: {e}")
        flash("An error occurred while preparing data for the relevance map.", "danger")
        return render_template(
            'relevance_visualize.html',
            title='Process Relevance Map',
            echarts_data={'nodes': [], 'links': [], 'categories': []}
        )
    finally:
        SessionLocal.remove()