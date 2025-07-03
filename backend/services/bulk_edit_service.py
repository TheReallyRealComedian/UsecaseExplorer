# backend/services/bulk_edit_service.py
from sqlalchemy.orm import Session, joinedload
from ..models import ProcessStep, UseCase, Area

def prepare_steps_for_bulk_edit(db_session: Session, step_ids: list[int], editable_fields: dict):
    """
    Prepares a list of ProcessStep objects for bulk editing, fetching current
    values and structuring them for the template.
    """
    steps_to_edit = db_session.query(ProcessStep).options(
        joinedload(ProcessStep.area)
    ).filter(ProcessStep.id.in_(step_ids)).all()
    
    prepared_data = []
    for step in steps_to_edit:
        prepared_data.append({
            'id': step.id, 'name': step.name, 'bi_id': step.bi_id,
            'current_area_id': step.area_id,
            'current_area_name': step.area.name if step.area else 'N/A',
            **{f'current_{key}': getattr(step, key) for key in editable_fields if key not in ['name', 'bi_id', 'area_id']},
            'new_values': {key: getattr(step, key) for key in editable_fields}
        })
    return prepared_data

def save_bulk_step_changes(db_session: Session, changes: list[dict]):
    """
    Saves a batch of changes to multiple ProcessStep objects.
    """
    for item in changes:
        step = db_session.query(ProcessStep).get(item['id'])
        if step:
            for field, value in item['updated_fields'].items():
                if field == 'area_id':
                    # Ensure value is an integer or None
                    step.area_id = int(value) if value is not None else None
                else:
                    setattr(step, field, value)
    db_session.commit()
    return f"Successfully saved changes for {len(changes)} process step(s)."

def prepare_usecases_for_bulk_edit(db_session: Session, usecase_ids: list[int], editable_fields: dict):
    """
    Prepares a list of UseCase objects for bulk editing, fetching current
    values and structuring them for the template.
    """
    usecases_to_edit = db_session.query(UseCase).options(
        joinedload(UseCase.process_step).joinedload(ProcessStep.area)
    ).filter(UseCase.id.in_(usecase_ids)).all()
    
    prepared_data = []
    for uc in usecases_to_edit:
        current_step = uc.process_step
        prepared_data.append({
            'id': uc.id, 'name': uc.name, 'bi_id': uc.bi_id,
            'current_process_step_id': uc.process_step_id,
            'current_process_step_name': current_step.name if current_step else 'N/A',
            'area_name': current_step.area.name if current_step and current_step.area else 'N/A',
            **{f'current_{key}': getattr(uc, key) for key in editable_fields if key not in ['name', 'bi_id', 'process_step_id']},
            'new_values': {key: getattr(uc, key) for key in editable_fields}
        })
    return prepared_data

def save_bulk_usecase_changes(db_session: Session, changes: list[dict]):
    """
    Saves a batch of changes to multiple UseCase objects.
    """
    for item in changes:
        usecase = db_session.query(UseCase).get(item['id'])
        if usecase:
            for field, value in item['updated_fields'].items():
                if field in ['process_step_id', 'priority']:
                    # Ensure value is an integer or None
                    setattr(usecase, field, int(value) if value is not None else None)
                else:
                    setattr(usecase, field, value)
    db_session.commit()
    return f"Successfully saved changes for {len(changes)} use case(s)."