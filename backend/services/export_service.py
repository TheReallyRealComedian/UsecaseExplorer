# backend/services/export_service.py
import json
from sqlalchemy.orm import class_mapper, joinedload, selectinload
from ..db import SessionLocal
from ..models import Base, Area, ProcessStep, UseCase

def datetime_serializer(obj):
    """JSON serializer for datetime objects."""
    if hasattr(obj, 'isoformat'):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def export_database_to_json_string():
    """Exports the entire database to a JSON string."""
    session = SessionLocal()
    try:
        data_to_export = {"data": {}}
        for model in Base.registry.mappers:
            model_class = model.class_
            table_name = model.mapped_table.name
            query = session.query(model_class).all()
            
            serialized_data = []
            for instance in query:
                columns = [c.key for c in class_mapper(instance.__class__).columns]
                instance_dict = {c: getattr(instance, c) for c in columns}
                serialized_data.append(instance_dict)
                
            data_to_export["data"][table_name] = serialized_data

        return json.dumps(data_to_export, default=datetime_serializer, indent=4)
    except Exception as e:
        print(f"Error exporting database to JSON: {e}")
        return None
    finally:
        session.close()

def export_area_to_markdown(area_id: int):
    """Exports a single area and its children to a Markdown string."""
    session = SessionLocal()
    try:
        area = session.query(Area).options(
            joinedload(Area.process_steps).selectinload(ProcessStep.use_cases)
        ).get(area_id)
        
        if not area:
            return None

        md_lines = [f"# Area: {area.name}\n"]
        if area.description:
            md_lines.append(f"**Description:**\n{area.description}\n")

        md_lines.append("## Process Steps\n")
        if not area.process_steps:
            md_lines.append("*No process steps in this area.*\n")
        else:
            for step in sorted(area.process_steps, key=lambda s: s.name):
                md_lines.append(f"### {step.name} (BI_ID: {step.bi_id})\n")
                if step.step_description:
                    md_lines.append(f"**Description:** {step.step_description}\n")
                if step.vision_statement:
                    md_lines.append(f"**Vision:** {step.vision_statement}\n")
                
                md_lines.append("#### Use Cases\n")
                if not step.use_cases:
                    md_lines.append("*No use cases for this step.*\n")
                else:
                    for uc in sorted(step.use_cases, key=lambda u: u.name):
                        md_lines.append(f"- **{uc.name}** (BI_ID: {uc.bi_id})")
                        if uc.summary:
                            md_lines.append(f"  - Summary: {uc.summary}")
                md_lines.append("\n---\n")

        return "\n".join(md_lines)
    except Exception as e:
        print(f"Error exporting area {area_id} to Markdown: {e}")
        return None
    finally:
        session.close()