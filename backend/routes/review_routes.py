# backend/routes/review_routes.py
from flask import Blueprint, render_template, jsonify, request, flash, redirect, url_for, Response
from flask_login import login_required
from sqlalchemy.orm import joinedload, aliased
from sqlalchemy import or_, and_, exc as sqlalchemy_exc

from ..db import SessionLocal
from ..utils import serialize_for_js
from ..models import Area, ProcessStep, ProcessStepProcessStepRelevance, UseCase
from ..services import review_service

import io
import csv
import datetime

review_routes = Blueprint('review', __name__,
                          template_folder='../templates',
                          url_prefix='/review')


@review_routes.route('/')
@login_required
def review_dashboard():
    session = SessionLocal()
    try:
        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
    finally:
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


@review_routes.route('/process-links/')
@login_required
def review_process_links_page():
    session = SessionLocal()
    try:
        areas = session.query(Area).order_by(Area.name).all()

        all_areas_flat = serialize_for_js(areas, 'area')
        all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')

        return render_template('review_process_links.html',
                               title="Review Process Step Links",
                               areas=areas,
                               current_item=None,
                               current_area=None,
                               current_step=None,
                               current_usecase=None,
                               all_areas_flat=all_areas_flat,
                               all_steps_flat=all_steps_flat,
                               all_usecases_flat=all_usecases_flat)
    finally:
        session.close()


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
                comparison_area_ids = [int(id_str) for id_str in comparison_area_ids_str if id_str and id_str.isdigit()]
            except ValueError:
                return jsonify(error="Invalid comparison_area_ids format."), 400

        if not focus_area_id:
            return jsonify(error="Focus area ID is required."), 400

        # Call the service function to get the data
        links_data = review_service.get_process_links_for_review(session, focus_area_id, comparison_area_ids)

        return jsonify(links=links_data)

    except Exception as e:
        print(f"Error fetching process links data for table: {e}")
        import traceback
        traceback.print_exc()
        return jsonify(error=str(e)), 500
    finally:
        if session and session.is_active:
            session.close()


@review_routes.route('/export-involved-steps-csv', methods=['GET'])
@login_required
def export_involved_steps_csv():
    session = SessionLocal()
    try:
        focus_area_id = request.args.get('focus_area_id', type=int)
        comparison_area_ids_str = request.args.getlist('comparison_area_ids[]')

        comparison_area_ids = []
        if comparison_area_ids_str:
            try:
                comparison_area_ids = [int(id_str) for id_str in comparison_area_ids_str if id_str.strip().isdigit()]
            except ValueError:
                flash("Invalid comparison area IDs provided.", "danger")
                return redirect(url_for('review.review_process_links_page'))

        if not focus_area_id:
            flash("Focus area ID is required for export.", "danger")
            return redirect(url_for('review.review_process_links_page'))

        SourceStep = aliased(ProcessStep, name='source_step')
        TargetStep = aliased(ProcessStep, name='target_step')

        query = session.query(
            ProcessStepProcessStepRelevance.source_process_step_id,
            ProcessStepProcessStepRelevance.target_process_step_id
        ).join(
            SourceStep, ProcessStepProcessStepRelevance.source_process_step_id == SourceStep.id
        ).join(
            TargetStep, ProcessStepProcessStepRelevance.target_process_step_id == TargetStep.id
        )

        main_filter_conditions = []
        is_focus_only_scenario = not comparison_area_ids or \
                                 (len(comparison_area_ids) == 1 and comparison_area_ids[0] == focus_area_id)

        if is_focus_only_scenario:
            main_filter_conditions.append(
                and_(SourceStep.area_id == focus_area_id, TargetStep.area_id == focus_area_id)
            )
        else:
            cond1 = and_(SourceStep.area_id == focus_area_id, TargetStep.area_id.in_(comparison_area_ids))
            cond2 = and_(TargetStep.area_id == focus_area_id, SourceStep.area_id.in_(comparison_area_ids))
            main_filter_conditions.append(or_(cond1, cond2))

        if main_filter_conditions:
            query = query.filter(or_(*main_filter_conditions))
        else:
            query = query.filter(False)

        link_results = query.all()

        involved_step_ids = set()
        for source_id, target_id in link_results:
            involved_step_ids.add(source_id)
            involved_step_ids.add(target_id)

        steps_to_export = []
        if involved_step_ids:
            steps_to_export = session.query(
                ProcessStep.id,
                ProcessStep.step_description
            ).filter(ProcessStep.id.in_(list(involved_step_ids))).order_by(ProcessStep.id).all()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=';')
        writer.writerow(['id', 'short_description'])

        for step_id, description in steps_to_export:
            writer.writerow([step_id, description or ""])

        csv_data = output.getvalue()
        output.close()

        timestamp = datetime.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        filename = f"involved_process_steps_{timestamp}.csv"

        return Response(
            csv_data,
            mimetype='text/csv',
            headers={"Content-Disposition": f"attachment;filename={filename}"}
        )

    except Exception as e:
        print(f"Error exporting involved steps CSV: {e}")
        import traceback
        traceback.print_exc()
        flash("An error occurred while exporting involved steps.", "danger")
        return redirect(url_for('review.review_process_links_page'))
    finally:
        if session and session.is_active:
            session.close()


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
            "source_area_name": link.source_process_step.area.name if link.source_process_step.area else "N/A",
            "target_step_id": link.target_process_step_id,
            "target_step_name": link.target_process_step.name,
            "target_area_name": link.target_process_step.area.name if link.target_process_step.area else "N/A",
            "relevance_score": link.relevance_score,
            "relevance_content": link.relevance_content or ""
        })
    finally:
        if session and session.is_active:
            session.close()


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

        source_step_id = int(source_step_id)
        target_step_id = int(target_step_id)

        if source_step_id == target_step_id:
            return jsonify(error="Cannot link a step to itself."), 400

        try:
            score = int(relevance_score)
            if not (0 <= score <= 100):
                return jsonify(error="Score must be between 0 and 100."), 400
        except ValueError:
            return jsonify(error="Invalid score format."), 400

        source_step_exists = session.query(ProcessStep).get(source_step_id)
        target_step_exists = session.query(ProcessStep).get(target_step_id)
        if not source_step_exists:
            return jsonify(error=f"Source step with ID {source_step_id} not found."), 404
        if not target_step_exists:
            return jsonify(error=f"Target step with ID {target_step_id} not found."), 404

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
    except sqlalchemy_exc.IntegrityError as e:
        session.rollback()
        if "no_self_step_relevance" in str(e.orig).lower():
            return jsonify(error="Database constraint violation: Cannot link a step to itself."), 400
        if "unique_process_step_process_step_relevance" in str(e.orig).lower():
            return jsonify(error="Database constraint violation: This link already exists."), 409
        return jsonify(error=f"Database integrity error: {e.orig}"), 500
    except Exception as e:
        session.rollback()
        return jsonify(error=str(e)), 500
    finally:
        if session and session.is_active:
            session.close()


@review_routes.route('/api/process-links/link/<int:link_id>', methods=['PUT'])
@login_required
def update_process_link(link_id):
    session = SessionLocal()
    try:
        link = session.query(ProcessStepProcessStepRelevance).get(link_id)
        if not link:
            return jsonify(error="Link not found."), 404

        data = request.json

        new_source_step_id = data.get('source_step_id')
        new_target_step_id = data.get('target_step_id')

        source_changed = new_source_step_id is not None and int(new_source_step_id) != link.source_process_step_id
        target_changed = new_target_step_id is not None and int(new_target_step_id) != link.target_process_step_id

        final_source_id = int(new_source_step_id) if source_changed else link.source_process_step_id
        final_target_id = int(new_target_step_id) if target_changed else link.target_process_step_id

        if final_source_id == final_target_id:
            return jsonify(error="Cannot link a step to itself."), 400

        if source_changed or target_changed:
            if source_changed:
                source_step_exists = session.query(ProcessStep).get(final_source_id)
                if not source_step_exists:
                    return jsonify(error=f"New source step with ID {final_source_id} not found."), 404

            if target_changed:
                target_step_exists = session.query(ProcessStep).get(final_target_id)
                if not target_step_exists:
                    return jsonify(error=f"New target step with ID {final_target_id} not found."), 404

            existing_duplicate = session.query(ProcessStepProcessStepRelevance).filter(
                ProcessStepProcessStepRelevance.id != link_id,
                ProcessStepProcessStepRelevance.source_process_step_id == final_source_id,
                ProcessStepProcessStepRelevance.target_process_step_id == final_target_id
            ).first()
            if existing_duplicate:
                return jsonify(error="A link with the new source and target steps already exists."), 409

            link.source_process_step_id = final_source_id
            link.target_process_step_id = final_target_id

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

        if 'relevance_content' in data:
            link.relevance_content = relevance_content or None

        session.commit()
        return jsonify(success=True, message="Link updated successfully.")
    except sqlalchemy_exc.IntegrityError as e:
        session.rollback()
        if "no_self_step_relevance" in str(e.orig).lower():
            return jsonify(error="Database constraint violation: Cannot link a step to itself."), 400
        if "unique_process_step_process_step_relevance" in str(e.orig).lower():
            return jsonify(error="Database constraint violation: This link (source/target combination) already exists."), 409
        return jsonify(error=f"Database integrity error: {e.orig}"), 500
    except Exception as e:
        session.rollback()
        return jsonify(error=str(e)), 500
    finally:
        if session and session.is_active:
            session.close()


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
        if session and session.is_active:
            session.close()


@review_routes.route('/api/process-links/delete-all', methods=['POST'])
@login_required
def delete_all_process_links():
    session = SessionLocal()
    try:
        num_deleted = session.query(ProcessStepProcessStepRelevance).delete()
        session.commit()

        message = f"Successfully deleted {num_deleted} process step link(s)."
        if num_deleted == 0:
            message = "No process step links found to delete."

        return jsonify(success=True, message=message), 200
    except Exception as e:
        session.rollback()
        print(f"Error deleting all process step links: {e}")
        return jsonify(success=False, error="An unexpected error occurred while deleting links."), 500
    finally:
        if session and session.is_active:
            session.close()


general_api_routes = Blueprint('general_api', __name__, url_prefix='/api')


@general_api_routes.route('/steps', methods=['GET'])
@login_required
def get_all_steps_for_select():
    session = SessionLocal()
    try:
        steps_query = session.query(ProcessStep).options(
            joinedload(ProcessStep.area)
        ).order_by(ProcessStep.name).all()

        steps_data = []
        for step in steps_query:
            steps_data.append({
                "id": step.id,
                "name": step.name,
                "bi_id": step.bi_id,
                "area_name": step.area.name if step.area else "N/A"
            })
        return jsonify(steps_data)
    except Exception as e:
        print(f"Error fetching all steps for select: {e}")
        import traceback
        traceback.print_exc()
        return jsonify(error=str(e)), 500
    finally:
        if session and session.is_active:
            session.close()