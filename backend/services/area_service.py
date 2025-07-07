# backend/services/area_service.py
from sqlalchemy.orm import Session, selectinload
from sqlalchemy.exc import IntegrityError
from ..models import Area, ProcessStep, UsecaseAreaRelevance

def get_all_areas_with_details(db_session: Session):
    """
    Retrieves all areas, preloading their process steps and the use cases
    within those steps for efficient access.
    """
    return db_session.query(Area).options(
        selectinload(Area.process_steps).selectinload(ProcessStep.use_cases)
    ).order_by(Area.name).all()

def get_area_by_id(db_session: Session, area_id: int):
    """
    Retrieves a single area by its ID, preloading all related data
    for the detail view. The usecase_relevance is no longer needed here.
    """
    return db_session.query(Area).options(
        selectinload(Area.process_steps).selectinload(ProcessStep.use_cases)
    ).get(area_id)

def update_area_from_form(db_session: Session, area: Area, form_data: dict):
    """
    Updates an Area object from form data.
    Returns a tuple (success: bool, message: str).
    """
    original_name = area.name
    new_name = form_data.get('name', '').strip()

    if not new_name:
        return False, "Area name cannot be empty."

    area.name = new_name
    # Use .get() which returns None if key is missing, then strip or default to None
    area.description = form_data.get('description', '').strip() or None

    if new_name != original_name:
        # Check if the new name already exists for a different area
        existing_area = db_session.query(Area).filter(Area.name == new_name, Area.id != area.id).first()
        if existing_area:
            # Revert name change to avoid IntegrityError on commit
            area.name = original_name
            db_session.rollback() # Rollback any potential session changes before returning
            return False, f"An area with the name '{new_name}' already exists."

    try:
        db_session.commit()
        return True, "Area updated successfully!"
    except IntegrityError as e:
        db_session.rollback()
        return False, f"Database error: Could not update the area. {e.orig}"
    except Exception as e:
        db_session.rollback()
        return False, f"An unexpected error occurred: {e}"