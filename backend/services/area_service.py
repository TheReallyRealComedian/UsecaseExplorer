# backend/services/area_service.py
from sqlalchemy.orm import Session, selectinload
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
    for the detail view.
    """
    return db_session.query(Area).options(
        selectinload(Area.process_steps).selectinload(ProcessStep.use_cases),
        selectinload(Area.usecase_relevance)
            .joinedload(UsecaseAreaRelevance.source_usecase)
    ).get(area_id)