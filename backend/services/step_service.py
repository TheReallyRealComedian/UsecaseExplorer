# backend/services/step_service.py
from sqlalchemy.orm import Session, joinedload, selectinload
from sqlalchemy.exc import IntegrityError
from ..models import ProcessStep, UseCase, Area, UsecaseStepRelevance, ProcessStepProcessStepRelevance

def get_all_steps_with_details(db_session: Session):
    """Retrieves all process steps, preloading area and use case data."""
    return db_session.query(ProcessStep).options(
        joinedload(ProcessStep.area),
        joinedload(ProcessStep.use_cases)
    ).order_by(ProcessStep.area_id, ProcessStep.name).all()

def get_all_steps_for_api(db_session: Session):
    """Retrieves all steps with a minimal set of data for API responses."""
    steps = db_session.query(ProcessStep).options(joinedload(ProcessStep.area)).order_by(ProcessStep.name).all()
    return [{
        "id": step.id, "name": step.name, "bi_id": step.bi_id,
        "area_id": step.area_id, "area_name": step.area.name if step.area else "N/A"
    } for step in steps]

def get_step_by_id(db_session: Session, step_id: int):
    """Retrieves a single step by ID, preloading all related data for the detail view."""
    return db_session.query(ProcessStep).options(
        joinedload(ProcessStep.area),
        selectinload(ProcessStep.use_cases),
        selectinload(ProcessStep.usecase_relevance).joinedload(UsecaseStepRelevance.source_usecase),
        selectinload(ProcessStep.relevant_to_steps_as_source).joinedload(ProcessStepProcessStepRelevance.target_process_step),
        selectinload(ProcessStep.relevant_to_steps_as_target).joinedload(ProcessStepProcessStepRelevance.source_process_step)
    ).get(step_id)

def get_all_other_steps(db_session: Session, step_id: int):
    """Gets all steps except the one with the given ID."""
    return db_session.query(ProcessStep).filter(ProcessStep.id != step_id).order_by(ProcessStep.name).all()

def update_step_from_form(db_session: Session, step: ProcessStep, form_data: dict):
    """Updates a ProcessStep object from form data."""
    original_bi_id = step.bi_id
    
    # Core fields
    step.name = form_data.get('name', '').strip()
    step.bi_id = form_data.get('bi_id', '').strip()
    step.area_id = int(form_data.get('area_id'))
    
    # List of all text-based fields to update
    text_fields = [
        'step_description', 'raw_content', 'summary', 'vision_statement',
        'in_scope', 'out_of_scope', 'interfaces_text', 'what_is_actually_done',
        'pain_points', 'targets_text', 'llm_comment_1', 'llm_comment_2',
        'llm_comment_3', 'llm_comment_4', 'llm_comment_5'
    ]

    for field in text_fields:
        # Use .get() which returns None if key is missing, then strip or default to None
        setattr(step, field, form_data.get(field, '').strip() or None)

    if not all([step.name, step.bi_id, step.area_id]):
        return False, "Step Name, BI_ID, and Area are required."

    if step.bi_id != original_bi_id:
        existing_step = db_session.query(ProcessStep).filter(ProcessStep.bi_id == step.bi_id, ProcessStep.id != step.id).first()
        if existing_step:
            db_session.rollback()
            return False, f"Another process step with BI_ID '{step.bi_id}' already exists."

    try:
        db_session.commit()
        return True, "Process Step updated successfully!"
    except Exception as e:
        db_session.rollback()
        return False, f"An unexpected error occurred during update: {e}"

def inline_update_step_field(db_session: Session, step: ProcessStep, field_to_update: str, new_value):
    """Updates a single field on a step for inline editing."""
    if field_to_update in ['name', 'bi_id']:
        stripped_value = new_value.strip() if isinstance(new_value, str) else ''
        if not stripped_value:
            return None, f"{field_to_update.replace('_', ' ').title()} cannot be empty."
        if field_to_update == 'bi_id':
            existing = db_session.query(ProcessStep).filter(ProcessStep.bi_id == stripped_value, ProcessStep.id != step.id).first()
            if existing:
                return None, f"BI_ID '{stripped_value}' already exists."
        setattr(step, field_to_update, stripped_value)
    elif field_to_update == 'area_id':
        if not new_value: return None, "Area cannot be empty."
        if not db_session.query(Area).get(new_value): return None, "Selected area does not exist."
        setattr(step, field_to_update, new_value)
    else:
        setattr(step, field_to_update, new_value)
    
    db_session.commit()
    db_session.refresh(step, ['area'])
    return step, "Step updated."

def delete_step_by_id(db_session: Session, step_id: int):
    """Deletes a step and returns its name and area_id for redirection."""
    step = get_step_by_id(db_session, step_id)
    if not step:
        return None, None, "Process Step not found."
    
    area_id = step.area_id
    step_name = step.name
    db_session.delete(step)
    db_session.commit()
    return step_name, area_id, f"Process Step '{step_name}' and its use cases deleted successfully."