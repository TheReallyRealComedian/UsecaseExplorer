# backend/routes/review_routes.py
from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for
from flask_login import login_required
from sqlalchemy.orm import joinedload, aliased
from sqlalchemy import or_, and_

from ..db import SessionLocal
from ..utils import serialize_for_js
from ..utils import serialize_for_js
from ..models import Area, ProcessStep, ProcessStepProcessStepRelevance, UseCase

review_routes = Blueprint('review', __name__,
                          template_folder='../templates',
                          url_prefix='/review')

# Route for the main review dashboard
@review_routes.route('/')
@login_required
def review_dashboard():
    session = SessionLocal()
    # For breadcrumbs
    all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
    all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
    all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
    session.close()

    return render_template('review_dashboard.html',
                           title="Review Center",
                           current_item=None,
                           current_area=None,
                           current_step=None,
                           current_usecase=None,
                           all_areas_flat=all_areas_flat,
                           all_steps_flat=all_steps_flat,
                           all_usecases_flat=all_usecases_flat)

# Route for the Process Links Review page
@review_routes.route('/process-links/')
@login_required
def review_process_links_page():
    session = SessionLocal()
    try:
        areas = session.query(Area).order_by(Area.name).all()
        
        # For breadcrumbs
        all_areas_flat = serialize_for_js(areas, 'area') # Use already fetched areas
        all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')

        return render_template('review_process_links.html',
                               title="Review Process Step Links",
                               areas=areas, # For populating selectors
                               current_item=None,
                               current_area=None,
                               current_step=None,
                               current_usecase=None,
                               all_areas_flat=all_areas_flat,
                               all_steps_flat=all_steps_flat,
                               all_usecases_flat=all_usecases_flat)
    finally:
        session.close()

# API endpoint to fetch data for the Sankey diagram
@review_routes.route('/api/process-links/data', methods=['GET'])
@login_required
def get_process_links_data():
    session = SessionLocal()
    try:
        focus_area_id = request.args.get('focus_area_id', type=int)
        comparison_area_ids_str = request.args.getlist('comparison_area_ids[]')
        
        comparison_area_ids = []
        if comparison_area_ids_str:
            try:
                comparison_area_ids = [int(id_str) for id_str in comparison_area_ids_str if id_str.isdigit()]
            except ValueError:
                return jsonify(error="Invalid comparison_area_ids format."), 400

        if not focus_area_id:
            return jsonify(error="Focus area ID is required."), 400

        nodes_dict = {} # Use a dict to ensure unique nodes by step_id
        links = []
        
        # Use a simple color list for areas for now
        area_colors_list = ['#5470C6', '#91CC75', '#EE6666', '#73C0DE', '#3BA272', '#FC8452', '#9A60B4', '#EA7CCC']
        area_color_map = {}
        
        all_db_areas = session.query(Area).all()
        for i, area in enumerate(all_db_areas):
            area_color_map[area.id] = area_colors_list[i % len(area_colors_list)]

        def get_node_name(step, area_name_override=None):
            # Use area_name_override if provided, otherwise fetch from step's area
            area_name = area_name_override
            if not area_name and step.area:
                 area_name = step.area.name
            elif not area_name: # Fallback if step.area is None for some reason
                area_obj = session.query(Area).get(step.area_id)
                area_name = area_obj.name if area_obj else "Unknown Area"
            return f"{step.name} ({area_name})"

        # Collect all steps from selected areas to build nodes
        all_selected_area_ids_for_nodes = [focus_area_id] + comparison_area_ids
        steps_for_nodes = session.query(ProcessStep).options(joinedload(ProcessStep.area)).filter(
            ProcessStep.area_id.in_(all_selected_area_ids_for_nodes)
        ).all()

        for step in steps_for_nodes:
            if step.id not in nodes_dict: # Ensure unique nodes by step.id
                nodes_dict[step.id] = {
                    "name": get_node_name(step), # ECharts Sankey uses 'name' for linking
                    "id": step.id, # Our internal step ID
                    "itemStyle": {"color": area_color_map.get(step.area_id, '#CCCCCC')}
                }
        
        # Build query for links based on selected areas
        # Source Step Alias
        SourceStep = aliased(ProcessStep, name='source_step')
        # Target Step Alias
        TargetStep = aliased(ProcessStep, name='target_step')

        query = session.query(ProcessStepProcessStepRelevance).join(
            SourceStep, ProcessStepProcessStepRelevance.source_process_step_id == SourceStep.id
        ).join(
            TargetStep, ProcessStepProcessStepRelevance.target_process_step_id == TargetStep.id
        )

        link_filters = []
        if not comparison_area_ids:
            # Only focus area selected: links within the focus area
            link_filters.append(and_(SourceStep.area_id == focus_area_id, TargetStep.area_id == focus_area_id))
        else:
            # Focus to Comparison(s)
            link_filters.append(and_(SourceStep.area_id == focus_area_id, TargetStep.area_id.in_(comparison_area_ids)))
            # Comparison(s) to Focus
            link_filters.append(and_(SourceStep.area_id.in_(comparison_area_ids), TargetStep.area_id == focus_area_id))
            # Within Comparison Area(s) - if more than one comparison area or if a comparison area is linked to itself
            if len(comparison_area_ids) > 0:
                 link_filters.append(and_(SourceStep.area_id.in_(comparison_area_ids), TargetStep.area_id.in_(comparison_area_ids)))
        
        if link_filters:
            query = query.filter(or_(*link_filters))

        db_links = query.all()

        for link in db_links:
            # Ensure both source and target steps are in our collected nodes_dict
            if link.source_process_step_id in nodes_dict and link.target_process_step_id in nodes_dict:
                links.append({
                    "source": nodes_dict[link.source_process_step_id]["name"],
                    "target": nodes_dict[link.target_process_step_id]["name"],
                    "value": link.relevance_score if link.relevance_score > 0 else 1, # Sankey value must be > 0
                    "lineStyle": {"opacity": 0.7, "curveness": 0.15},
                    "data": {
                        "link_id": link.id,
                        "content_snippet": (link.relevance_content[:50] + '...' if link.relevance_content and len(link.relevance_content) > 50 else link.relevance_content) or "No content."
                    }
                })
        
        final_nodes_list = list(nodes_dict.values())

        return jsonify(nodes=final_nodes_list, links=links)
    except Exception as e:
        print(f"Error fetching Sankey data: {e}")
        import traceback
        traceback.print_exc()
        return jsonify(error=str(e)), 500
    finally:
        session.close()

# API endpoint to get a single link's details (for pre-filling edit modal)
@review_routes.route('/api/process-links/link/<int:link_id>', methods=['GET'])
@login_required
def get_process_link_detail(link_id):
    session = SessionLocal()
    try:
        link = session.query(ProcessStepProcessStepRelevance).options(
            joinedload(ProcessStepProcessStepRelevance.source_process_step).joinedload(ProcessStep.area),
            joinedload(ProcessStepProcessStepRelevance.target_process_step).joinedload(ProcessStep.area)
        ).get(link_id)

        if not link:
            return jsonify(error="Link not found"), 404
        
        return jsonify({
            "id": link.id,
            "source_step_id": link.source_process_step_id,
            "source_step_name": link.source_process_step.name,
            "source_area_name": link.source_process_step.area.name,
            "target_step_id": link.target_process_step_id,
            "target_step_name": link.target_process_step.name,
            "target_area_name": link.target_process_step.area.name,
            "relevance_score": link.relevance_score,
            "relevance_content": link.relevance_content or ""
        })
    finally:
        session.close()


# API endpoint to create a new ProcessStep-ProcessStep relevance link
@review_routes.route('/api/process-links/link', methods=['POST'])
@login_required
def create_process_link():
    session = SessionLocal()
    try:
        data = request.json
        source_step_id = data.get('source_step_id')
        target_step_id = data.get('target_step_id')
        relevance_score = data.get('relevance_score')
        relevance_content = data.get('relevance_content', '').strip()

        if not all([source_step_id, target_step_id, relevance_score is not None]):
            return jsonify(error="Missing required fields (source, target, score)."), 400
        
        if source_step_id == target_step_id:
            return jsonify(error="Cannot link a step to itself."), 400

        try:
            score = int(relevance_score)
            if not (0 <= score <= 100):
                return jsonify(error="Score must be between 0 and 100."), 400
        except ValueError:
            return jsonify(error="Invalid score format."), 400

        # Check if link already exists
        existing = session.query(ProcessStepProcessStepRelevance).filter_by(
            source_process_step_id=source_step_id,
            target_process_step_id=target_step_id
        ).first()
        if existing:
            return jsonify(error="Link already exists."), 409

        new_link = ProcessStepProcessStepRelevance(
            source_process_step_id=source_step_id,
            target_process_step_id=target_step_id,
            relevance_score=score,
            relevance_content=relevance_content or None
        )
        session.add(new_link)
        session.commit()
        return jsonify(success=True, message="Link created successfully.", link_id=new_link.id), 201
    except Exception as e:
        session.rollback()
        return jsonify(error=str(e)), 500
    finally:
        session.close()

# API endpoint to update an existing ProcessStep-ProcessStep relevance link
@review_routes.route('/api/process-links/link/<int:link_id>', methods=['PUT'])
@login_required
def update_process_link(link_id):
    session = SessionLocal()
    try:
        link = session.query(ProcessStepProcessStepRelevance).get(link_id)
        if not link:
            return jsonify(error="Link not found."), 404

        data = request.json
        relevance_score = data.get('relevance_score')
        relevance_content = data.get('relevance_content', '').strip()

        if relevance_score is not None:
            try:
                score = int(relevance_score)
                if not (0 <= score <= 100):
                    return jsonify(error="Score must be between 0 and 100."), 400
                link.relevance_score = score
            except ValueError:
                return jsonify(error="Invalid score format."), 400
        
        if 'relevance_content' in data: # Allow clearing content
            link.relevance_content = relevance_content or None
        
        session.commit()
        return jsonify(success=True, message="Link updated successfully.")
    except Exception as e:
        session.rollback()
        return jsonify(error=str(e)), 500
    finally:
        session.close()

# API endpoint to delete an existing ProcessStep-ProcessStep relevance link
@review_routes.route('/api/process-links/link/<int:link_id>', methods=['DELETE'])
@login_required
def delete_process_link(link_id):
    session = SessionLocal()
    try:
        link = session.query(ProcessStepProcessStepRelevance).get(link_id)
        if not link:
            return jsonify(error="Link not found."), 404
        
        session.delete(link)
        session.commit()
        return jsonify(success=True, message="Link deleted successfully.")
    except Exception as e:
        session.rollback()
        return jsonify(error=str(e)), 500
    finally:
        session.close()
