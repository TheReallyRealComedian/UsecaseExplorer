# backend/routes/relevance_routes.py
from flask import Blueprint, request, flash, redirect, url_for, render_template, g
from flask_login import login_required
from ..services import relevance_service
from ..utils import serialize_for_js
from ..models import Area, ProcessStep, UseCase


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
        else url_for('main.index')
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

    try:
        new_link, message = relevance_service.add_relevance_link(
            g.db_session,
            source_id=source_usecase_id,
            target_id=target_area_id,
            score=score,
            content=content,
            link_type='area'
        )
        flash(message, 'success' if new_link else 'danger')
        if new_link:
            g.db_session.commit()
    except Exception as e:
        g.db_session.rollback()
        flash(f"An unexpected error occurred: {e}", "danger")

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
        else url_for('main.index')
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

    try:
        new_link, message = relevance_service.add_relevance_link(
            g.db_session,
            source_id=source_usecase_id,
            target_id=target_process_step_id,
            score=score,
            content=content,
            link_type='step'
        )
        flash(message, 'success' if new_link else 'danger')
        if new_link:
            g.db_session.commit()
    except Exception as e:
        g.db_session.rollback()
        flash(f"An unexpected error occurred: {e}", "danger")

    return redirect(redirect_url)


@relevance_routes.route('/add/usecase', methods=['POST'])
@login_required
def add_usecase_relevance():
    """Handles the form submission for adding UseCase-UseCase relevance."""
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    target_usecase_id = request.form.get('target_usecase_id', type=int)
    score_str = request.form.get('relevance_score')
    content = request.form.get('relevance_content', '').strip()

    redirect_url = (
        url_for('usecases.view_usecase', usecase_id=source_usecase_id)
        if source_usecase_id
        else url_for('main.index')
    )

    if not all([source_usecase_id, target_usecase_id, score_str is not None]):
        flash("Missing required fields (Source UC ID, Target UC ID, Score).", "danger")
        return redirect(request.referrer or redirect_url)

    if source_usecase_id == target_usecase_id:
        flash("Cannot link a Use Case to itself.", "warning")
        return redirect(redirect_url)

    try:
        score = int(score_str)
        if not (0 <= score <= 100):
            flash("Score must be between 0 and 100.", "danger")
            return redirect(redirect_url)
    except ValueError:
        flash("Invalid score format. Score must be a number.", "danger")
        return redirect(redirect_url)

    try:
        new_link, message = relevance_service.add_relevance_link(
            g.db_session,
            source_id=source_usecase_id,
            target_id=target_usecase_id,
            score=score,
            content=content,
            link_type='usecase'
        )
        flash(message, 'success' if new_link else 'danger')
        if new_link:
            g.db_session.commit()
    except Exception as e:
        g.db_session.rollback()
        flash(f"An unexpected error occurred: {e}", "danger")

    return redirect(redirect_url)


@relevance_routes.route('/add/step_to_step', methods=['POST'])
@login_required
def add_step_to_step_relevance():
    """Handles the form submission for adding ProcessStep-ProcessStep relevance."""
    source_process_step_id = request.form.get('source_process_step_id', type=int)
    target_process_step_id = request.form.get('target_process_step_id', type=int)
    score_str = request.form.get('relevance_score')
    content = request.form.get('relevance_content', '').strip()

    redirect_url = (
        url_for('steps.view_step', step_id=source_process_step_id)
        if source_process_step_id
        else url_for('main.index')
    )

    if not all([source_process_step_id, target_process_step_id, score_str is not None]):
        flash("Missing required fields (Source Step ID, Target Step ID, Score).", "danger")
        return redirect(request.referrer or redirect_url)

    if source_process_step_id == target_process_step_id:
        flash("Cannot link a Process Step to itself.", "warning")
        return redirect(redirect_url)

    try:
        score = int(score_str)
        if not (0 <= score <= 100):
            flash("Score must be between 0 and 100.", "danger")
            return redirect(redirect_url)
    except ValueError:
        flash("Invalid score format. Score must be a number.", "danger")
        return redirect(redirect_url)

    try:
        new_link, message = relevance_service.add_relevance_link(
            g.db_session,
            source_id=source_process_step_id,
            target_id=target_process_step_id,
            score=score,
            content=content,
            link_type='step_to_step'
        )
        flash(message, 'success' if new_link else 'danger')
        if new_link:
            g.db_session.commit()
    except Exception as e:
        g.db_session.rollback()
        flash(f"An unexpected error occurred: {e}", "danger")

    return redirect(redirect_url)


# --- DELETE ROUTES ---

@relevance_routes.route('/delete/area/<int:relevance_id>', methods=['POST'])
@login_required
def delete_area_relevance(relevance_id):
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    redirect_id = source_usecase_id
    try:
        success, message, redirect_id_from_service = relevance_service.delete_relevance_link(
            g.db_session, relevance_id, 'area', source_usecase_id
        )
        flash(message, 'success' if success else 'danger')
        if success:
            g.db_session.commit()
            if redirect_id_from_service:
                redirect_id = redirect_id_from_service
    except Exception as e:
        g.db_session.rollback()
        flash(f"Error deleting area relevance link: {e}", "danger")

    return redirect(url_for('usecases.view_usecase', usecase_id=redirect_id) if redirect_id else url_for('main.index'))


@relevance_routes.route('/delete/step/<int:relevance_id>', methods=['POST'])
@login_required
def delete_step_relevance(relevance_id):
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    referrer_step_id = request.form.get('referrer_step_id', type=int)
    try:
        success, message, redirect_ids = relevance_service.delete_relevance_link(
            g.db_session, relevance_id, 'step', {'uc_id': source_usecase_id, 'step_id': referrer_step_id}
        )
        flash(message, 'success' if success else 'danger')
        if success:
            g.db_session.commit()
            source_usecase_id = redirect_ids.get('uc_id', source_usecase_id)
            referrer_step_id = redirect_ids.get('step_id', referrer_step_id)
    except Exception as e:
        g.db_session.rollback()
        flash(f"Error deleting step relevance link: {e}", "danger")

    if referrer_step_id:
        return redirect(url_for('steps.view_step', step_id=referrer_step_id))
    if source_usecase_id:
        return redirect(url_for('usecases.view_usecase', usecase_id=source_usecase_id))
    return redirect(url_for('main.index'))


@relevance_routes.route('/delete/usecase/<int:relevance_id>', methods=['POST'])
@login_required
def delete_usecase_relevance(relevance_id):
    source_usecase_id = request.form.get('source_usecase_id', type=int)
    redirect_id = source_usecase_id
    try:
        success, message, redirect_id_from_service = relevance_service.delete_relevance_link(
            g.db_session, relevance_id, 'usecase', source_usecase_id
        )
        flash(message, 'success' if success else 'danger')
        if success:
            g.db_session.commit()
            if redirect_id_from_service:
                redirect_id = redirect_id_from_service
    except Exception as e:
        g.db_session.rollback()
        flash(f"Error deleting use case relevance link: {e}", "danger")

    return redirect(url_for('usecases.view_usecase', usecase_id=redirect_id) if redirect_id else url_for('main.index'))


@relevance_routes.route('/delete/step_to_step/<int:relevance_id>', methods=['POST'])
@login_required
def delete_step_to_step_relevance(relevance_id):
    source_step_id = request.form.get('source_process_step_id', type=int)
    redirect_id = source_step_id
    try:
        success, message, redirect_id_from_service = relevance_service.delete_relevance_link(
            g.db_session, relevance_id, 'step_to_step', source_step_id
        )
        flash(message, 'success' if success else 'danger')
        if success:
            g.db_session.commit()
            if redirect_id_from_service:
                redirect_id = redirect_id_from_service
    except Exception as e:
        g.db_session.rollback()
        flash(f"Error deleting process step relevance link: {e}", "danger")

    return redirect(url_for('steps.view_step', step_id=redirect_id) if redirect_id else url_for('main.index'))


# --- EDIT ROUTES ---

def _get_breadcrumb_data():
    return {
        'all_areas_flat': serialize_for_js(g.db_session.query(Area).order_by(Area.name).all(), 'area'),
        'all_steps_flat': serialize_for_js(g.db_session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step'),
        'all_usecases_flat': serialize_for_js(g.db_session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
    }

def handle_edit_relevance(relevance_id, link_type, view_name_for_redirect, id_name_for_redirect):
    try:
        page_data = relevance_service.get_data_for_edit_page(g.db_session, relevance_id, link_type)
        if not page_data.get('relevance_link'):
            flash(f"{link_type.replace('_', ' ').capitalize()} relevance link not found.", "danger")
            return redirect(url_for('main.index'))

        page_data.update(_get_breadcrumb_data())

        if request.method == 'POST':
            form_data = {
                'source_id': request.form.get('source_id', type=int),
                'target_id': request.form.get('target_id', type=int),
                'score': request.form.get('relevance_score'),
                'content': request.form.get('relevance_content', '').strip()
            }

            try:
                score = int(form_data['score'])
                if not (0 <= score <= 100):
                    flash("Relevance score must be between 0 and 100.", "danger")
                    return render_template('edit_relevance.html', **page_data)
                form_data['score'] = score
            except (ValueError, TypeError):
                flash("Invalid score format. Score must be a number.", "danger")
                return render_template('edit_relevance.html', **page_data)

            if form_data['source_id'] == form_data['target_id'] and link_type in ['usecase', 'step_to_step']:
                flash("Cannot link an item to itself.", "warning")
                return render_template('edit_relevance.html', **page_data)

            success, message, redirect_id = relevance_service.update_relevance_link(
                g.db_session, relevance_id, link_type, form_data
            )

            if success:
                g.db_session.commit()
                flash(message, 'success')
                return redirect(url_for(view_name_for_redirect, **{id_name_for_redirect: redirect_id}))
            else:
                g.db_session.rollback()
                flash(message, 'danger')
                # Re-fetch data to reflect potential changes before the failed update attempt
                updated_page_data = relevance_service.get_data_for_edit_page(g.db_session, relevance_id, link_type)
                updated_page_data.update(_get_breadcrumb_data())
                return render_template('edit_relevance.html', **updated_page_data)

        return render_template('edit_relevance.html', **page_data)
    except Exception as e:
        g.db_session.rollback()
        flash(f"An unexpected error occurred: {e}", "danger")
        return redirect(url_for('main.index'))


@relevance_routes.route('/edit/area/<int:relevance_id>', methods=['GET', 'POST'])
@login_required
def edit_area_relevance(relevance_id):
    return handle_edit_relevance(relevance_id, 'area', 'usecases.view_usecase', 'usecase_id')


@relevance_routes.route('/edit/step/<int:relevance_id>', methods=['GET', 'POST'])
@login_required
def edit_step_relevance(relevance_id):
    return handle_edit_relevance(relevance_id, 'step', 'usecases.view_usecase', 'usecase_id')


@relevance_routes.route('/edit/usecase/<int:relevance_id>', methods=['GET', 'POST'])
@login_required
def edit_usecase_relevance(relevance_id):
    return handle_edit_relevance(relevance_id, 'usecase', 'usecases.view_usecase', 'usecase_id')


@relevance_routes.route('/edit/step_to_step/<int:relevance_id>', methods=['GET', 'POST'])
@login_required
def edit_step_to_step_relevance(relevance_id):
    return handle_edit_relevance(relevance_id, 'step_to_step', 'steps.view_step', 'step_id')


@relevance_routes.route('/visualize')
@login_required
def visualize_relevance():
    try:
        echarts_data = relevance_service.get_relevance_graph_data(g.db_session)
        breadcrumb_data = _get_breadcrumb_data()

        return render_template(
            'relevance_visualize.html',
            title='Process Relevance Map',
            echarts_data=echarts_data,
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            **breadcrumb_data
        )
    except Exception as e:
        print(f"Error fetching data for ECharts visualization: {e}")
        flash("An error occurred while preparing data for the relevance map.", "danger")
        return render_template(
            'relevance_visualize.html',
            title='Process Relevance Map',
            echarts_data={'nodes': [], 'links': [], 'categories': []},
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            all_areas_flat=[],
            all_steps_flat=[],
            all_usecases_flat=[]
        )