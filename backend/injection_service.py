# backend/injection_service.py
import json
import traceback
from sqlalchemy.exc import IntegrityError
from .db import SessionLocal # CHANGED
from .models import Area, ProcessStep, UseCase 

def process_area_file(file_stream):
    """
    Processes an uploaded JSON file stream to add new Areas to the database.

    Args:
        file_stream: A file-like object containing the JSON data.

    Returns:
        A dictionary containing processing results.
    """
    session = SessionLocal()
    added_count = 0
    skipped_count = 0
    duplicates = []
    message = ""
    success = False

    try:
        print("Processing area file") # Debug log
        try:
            data = json.load(file_stream)
        except UnicodeDecodeError:
            file_stream.seek(0)
            data = json.loads(file_stream.read().decode('utf-8'))

        if not isinstance(data, list):
            raise ValueError("Invalid JSON format: Top level must be a list.")

        existing_names = {name[0] for name in session.query(Area.name).all()}

        for item in data:
            if not (isinstance(item, dict) and
                    'name' in item and
                    isinstance(item['name'], str) and
                    item['name'].strip()):
                skipped_count += 1
                continue

            area_name = item['name'].strip()
            description = item.get('description')

            if description is not None and not isinstance(description, str):
                description = None

            if area_name in existing_names:
                if area_name not in duplicates:
                    duplicates.append(area_name)
                skipped_count += 1
            else:
                new_area = Area(
                    name=area_name,
                    description=description
                )
                session.add(new_area)
                existing_names.add(area_name)
                added_count += 1

        session.commit()
        success = True

        if added_count == 0 and skipped_count > 0:
            message = "Processing complete. No new areas were added."
            if duplicates:
                message += f" {len(duplicates)} duplicate name(s) found."
        elif added_count > 0 and skipped_count == 0:
            message = f"Successfully added {added_count} new area(s)."
        elif added_count > 0 or skipped_count > 0 or duplicates: 
             message = f"Processing complete. Added: {added_count}, Skipped: {skipped_count}."
             if duplicates:
                message += f" Duplicate name(s) found: {len(duplicates)}."
        else: 
            message = "Processing complete. No data found or processed in the file."


    except json.JSONDecodeError:
        print("JSON Decode Error in process_area_file") 
        session.rollback()
        success = False
        message = "Invalid JSON format in the uploaded file."
        added_count = 0
        skipped_count = 0
        duplicates = []
    except ValueError as ve: 
        session.rollback()
        success = False
        message = f"Error: {ve}"
        added_count = 0
        skipped_count = 0
        duplicates = []
    except Exception as e:
        traceback.print_exc() 
        session.rollback()
        success = False
        message = f"An error occurred: {str(e)}"
        added_count = 0
        skipped_count = 0
        duplicates = []
    finally:
        SessionLocal.remove()

    return {
        "success": success,
        "message": message,
        "added_count": added_count,
        "skipped_count": skipped_count,
        "duplicates": duplicates
    }


def process_step_file(file_stream):
    """
    Processes an uploaded JSON file stream to add new Process Steps.

    Args:
        file_stream: A file-like object containing the JSON data.

    Returns:
        A dictionary containing processing results.
    """
    session = SessionLocal()
    added_count = 0
    skipped_invalid_format = 0
    skipped_duplicate_bi_id = 0
    skipped_missing_area = 0
    duplicates_bi_ids = []
    missing_area_names = []
    message = ""
    success = False

    try:
        print("Processing step file") 
        area_lookup = {
            area.name: area.id for area in session.query(Area.name, Area.id).all()
        }
        existing_bi_ids = {
            step.bi_id for step in session.query(ProcessStep.bi_id).all()
        }

        try:
            data = json.load(file_stream)
        except UnicodeDecodeError:
            file_stream.seek(0)
            data = json.loads(file_stream.read().decode('utf-8'))

        if not isinstance(data, list):
            raise ValueError("Invalid JSON format: Top level must be a list.")

        for item in data:
            if not (isinstance(item, dict) and
                    all(k in item for k in ('bi_id', 'name', 'area_name')) and
                    isinstance(item['bi_id'], str) and item['bi_id'].strip() and
                    isinstance(item['name'], str) and item['name'].strip() and
                    isinstance(item['area_name'], str) and item['area_name'].strip()):
                skipped_invalid_format += 1
                continue

            bi_id = item['bi_id'].strip()
            name = item['name'].strip()
            area_name = item['area_name'].strip()

            raw_content = item.get('raw_content')
            summary = item.get('summary')
            step_description = item.get('step_description')
            vision_statement = item.get('vision_statement')
            in_scope = item.get('in_scope')
            out_of_scope = item.get('out_of_scope')
            interfaces_text = item.get('interfaces_text')
            what_is_actually_done = item.get('what_is_actually_done')
            pain_points = item.get('pain_points')
            targets_text = item.get('targets_text')

            optional_text_fields = {
                "raw_content": raw_content, "summary": summary,
                "step_description": step_description, "vision_statement": vision_statement,
                "in_scope": in_scope, "out_of_scope": out_of_scope,
                "interfaces_text": interfaces_text, "what_is_actually_done": what_is_actually_done,
                "pain_points": pain_points, "targets_text": targets_text,
            }
            
            processed_optional_fields = {}
            for key, value in optional_text_fields.items():
                if value is not None and not isinstance(value, str):
                    print(f"Warning: Field '{key}' for BI_ID '{bi_id}' was not a string, setting to None. Value: {value}")
                    processed_optional_fields[key] = None
                else:
                    processed_optional_fields[key] = value

            if bi_id in existing_bi_ids:
                skipped_duplicate_bi_id += 1
                if bi_id not in duplicates_bi_ids:
                    duplicates_bi_ids.append(bi_id)
                continue

            if area_name not in area_lookup:
                skipped_missing_area += 1
                if area_name not in missing_area_names:
                    missing_area_names.append(area_name)
                continue

            area_id = area_lookup[area_name]
            new_step = ProcessStep(
                bi_id=bi_id, name=name, area_id=area_id,
                step_description=processed_optional_fields.get('step_description'),
                raw_content=processed_optional_fields.get('raw_content'),
                summary=processed_optional_fields.get('summary'),
                vision_statement=processed_optional_fields.get('vision_statement'),
                in_scope=processed_optional_fields.get('in_scope'),
                out_of_scope=processed_optional_fields.get('out_of_scope'),
                interfaces_text=processed_optional_fields.get('interfaces_text'),
                what_is_actually_done=processed_optional_fields.get('what_is_actually_done'),
                pain_points=processed_optional_fields.get('pain_points'),
                targets_text=processed_optional_fields.get('targets_text')
            )
            session.add(new_step)
            existing_bi_ids.add(bi_id)
            added_count += 1

        session.commit()
        success = True
        parts = []
        if added_count > 0:
            parts.append(f"Added: {added_count}")
        if skipped_invalid_format > 0:
            parts.append(f"Skipped (Invalid Format): {skipped_invalid_format}")
        if skipped_duplicate_bi_id > 0:
            parts.append(f"Skipped (Duplicate BI_ID): {skipped_duplicate_bi_id}")
        if skipped_missing_area > 0:
            parts.append(f"Skipped (Missing Area): {skipped_missing_area}")

        if not parts:
            message = "Processing complete. No data found or processed in the file."
        else:
            message = f"Processing complete. {', '.join(parts)}."

        if duplicates_bi_ids:
            message += f" Duplicates BI_IDs found: {', '.join(duplicates_bi_ids)}."
        if missing_area_names:
            message += f" Missing areas: {', '.join(missing_area_names)}."


    except json.JSONDecodeError:
        print("JSON Decode Error in process_step_file") 
        session.rollback()
        success = False
        message = "Invalid JSON format in the uploaded file."
        added_count = 0
        skipped_invalid_format = 0
        skipped_duplicate_bi_id = 0
        skipped_missing_area = 0
        duplicates_bi_ids = []
        missing_area_names = []
    except ValueError as ve:
        session.rollback()
        success = False
        message = f"Error: {ve}"
        added_count = 0
        skipped_invalid_format = 0
        skipped_duplicate_bi_id = 0
        skipped_missing_area = 0
        duplicates_bi_ids = []
        missing_area_names = []
    except Exception as e:
        traceback.print_exc() 
        session.rollback()
        success = False
        message = f"An error occurred: {str(e)}"
        added_count = 0
        skipped_invalid_format = 0
        skipped_duplicate_bi_id = 0
        skipped_missing_area = 0
        duplicates_bi_ids = []
        missing_area_names = []
    finally:
        SessionLocal.remove()

    return {
        "success": success,
        "message": message,
        "added_count": added_count,
        "skipped_count": skipped_invalid_format + skipped_duplicate_bi_id + skipped_missing_area,
        "skipped_invalid_format": skipped_invalid_format,
        "skipped_duplicate_bi_id": skipped_duplicate_bi_id,
        "skipped_missing_area": skipped_missing_area,
        "duplicates_bi_ids": duplicates_bi_ids,
        "missing_area_names": missing_area_names
    }


def process_usecase_file(file_stream):
    """
    Processes an uploaded JSON file stream to add new Use Cases.

    Args:
        file_stream: A file-like object containing the JSON data.

    Returns:
        A dictionary containing processing results.
    """
    session = SessionLocal()
    added_count = 0
    skipped_invalid_format = 0
    skipped_duplicate_uc_bi_id = 0
    skipped_missing_step = 0
    duplicate_uc_bi_ids = []
    missing_step_bi_ids = []
    message = ""
    success = False

    try:
        print("Processing use case file")
        step_lookup = {
            step.bi_id: step.id
            for step in session.query(ProcessStep.bi_id, ProcessStep.id).all()
        }
        existing_uc_bi_ids = {
            uc.bi_id for uc in session.query(UseCase.bi_id).all()
        }

        try:
            data = json.load(file_stream)
        except UnicodeDecodeError:
            file_stream.seek(0)
            data = json.loads(file_stream.read().decode('utf-8'))

        if not isinstance(data, list):
            raise ValueError("Invalid JSON format: Top level must be a list.")

        for item in data:
            # Validate required fields format and presence
            if not (isinstance(item, dict) and
                    all(k in item for k in ('bi_id', 'name', 'process_step_bi_id')) and
                    isinstance(item['bi_id'], str) and item['bi_id'].strip() and
                    isinstance(item['name'], str) and item['name'].strip() and
                    isinstance(item['process_step_bi_id'], str) and item['process_step_bi_id'].strip()):
                skipped_invalid_format += 1
                continue  # Skip if required fields are missing or empty or not strings

            uc_bi_id = item['bi_id'].strip()
            name = item['name'].strip()
            process_step_bi_id = item['process_step_bi_id'].strip()

            raw_content = item.get('raw_content')
            summary = item.get('summary')
            inspiration = item.get('inspiration')
            priority_str = item.get('priority')

            if raw_content is not None and not isinstance(raw_content, str):
                raw_content = None
            if summary is not None and not isinstance(summary, str):
                summary = None
            if inspiration is not None and not isinstance(inspiration, str):
                inspiration = None

            priority = None
            if priority_str is not None:
                try:
                    priority_val = int(priority_str)
                    if 1 <= priority_val <= 4:
                        priority = priority_val
                    else:
                        print(f"Skipping item with invalid priority value '{priority_str}': {item}")
                        skipped_invalid_format += 1
                        continue
                except ValueError:
                    print(f"Skipping item with non-integer priority '{priority_str}': {item}")
                    skipped_invalid_format += 1
                    continue
            
            # Extract New Fields
            wave = item.get('wave')
            effort_level = item.get('effort')
            status = item.get('status')
            business_problem_solved = item.get('BUSINESS PROBLEM SOLVED')
            target_solution_description = item.get('TARGET / SOLUTION DESCRIPTION')
            technologies_text = item.get('TECHNOLOGIES')
            requirements = item.get('REQUIREMENTS')
            relevants_text = item.get('RELEVANTS')
            reduction_time_transfer = item.get('REDUCTION TIME FOR PRODUCT TRANSFER')
            reduction_time_launches = item.get('REDUCTION TIME FOR PRODUCT LAUNCHES')
            reduction_costs_supply = item.get('REDUCTION OF TOTAL COSTS OF SUPPLY')
            quality_improvement_quant = item.get('QUALITY IMPROVEMENT')
            ideation_notes = item.get('Original notes from ideation')
            further_ideas = item.get('Further ideas/ input (Stickers, pictures, files, ...)')
            effort_quantification = item.get('Effort description & quantification')
            potential_quantification = item.get('Potential description & quantification')
            dependencies_text = item.get('Redundancies & Dependencies')
            contact_persons_text = item.get('Contact persons for further detailing')
            related_projects_text = item.get('Related ongoing projects (incl. contact person)')

            # Validate new text fields (ensure string or None)
            if wave is not None and not isinstance(wave, str): wave = None
            if effort_level is not None and not isinstance(effort_level, str): effort_level = None
            if status is not None and not isinstance(status, str): status = None
            if business_problem_solved is not None and not isinstance(business_problem_solved, str): business_problem_solved = None
            if target_solution_description is not None and not isinstance(target_solution_description, str): target_solution_description = None
            if technologies_text is not None and not isinstance(technologies_text, str): technologies_text = None
            if requirements is not None and not isinstance(requirements, str): requirements = None
            if relevants_text is not None and not isinstance(relevants_text, str): relevants_text = None
            if reduction_time_transfer is not None and not isinstance(reduction_time_transfer, str): reduction_time_transfer = None
            if reduction_time_launches is not None and not isinstance(reduction_time_launches, str): reduction_time_launches = None
            if reduction_costs_supply is not None and not isinstance(reduction_costs_supply, str): reduction_costs_supply = None
            if quality_improvement_quant is not None and not isinstance(quality_improvement_quant, str): quality_improvement_quant = None
            if ideation_notes is not None and not isinstance(ideation_notes, str): ideation_notes = None
            if further_ideas is not None and not isinstance(further_ideas, str): further_ideas = None
            if effort_quantification is not None and not isinstance(effort_quantification, str): effort_quantification = None
            if potential_quantification is not None and not isinstance(potential_quantification, str): potential_quantification = None
            if dependencies_text is not None and not isinstance(dependencies_text, str): dependencies_text = None
            if contact_persons_text is not None and not isinstance(contact_persons_text, str): contact_persons_text = None
            if related_projects_text is not None and not isinstance(related_projects_text, str): related_projects_text = None

            if uc_bi_id in existing_uc_bi_ids:
                skipped_duplicate_uc_bi_id += 1
                if uc_bi_id not in duplicate_uc_bi_ids:
                    duplicate_uc_bi_ids.append(uc_bi_id)
                continue

            if process_step_bi_id not in step_lookup:
                skipped_missing_step += 1
                if process_step_bi_id not in missing_step_bi_ids:
                    missing_step_bi_ids.append(process_step_bi_id)
                continue

            process_step_id = step_lookup[process_step_bi_id]
            
            new_uc = UseCase(
                bi_id=uc_bi_id, 
                name=name, 
                process_step_id=process_step_id,
                priority=priority, 
                raw_content=raw_content,
                summary=summary, 
                inspiration=inspiration,
                # New fields
                wave=wave,
                effort_level=effort_level,
                status=status,
                business_problem_solved=business_problem_solved,
                target_solution_description=target_solution_description,
                technologies_text=technologies_text,
                requirements=requirements,
                relevants_text=relevants_text,
                reduction_time_transfer=reduction_time_transfer,
                reduction_time_launches=reduction_time_launches,
                reduction_costs_supply=reduction_costs_supply,
                quality_improvement_quant=quality_improvement_quant,
                ideation_notes=ideation_notes,
                further_ideas=further_ideas,
                effort_quantification=effort_quantification,
                potential_quantification=potential_quantification,
                dependencies_text=dependencies_text,
                contact_persons_text=contact_persons_text,
                related_projects_text=related_projects_text,
                # LLM comments
                llm_comment_1=None,
                llm_comment_2=None,
                llm_comment_3=None,
                llm_comment_4=None,
                llm_comment_5=None,
            )
            session.add(new_uc)
            existing_uc_bi_ids.add(uc_bi_id)
            added_count += 1

        session.commit()
        success = True
        parts = []
        if added_count > 0:
            parts.append(f"Added: {added_count}")
        if skipped_invalid_format > 0:
            parts.append(f"Skipped (Invalid Format/Priority): {skipped_invalid_format}")
        if skipped_duplicate_uc_bi_id > 0:
            parts.append(f"Skipped (Duplicate UC BI_ID): {skipped_duplicate_uc_bi_id}")
        if skipped_missing_step > 0:
            parts.append(f"Skipped (Missing Step): {skipped_missing_step}")

        if not parts:
            message = "Processing complete. No Use Case data found or processed."
        else:
            message = f"Processing complete. {', '.join(parts)}."

        if duplicate_uc_bi_ids:
            message += f" Duplicate UC IDs: {', '.join(duplicate_uc_bi_ids)}."
        if missing_step_bi_ids:
            message += f" Missing Step IDs: {', '.join(missing_step_bi_ids)}."

    except json.JSONDecodeError:
        print("JSON Decode Error in process_usecase_file")
        session.rollback()
        success = False
        message = "Invalid JSON format in the uploaded file."
    except ValueError as ve:
        session.rollback()
        success = False
        message = f"Error: {ve}"
    except Exception as e:
        traceback.print_exc()
        session.rollback()
        success = False
        message = f"An error occurred: {str(e)}"
    finally:
        if session.is_active: # Ensure session is active before trying to remove, though remove should handle it
             SessionLocal.remove()


    return {
        "success": success,
        "message": message,
        "added_count": added_count,
        "skipped_count": skipped_invalid_format + skipped_duplicate_uc_bi_id + skipped_missing_step,
        "skipped_invalid_format": skipped_invalid_format,
        "skipped_duplicate_uc_bi_id": skipped_duplicate_uc_bi_id,
        "skipped_missing_step": skipped_missing_step,
        "duplicate_uc_bi_ids": duplicate_uc_bi_ids,
        "missing_step_bi_ids": missing_step_bi_ids
    }