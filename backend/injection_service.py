# UsecaseExplorer/backend/injection_service.py
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
from datetime import datetime

# --- Keep existing functions as they are (datetime_serializer, export_database_to_json_string, export_area_to_markdown, process_area_file) ---
# ... (contents of process_area_file, etc.) ...

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


# MODIFIED: process_step_file to correctly handle nested JSON and add more logging
def process_step_file(file_content_json):
    """
    Parses a JSON file of process steps, compares with existing data,
    and returns a structured preview of changes for user review.
    Handles JSON where steps are a top-level list OR nested under a 'process_steps' key.
    Does NOT commit any changes to the database.
    """
    session = SessionLocal()
    preview_data = [] # This will store the structured preview
    
    # Helper to convert an SQLAlchemy model instance to a dict for comparison/JSON
    def model_to_dict(obj, fields_to_include, session):
        data = {}
        for field in fields_to_include:
            val = getattr(obj, field, None)
            if isinstance(val, datetime):
                data[field] = val.isoformat()
            else:
                data[field] = val
        
        # Include area_name for display convenience in preview
        if obj.area_id:
            area = session.query(Area).get(obj.area_id)
            data['area_name'] = area.name if area else 'Unknown Area'
        else:
            data['area_name'] = 'N/A'

        return data

    # Define all fields to be considered for updates/conflicts
    step_fields = [
        "name", "step_description", "raw_content", "summary", "vision_statement",
        "in_scope", "out_of_scope", "interfaces_text", "what_is_actually_done",
        "pain_points", "targets_text"
    ]

    try:
        print("Starting process_step_file for preview generation...")
        area_name_to_id_map = {
            area.name: area.id for area in session.query(Area.name, Area.id).all()
        }
        area_id_to_name_map = {
            area.id: area.name for area in session.query(Area.id, Area.name).all()
        }
        print(f"Available areas in DB: {list(area_name_to_id_map.keys())}")


        json_data_list = []
        if isinstance(file_content_json, list):
            json_data_list = file_content_json
            print("Detected top-level JSON as a list.")
        elif isinstance(file_content_json, dict) and "process_steps" in file_content_json and isinstance(file_content_json["process_steps"], list):
            json_data_list = file_content_json["process_steps"]
            print("Detected top-level JSON as a dictionary with 'process_steps' key.")
        else:
            raise ValueError("Invalid JSON format: Top level must be a list of objects or a dictionary containing a 'process_steps' list.")
        
        print(f"Number of items found in JSON for processing: {len(json_data_list)}")

        if not json_data_list: # Check if the list is empty after extraction
            print("json_data_list is empty. Returning success=True with empty preview_data.")
            return {"success": True, "preview_data": [], "message": "No process steps found in the uploaded file."}


        for item_from_json in json_data_list:
            print(f"\nProcessing JSON item: {item_from_json.get('bi_id', 'N/A')} - {item_from_json.get('name', 'N/A')}")
            entry = {
                'status': 'skipped', # Default status
                'bi_id': item_from_json.get('bi_id'),
                'name': item_from_json.get('name'),
                'area_name': item_from_json.get('area_name'), # Area name from JSON
                'json_data': {}, # Raw data from JSON (cleaned)
                'db_data': {},   # Current data from DB (cleaned)
                'conflicts': {}, # Fields with differences (old_value, new_value)
                'new_values': {}, # Proposed values based on conflict resolution logic (initial state)
                'messages': []   # Messages specific to this item
            }

            # Basic validation for required fields from JSON
            if not (isinstance(item_from_json, dict) and
                    all(k in item_from_json for k in ('bi_id', 'name', 'area_name')) and
                    isinstance(item_from_json['bi_id'], str) and item_from_json['bi_id'].strip() and
                    isinstance(item_from_json['name'], str) and item_from_json['name'].strip() and
                    isinstance(item_from_json['area_name'], str) and item_from_json['area_name'].strip()):
                entry['messages'].append("Skipped: Invalid JSON format or missing required fields (bi_id, name, area_name).")
                print(f"  Skipped due to invalid format: {item_from_json.get('bi_id', 'N/A')}")
                preview_data.append(entry)
                continue

            bi_id = item_from_json['bi_id'].strip()
            name = item_from_json['name'].strip()
            area_name_json = item_from_json['area_name'].strip()

            entry['bi_id'] = bi_id
            entry['name'] = name
            entry['area_name'] = area_name_json

            json_values_cleaned = {}
            for field in step_fields:
                val = item_from_json.get(field)
                json_values_cleaned[field] = val.strip() if isinstance(val, str) and val.strip() else None
            json_values_cleaned['name'] = name
            json_values_cleaned['bi_id'] = bi_id
            json_values_cleaned['area_name'] = area_name_json
            
            entry['json_data'] = json_values_cleaned


            existing_step = session.query(ProcessStep).filter_by(bi_id=bi_id).first()
            area_id_from_json = area_name_to_id_map.get(area_name_json)

            if existing_step:
                print(f"  Existing step found in DB: {existing_step.name} (BI_ID: {existing_step.bi_id})")
                entry['db_data'] = model_to_dict(existing_step, step_fields + ['bi_id', 'area_id', 'name'], session)
                entry['new_values'] = dict(entry['db_data'])
                
                is_dirty = False
                
                # Check for area_id change
                if area_id_from_json is None:
                    entry['messages'].append(f"Warning: Area '{area_name_json}' for step BI_ID '{bi_id}' from JSON not found in database. Cannot assign new area.")
                    print(f"  Warning: Area '{area_name_json}' not found for existing step.")
                elif existing_step.area_id != area_id_from_json:
                    entry['conflicts']['area_id'] = {
                        'old_value': area_id_to_name_map.get(existing_step.area_id, 'N/A (ID: ' + str(existing_step.area_id) + ')'),
                        'new_value': area_name_json,
                        'db_id': existing_step.area_id,
                        'json_id': area_id_from_json
                    }
                    entry['new_values']['area_id'] = area_id_from_json
                    is_dirty = True
                    print(f"  Conflict detected for area_id: DB '{existing_step.area_id}' vs JSON '{area_id_from_json}'")
                else:
                    entry['messages'].append(f"Area '{area_name_json}' matches existing area.")
                    entry['new_values']['area_id'] = existing_step.area_id

                # Compare other fields for conflicts
                for field in step_fields:
                    db_value = getattr(existing_step, field)
                    json_value = json_values_cleaned.get(field)
                    
                    normalized_db_value = db_value.strip() if isinstance(db_value, str) and db_value.strip() else None
                    normalized_json_value = json_value.strip() if isinstance(json_value, str) and json_value.strip() else None

                    if normalized_json_value != normalized_db_value:
                        entry['conflicts'][field] = {
                            'old_value': normalized_db_value if normalized_db_value is not None else "N/A (Empty)",
                            'new_value': normalized_json_value if normalized_json_value is not None else "N/A (Empty)"
                        }
                        entry['new_values'][field] = normalized_json_value
                        is_dirty = True
                        print(f"  Conflict detected for field '{field}': DB '{normalized_db_value}' vs JSON '{normalized_json_value}'")
                    else:
                        entry['new_values'][field] = normalized_db_value

                if is_dirty:
                    entry['status'] = 'update'
                    entry['messages'].append("Existing step will be updated with new values for conflicting fields.")
                    print(f"  Status set to 'update' for {bi_id}.")
                else:
                    entry['status'] = 'no_change'
                    entry['messages'].append("Existing step found with no changes detected.")
                    print(f"  Status set to 'no_change' for {bi_id}.")
            else:
                # New step
                print(f"  No existing step found for BI_ID: {bi_id}")
                if area_id_from_json is None:
                    entry['status'] = 'skipped'
                    entry['messages'].append(f"Skipped: Area '{area_name_json}' not found for new step BI_ID '{bi_id}'.")
                    print(f"  Skipped new step because Area '{area_name_json}' was not found.")
                else:
                    entry['status'] = 'new'
                    entry['new_values'] = dict(json_values_cleaned)
                    entry['new_values']['area_id'] = area_id_from_json
                    entry['messages'].append("New step will be added.")
                    print(f"  Status set to 'new' for {bi_id}.")
            
            preview_data.append(entry)
        
        print(f"\nFinished processing file. Total items in preview_data: {len(preview_data)}")
        return {"success": True, "preview_data": preview_data}

    except ValueError as ve:
        print(f"Value Error in process_step_file (for preview): {ve}")
        return {"success": False, "message": f"Data processing error: {ve}", "preview_data": []}
    except Exception as e:
        traceback.print_exc()
        print(f"Unexpected error in process_step_file (for preview): {e}")
        return {"success": False, "message": f"An unexpected error occurred: {str(e)}", "preview_data": []}
    finally:
        SessionLocal.remove()


# NEW: Function to finalize step import based on user's resolved data
def finalize_step_import(resolved_steps_data):
    """
    Receives resolved step data from the frontend and performs database operations.
    """
    session = SessionLocal()
    add_count = 0
    update_count = 0
    fail_count = 0
    messages = []

    try:
        for item in resolved_steps_data:
            bi_id = item['bi_id']
            action = item['action'] # 'add', 'update', 'skip'
            final_data = item['final_data'] # The dictionary with resolved values

            if action == 'add':
                try:
                    new_step = ProcessStep(
                        bi_id=bi_id,
                        name=final_data.get('name'), # Ensure 'name' is in final_data
                        area_id=final_data.get('area_id'), # Ensure 'area_id' is in final_data
                        step_description=final_data.get('step_description'),
                        raw_content=final_data.get('raw_content'),
                        summary=final_data.get('summary'),
                        vision_statement=final_data.get('vision_statement'),
                        in_scope=final_data.get('in_scope'),
                        out_of_scope=final_data.get('out_of_scope'),
                        interfaces_text=final_data.get('interfaces_text'),
                        what_is_actually_done=final_data.get('what_is_actually_done'),
                        pain_points=final_data.get('pain_points'),
                        targets_text=final_data.get('targets_text')
                    )
                    session.add(new_step)
                    add_count += 1
                    messages.append(f"Added new step: {new_step.name} (BI_ID: {new_step.bi_id})")
                except IntegrityError as ie:
                    session.rollback()
                    fail_count += 1
                    messages.append(f"Failed to add new step {bi_id}: BI_ID already exists or invalid area_id. Error: {ie}")
                    session = SessionLocal() # Re-create session after rollback
                except Exception as e:
                    session.rollback()
                    fail_count += 1
                    messages.append(f"Failed to add new step {bi_id}: Unexpected error. Error: {e}")
                    session = SessionLocal()

            elif action == 'update':
                existing_step = session.query(ProcessStep).filter_by(bi_id=bi_id).first()
                if existing_step:
                    try:
                        changes = []
                        for field, value in final_data.items():
                            # Special handling for area_id to update directly on model
                            if field == 'area_id':
                                if existing_step.area_id != value:
                                    existing_step.area_id = value
                                    changes.append('area_id')
                            # Handle other fields
                            elif field not in ['bi_id'] and getattr(existing_step, field) != value: # 'id' not a field to update
                                setattr(existing_step, field, value)
                                changes.append(field)
                        if changes:
                            update_count += 1
                            messages.append(f"Updated step: {existing_step.name} (BI_ID: {bi_id}). Fields changed: {', '.join(changes)}")
                        else:
                            messages.append(f"No changes applied to step {bi_id}.")
                    except Exception as e:
                        session.rollback()
                        fail_count += 1
                        messages.append(f"Failed to update step {bi_id}: Unexpected error. Error: {e}")
                        session = SessionLocal() # Re-create session after rollback
                else:
                    fail_count += 1
                    messages.append(f"Failed to update step {bi_id}: Original step not found in database.")
            elif action == 'skip':
                messages.append(f"Skipped step: {bi_id}")
            # Add other actions if needed (e.g., 'delete')
        
        session.commit()
        return {
            "success": True,
            "added_count": add_count,
            "updated_count": update_count,
            "failed_count": fail_count,
            "messages": messages
        }

    except Exception as e:
        session.rollback()
        messages.append(f"An unexpected error occurred during final import: {str(e)}")
        traceback.print_exc()
        return {
            "success": False,
            "added_count": 0,
            "updated_count": 0,
            "failed_count": len(resolved_steps_data), # All data is considered failed if the global transaction rolls back
            "messages": messages
        }
    finally:
        SessionLocal.remove()


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

                area_id = step_lookup[process_step_bi_id_from_json] # This was originally `area_id = area_lookup[area_name]` in process_step_file, should be `process_step_id` here.
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

# --- NEW FUNCTIONS FOR USECASE RELEVANCE INJECTION ---

def process_usecase_area_relevance_file(file_stream):
    session = SessionLocal()
    added_count = 0
    skipped_invalid_format = 0
    skipped_existing_link = 0
    skipped_missing_entities = 0
    skipped_errors = []
    message = ""
    success = False

    try:
        print("Processing Use Case-Area relevance links file...")
        usecase_lookup = {uc.bi_id: uc.id for uc in session.query(UseCase.bi_id, UseCase.id).all()}
        area_lookup = {area.name: area.id for area in session.query(Area.name, Area.id).all()}

        try:
            data = json.load(file_stream)
        except UnicodeDecodeError:
            file_stream.seek(0)
            data = json.loads(file_stream.read().decode('utf-8'))

        if not isinstance(data, list):
            raise ValueError("Invalid JSON format: Top level must be a list.")

        for item in data:
            if not (isinstance(item, dict) and
                    all(k in item for k in ('source_usecase_bi_id', 'target_area_name', 'relevance_score')) and
                    isinstance(item['source_usecase_bi_id'], str) and item['source_usecase_bi_id'].strip() and
                    isinstance(item['target_area_name'], str) and item['target_area_name'].strip()):
                skipped_invalid_format += 1
                skipped_errors.append(f"Invalid format for item: {item}")
                continue

            source_uc_bi_id = item['source_usecase_bi_id'].strip()
            target_area_name = item['target_area_name'].strip()
            relevance_score_raw = item['relevance_score']
            relevance_content = item.get('relevance_content')

            if relevance_content is not None and not isinstance(relevance_content, str):
                print(f"Warning: Relevance content for {source_uc_bi_id} -> {target_area_name} was not a string, setting to None. Value: {relevance_content}")
                relevance_content = None
            elif isinstance(relevance_content, str):
                stripped_content = relevance_content.strip()
                relevance_content = stripped_content if stripped_content else None
            

            source_uc_id = usecase_lookup.get(source_uc_bi_id)
            target_area_id = area_lookup.get(target_area_name)

            if source_uc_id is None:
                skipped_missing_entities += 1
                skipped_errors.append(f"Missing source Use Case BI_ID: {source_uc_bi_id}")
                continue
            if target_area_id is None:
                skipped_missing_entities += 1
                skipped_errors.append(f"Missing target Area Name: {target_area_name}")
                continue
            
            try:
                score = int(relevance_score_raw)
                if not (0 <= score <= 100):
                    skipped_invalid_format += 1
                    skipped_errors.append(f"Invalid score for {source_uc_bi_id} -> {target_area_name}: {relevance_score_raw}")
                    continue
            except (ValueError, TypeError):
                skipped_invalid_format += 1
                skipped_errors.append(f"Non-integer score for {source_uc_bi_id} -> {target_area_name}: {relevance_score_raw}")
                continue

            existing_link = session.query(UsecaseAreaRelevance).filter_by(
                source_usecase_id=source_uc_id,
                target_area_id=target_area_id
            ).first()

            if existing_link:
                skipped_existing_link += 1
                skipped_errors.append(f"Existing link skipped: {source_uc_bi_id} -> {target_area_name}")
                continue

            new_link = UsecaseAreaRelevance(
                source_usecase_id=source_uc_id,
                target_area_id=target_area_id,
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
        if skipped_missing_entities > 0: parts.append(f"Skipped (Missing Entities): {skipped_missing_entities}")
        if skipped_invalid_format > 0: parts.append(f"Skipped (Invalid Data): {skipped_invalid_format}")

        if not parts:
            message = "Processing complete. No Use Case-Area relevance links found or processed."
        else:
            message = f"Processing complete. {', '.join(parts)}."

    except json.JSONDecodeError:
        print("JSON Decode Error in process_usecase_area_relevance_file")
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
        "skipped_count": skipped_invalid_format + skipped_existing_link + skipped_missing_entities,
        "skipped_invalid_format": skipped_invalid_format,
        "skipped_existing_link": skipped_existing_link,
        "skipped_missing_entities": skipped_missing_entities,
        "skipped_errors": skipped_errors
    }

def process_usecase_step_relevance_file(file_stream):
    session = SessionLocal()
    added_count = 0
    skipped_invalid_format = 0
    skipped_existing_link = 0
    skipped_missing_entities = 0
    skipped_errors = []
    message = ""
    success = False

    try:
        print("Processing Use Case-Step relevance links file...")
        usecase_lookup = {uc.bi_id: uc.id for uc in session.query(UseCase.bi_id, UseCase.id).all()}
        step_lookup = {step.bi_id: step.id for step in session.query(ProcessStep.bi_id, ProcessStep.id).all()}

        try:
            data = json.load(file_stream)
        except UnicodeDecodeError:
            file_stream.seek(0)
            data = json.loads(file_stream.read().decode('utf-8'))

        if not isinstance(data, list):
            raise ValueError("Invalid JSON format: Top level must be a list.")

        for item in data:
            if not (isinstance(item, dict) and
                    all(k in item for k in ('source_usecase_bi_id', 'target_process_step_bi_id', 'relevance_score')) and
                    isinstance(item['source_usecase_bi_id'], str) and item['source_usecase_bi_id'].strip() and
                    isinstance(item['target_process_step_bi_id'], str) and item['target_process_step_bi_id'].strip()):
                skipped_invalid_format += 1
                skipped_errors.append(f"Invalid format for item: {item}")
                continue

            source_uc_bi_id = item['source_usecase_bi_id'].strip()
            target_ps_bi_id = item['target_process_step_bi_id'].strip()
            relevance_score_raw = item['relevance_score']
            relevance_content = item.get('relevance_content')

            if relevance_content is not None and not isinstance(relevance_content, str):
                print(f"Warning: Relevance content for {source_uc_bi_id} -> {target_ps_bi_id} was not a string, setting to None. Value: {relevance_content}")
                relevance_content = None
            elif isinstance(relevance_content, str):
                stripped_content = relevance_content.strip()
                relevance_content = stripped_content if stripped_content else None


            source_uc_id = usecase_lookup.get(source_uc_bi_id)
            target_ps_id = step_lookup.get(target_ps_bi_id)

            if source_uc_id is None:
                skipped_missing_entities += 1
                skipped_errors.append(f"Missing source Use Case BI_ID: {source_uc_bi_id}")
                continue
            if target_ps_id is None:
                skipped_missing_entities += 1
                skipped_errors.append(f"Missing target Process Step BI_ID: {target_ps_bi_id}")
                continue
            
            try:
                score = int(relevance_score_raw)
                if not (0 <= score <= 100):
                    skipped_invalid_format += 1
                    skipped_errors.append(f"Invalid score for {source_uc_bi_id} -> {target_ps_bi_id}: {relevance_score_raw}")
                    continue
            except (ValueError, TypeError):
                skipped_invalid_format += 1
                skipped_errors.append(f"Non-integer score for {source_uc_bi_id} -> {target_ps_bi_id}: {relevance_score_raw}")
                continue

            existing_link = session.query(UsecaseStepRelevance).filter_by(
                source_usecase_id=source_uc_id,
                target_process_step_id=target_ps_id
            ).first()

            if existing_link:
                skipped_existing_link += 1
                skipped_errors.append(f"Existing link skipped: {source_uc_bi_id} -> {target_ps_bi_id}")
                continue

            new_link = UsecaseStepRelevance(
                source_usecase_id=source_uc_id,
                target_process_step_id=target_ps_id,
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
        if skipped_missing_entities > 0: parts.append(f"Skipped (Missing Entities): {skipped_missing_entities}")
        if skipped_invalid_format > 0: parts.append(f"Skipped (Invalid Data): {skipped_invalid_format}")

        if not parts:
            message = "Processing complete. No Use Case-Step relevance links found or processed."
        else:
            message = f"Processing complete. {', '.join(parts)}."

    except json.JSONDecodeError:
        print("JSON Decode Error in process_usecase_step_relevance_file")
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
        "skipped_count": skipped_invalid_format + skipped_existing_link + skipped_missing_entities,
        "skipped_invalid_format": skipped_invalid_format,
        "skipped_existing_link": skipped_existing_link,
        "skipped_missing_entities": skipped_missing_entities,
        "skipped_errors": skipped_errors
    }

def process_usecase_usecase_relevance_file(file_stream):
    session = SessionLocal()
    added_count = 0
    skipped_invalid_format = 0
    skipped_existing_link = 0
    skipped_missing_entities = 0
    skipped_self_link = 0
    skipped_errors = []
    message = ""
    success = False

    try:
        print("Processing Use Case-Use Case relevance links file...")
        usecase_lookup = {uc.bi_id: uc.id for uc in session.query(UseCase.bi_id, UseCase.id).all()}

        try:
            data = json.load(file_stream)
        except UnicodeDecodeError:
            file_stream.seek(0)
            data = json.loads(file_stream.read().decode('utf-8'))

        if not isinstance(data, list):
            raise ValueError("Invalid JSON format: Top level must be a list.")

        for item in data:
            if not (isinstance(item, dict) and
                    all(k in item for k in ('source_usecase_bi_id', 'target_usecase_bi_id', 'relevance_score')) and
                    isinstance(item['source_usecase_bi_id'], str) and item['source_usecase_bi_id'].strip() and
                    isinstance(item['target_usecase_bi_id'], str) and item['target_usecase_bi_id'].strip()):
                skipped_invalid_format += 1
                skipped_errors.append(f"Invalid format for item: {item}")
                continue

            source_uc_bi_id = item['source_usecase_bi_id'].strip()
            target_uc_bi_id = item['target_usecase_bi_id'].strip()
            relevance_score_raw = item['relevance_score']
            relevance_content = item.get('relevance_content')

            if relevance_content is not None and not isinstance(relevance_content, str):
                print(f"Warning: Relevance content for {source_uc_bi_id} -> {target_uc_bi_id} was not a string, setting to None. Value: {relevance_content}")
                relevance_content = None
            elif isinstance(relevance_content, str):
                stripped_content = relevance_content.strip()
                relevance_content = stripped_content if stripped_content else None


            if source_uc_bi_id == target_uc_bi_id:
                skipped_self_link += 1
                skipped_errors.append(f"Self-relevance link: {source_uc_bi_id} -> {target_uc_bi_id}")
                continue

            source_uc_id = usecase_lookup.get(source_uc_bi_id)
            target_uc_id = usecase_lookup.get(target_uc_bi_id)

            if source_uc_id is None:
                skipped_missing_entities += 1
                skipped_errors.append(f"Missing source Use Case BI_ID: {source_uc_bi_id}")
                continue
            if target_uc_id is None:
                skipped_missing_entities += 1
                skipped_errors.append(f"Missing target Use Case BI_ID: {target_uc_bi_id}")
                continue
            
            try:
                score = int(relevance_score_raw)
                if not (0 <= score <= 100):
                    skipped_invalid_format += 1
                    skipped_errors.append(f"Invalid score for {source_uc_bi_id} -> {target_uc_bi_id}: {relevance_score_raw}")
                    continue
            except (ValueError, TypeError):
                skipped_invalid_format += 1
                skipped_errors.append(f"Non-integer score for {source_uc_bi_id} -> {target_uc_bi_id}: {relevance_score_raw}")
                continue

            existing_link = session.query(UsecaseUsecaseRelevance).filter_by(
                source_usecase_id=source_uc_id,
                target_usecase_id=target_uc_id
            ).first()

            if existing_link:
                skipped_existing_link += 1
                skipped_errors.append(f"Existing link skipped: {source_uc_bi_id} -> {target_uc_bi_id}")
                continue

            new_link = UsecaseUsecaseRelevance(
                source_usecase_id=source_uc_id,
                target_usecase_id=target_uc_id,
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
        if skipped_missing_entities > 0: parts.append(f"Skipped (Missing Entities): {skipped_missing_entities}")
        if skipped_invalid_format > 0: parts.append(f"Skipped (Invalid Data): {skipped_invalid_format}")

        if not parts:
            message = "Processing complete. No Use Case-Use Case relevance links found or processed."
        else:
            message = f"Processing complete. {', '.join(parts)}."

    except json.JSONDecodeError:
        print("JSON Decode Error in process_usecase_usecase_relevance_file")
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
        "skipped_count": skipped_invalid_format + skipped_existing_link + skipped_missing_entities + skipped_self_link,
        "skipped_invalid_format": skipped_invalid_format,
        "skipped_existing_link": skipped_existing_link,
        "skipped_missing_entities": skipped_missing_entities,
        "skipped_self_link": skipped_self_link,
        "skipped_errors": skipped_errors
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