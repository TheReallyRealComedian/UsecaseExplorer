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

    if request.method == 'POST':
        score_str = request.form.get('relevance_score')
        content = request.form.get('relevance_content', '').strip()
        source_process_step_id_form = request.form.get('source_process_step_id', type=int)

        try:
            score = int(score_str)
            if not (0 <= score <= 100):
                flash("Score must be between 0 and 100.", "danger")
                return render_template('edit_relevance.html',
                                       relevance_link=link,
                                       link_type='step_to_step') # Indicate link type
        except (ValueError, TypeError):
            flash("Invalid score format. Score must be a number.", "danger")
            return render_template('edit_relevance.html',
                                   relevance_link=link,
                                   link_type='step_to_step') # Indicate link type

        link.relevance_score = score
        link.relevance_content = content if content else None
        try:
            session.commit()
            flash("Process Step relevance link updated successfully!", "success")
        except Exception as e:
            session.rollback()
            flash(f"Error updating link: {e}", "danger")
            print(f"Error updating step-to-step relevance {relevance_id}: {e}")
        finally:
            SessionLocal.remove()

        redirect_id = source_process_step_id_form or link.source_process_step_id
        return redirect(url_for('steps.view_step', step_id=redirect_id))

    # GET request:
    SessionLocal.remove()
    return render_template('edit_relevance.html',
                           relevance_link=link,
                           link_type='step_to_step') # Indicate link type


@relevance_routes.route('/visualize')
@login_required
def visualize_relevance():
    session = SessionLocal()
    try:
        areas = session.query(Area).order_by(Area.name).all()
        # Fetch steps and eager load their associated area and use cases.
        # Order by area_id and then step name to group steps from the same area together.
        steps = session.query(ProcessStep).options(
            joinedload(ProcessStep.area),
            joinedload(ProcessStep.use_cases) # Load use cases to count them for node size
        ).order_by(ProcessStep.area_id, ProcessStep.name).all()
        
        relevances = session.query(ProcessStepProcessStepRelevance).all()

        echarts_categories = []
        area_id_to_category_index = {}
        # Define a consistent set of colors for areas.
        # These colors are chosen to complement your existing style.css and provide
        # enough distinct values for a reasonable number of areas.
        area_colors = [
            '#5D8C7B',  # Primary Green
            '#4A7062',  # Dark Green
            '#6c757d',  # Medium Grey (breadcrumb default)
            '#78909C',  # Blue-grey
            '#A0A0A0',  # Another grey tone
            '#B5C4B1',  # Light green-grey
            '#8C9A8C',  # Darker green-grey
            '#455A64',  # Dark blue-grey
            '#CFD8DC',  # Very light grey
            '#FFB6C1',  # Pink
            '#FFD700',  # Gold
            '#FFA07A',  # Light Salmon
            '#87CEEB',  # Sky Blue
            '#DA70D6',  # Orchid
            '#CD5C5C',  # Indian Red
            '#4682B4'   # Steel Blue
        ]

        # 1. Prepare Categories (Areas) for ECharts legend and node coloring
        for i, area in enumerate(areas):
            echarts_categories.append({
                'name': area.name,
                'itemStyle': {'color': area_colors[i % len(area_colors)]} # Cycle through defined colors
            })
            area_id_to_category_index[area.id] = i

        echarts_nodes = []
        # 2. Prepare Nodes (Process Steps)
        for step in steps:
            # Ensure the area exists and has a mapped category index
            category_index = area_id_to_category_index.get(step.area_id)
            if category_index is None:
                # Handle steps without a valid area gracefully, or skip them
                print(f"Warning: Process step {step.name} (ID: {step.id}) has no valid area or area not found. Skipping node.")
                continue

            # Calculate symbol size based on number of associated use cases
            # Base size of 15, plus 1.5px per use case. Adjust as needed.
            num_use_cases = len(step.use_cases) if step.use_cases else 0
            symbol_size = 15 + (num_use_cases * 1.5) 

            # For the node label, use only the step name to keep it concise.
            # The full name and BI_ID are moved to the tooltip for detailed info on hover.
            node_display_name = step.name
            # Optional: Truncate very long names for display on the node label
            # This helps prevent labels from overlapping too much, especially in circular layouts.
            if len(node_display_name) > 25: # Adjust threshold as needed
                node_display_name = node_display_name[:22] + '...'


            echarts_nodes.append({
                'id': str(step.id), # ECharts graph often works best with string IDs
                'name': node_display_name, # Display only the name, potentially truncated
                'value': num_use_cases, # Can be used for sorting, layout, or other visual encoding
                'category': category_index, # Link node to its area category
                'symbolSize': symbol_size, # Vary node size based on use case count
                'tooltip': { # Custom tooltip for node, including BI_ID and other details
                    'formatter': (
                        f'<strong>{step.name}</strong><br>'
                        f'BI_ID: {step.bi_id}<br>'
                        f'Area: {step.area.name if step.area else "N/A"}<br>'
                        f'Use Cases: {num_use_cases}<br>'
                        f'<i>Click for details</i>'
                    )
                },
                'itemStyle': {
                    'color': echarts_categories[category_index]['itemStyle']['color'] # Assign node color based on its category's color
                }
            })

        echarts_links = []
        # 3. Prepare Links (Process Step Relevance)
        for rel in relevances:
            # Ensure both source and target nodes exist in our prepared list
            source_node = next((node for node in echarts_nodes if node['id'] == str(rel.source_process_step_id)), None)
            target_node = next((node for node in echarts_nodes if node['id'] == str(rel.target_process_step_id)), None)

            if source_node and target_node: # Only add links if both ends are valid nodes
                # Scale relevance score (0-100) to link width (e.g., 0.5 to 4).
                # Minimum width 0.5 for visibility.
                link_width = max(0.5, rel.relevance_score / 25) 
                echarts_links.append({
                    'source': str(rel.source_process_step_id),
                    'target': str(rel.target_process_step_id),
                    'value': rel.relevance_score, # Used by link label formatter and width
                    'label': {
                        'show': True,
                        'formatter': '{c}', # Display relevance score on the link
                        'fontSize': 10,
                        'color': '#333',
                        'backgroundColor': 'rgba(255, 255, 255, 0.7)', # Semi-transparent background for label
                        'padding': [2, 4],
                        'borderRadius': 2
                    },
                    'lineStyle': {
                        'width': link_width,
                        'opacity': 0.8,
                        'curveness': 0.3 # Make links curved
                    },
                    'tooltip': { # Custom tooltip for link
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
        # Return an empty data structure to prevent chart rendering errors
        return render_template(
            'relevance_visualize.html',
            title='Process Relevance Map',
            echarts_data={'nodes': [], 'links': [], 'categories': []}
        )
    finally:
        SessionLocal.remove()