# backend/routes/step_routes.py
from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify # Added jsonify
from flask_login import login_required
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy.exc import IntegrityError

from ..db import SessionLocal
from ..models import ProcessStep, UseCase, Area, UsecaseStepRelevance, ProcessStepProcessStepRelevance
from ..utils import serialize_for_js

step_routes = Blueprint('steps', __name__,
                        template_folder='../templates',
                        url_prefix='/steps')

# NEW API Endpoint to get all steps as JSON
@step_routes.route('/api/all', methods=['GET']) # Changed route to /api/all to avoid conflict and be more specific
@login_required
def api_get_all_steps():
    session = SessionLocal()
    try:
        steps = session.query(ProcessStep).options(
            joinedload(ProcessStep.area) # Eager load area for area_name
        ).order_by(ProcessStep.name).all()
        
        steps_data = []
        for step in steps:
            steps_data.append({
                "id": step.id,
                "name": step.name,
                "bi_id": step.bi_id,
                "area_id": step.area_id,
                "area_name": step.area.name if step.area else "N/A"
                # Add other fields if needed by the modal's select dropdown rendering
            })
        return jsonify(steps_data)
    except Exception as e:
        print(f"Error fetching all steps for API: {e}")
        return jsonify(error=str(e)), 500
    finally:
        session.close()


@step_routes.route('/')
@login_required
def list_steps():
    session = SessionLocal()
    # Removed redundant initialization of steps, all_areas_flat etc.
    try:
        steps = session.query(ProcessStep).options(
            joinedload(ProcessStep.area),
            joinedload(ProcessStep.use_cases)
        ).order_by(ProcessStep.name).all()

        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(steps, 'step') # Pass the already queried steps
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')

        return render_template(
            'step_overview.html', 
            title="All Process Steps",
            steps=steps,
            current_item=None, 
            current_area=None, 
            current_step=None, 
            current_usecase=None, 
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
        )
    except Exception as e:
        print(f"Error fetching all steps for overview: {e}")
        flash("An error occurred while fetching process step overview.", "danger")
        return redirect(url_for('index'))
    finally:
        # SessionLocal.remove() is handled by app.teardown_request
        pass


@step_routes.route('/<int:step_id>')
@login_required
def view_step(step_id):
    session = SessionLocal()
    # Removed redundant initialization of all_areas_flat etc.
    try:
        step = session.query(ProcessStep).options(
            joinedload(ProcessStep.area),
            selectinload(ProcessStep.use_cases),
            selectinload(ProcessStep.usecase_relevance)
                .joinedload(UsecaseStepRelevance.source_usecase),
            selectinload(ProcessStep.relevant_to_steps_as_source)
                .joinedload(ProcessStepProcessStepRelevance.target_process_step),
            selectinload(ProcessStep.relevant_to_steps_as_target)
                .joinedload(ProcessStepProcessStepRelevance.source_process_step)
        ).get(step_id)

        if step is None:
            flash(f"Process Step with ID {step_id} not found.", "warning")
            return redirect(url_for('index'))

        other_steps_query = session.query(ProcessStep)\
            .filter(ProcessStep.id != step_id)\
            .order_by(ProcessStep.name)
        
        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        # Pass the already queried other_steps to serialize_for_js if appropriate, or query all again for consistency
        all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step') 
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')

        return render_template(
            'step_detail.html',
            title=f"Process Step: {step.name}",
            step=step,
            other_steps=other_steps_query.all(), 
            current_step=step, 
            current_area=step.area, 
            current_usecase=None, 
            current_item=step, 
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
        )
    except Exception as e:
        print(f"Error fetching step {step_id}: {e}")
        flash("An error occurred while fetching step details. Please check server logs.", "danger")
        return redirect(url_for('index'))
    finally:
        # SessionLocal.remove() is handled by app.teardown_request
        pass


@step_routes.route('/<int:step_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_step(step_id):
    session = SessionLocal()
    step = session.query(ProcessStep).options(joinedload(ProcessStep.area)).get(step_id)
    
    # Fetch all_areas once for the select dropdown
    all_areas_for_select = session.query(Area).order_by(Area.name).all()

    # Prepare breadcrumb data
    all_areas_flat_js = serialize_for_js(all_areas_for_select, 'area') # Use already queried data
    all_steps_flat_js = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
    all_usecases_flat_js = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')

    if step is None:
        flash(f"Process Step with ID {step_id} not found.", "warning")
        # SessionLocal.remove() # Let teardown_request handle session removal
        return redirect(url_for('index'))

    # Store original step name for title in case of validation errors before commit
    # If step.name is changed by form, this preserves the original for the title if re-rendering
    original_step_name_for_title = step.name 

    if request.method == 'POST':
        original_bi_id = step.bi_id # Store original BI_ID for comparison
        
        # Update step attributes from form
        step.name = request.form.get('name', '').strip()
        step.bi_id = request.form.get('bi_id', '').strip()
        step.area_id = request.form.get('area_id', type=int)
        step.step_description = request.form.get('step_description', '').strip() or None
        step.raw_content = request.form.get('raw_content', '').strip() or None
        step.summary = request.form.get('summary', '').strip() or None
        step.vision_statement = request.form.get('vision_statement', '').strip() or None
        step.in_scope = request.form.get('in_scope', '').strip() or None
        step.out_of_scope = request.form.get('out_of_scope', '').strip() or None
        step.interfaces_text = request.form.get('interfaces_text', '').strip() or None
        step.what_is_actually_done = request.form.get('what_is_actually_done', '').strip() or None
        step.pain_points = request.form.get('pain_points', '').strip() or None
        step.targets_text = request.form.get('targets_text', '').strip() or None

        if not step.name or not step.bi_id or not step.area_id:
            flash("Step Name, BI_ID, and Area are required.", "danger")
        else:
            # Check for BI_ID uniqueness only if it has changed
            if step.bi_id != original_bi_id:
                existing_step = session.query(ProcessStep).filter(
                    ProcessStep.bi_id == step.bi_id, 
                    ProcessStep.id != step_id  # Exclude the current step itself
                ).first()
                if existing_step:
                    flash(f"Another process step with BI_ID '{step.bi_id}' already exists.", "danger")
                    # Do not remove session here, re-render template with current (unsaved) step data
                    return render_template(
                        'edit_step.html',
                        title=f"Edit Step: {original_step_name_for_title}", # Use original name for title
                        step=step, # Pass the modified step object back to the form
                        all_areas=all_areas_for_select, 
                        current_step=step, 
                        current_area=step.area, # This will be reloaded if needed, or use the new one
                        current_usecase=None, 
                        current_item=step, 
                        all_areas_flat=all_areas_flat_js,
                        all_steps_flat=all_steps_flat_js,
                        all_usecases_flat=all_usecases_flat_js
                    )
            
            # If all checks pass, attempt to commit
            try:
                session.commit()
                flash("Process Step updated successfully!", "success")
                # SessionLocal.remove() # Let teardown_request handle session removal
                return redirect(url_for('steps.view_step', step_id=step.id))
            except IntegrityError: # Catches DB-level uniqueness violations if any slip through
                session.rollback()
                flash("Database error: Could not update step. BI_ID might already exist or area is invalid.", "danger")
            except Exception as e:
                session.rollback()
                flash(f"An unexpected error occurred: {e}", "danger")
                print(f"Error updating step {step_id}: {e}")
        
        # If any validation failed or commit error occurred, re-render the form
        # The session is still active here.
        return render_template(
            'edit_step.html',
            title=f"Edit Step: {original_step_name_for_title}", # Use original name for title
            step=step, 
            all_areas=all_areas_for_select, 
            current_step=step, 
            current_area=step.area, # Use current step's area
            current_usecase=None, 
            current_item=step, 
            all_areas_flat=all_areas_flat_js,
            all_steps_flat=all_steps_flat_js,
            all_usecases_flat=all_usecases_flat_js
        )
    
    # For GET requests
    # SessionLocal.remove() # Let teardown_request handle session removal
    return render_template(
        'edit_step.html',
        title=f"Edit Step: {step.name}", # Use current step name for title
        step=step, 
        all_areas=all_areas_for_select, 
        current_step=step, 
        current_area=step.area, 
        current_usecase=None, 
        current_item=step, 
        all_areas_flat=all_areas_flat_js,
        all_steps_flat=all_steps_flat_js,
        all_usecases_flat=all_usecases_flat_js
    )


@step_routes.route('/<int:step_id>/delete', methods=['POST'])
@login_required
def delete_step(step_id):
    session = SessionLocal()
    step = session.query(ProcessStep).options(joinedload(ProcessStep.area)).get(step_id)
    redirect_url = url_for('index') # Default redirect

    if step is None:
        flash(f"Process Step with ID {step_id} not found.", "warning")
    else:
        area_id_for_redirect = step.area_id # Store before potential deletion
        step_name = step.name
        try:
            session.delete(step)
            session.commit()
            flash(f"Process Step '{step_name}' and its use cases deleted successfully.", "success")
            if area_id_for_redirect:
                 redirect_url = url_for('areas.view_area', area_id=area_id_for_redirect)
        except Exception as e:
            session.rollback()
            flash(f"Error deleting process step: {e}", "danger")
            print(f"Error deleting step {step_id}: {e}")
            # If step still exists (e.g., rollback occurred), redirect to its area
            if step and step.area_id: 
                 redirect_url = url_for('areas.view_area', area_id=step.area_id)
    # SessionLocal.remove() will be handled by teardown_request
    return redirect(redirect_url)