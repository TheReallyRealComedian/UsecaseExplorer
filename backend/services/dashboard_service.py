# backend/services/dashboard_service.py
from sqlalchemy.orm import Session
from sqlalchemy import func
from ..models import Area, ProcessStep, UseCase

def get_dashboard_stats(db_session: Session):
    """
    Retrieves the count of total areas, steps, and use cases for the dashboard.
    """
    total_areas = db_session.query(func.count(Area.id)).scalar()
    total_process_steps = db_session.query(func.count(ProcessStep.id)).scalar()
    total_usecases = db_session.query(func.count(UseCase.id)).scalar()

    return {
        "total_areas": total_areas,
        "total_steps": total_process_steps,
        "total_usecases": total_usecases,
    }