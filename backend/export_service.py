# backend/export_service.py
import json
from datetime import datetime
import traceback # Added for export_area_to_markdown
from sqlalchemy.orm import joinedload, selectinload # Added selectinload
from .db import SessionLocal
from .models import User, Area, ProcessStep, UseCase, UsecaseAreaRelevance, UsecaseStepRelevance, UsecaseUsecaseRelevance

def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def export_database_to_json_string():
    session = SessionLocal()
    try:
        export_data = {
            "metadata": {
                "export_date": datetime.utcnow().isoformat(),
                "version": "1.0"
            },
            "data": {}
        }

        users = session.query(User).all()
        export_data["data"]["users"] = [
            {"id": u.id, "username": u.username, "created_at": u.created_at}
            for u in users
        ]

        areas = session.query(Area).all()
        export_data["data"]["areas"] = [
            {"id": a.id, "name": a.name, "description": a.description, "created_at": a.created_at}
            for a in areas
        ]

        process_steps = session.query(ProcessStep).all()
        export_data["data"]["process_steps"] = [
            {
                "id": ps.id, "bi_id": ps.bi_id, "name": ps.name, "area_id": ps.area_id,
                "step_description": ps.step_description, "raw_content": ps.raw_content,
                "summary": ps.summary, "vision_statement": ps.vision_statement,
                "in_scope": ps.in_scope, "out_of_scope": ps.out_of_scope,
                "interfaces_text": ps.interfaces_text, "what_is_actually_done": ps.what_is_actually_done,
                "pain_points": ps.pain_points, "targets_text": ps.targets_text,
                "created_at": ps.created_at, "updated_at": ps.updated_at
            } for ps in process_steps
        ]

        use_cases = session.query(UseCase).all()
        export_data["data"]["use_cases"] = [
            {
                "id": uc.id, "bi_id": uc.bi_id, "name": uc.name,
                "process_step_id": uc.process_step_id, "priority": uc.priority,
                "raw_content": uc.raw_content, "summary": uc.summary, "inspiration": uc.inspiration,
                "wave": uc.wave, "effort_level": uc.effort_level, "status": uc.status,
                "business_problem_solved": uc.business_problem_solved,
                "target_solution_description": uc.target_solution_description,
                "technologies_text": uc.technologies_text, "requirements": uc.requirements,
                "relevants_text": uc.relevants_text,
                "reduction_time_transfer": uc.reduction_time_transfer,
                "reduction_time_launches": uc.reduction_time_launches,
                "reduction_costs_supply": uc.reduction_costs_supply,
                "quality_improvement_quant": uc.quality_improvement_quant,
                "ideation_notes": uc.ideation_notes, "further_ideas": uc.further_ideas,
                "effort_quantification": uc.effort_quantification,
                "potential_quantification": uc.potential_quantification,
                "dependencies_text": uc.dependencies_text,
                "contact_persons_text": uc.contact_persons_text,
                "related_projects_text": uc.related_projects_text,
                "created_at": uc.created_at, "updated_at": uc.updated_at
            } for uc in use_cases
        ]

        uar = session.query(UsecaseAreaRelevance).all()
        export_data["data"]["usecase_area_relevance"] = [
            {
                "id": r.id, "source_usecase_id": r.source_usecase_id,
                "target_area_id": r.target_area_id, "relevance_score": r.relevance_score,
                "relevance_content": r.relevance_content, "created_at": r.created_at, "updated_at": r.updated_at
            } for r in uar
        ]
        usr = session.query(UsecaseStepRelevance).all()
        export_data["data"]["usecase_step_relevance"] = [
            {
                "id": r.id, "source_usecase_id": r.source_usecase_id,
                "target_process_step_id": r.target_process_step_id, "relevance_score": r.relevance_score,
                "relevance_content": r.relevance_content, "created_at": r.created_at, "updated_at": r.updated_at
            } for r in usr
        ]
        uur = session.query(UsecaseUsecaseRelevance).all()
        export_data["data"]["usecase_usecase_relevance"] = [
            {
                "id": r.id, "source_usecase_id": r.source_usecase_id,
                "target_usecase_id": r.target_usecase_id, "relevance_score": r.relevance_score,
                "relevance_content": r.relevance_content, "created_at": r.created_at, "updated_at": r.updated_at
            } for r in uur
        ]

        return json.dumps(export_data, default=datetime_serializer, indent=2)

    except Exception as e:
        print(f"Error during database export: {e}")
        traceback.print_exc()
        return None
    finally:
        session.close()


def format_text_for_markdown(text_content):
    if not text_content:
        return "N/A"
    if '`' in text_content or '\n' in text_content:
        escaped_content = text_content.replace('`', '\\`')
        return f"```\n{escaped_content}\n```"
    return text_content

def export_area_to_markdown(area_id: int):
    session = SessionLocal()
    try:
        area = session.query(Area).options(
            selectinload(Area.process_steps)
            .selectinload(ProcessStep.use_cases)
        ).get(area_id)

        if not area:
            return None

        md_content = []
        md_content.append(f"# Area: {area.name}\n")
        if area.description:
            md_content.append(f"**Description:**\n{format_text_for_markdown(area.description)}\n")
        md_content.append(f"**Area ID:** {area.id}\n")
        md_content.append(f"**Created At:** {area.created_at.strftime('%Y-%m-%d %H:%M') if area.created_at else 'N/A'}\n")
        md_content.append("---\n")

        if not area.process_steps:
            md_content.append("No process steps found in this area.\n")
        else:
            md_content.append("## Process Steps\n")
            for step in sorted(area.process_steps, key=lambda s: s.name):
                md_content.append(f"### Process Step: {step.name}\n")
                md_content.append(f"- **Step ID:** {step.id}")
                md_content.append(f"- **Step BI_ID:** {step.bi_id}")
                if step.step_description:
                    md_content.append(f"- **Description:** {format_text_for_markdown(step.step_description)}")
                if step.vision_statement:
                    md_content.append(f"- **Vision:** {format_text_for_markdown(step.vision_statement)}")
                if step.what_is_actually_done:
                    md_content.append(f"- **What's Done:** {format_text_for_markdown(step.what_is_actually_done)}")
                if step.in_scope:
                    md_content.append(f"- **In Scope:** {format_text_for_markdown(step.in_scope)}")
                if step.out_of_scope:
                    md_content.append(f"- **Out of Scope:** {format_text_for_markdown(step.out_of_scope)}")
                if step.pain_points:
                    md_content.append(f"- **Pain Points:** {format_text_for_markdown(step.pain_points)}")
                if step.targets_text:
                    md_content.append(f"- **Targets:** {format_text_for_markdown(step.targets_text)}")
                if step.summary:
                    md_content.append(f"- **Summary:** {format_text_for_markdown(step.summary)}")
                if step.raw_content:
                    md_content.append(f"- **Raw Content:** {format_text_for_markdown(step.raw_content)}")

                md_content.append("\n#### Use Cases for this Step\n")
                if not step.use_cases:
                    md_content.append("_No use cases found for this process step._\n")
                else:
                    for uc in sorted(step.use_cases, key=lambda u: u.name):
                        md_content.append(f"##### Use Case: {uc.name}\n")
                        md_content.append(f"- **UC ID:** {uc.id}")
                        md_content.append(f"- **UC BI_ID:** {uc.bi_id}")
                        priority_map = {1: "High", 2: "Medium", 3: "Low", 4: "Waiting List"}
                        md_content.append(f"- **Priority:** {priority_map.get(uc.priority, 'N/A')}")
                        
                        if uc.wave: md_content.append(f"- **Wave:** {uc.wave}")
                        if uc.status: md_content.append(f"- **Status:** {uc.status}")
                        if uc.effort_level: md_content.append(f"- **Effort Level:** {uc.effort_level}")

                        text_fields_uc = {
                            "Business Problem Solved": uc.business_problem_solved,
                            "Target/Solution Description": uc.target_solution_description,
                            "Technologies": uc.technologies_text,
                            "Requirements": uc.requirements,
                            "Relevants (Tags)": uc.relevants_text,
                            "Ideation Notes": uc.ideation_notes,
                            "Further Ideas": uc.further_ideas,
                            "Effort Quantification": uc.effort_quantification,
                            "Potential Quantification": uc.potential_quantification,
                            "Dependencies": uc.dependencies_text,
                            "Contact Persons": uc.contact_persons_text,
                            "Related Projects": uc.related_projects_text,
                            "Summary": uc.summary,
                            "Inspiration": uc.inspiration,
                            "Raw Content": uc.raw_content,
                        }
                        for label, value in text_fields_uc.items():
                            if value:
                                md_content.append(f"- **{label}:** {format_text_for_markdown(value)}")
                        
                        quant_fields_uc = {
                            "Time Reduction (Transfer)": uc.reduction_time_transfer,
                            "Time Reduction (Launches)": uc.reduction_time_launches,
                            "Cost Reduction (Supply)": uc.reduction_costs_supply,
                            "Quality Improvement": uc.quality_improvement_quant,
                        }
                        for label, value in quant_fields_uc.items():
                            if value:
                                md_content.append(f"- **{label}:** {value}")

                        md_content.append("\n") 
                md_content.append("---\n") 
        
        return "".join(md_content)
    except Exception as e:
        print(f"Error exporting area {area_id} to markdown: {e}")
        traceback.print_exc()
        return None
    finally:
        SessionLocal.remove()