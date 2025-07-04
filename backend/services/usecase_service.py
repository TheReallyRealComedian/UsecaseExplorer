# backend/services/usecase_service.py
from sqlalchemy.orm import Session, joinedload, selectinload
from ..models import UseCase, ProcessStep, Area, UsecaseAreaRelevance, UsecaseStepRelevance, UsecaseUsecaseRelevance, Tag

def get_all_usecases_with_details(db_session: Session):
    return db_session.query(UseCase).options(
        joinedload(UseCase.process_step).joinedload(ProcessStep.area),
        selectinload(UseCase.tags) # Eager load tags
    ).order_by(UseCase.name).all()

def get_usecase_by_id(db_session: Session, usecase_id: int):
    return db_session.query(UseCase).options(
        joinedload(UseCase.process_step).joinedload(ProcessStep.area),
        selectinload(UseCase.tags), # Eager load tags
        selectinload(UseCase.relevant_to_areas).joinedload(UsecaseAreaRelevance.target_area),
        selectinload(UseCase.relevant_to_steps).joinedload(UsecaseStepRelevance.target_process_step),
        selectinload(UseCase.relevant_to_usecases_as_source).joinedload(UsecaseUsecaseRelevance.target_usecase),
        selectinload(UseCase.relevant_to_usecases_as_target).joinedload(UsecaseUsecaseRelevance.source_usecase)
    ).get(usecase_id)

def get_all_other_usecases(db_session: Session, usecase_id: int):
    return db_session.query(UseCase).filter(UseCase.id != usecase_id).order_by(UseCase.name).all()

def _handle_tags(db_session: Session, tag_string: str, category: str):
    """Helper function to process a comma-separated string of tags."""
    if not tag_string:
        return []
    
    tag_names = [name.strip() for name in tag_string.split(',') if name.strip()]
    if not tag_names:
        return []
    
    # Find existing tags in one query
    existing_tags = db_session.query(Tag).filter(
        Tag.category == category,
        Tag.name.in_(tag_names)
    ).all()
    existing_tag_names = {tag.name for tag in existing_tags}
    
    # Create new tags for those that don't exist
    new_tags = [
        Tag(name=name, category=category)
        for name in tag_names if name not in existing_tag_names
    ]
    
    # Add new tags to the session
    if new_tags:
        db_session.add_all(new_tags)
        db_session.flush() # Flush to get IDs for new tags
        
    return existing_tags + new_tags

def update_usecase_from_form(db_session: Session, usecase: UseCase, form_data: dict):
    original_bi_id = usecase.bi_id
    usecase.name = form_data.get('name', '').strip()
    usecase.bi_id = form_data.get('bi_id', '').strip()
    usecase.process_step_id = int(form_data.get('process_step_id'))

    priority_str = form_data.get('priority')
    if priority_str and priority_str.isdigit() and 1 <= int(priority_str) <= 4:
        usecase.priority = int(priority_str)
    else:
        usecase.priority = None

    text_fields = [
        'raw_content', 'summary', 'inspiration', 'wave', 'effort_level', 'status',
        'business_problem_solved', 'target_solution_description', 'technologies_text',
        'requirements', 'relevants_text', 'reduction_time_transfer', 'reduction_time_launches',
        'reduction_costs_supply', 'quality_improvement_quant', 'ideation_notes',
        'further_ideas', 'effort_quantification', 'potential_quantification',
        'dependencies_text', 'contact_persons_text', 'related_projects_text',
        'pilot_site_factory_text', 'usecase_type_category',
        'llm_comment_1', 'llm_comment_2', 'llm_comment_3', 'llm_comment_4', 'llm_comment_5'
    ]
    for field in text_fields:
        setattr(usecase, field, form_data.get(field, '').strip() or None)

    # --- NEW: Handle tags ---
    it_system_tags = _handle_tags(db_session, form_data.get('it_systems', ''), 'it_system')
    data_type_tags = _handle_tags(db_session, form_data.get('data_types', ''), 'data_type')
    generic_tags = _handle_tags(db_session, form_data.get('generic_tags', ''), 'tag')

    # Combine all tags and update the relationship
    # This automatically handles the association table
    usecase.tags = it_system_tags + data_type_tags + generic_tags

    if not all([usecase.name, usecase.bi_id, usecase.process_step_id]):
        return False, "Use Case Name, BI_ID, and Process Step are required."

    if usecase.bi_id != original_bi_id:
        existing = db_session.query(UseCase).filter(UseCase.bi_id == usecase.bi_id, UseCase.id != usecase.id).first()
        if existing:
            return False, f"Another use case with BI_ID '{usecase.bi_id}' already exists."

    db_session.commit()
    return True, "Use Case updated successfully!"

def inline_update_usecase_field(db_session: Session, usecase: UseCase, field: str, value):
    if field == 'name':
        stripped = value.strip()
        if not stripped: return None, "Name cannot be empty."
        setattr(usecase, field, stripped)
    elif field == 'bi_id':
        stripped = value.strip()
        if not stripped: return None, "BI_ID cannot be empty."
        if db_session.query(UseCase).filter(UseCase.bi_id == stripped, UseCase.id != usecase.id).first():
            return None, f"BI_ID '{stripped}' already exists."
        setattr(usecase, field, stripped)
    elif field in ['quality_improvement_quant', 'effort_level', 'wave']:
        setattr(usecase, field, value.strip() if value and value.strip().upper() != 'N/A' else None)
    else:
        return None, "Field not allowed for inline update."
        
    db_session.commit()
    updated_data = {
        'id': usecase.id, 'name': usecase.name, 'bi_id': usecase.bi_id,
        'quality_improvement_quant': usecase.quality_improvement_quant,
        'priority': usecase.priority, 'effort_level': usecase.effort_level, 'wave': usecase.wave,
    }
    return usecase, "Use Case updated.", updated_data

def delete_usecase_by_id(db_session: Session, usecase_id: int):
    usecase = get_usecase_by_id(db_session, usecase_id)
    if not usecase:
        return None, "Use Case not found."
    uc_name = usecase.name
    db_session.delete(usecase)
    db_session.commit()
    return uc_name, f"Use Case '{uc_name}' deleted successfully."