# backend/services/review_service.py
from sqlalchemy.orm import Session, joinedload, aliased
from sqlalchemy import or_, and_
from ..models import Area, ProcessStep, ProcessStepProcessStepRelevance

def get_process_links_for_review(session: Session, focus_area_id: int, comparison_area_ids: list[int]):
    """Fetches and structures process step links for the review page table."""
    SourceStep = aliased(ProcessStep, name='source_step')
    TargetStep = aliased(ProcessStep, name='target_step')
    SourceArea = aliased(Area, name='source_area')
    TargetArea = aliased(Area, name='target_area')

    query = session.query(
        ProcessStepProcessStepRelevance,
        SourceStep.name.label('source_step_name'),
        SourceStep.bi_id.label('source_step_bi_id'),
        TargetStep.name.label('target_step_name'),
        TargetStep.bi_id.label('target_step_bi_id'),
        SourceArea.name.label('source_area_name'),
        TargetArea.name.label('target_area_name'),
        SourceStep.id.label('source_step_actual_id'),
        TargetStep.id.label('target_step_actual_id')
    ).join(
        SourceStep, ProcessStepProcessStepRelevance.source_process_step_id == SourceStep.id
    ).join(
        TargetStep, ProcessStepProcessStepRelevance.target_process_step_id == TargetStep.id
    ).join(
        SourceArea, SourceStep.area_id == SourceArea.id
    ).join(
        TargetArea, TargetStep.area_id == TargetArea.id
    )

    main_filter_conditions = []
    is_focus_only_scenario = not comparison_area_ids or (len(comparison_area_ids) == 1 and comparison_area_ids[0] == focus_area_id)

    if is_focus_only_scenario:
        main_filter_conditions.append(and_(SourceStep.area_id == focus_area_id, TargetStep.area_id == focus_area_id))
    else:
        cond1 = and_(SourceStep.area_id == focus_area_id, TargetStep.area_id.in_(comparison_area_ids))
        cond2 = and_(TargetStep.area_id == focus_area_id, SourceStep.area_id.in_(comparison_area_ids))
        main_filter_conditions.append(or_(cond1, cond2))
    
    if main_filter_conditions:
        query = query.filter(or_(*main_filter_conditions))
    else:
        query = query.filter(False)

    db_results = query.order_by(SourceStep.name, TargetStep.name).all()

    links_data = []
    for result_row in db_results:
        (relevance_obj, source_step_name, source_step_bi_id,
         target_step_name, target_step_bi_id,
         source_area_name, target_area_name,
         source_step_actual_id, target_step_actual_id) = result_row

        links_data.append({
            "id": relevance_obj.id,
            "source_step_id": source_step_actual_id,
            "target_step_id": target_step_actual_id,
            "source_step_name": source_step_name,
            "source_step_bi_id": source_step_bi_id,
            "target_step_name": target_step_name,
            "target_step_bi_id": target_step_bi_id,
            "source_area_name": source_area_name,
            "target_area_name": target_area_name,
            "relevance_score": relevance_obj.relevance_score,
            "relevance_content_snippet": (relevance_obj.relevance_content or "")[:100] + ('...' if (relevance_obj.relevance_content or "")[100:] else ''),
            "relevance_content": relevance_obj.relevance_content or "",
            "created_at": relevance_obj.created_at.isoformat() if relevance_obj.created_at else None,
            "updated_at": relevance_obj.updated_at.isoformat() if relevance_obj.updated_at else None,
        })
    
    return links_data