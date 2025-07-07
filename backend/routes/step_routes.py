# backend/routes/step_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, g
from flask_login import login_required
from sqlalchemy.exc import IntegrityError

from ..models import ProcessStep, UseCase, Area
from ..utils import serialize_for_js
from ..services import step_service  # <-- Use the new service

step_routes = Blueprint('steps', __name__,
                        template_folder='../templates',
                        url_prefix='/steps')

@step_routes.route('/api/all', methods=['GET'])
@login_required
def api_get_all_steps():
    try:
        steps_data = step_service.get_all_steps_for_api(g.db_session)
        return jsonify(steps_data)
    except Exception as e:
        return jsonify(error=str(e)), 500

@step_routes.route('/')
@login_required
def list_steps():
    # This route is now only for potential future use or API calls.
    # The main Process Steps overview is at main.index ('/').
    return redirect(url_for('main.index'))

@step_routes.route('/<int:step_id>', methods=['GET', 'POST'])
@login_required
def view_step(step_id):
    step = step_service.get_step_by_id(g.db_session, step_id)
    if not step:
        flash(f"Process Step with ID {step_id} not found.", "warning")
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        try:
            success, message = step_service.update_step_from_form(g.db_session, step, request.form)
            flash(message, "success" if success else "danger")
            # Redirect to the same page to show updated data and avoid form resubmission
            return redirect(url_for('steps.view_step', step_id=step.id))
        except Exception as e:
            g.db_session.rollback()
            flash(f"An unexpected error occurred: {e}", "danger")
    
    # Data needed for the template
    other_steps = step_service.get_all_other_steps(g.db_session, step_id)
    all_areas = g.db_session.query(Area).order_by(Area.name).all()

    return render_template(
        'step_detail.html',
        title=f"Process Step: {step.name}",
        step=step,
        other_steps=other_steps,
        all_areas=all_areas,
        current_step=step,
        current_area=step.area,
        current_item=step,
    )

@step_routes.route('/<int:step_id>/delete', methods=['POST'])
@login_required
def delete_step(step_id):
    redirect_url = url_for('main.index')
    try:
        step_name, area_id, message = step_service.delete_step_by_id(g.db_session, step_id)
        if step_name:
            flash(message, "success")
            if area_id:
                # After deleting a step, go back to the area it belonged to
                redirect_url = url_for('main.index', filter_area_id=area_id)
        else:
            flash(message, "warning")
    except Exception as e:
        flash(f"Error deleting process step: {e}", "danger")
    return redirect(redirect_url)

@step_routes.route('/api/steps/<int:step_id>/inline-update', methods=['PUT'])
@login_required
def inline_update_step(step_id):
    try:
        step_to_update = g.db_session.query(ProcessStep).get(step_id)
        if not step_to_update:
            return jsonify(success=False, message="Process Step not found"), 404

        data = request.json
        if not data or len(data) != 1: return jsonify(success=False, message="Invalid update data."), 400
        field, value = list(data.items())[0]
        
        updated_step, message = step_service.inline_update_step_field(g.db_session, step_to_update, field, value)
        if updated_step:
            updated_data = {'id': updated_step.id, 'name': updated_step.name, 'bi_id': updated_step.bi_id, 'area_id': updated_step.area_id, 'area_name': updated_step.area.name if updated_step.area else 'N/A', 'step_description': updated_step.step_description}
            return jsonify(success=True, message=message, step=updated_data)
        else:
            return jsonify(success=False, message=message), 400
    except Exception as e:
        g.db_session.rollback()
        return jsonify(success=False, message=f"An unexpected error occurred: {str(e)}"), 500