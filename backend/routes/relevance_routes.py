# backend/routes/relevance_routes.py
from flask import Blueprint, request, flash, redirect, url_for, abort, render_template
from flask_login import login_required
from sqlalchemy.orm import joinedload
from ..db import SessionLocal # CHANGED
from ..models import UsecaseAreaRelevance, UsecaseStepRelevance, UsecaseUsecaseRelevance, UseCase
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

# --- DELETE ROUTES ---

@relevance_routes.route('/delete/area/<int:relevance_id>', methods=['POST'])
@login_required
def delete_area_relevance(relevance_id):
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    session = SessionLocal()
    try:
        link = session.query(UsecaseAreaRelevance).get(relevance_id)
        if link:
            if not source_usecase_id and hasattr(link, 'source_usecase_id') and link.source_usecase_id:
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
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    session = SessionLocal()
    try:
        link = session.query(UsecaseStepRelevance).get(relevance_id)
        if link:
            if not source_usecase_id and hasattr(link, 'source_usecase_id') and link.source_usecase_id:
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

    if source_usecase_id:
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

    if request.method == 'POST':
        score_str = request.form.get('relevance_score')
        content = request.form.get('relevance_content', '').strip()
        source_usecase_id_form = request.form.get('source_usecase_id', type=int)

        try:
            score = int(score_str)
            if not (0 <= score <= 100):
                flash("Score must be between 0 and 100.", "danger")
                return render_template('edit_relevance.html',
                                       relevance_link=link,
                                       link_type='area')
        except (ValueError, TypeError):
            flash("Invalid score format. Score must be a number.", "danger")
            return render_template('edit_relevance.html',
                                   relevance_link=link,
                                   link_type='area')

        link.relevance_score = score
        link.relevance_content = content if content else None
        try:
            session.commit()
            flash("Area relevance link updated successfully!", "success")
        except Exception as e:
            session.rollback()
            flash(f"Error updating link: {e}", "danger")
            print(f"Error updating area relevance {relevance_id}: {e}")
        finally:
            SessionLocal.remove()

        redirect_id = source_usecase_id_form or link.source_usecase_id
        return redirect(url_for('usecases.view_usecase', usecase_id=redirect_id))

    # GET request:
    SessionLocal.remove() # remove session explicitly for GET if not using teardown_request strictly
    return render_template('edit_relevance.html',
                           relevance_link=link,
                           link_type='area')


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

    if request.method == 'POST':
        score_str = request.form.get('relevance_score')
        content = request.form.get('relevance_content', '').strip()
        source_usecase_id_form = request.form.get('source_usecase_id', type=int)

        try:
            score = int(score_str)
            if not (0 <= score <= 100):
                flash("Score must be between 0 and 100.", "danger")
                return render_template('edit_relevance.html',
                                       relevance_link=link,
                                       link_type='step')
        except (ValueError, TypeError):
            flash("Invalid score format. Score must be a number.", "danger")
            return render_template('edit_relevance.html',
                                   relevance_link=link,
                                   link_type='step')

        link.relevance_score = score
        link.relevance_content = content if content else None
        try:
            session.commit()
            flash("Step relevance link updated successfully!", "success")
        except Exception as e:
            session.rollback()
            flash(f"Error updating link: {e}", "danger")
            print(f"Error updating step relevance {relevance_id}: {e}")
        finally:
            SessionLocal.remove()

        redirect_id = source_usecase_id_form or link.source_usecase_id
        return redirect(url_for('usecases.view_usecase', usecase_id=redirect_id))

    # GET request:
    SessionLocal.remove() # remove session explicitly for GET
    return render_template('edit_relevance.html',
                           relevance_link=link,
                           link_type='step')


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

    if request.method == 'POST':
        score_str = request.form.get('relevance_score')
        content = request.form.get('relevance_content', '').strip()
        source_usecase_id_form = request.form.get('source_usecase_id', type=int)

        try:
            score = int(score_str)
            if not (0 <= score <= 100):
                flash("Score must be between 0 and 100.", "danger")
                return render_template('edit_relevance.html',
                                       relevance_link=link,
                                       link_type='usecase')
        except (ValueError, TypeError):
            flash("Invalid score format. Score must be a number.", "danger")
            return render_template('edit_relevance.html',
                                   relevance_link=link,
                                   link_type='usecase')

        link.relevance_score = score
        link.relevance_content = content if content else None
        try:
            session.commit()
            flash("Use Case relevance link updated successfully!", "success")
        except Exception as e:
            session.rollback()
            flash(f"Error updating link: {e}", "danger")
            print(f"Error updating usecase-usecase relevance {relevance_id}: {e}")
        finally:
            SessionLocal.remove()

        redirect_id = source_usecase_id_form or link.source_usecase_id
        return redirect(url_for('usecases.view_usecase', usecase_id=redirect_id))

    # GET request:
    SessionLocal.remove() # remove session explicitly for GET
    return render_template('edit_relevance.html',
                           relevance_link=link,
                           link_type='usecase')