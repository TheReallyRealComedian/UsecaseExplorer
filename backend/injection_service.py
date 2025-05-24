# backend/injection_service.py
import json
import traceback
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from .db import SessionLocal
from .models import (
    Base, User, Area, ProcessStep, UseCase,
    UsecaseAreaRelevance, UsecaseStepRelevance, UsecaseUsecaseRelevance,
    ProcessStepProcessStepRelevance
)

def process_area_file(file_stream):
    session = SessionLocal()
    added_count = 0
    updated_count = 0
    skipped_count = 0
    duplicates_not_updated = []
    message = ""
    success = False

    try:
        print("Processing area file (with update logic)")
        try:
            data = json.load(file_stream)
        except UnicodeDecodeError:
            file_stream.seek(0)
            data = json.loads(file_stream.read().decode('utf-8'))

        if not isinstance(data, list):
            raise ValueError("Invalid JSON format: Top level must be a list.")

        for item in data:
            if not (isinstance(item, dict) and
                    'name' in item and
                    isinstance(item['name'], str) and
                    item['name'].strip()):
                skipped_count += 1
                continue

            area_name = item['name'].strip()
            description_from_json = item.get('description')
            if description_from_json is not None:
                if not isinstance(description_from_json, str):
                    description_from_json = None
                else:
                    description_from_json = description_from_json.strip()
                    if not description_from_json: 
                        description_from_json = None


            existing_area = session.query(Area).filter_by(name=area_name).first()
            item_updated = False

            if existing_area:
                if description_from_json and \
                   (existing_area.description is None or existing_area.description == ''):
                    existing_area.description = description_from_json
                    item_updated = True

                if item_updated:
                    updated_count += 1
                else:
                    if area_name not in duplicates_not_updated:
                        duplicates_not_updated.append(area_name)
                    skipped_count +=1 
            else:
                new_area = Area(
                    name=area_name,
                    description=description_from_json if description_from_json else None
                )
                session.add(new_area)
                added_count += 1

        session.commit()
        success = True

        parts = []
        if added_count > 0: parts.append(f"Added: {added_count}")
        if updated_count > 0: parts.append(f"Updated: {updated_count}")
        if skipped_count > 0: parts.append(f"Skipped: {skipped_count}")

        if not parts:
            message = "Processing complete. No data found or processed in the file."
        else:
            message = f"Processing complete. {', '.join(parts)}."

        if duplicates_not_updated:
            message += f" Existing items not updated (no empty fields to fill or data matched): {len(duplicates_not_updated)}."

    except json.JSONDecodeError:
        print("JSON Decode Error in process_area_file")
        session.rollback()
        success = False
        message = "Invalid JSON format in the uploaded file."
        added_count = 0
        updated_count = 0
        skipped_count = 0
        duplicates_not_updated = []
    except ValueError as ve:
        session.rollback()
        success = False
        message = f"Error: {ve}"
        added_count = 0
        updated_count = 0
        skipped_count = 0
        duplicates_not_updated = []
    except Exception as e:
        traceback.print_exc()
        session.rollback()
        success = False
        message = f"An error occurred: {str(e)}"
        added_count = 0
        updated_count = 0
        skipped_count = 0
        duplicates_not_updated = []
    finally:
        SessionLocal.remove()

    return {
        "success": success,
        "message": message,
        "added_count": added_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "duplicates_not_updated": duplicates_not_updated
    }


def process_step_file(file_stream):
    session = SessionLocal()
    added_count = 0
    updated_count = 0
    skipped_invalid_format = 0
    skipped_existing_no_update_count = 0 
    skipped_missing_area = 0
    bi_ids_existing_no_update = [] 
    missing_area_names = []
    message = ""
    success = False

    try:
        print("Processing step file (with update logic)")
        area_lookup = {
            area.name: area.id for area in session.query(Area.name, Area.id).all()
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

            existing_step = session.query(ProcessStep).filter_by(bi_id=bi_id).first()
            item_updated = False

            step_fields_from_json = {
                "name": name, 
                "step_description": item.get('step_description'),
                "raw_content": item.get('raw_content'),
                "summary": item.get('summary'),
                "vision_statement": item.get('vision_statement'),
                "in_scope": item.get('in_scope'),
                "out_of_scope": item.get('out_of_scope'),
                "interfaces_text": item.get('interfaces_text'),
                "what_is_actually_done": item.get('what_is_actually_done'),
                "pain_points": item.get('pain_points'),
                "targets_text": item.get('targets_text'),
            }

            for field_name, json_value in step_fields_from_json.items():
                if json_value is not None:
                    if not isinstance(json_value, str):
                        print(f"Warning: Field '{field_name}' for BI_ID '{bi_id}' was not a string, setting to None. Value: {json_value}")
                        step_fields_from_json[field_name] = None
                    else:
                        stripped_value = json_value.strip()
                        step_fields_from_json[field_name] = stripped_value if stripped_value else None


            if existing_step:
                for field_name, json_value in step_fields_from_json.items():
                    db_value = getattr(existing_step, field_name)
                    if json_value and (db_value is None or db_value == ''):
                        setattr(existing_step, field_name, json_value)
                        item_updated = True
                
                if area_name in area_lookup and existing_step.area_id != area_lookup[area_name]:
                    print(f"Step BI_ID {bi_id} has area_name '{area_name}' in JSON, different from current. Area re-association logic not fully implemented here for updates.")
                    pass 

                if item_updated:
                    updated_count += 1
                else:
                    skipped_existing_no_update_count += 1
                    if bi_id not in bi_ids_existing_no_update:
                        bi_ids_existing_no_update.append(bi_id)
            else:
                if area_name not in area_lookup:
                    skipped_missing_area += 1
                    if area_name not in missing_area_names:
                        missing_area_names.append(area_name)
                    continue

                area_id = area_lookup[area_name]
                new_step_data = {
                    "bi_id": bi_id,
                    "area_id": area_id,
                }
                for field_name, json_value in step_fields_from_json.items():
                    new_step_data[field_name] = json_value 

                new_step = ProcessStep(**new_step_data)
                session.add(new_step)
                added_count += 1

        session.commit()
        success = True
        parts = []
        if added_count > 0: parts.append(f"Added: {added_count}")
        if updated_count > 0: parts.append(f"Updated: {updated_count}")
        if skipped_invalid_format > 0: parts.append(f"Skipped (Invalid Format): {skipped_invalid_format}")
        if skipped_existing_no_update_count > 0: parts.append(f"Skipped (Existing, No Update): {skipped_existing_no_update_count}")
        if skipped_missing_area > 0: parts.append(f"Skipped (Missing Area): {skipped_missing_area}")

        if not parts:
            message = "Processing complete. No data found or processed in the file."
        else:
            message = f"Processing complete. {', '.join(parts)}."

        if bi_ids_existing_no_update:
            message += f" Existing BI_IDs not updated (no empty fields to fill or data matched): {len(bi_ids_existing_no_update)}."
        if missing_area_names:
            message += f" Missing areas for new steps: {', '.join(missing_area_names)}."

    except json.JSONDecodeError:
        print("JSON Decode Error in process_step_file")
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
        if not success:
            added_count = 0
            updated_count = 0
            skipped_invalid_format = 0
            skipped_existing_no_update_count = 0
            skipped_missing_area = 0
            bi_ids_existing_no_update = []
            missing_area_names = []
        SessionLocal.remove()

    return {
        "success": success,
        "message": message,
        "added_count": added_count,
        "updated_count": updated_count,
        "skipped_count": skipped_invalid_format + skipped_existing_no_update_count + skipped_missing_area,
        "skipped_invalid_format": skipped_invalid_format,
        "skipped_existing_no_update_count": skipped_existing_no_update_count, 
        "skipped_missing_area": skipped_missing_area,
        "bi_ids_existing_no_update": bi_ids_existing_no_update, 
        "missing_area_names": missing_area_names
    }

def process_usecase_file(file_stream):
    session = SessionLocal()
    added_count = 0
    updated_count = 0
    skipped_invalid_format = 0
    skipped_existing_no_update_uc_bi_id_count = 0 
    skipped_missing_step = 0
    uc_bi_ids_existing_no_update = [] 
    missing_step_bi_ids = []
    message = ""
    success = False

    json_to_model_map = {
        'name': 'name',
        'priority': 'priority',
        'raw_content': 'raw_content',
        'summary': 'summary',
        'inspiration': 'inspiration',
        'wave': 'wave',
        'effort': 'effort_level', 
        'status': 'status',
        'BUSINESS PROBLEM SOLVED': 'business_problem_solved',
        'TARGET / SOLUTION DESCRIPTION': 'target_solution_description',
        'TECHNOLOGIES': 'technologies_text',
        'REQUIREMENTS': 'requirements',
        'RELEVANTS': 'relevants_text',
        'REDUCTION TIME FOR PRODUCT TRANSFER': 'reduction_time_transfer',
        'REDUCTION TIME FOR PRODUCT LAUNCHES': 'reduction_time_launches',
        'REDUCTION OF TOTAL COSTS OF SUPPLY': 'reduction_costs_supply',
        'QUALITY IMPROVEMENT': 'quality_improvement_quant',
        'Original notes from ideation': 'ideation_notes',
        'Further ideas/ input (Stickers, pictures, files, ...)': 'further_ideas',
        'Effort description & quantification': 'effort_quantification',
        'Potential description & quantification': 'potential_quantification',
        'Redundancies & Dependencies': 'dependencies_text',
        'Contact persons for further detailing': 'contact_persons_text',
        'Related ongoing projects (incl. contact person)': 'related_projects_text',
    }


    try:
        print("Processing use case file (with update logic)")
        step_lookup = {
            step.bi_id: step.id
            for step in session.query(ProcessStep.bi_id, ProcessStep.id).all()
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
                    all(k in item for k in ('bi_id', 'name', 'process_step_bi_id')) and
                    isinstance(item['bi_id'], str) and item['bi_id'].strip() and
                    isinstance(item['name'], str) and item['name'].strip() and
                    isinstance(item['process_step_bi_id'], str) and item['process_step_bi_id'].strip()):
                skipped_invalid_format += 1
                continue

            uc_bi_id = item['bi_id'].strip()
            process_step_bi_id_from_json = item['process_step_bi_id'].strip()

            existing_usecase = session.query(UseCase).filter_by(bi_id=uc_bi_id).first()
            item_updated = False

            uc_fields_from_json = {}
            for json_key, model_attr in json_to_model_map.items():
                json_value = item.get(json_key)
                if model_attr == 'priority':
                    priority_val = None
                    if json_value is not None:
                        try:
                            priority_int = int(json_value)
                            if 1 <= priority_int <= 4:
                                priority_val = priority_int
                            else:
                                print(f"Warning: Invalid priority value '{json_value}' for UC BI_ID '{uc_bi_id}'. Skipping priority.")
                        except ValueError:
                            print(f"Warning: Non-integer priority '{json_value}' for UC BI_ID '{uc_bi_id}'. Skipping priority.")
                    uc_fields_from_json[model_attr] = priority_val
                elif isinstance(json_value, str):
                    stripped_value = json_value.strip()
                    uc_fields_from_json[model_attr] = stripped_value if stripped_value else None
                elif json_value is not None : 
                     print(f"Warning: Field '{model_attr}' (from JSON key '{json_key}') for UC BI_ID '{uc_bi_id}' was not a string, setting to None. Value: {json_value}")
                     uc_fields_from_json[model_attr] = None
                else: 
                    uc_fields_from_json[model_attr] = None
            
            if 'name' not in uc_fields_from_json :
                 name_val = item['name'].strip()
                 uc_fields_from_json['name'] = name_val if name_val else None


            if existing_usecase:
                for model_attr, json_val in uc_fields_from_json.items():
                    db_value = getattr(existing_usecase, model_attr)
                    if model_attr == 'priority':
                        if json_val is not None and db_value is None : 
                            setattr(existing_usecase, model_attr, json_val)
                            item_updated = True
                    elif json_val and (db_value is None or db_value == ''):
                        setattr(existing_usecase, model_attr, json_val)
                        item_updated = True
                
                if process_step_bi_id_from_json in step_lookup and existing_usecase.process_step_id != step_lookup[process_step_bi_id_from_json]:
                    print(f"UC BI_ID {uc_bi_id} has process_step_bi_id '{process_step_bi_id_from_json}' in JSON, different from current. Step re-association logic not fully implemented here for updates.")
                    pass


                if item_updated:
                    updated_count += 1
                else:
                    skipped_existing_no_update_uc_bi_id_count += 1
                    if uc_bi_id not in uc_bi_ids_existing_no_update:
                        uc_bi_ids_existing_no_update.append(uc_bi_id)
            else:
                if process_step_bi_id_from_json not in step_lookup:
                    skipped_missing_step += 1
                    if process_step_bi_id_from_json not in missing_step_bi_ids:
                        missing_step_bi_ids.append(process_step_bi_id_from_json)
                    continue

                process_step_id = step_lookup[process_step_bi_id_from_json]
                new_uc_data = {
                    "bi_id": uc_bi_id,
                    "process_step_id": process_step_id,
                    "llm_comment_1": None, "llm_comment_2": None, "llm_comment_3": None,
                    "llm_comment_4": None, "llm_comment_5": None,
                }
                for model_attr, json_val in uc_fields_from_json.items():
                     new_uc_data[model_attr] = json_val 

                new_uc = UseCase(**new_uc_data)
                session.add(new_uc)
                added_count += 1

        session.commit()
        success = True
        parts = []
        if added_count > 0: parts.append(f"Added: {added_count}")
        if updated_count > 0: parts.append(f"Updated: {updated_count}")
        if skipped_invalid_format > 0: parts.append(f"Skipped (Invalid Format/Priority): {skipped_invalid_format}")
        if skipped_existing_no_update_uc_bi_id_count > 0: parts.append(f"Skipped (Existing UC, No Update): {skipped_existing_no_update_uc_bi_id_count}")
        if skipped_missing_step > 0: parts.append(f"Skipped (Missing Step): {skipped_missing_step}")

        if not parts:
            message = "Processing complete. No Use Case data found or processed."
        else:
            message = f"Processing complete. {', '.join(parts)}."

        if uc_bi_ids_existing_no_update:
            message += f" Existing UC BI_IDs not updated (no empty fields to fill or data matched): {len(uc_bi_ids_existing_no_update)}."
        if missing_step_bi_ids:
            message += f" Missing Step BI_IDs for new UCs: {', '.join(missing_step_bi_ids)}."

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
        if not success: 
            added_count = 0
            updated_count = 0
            skipped_invalid_format = 0
            skipped_existing_no_update_uc_bi_id_count = 0
            skipped_missing_step = 0
            uc_bi_ids_existing_no_update = []
            missing_step_bi_ids = []
        SessionLocal.remove()

    return {
        "success": success,
        "message": message,
        "added_count": added_count,
        "updated_count": updated_count,
        "skipped_count": skipped_invalid_format + skipped_existing_no_update_uc_bi_id_count + skipped_missing_step,
        "skipped_invalid_format": skipped_invalid_format,
        "skipped_existing_no_update_uc_bi_id_count": skipped_existing_no_update_uc_bi_id_count,
        "skipped_missing_step": skipped_missing_step,
        "uc_bi_ids_existing_no_update": uc_bi_ids_existing_no_update, 
        "missing_step_bi_ids": missing_step_bi_ids
    }

# NEW FUNCTION: process_ps_ps_relevance_file
def process_ps_ps_relevance_file(file_stream):
    session = SessionLocal()
    added_count = 0
    skipped_invalid_format = 0
    skipped_existing_link = 0
    skipped_missing_step = 0
    skipped_self_link = 0
    skipped_errors = []
    message = ""
    success = False

    try:
        print("Processing process step relevance links file...")
        step_lookup = {
            step.bi_id: step.id
            for step in session.query(ProcessStep.bi_id, ProcessStep.id).all()
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
                    all(k in item for k in ('source_process_step_bi_id', 'target_process_step_bi_id', 'relevance_score')) and
                    isinstance(item['source_process_step_bi_id'], str) and item['source_process_step_bi_id'].strip() and
                    isinstance(item['target_process_step_bi_id'], str) and item['target_process_step_bi_id'].strip()):
                skipped_invalid_format += 1
                skipped_errors.append(f"Invalid format for item: {item.get('source_process_step_bi_id', 'N/A')} -> {item.get('target_process_step_bi_id', 'N/A')}")
                continue

            source_bi_id = item['source_process_step_bi_id'].strip()
            target_bi_id = item['target_process_step_bi_id'].strip()
            relevance_score_raw = item['relevance_score']
            relevance_content = item.get('relevance_content')

            # Convert content to string and handle empty
            if relevance_content is not None:
                if not isinstance(relevance_content, str):
                    print(f"Warning: Relevance content for {source_bi_id} -> {target_bi_id} was not a string, setting to None. Value: {relevance_content}")
                    relevance_content = None
                else:
                    stripped_content = relevance_content.strip()
                    relevance_content = stripped_content if stripped_content else None


            if source_bi_id == target_bi_id:
                skipped_self_link += 1
                skipped_errors.append(f"Self-relevance link: {source_bi_id} -> {target_bi_id}")
                continue

            source_id = step_lookup.get(source_bi_id)
            target_id = step_lookup.get(target_bi_id)

            if source_id is None:
                skipped_missing_step += 1
                skipped_errors.append(f"Missing source step BI_ID: {source_bi_id}")
                continue
            if target_id is None:
                skipped_missing_step += 1
                skipped_errors.append(f"Missing target step BI_ID: {target_bi_id}")
                continue

            try:
                score = int(relevance_score_raw)
                if not (0 <= score <= 100):
                    skipped_invalid_format += 1
                    skipped_errors.append(f"Invalid score for {source_bi_id} -> {target_bi_id}: {relevance_score_raw}")
                    continue
            except (ValueError, TypeError):
                skipped_invalid_format += 1
                skipped_errors.append(f"Non-integer score for {source_bi_id} -> {target_bi_id}: {relevance_score_raw}")
                continue

            existing_link = session.query(ProcessStepProcessStepRelevance).filter_by(
                source_process_step_id=source_id,
                target_process_step_id=target_id
            ).first()

            if existing_link:
                skipped_existing_link += 1
                # You could add update logic here if desired, but for simplicity, we skip duplicates
                skipped_errors.append(f"Existing link skipped: {source_bi_id} -> {target_bi_id}")
                continue
            
            # Check for reverse link already existing to avoid inserting A->B and then B->A if only one direction is desired.
            # Your unique constraint (source, target) allows A->B and B->A to exist separately.
            # If you want to prevent both, you'd need more complex logic or a different constraint.
            # For now, we only check for exact duplicates (source=S, target=T).

            new_link = ProcessStepProcessStepRelevance(
                source_process_step_id=source_id,
                target_process_step_id=target_id,
                relevance_score=score,
                relevance_content=relevance_content
            )
            session.add(new_link)
            added_count += 1

        session.commit()
        success = True

        parts = []
        if added_count > 0: parts.append(f"Added: {added_count}")
        if skipped_existing_link > 0: parts.append(f"Skipped (Already Exists): {skipped_existing_link}")
        if skipped_self_link > 0: parts.append(f"Skipped (Self-Links): {skipped_self_link}")
        if skipped_missing_step > 0: parts.append(f"Skipped (Missing Steps): {skipped_missing_step}")
        if skipped_invalid_format > 0: parts.append(f"Skipped (Invalid Data): {skipped_invalid_format}")

        if not parts:
            message = "Processing complete. No process step relevance links found or processed."
        else:
            message = f"Processing complete. {', '.join(parts)}."

    except json.JSONDecodeError:
        print("JSON Decode Error in process_ps_ps_relevance_file")
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
        message = f"An unexpected error occurred: {str(e)}"
    finally:
        SessionLocal.remove()

    return {
        "success": success,
        "message": message,
        "added_count": added_count,
        "skipped_count": skipped_invalid_format + skipped_existing_link + skipped_missing_step + skipped_self_link,
        "skipped_invalid_format": skipped_invalid_format,
        "skipped_existing_link": skipped_existing_link,
        "skipped_missing_step": skipped_missing_step,
        "skipped_self_link": skipped_self_link,
        "skipped_errors": skipped_errors # Provide detailed skipped errors for debugging
    }

def import_database_from_json(file_stream, clear_existing_data=False):
    session = SessionLocal()
    try:
        data_to_import = json.load(file_stream)
        imported_data = data_to_import.get("data", {})

        if not imported_data:
            return {
                "success": False,
                "message": "No 'data' key found in JSON file or data is empty."
            }

        if clear_existing_data:
            print("Clearing existing data...")
            session.execute(text("TRUNCATE TABLE process_step_process_step_relevance RESTART IDENTITY CASCADE;"))
            session.execute(text("TRUNCATE TABLE usecase_usecase_relevance RESTART IDENTITY CASCADE;"))
            session.execute(text("TRUNCATE TABLE usecase_step_relevance RESTART IDENTITY CASCADE;"))
            session.execute(text("TRUNCATE TABLE usecase_area_relevance RESTART IDENTITY CASCADE;"))
            session.execute(text("TRUNCATE TABLE use_cases RESTART IDENTITY CASCADE;"))
            session.execute(text("TRUNCATE TABLE process_steps RESTART IDENTITY CASCADE;"))
            session.execute(text("TRUNCATE TABLE areas RESTART IDENTITY CASCADE;"))
            session.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE;"))
            session.commit() 
            print("Data cleared.")

        print("Importing Users...")
        if "users" in imported_data:
            for u_data in imported_data["users"]:
                user = User(username=u_data["username"])
                user.set_password("imported_default_password") # !!! CHANGE THIS !!!
                session.add(user)
        session.flush() 

        print("Importing Areas...")
        if "areas" in imported_data:
            for a_data in imported_data["areas"]:
                area = Area(
                    name=a_data["name"],
                    description=a_data.get("description")
                )
                session.add(area)
        session.flush()

        print("Importing Process Steps...")
        if "process_steps" in imported_data:
            for ps_data in imported_data["process_steps"]:
                # Assuming area_id in JSON refers to the new ID if cleared, or existing ID.
                # If using old_id -> new_id mapping, lookup would be needed here.
                area = session.query(Area).filter_by(id=ps_data["area_id"]).first() 
                if not area:
                    print(f"Warning: Area ID {ps_data['area_id']} for step '{ps_data['name']}' not found. Skipping step.")
                    continue
                
                step = ProcessStep(
                    bi_id=ps_data["bi_id"],
                    name=ps_data["name"],
                    area_id=area.id, # Use the looked-up area's ID
                    step_description=ps_data.get("step_description"),
                    raw_content=ps_data.get("raw_content"),
                    summary=ps_data.get("summary"),
                    vision_statement=ps_data.get("vision_statement"),
                    in_scope=ps_data.get("in_scope"),
                    out_of_scope=ps_data.get("out_of_scope"),
                    interfaces_text=ps_data.get("interfaces_text"),
                    what_is_actually_done=ps_data.get("what_is_actually_done"),
                    pain_points=ps_data.get("pain_points"),
                    targets_text=ps_data.get("targets_text")
                )
                session.add(step)
        session.flush()

        print("Importing Use Cases...")
        if "use_cases" in imported_data:
            for uc_data in imported_data["use_cases"]:
                # Assuming process_step_id in JSON refers to the new ID if cleared, or existing ID.
                process_step = session.query(ProcessStep).filter_by(id=uc_data["process_step_id"]).first()
                if not process_step:
                    print(f"Warning: Process Step ID {uc_data['process_step_id']} for use case '{uc_data['name']}' not found. Skipping UC.")
                    continue
                use_case = UseCase(
                    bi_id=uc_data["bi_id"],
                    name=uc_data["name"],
                    process_step_id=process_step.id, # Use the looked-up step's ID
                    priority=uc_data.get("priority"),
                    raw_content=uc_data.get("raw_content"),
                    summary=uc_data.get("summary"),
                    inspiration=uc_data.get("inspiration"),
                    wave=uc_data.get("wave"),
                    effort_level=uc_data.get("effort_level"),
                    status=uc_data.get("status"),
                    business_problem_solved=uc_data.get("business_problem_solved"),
                    target_solution_description=uc_data.get("target_solution_description"),
                    technologies_text=uc_data.get("technologies_text"),
                    requirements=uc_data.get("requirements"),
                    relevants_text=uc_data.get("relevants_text"),
                    reduction_time_transfer=uc_data.get("reduction_time_transfer"),
                    reduction_time_launches=uc_data.get("reduction_time_launches"),
                    reduction_costs_supply=uc_data.get("reduction_costs_supply"),
                    quality_improvement_quant=uc_data.get("quality_improvement_quant"),
                    ideation_notes=uc_data.get("ideation_notes"),
                    further_ideas=uc_data.get("further_ideas"),
                    effort_quantification=uc_data.get("effort_quantification"),
                    potential_quantification=uc_data.get("potential_quantification"),
                    dependencies_text=uc_data.get("dependencies_text"),
                    contact_persons_text=uc_data.get("contact_persons_text"),
                    related_projects_text=uc_data.get("related_projects_text")
                )
                session.add(use_case)
        session.flush()

        print("Importing Relevance Links...")
        if "usecase_area_relevance" in imported_data:
            for r_data in imported_data["usecase_area_relevance"]:
                rel = UsecaseAreaRelevance(
                    source_usecase_id=r_data["source_usecase_id"], 
                    target_area_id=r_data["target_area_id"],       
                    relevance_score=r_data["relevance_score"],
                    relevance_content=r_data.get("relevance_content")
                )
                session.add(rel)
        
        if "usecase_step_relevance" in imported_data:
             for r_data in imported_data["usecase_step_relevance"]:
                rel = UsecaseStepRelevance(
                    source_usecase_id=r_data["source_usecase_id"], 
                    target_process_step_id=r_data["target_process_step_id"], 
                    relevance_score=r_data["relevance_score"],
                    relevance_content=r_data.get("relevance_content")
                )
                session.add(rel)

        if "usecase_usecase_relevance" in imported_data:
             for r_data in imported_data["usecase_usecase_relevance"]:
                rel = UsecaseUsecaseRelevance(
                    source_usecase_id=r_data["source_usecase_id"], 
                    target_usecase_id=r_data["target_usecase_id"], 
                    relevance_score=r_data["relevance_score"],
                    relevance_content=r_data.get("relevance_content")
                )
                session.add(rel)

        # NEW: Import ProcessStepProcessStepRelevance
        if "process_step_process_step_relevance" in imported_data:
             for r_data in imported_data["process_step_process_step_relevance"]:
                rel = ProcessStepProcessStepRelevance(
                    source_process_step_id=r_data["source_process_step_id"],
                    target_process_step_id=r_data["target_process_step_id"],
                    relevance_score=r_data["relevance_score"],
                    relevance_content=r_data.get("relevance_content")
                )
                session.add(rel)

        session.commit()
        return {"success": True, "message": "Database import successful."}

    except IntegrityError as ie:
        session.rollback()
        print(f"Database integrity error during import: {ie}")
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Database integrity error: {ie}. Import rolled back."
        }
    except Exception as e:
        session.rollback()
        print(f"Error during database import: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "message": f"An error occurred: {e}. Import rolled back."
        }
    finally:
        SessionLocal.remove()