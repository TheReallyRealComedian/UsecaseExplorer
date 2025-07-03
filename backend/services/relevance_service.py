# backend/services/relevance_service.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy.exc import IntegrityError
import markdown
from ..models import (
    UseCase, ProcessStep, Area,
    UsecaseAreaRelevance, UsecaseStepRelevance, UsecaseUsecaseRelevance,
    ProcessStepProcessStepRelevance
)

def add_relevance_link(session: Session, source_usecase_id: int, target_id: int, score: int, content: str, link_type: str):
    """Generic function to add a relevance link."""
    model_map = {
        'area': UsecaseAreaRelevance,
        'step': UsecaseStepRelevance,
        'usecase': UsecaseUsecaseRelevance
    }
    target_fk_map = {
        'area': 'target_area_id',
        'step': 'target_process_step_id',
        'usecase': 'target_usecase_id'
    }

    model = model_map[link_type]
    target_fk = target_fk_map[link_type]

    if link_type == 'usecase' and source_usecase_id == target_id:
        return None, "Cannot link a Use Case to itself."

    existing_link = session.query(model).filter(
        model.source_usecase_id == source_usecase_id,
        getattr(model, target_fk) == target_id
    ).first()

    if existing_link:
        return None, "This relevance link already exists."

    new_link_data = {
        'source_usecase_id': source_usecase_id,
        'relevance_score': score,
        'relevance_content': content or None,
        target_fk: target_id
    }
    new_link = model(**new_link_data)
    session.add(new_link)
    session.commit()
    return new_link, "Relevance link added successfully!"

def add_step_to_step_relevance_link(session: Session, source_step_id: int, target_step_id: int, score: int, content: str):
    """Adds a relevance link between two Process Steps."""
    if source_step_id == target_step_id:
        return None, "Cannot link a Process Step to itself."

    existing_link = session.query(ProcessStepProcessStepRelevance).filter_by(
        source_process_step_id=source_step_id,
        target_process_step_id=target_step_id
    ).first()

    if existing_link:
        return None, "Relevance link between these Process Steps already exists."

    new_link = ProcessStepProcessStepRelevance(
        source_process_step_id=source_step_id,
        target_process_step_id=target_step_id,
        relevance_score=score,
        relevance_content=content or None
    )
    session.add(new_link)
    session.commit()
    return new_link, "Process Step relevance link added successfully!"

# ... (similar service functions for delete_relevance_link, get_relevance_link, update_relevance_link)

def get_relevance_graph_data(session: Session):
    """Prepares data for the ECharts relevance graph."""
    areas = session.query(Area).order_by(Area.name).all()
    steps = session.query(ProcessStep).options(
        joinedload(ProcessStep.area),
        joinedload(ProcessStep.use_cases)
    ).order_by(ProcessStep.area_id, ProcessStep.name).all()
    relevances = session.query(ProcessStepProcessStepRelevance).all()

    echarts_categories = []
    area_id_to_category_index = {}
    area_colors = [
        '#5D8C7B', '#4A7062', '#6c757d', '#78909C', '#A0A0A0',
        '#B5C4B1', '#8C9A8C', '#455A64', '#CFD8DC', '#FFB6C1',
        '#FFD700', '#FFA07A', '#87CEEB', '#DA70D6', '#CD5C5C', '#4682B4'
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

            tooltip_content_html = "N/A"
            if rel.relevance_content:
                processed_content = markdown.markdown(rel.relevance_content, extensions=["fenced_code", "tables"])
                tooltip_content_html = f'<div class="echarts-tooltip-content">{processed_content}</div>'

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
                        f'Content: {tooltip_content_html}'
                    )
                }
            })

    return {
        'nodes': echarts_nodes,
        'links': echarts_links,
        'categories': echarts_categories
    }