# backend/injection_service.py
import json
import traceback
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError, OperationalError
from .db import SessionLocal, db as flask_sqlalchemy_db
from .models import (
    Base, User, Area, ProcessStep, UseCase, LLMSettings,
    UsecaseAreaRelevance, UsecaseStepRelevance, UsecaseUsecaseRelevance,
    ProcessStepProcessStepRelevance
)
from datetime import datetime

def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def process_area_file(file_stream):
    session = SessionLocal()
    added_count = 0
    updated_count = 0
    skipped_count = 0
    duplicates_not_updated = []
    skipped_errors_details = []

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
            raise ValueError("Invalid JSON format: Top level must be a list of area objects.")

        for i, item in enumerate(data):
            item_identifier = f"Item {i+1}"
            if isinstance(item, dict) and 'name' in item and isinstance(item['name'], str) and item['name'].strip():
                area_name = item['name'].strip()
                item_identifier = f"Area '{area_name}'"
            else:
                skipped_count += 1
                skipped_errors_details.append(f"{item_identifier}: Invalid format or missing/empty 'name' field.")
                continue

            description_from_json = item.get('description')
            if description_from_json is not None:
                if not isinstance(description_from_json, str):
                    description_from_json = None
                    skipped_errors_details.append(f"{item_identifier}: 'description' field was not a string, treated as empty.")
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
                    skipped_count += 1
            else:
                new_area = Area(
                    name=area_name,
                    description=description_from_json
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
            message += f" (Existing items not updated: {len(duplicates_not_updated)}). "
        if skipped_errors_details:
            message += f" (Details on specific skips available in server logs). "

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error in process_area_file: {e}")
        session.rollback()
        success = False
        message = f"Invalid JSON format in the uploaded file: {e}."
    except ValueError as ve:
        print(f"Value Error in process_area_file: {ve}")
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
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "duplicates_not_updated": duplicates_not_updated,
        "skipped_errors_details": skipped_errors_details
    }


def process_step_file(file_content_json):
    session = SessionLocal()
    preview_data = []

    def model_to_dict(obj, fields_to_include, session):
        data = {}
        for field in fields_to_include:
            val = getattr(obj, field, None)
            if isinstance(val, datetime):
                data[field] = val.isoformat()
            else:
                data[field] = val

        if obj.area_id:
            area = session.query(Area).get(obj.area_id)
            data['area_name'] = area.name if area else 'Unknown Area'
        else:
            data['area_name'] = 'N/A'

        return data

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

        if not json_data_list:
            print("json_data_list is empty. Returning success=True with empty preview_data.")
            return {"success": True, "preview_data": [], "message": "No process steps found in the uploaded file."}


        for item_from_json in json_data_list:
            bi_id_log = item_from_json.get('bi_id', 'N/A')
            name_log = item_from_json.get('name', 'N/A')
            print(f"\nProcessing JSON item: BI_ID='{bi_id_log}' Name='{name_log}'")

            entry = {
                'status': 'skipped', # Default status
                'action': 'skip',    # Default action
                'bi_id': bi_id_log,
                'name': name_log,
                'area_name': item_from_json.get('area_name', 'N/A'),
                'json_data': {},
                'db_data': {},
                'conflicts': {},
                'new_values': {},
                'messages': []
            }

            if not (isinstance(item_from_json, dict) and
                    all(k in item_from_json for k in ('bi_id', 'name', 'area_name')) and
                    isinstance(item_from_json['bi_id'], str) and item_from_json['bi_id'].strip() and
                    isinstance(item_from_json['name'], str) and item_from_json['name'].strip() and
                    isinstance(item_from_json['area_name'], str) and item_from_json['area_name'].strip()):
                entry['messages'].append("Skipped: Invalid JSON format or missing required fields (bi_id, name, area_name).")
                print(f"  Skipped due to invalid format: BI_ID='{bi_id_log}'")
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
                print(f"  Existing step found in DB: '{existing_step.name}' (BI_ID: '{existing_step.bi_id}')")
                entry['db_data'] = model_to_dict(existing_step, step_fields + ['bi_id', 'area_id', 'name'], session)

                entry['new_values'] = {k: (v.strip() if isinstance(v, str) else v) for k, v in entry['db_data'].items()}
                if 'area_id' in entry['new_values']:
                    entry['new_values']['area_id'] = existing_step.area_id

                is_dirty = False

                if area_id_from_json is None:
                    entry['messages'].append(f"Warning: Area '{area_name_json}' from JSON not found in database. Keeping existing area for '{name}'.")
                    print(f"  Warning: Area '{area_name_json}' not found for existing step. Keeping DB value.")
                elif existing_step.area_id != area_id_from_json:
                    entry['conflicts']['area_id'] = {
                        'old_value': area_id_to_name_map.get(existing_step.area_id, f'N/A (ID: {existing_step.area_id})'),
                        'new_value': area_name_json,
                        'db_id': existing_step.area_id,
                        'json_id': area_id_from_json
                    }
                    entry['new_values']['area_id'] = area_id_from_json
                    is_dirty = True
                    entry['messages'].append(f"Conflict: Area changed from '{entry['conflicts']['area_id']['old_value']}' to '{entry['conflicts']['area_id']['new_value']}'.")
                    print(f"  Conflict detected for area_id: DB '{existing_step.area_id}' vs JSON '{area_id_from_json}' (Proposing JSON)")
                else:
                    entry['messages'].append(f"Area '{area_name_json}' matches existing area.")

                for field in step_fields:
                    db_value_raw = getattr(existing_step, field)
                    normalized_db_value = db_value_raw.strip() if isinstance(db_value_raw, str) and db_value_raw.strip() else None

                    normalized_json_value = json_values_cleaned.get(field)

                    if normalized_json_value is not None and normalized_json_value != normalized_db_value:
                        entry['conflicts'][field] = {
                            'old_value': normalized_db_value if normalized_db_value is not None else "N/A (Empty in DB)",
                            'new_value': normalized_json_value
                        }
                        entry['new_values'][field] = normalized_json_value
                        is_dirty = True
                        entry['messages'].append(f"Conflict: Field '{field}' changed from '{normalized_db_value}' to '{normalized_json_value}'.")
                        print(f"  Conflict detected for field '{field}': DB '{normalized_db_value}' vs JSON '{normalized_json_value}' (Proposing JSON)")
                    elif normalized_json_value is None and normalized_db_value is not None:
                        entry['conflicts'][field] = {
                            'old_value': normalized_db_value,
                            'new_value': "N/A (Empty in JSON)"
                        }
                        entry['messages'].append(f"Conflict: Field '{field}' exists in DB but is empty in JSON. Proposing to keep DB value unless explicitly changed.")
                        print(f"  Conflict detected for field '{field}': DB '{normalized_db_value}' vs JSON 'None' (Proposing DB)")
                    else:
                        pass

                if is_dirty:
                    entry['status'] = 'update'
                    entry['action'] = 'update'
                    entry['messages'].insert(0, "Existing step has changes or conflicts. Review details to finalize.")
                    print(f"  Status set to 'update' for {bi_id}.")
                else:
                    entry['status'] = 'no_change'
                    entry['action'] = 'skip' # Default action for no_change is 'skip'
                    entry['messages'].insert(0, "Existing step found with no changes detected.")
                    print(f"  Status set to 'no_change' for {bi_id}.")
            else: # New step
                print(f"  No existing step found for BI_ID: '{bi_id}'")
                if area_id_from_json is None:
                    entry['status'] = 'skipped'
                    entry['action'] = 'skip' # Explicitly 'skip'
                    entry['messages'].append(f"Skipped: Area '{area_name_json}' for new step BI_ID '{bi_id}' not found in database. Please create the area first.")
                    print(f"  Skipped new step because Area '{area_name_json}' was not found.")
                else:
                    entry['status'] = 'new'
                    entry['action'] = 'add' # Action is 'add'
                    entry['new_values'] = dict(json_values_cleaned)
                    entry['new_values']['area_id'] = area_id_from_json
                    entry['messages'].append("New step will be added.")
                    print(f"  Status set to 'new' for {bi_id}.")

            preview_data.append(entry)

        print(f"\nFinished processing file. Total items in preview_data: {len(preview_data)}")
        return {"success": True, "preview_data": preview_data, "message": "Step file processed successfully for preview."}

    except ValueError as ve:
        print(f"Value Error in process_step_file (for preview): {ve}")
        return {"success": False, "message": f"Data processing error: {ve}", "preview_data": []}
    except Exception as e:
        traceback.print_exc()
        print(f"Unexpected error in process_step_file (for preview): {e}")
        return {"success": False, "message": f"An unexpected error occurred: {str(e)}", "preview_data": []}
    finally:
        SessionLocal.remove()


def finalize_step_import(resolved_steps_data):
    session = SessionLocal()
    add_count = 0
    update_count = 0
    skip_count = 0
    fail_count = 0
    messages = []

    try:
        for item in resolved_steps_data:
            bi_id = item['bi_id']
            action = item['action']
            final_data = item['final_data']

            if action == 'add':
                try:
                    new_step = ProcessStep(
                        bi_id=bi_id,
                        name=final_data.get('name'),
                        area_id=final_data.get('area_id'),
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
                    session.flush()
                    add_count += 1
                    messages.append(f"Successfully added new step: {new_step.name} (BI_ID: {new_step.bi_id})")
                except IntegrityError as ie:
                    session.rollback()
                    fail_count += 1
                    messages.append(f"Failed to add new step {bi_id}: BI_ID already exists or invalid area_id. Error: {ie}")
                    print(f"IntegrityError adding step {bi_id}: {ie}")
                    session = SessionLocal()
                except Exception as e:
                    session.rollback()
                    fail_count += 1
                    messages.append(f"Failed to add new step {bi_id}: Unexpected error. Error: {e}")
                    print(f"Unexpected error adding step {bi_id}: {e}")
                    session = SessionLocal()

            elif action == 'update':
                existing_step = session.query(ProcessStep).filter_by(bi_id=bi_id).first()
                if existing_step:
                    try:
                        changes = []
                        for field, value in final_data.items():
                            normalized_value = value.strip() if isinstance(value, str) and value.strip() else None

                            if field == 'area_id':
                                current_value = existing_step.area_id
                                new_value_int = int(normalized_value) if normalized_value is not None else None # Ensure conversion to int
                                if current_value != new_value_int:
                                    existing_step.area_id = new_value_int
                                    changes.append('area_id')
                            elif field not in ['bi_id', 'id']: # 'id' should not be updated from JSON
                                current_value = getattr(existing_step, field)
                                current_value_normalized = current_value.strip() if isinstance(current_value, str) and current_value.strip() else None
                                if current_value_normalized != normalized_value:
                                    setattr(existing_step, field, normalized_value)
                                    changes.append(field)

                        if changes:
                            update_count += 1
                            messages.append(f"Successfully updated step: {existing_step.name} (BI_ID: {bi_id}). Fields changed: {', '.join(changes)}")
                        else:
                            messages.append(f"No changes applied to step {bi_id} (data matched existing values).")
                            skip_count += 1 # Or it could be treated as a specific kind of skip if needed
                    except Exception as e:
                        session.rollback()
                        fail_count += 1
                        messages.append(f"Failed to update step {bi_id}: Unexpected error. Error: {e}")
                        print(f"Unexpected error updating step {bi_id}: {e}")
                        session = SessionLocal()
                else:
                    fail_count += 1
                    messages.append(f"Failed to update step {bi_id}: Original step not found in database for update. (Possibly deleted mid-process?)")
            elif action == 'skip':
                skip_count += 1
                messages.append(f"Skipped step: {bi_id} as per user selection.")

        session.commit()
        return {
            "success": True,
            "added_count": add_count,
            "updated_count": update_count,
            "skipped_count": skip_count,
            "failed_count": fail_count,
            "messages": messages
        }

    except Exception as e:
        session.rollback()
        messages.append(f"An unexpected error occurred during final import transaction: {str(e)}")
        traceback.print_exc()
        return {
            "success": False,
            "added_count": 0,
            "updated_count": 0,
            "skipped_count": 0,
            "failed_count": len(resolved_steps_data),
            "messages": messages
        }
    finally:
        SessionLocal.remove()


def process_usecase_file(file_stream):
    session = SessionLocal()
    added_count = 0
    updated_count = 0
    skipped_count_total = 0
    skipped_invalid_format = 0
    skipped_existing_no_update_uc_bi_id_count = 0
    skipped_missing_step = 0
    skipped_invalid_priority = 0

    uc_bi_ids_existing_no_update = []
    missing_step_bi_ids = []
    skipped_errors_details = []

    message = ""
    success = False

    json_to_model_map = {
        'name': 'name', 'priority': 'priority', 'raw_content': 'raw_content',
        'summary': 'summary', 'inspiration': 'inspiration', 'wave': 'wave',
        'effort': 'effort_level', 'status': 'status', 'BUSINESS PROBLEM SOLVED': 'business_problem_solved',
        'TARGET / SOLUTION DESCRIPTION': 'target_solution_description', 'TECHNOLOGIES': 'technologies_text',
        'REQUIREMENTS': 'requirements', 'RELEVANTS': 'relevants_text',
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
        'pilot_site_factory_text': 'pilot_site_factory_text',
        'usecase_type_category': 'usecase_type_category'
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
            raise ValueError("Invalid JSON format: Top level must be a list of use case objects.")

        for i, item in enumerate(data):
            item_identifier = f"Item {i+1}"
            uc_bi_id_from_json = item.get('bi_id', 'N/A')
            uc_name_from_json = item.get('name', 'N/A')
            process_step_bi_id_from_json = item.get('process_step_bi_id', 'N/A')
            item_log_string = f"UC BI_ID '{uc_bi_id_from_json}' (Name: '{uc_name_from_json}', Parent: '{process_step_bi_id_from_json}')"

            if not (isinstance(item, dict) and
                    all(k in item for k in ('bi_id', 'name', 'process_step_bi_id')) and
                    isinstance(item['bi_id'], str) and item['bi_id'].strip() and
                    isinstance(item['name'], str) and item['name'].strip() and
                    isinstance(item['process_step_bi_id'], str) and item['process_step_bi_id'].strip()):
                skipped_invalid_format += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Invalid format or missing/empty 'bi_id', 'name', or 'process_step_bi_id'.")
                continue

            uc_bi_id = item['bi_id'].strip()
            process_step_bi_id = item['process_step_bi_id'].strip()

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
                                skipped_invalid_priority += 1
                                skipped_errors_details.append(f"{item_log_string}: Invalid priority value '{json_value}' (must be 1-4). Skipping priority for this item.")
                        except (ValueError, TypeError):
                            skipped_invalid_priority += 1
                            skipped_errors_details.append(f"{item_log_string}: Non-integer priority '{json_value}'. Skipping priority for this item.")
                    uc_fields_from_json[model_attr] = priority_val
                elif isinstance(json_value, str):
                    stripped_value = json_value.strip()
                    uc_fields_from_json[model_attr] = stripped_value if stripped_value else None
                else:
                    uc_fields_from_json[model_attr] = None
                    if json_value is not None:
                        skipped_errors_details.append(f"{item_log_string}: Field '{model_attr}' (from JSON key '{json_key}') was not a string, treated as empty.")

            if 'name' not in uc_fields_from_json or uc_fields_from_json['name'] is None:
                 name_val = item.get('name')
                 if isinstance(name_val, str) and name_val.strip():
                     uc_fields_from_json['name'] = name_val.strip()
                 else:
                     skipped_errors_details.append(f"{item_log_string}: 'name' field missing or empty after processing, will use N/A if added.")
                     uc_fields_from_json['name'] = None

            if existing_usecase:
                current_process_step_id = existing_usecase.process_step_id

                new_process_step_id = step_lookup.get(process_step_bi_id)
                if new_process_step_id is None:
                    skipped_errors_details.append(f"{item_log_string}: Parent Process Step BI_ID '{process_step_bi_id}' from JSON not found. Keeping existing parent step.")
                elif new_process_step_id != current_process_step_id:
                    existing_usecase.process_step_id = new_process_step_id
                    item_updated = True
                    skipped_errors_details.append(f"{item_log_string}: Parent Process Step changed from ID '{current_process_step_id}' to '{new_process_step_id}'.")

                for model_attr, json_val in uc_fields_from_json.items():
                    if model_attr == 'process_step_id':
                        continue

                    db_value = getattr(existing_usecase, model_attr)
                    db_value_normalized = db_value.strip() if isinstance(db_value, str) and db_value.strip() else (db_value if not isinstance(db_value, str) else None)

                    if json_val is not None and (db_value_normalized is None or (isinstance(db_value_normalized, str) and db_value_normalized == '')):
                        setattr(existing_usecase, model_attr, json_val)
                        item_updated = True

                if item_updated:
                    updated_count += 1
                else:
                    skipped_existing_no_update_uc_bi_id_count += 1
                    skipped_count_total += 1
                    if uc_bi_id not in uc_bi_ids_existing_no_update:
                        uc_bi_ids_existing_no_update.append(uc_bi_id)
                    skipped_errors_details.append(f"{item_log_string}: Already exists with no empty fields to fill or data matched. Skipped update.")
            else:
                if process_step_bi_id not in step_lookup:
                    skipped_missing_step += 1
                    skipped_count_total += 1
                    if process_step_bi_id not in missing_step_bi_ids:
                        missing_step_bi_ids.append(process_step_bi_id)
                    skipped_errors_details.append(f"{item_log_string}: Parent Process Step BI_ID '{process_step_bi_id}' not found. Cannot add new use case.")
                    continue

                process_step_id = step_lookup[process_step_bi_id]
                new_uc_data = {
                    "bi_id": uc_bi_id,
                    "process_step_id": process_step_id,
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
        if skipped_count_total > 0: parts.append(f"Skipped: {skipped_count_total}")

        if not parts:
            message = "Processing complete. No Use Case data found or processed."
        else:
            message = f"Processing complete. {', '.join(parts)}."

        if skipped_errors_details:
             message += f" (Details on specific skips available in server logs). "

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error in process_usecase_file: {e}")
        session.rollback()
        success = False
        message = f"Invalid JSON format in the uploaded file: {e}."
    except ValueError as ve:
        print(f"Value Error in process_usecase_file: {ve}")
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
        "success": success, "message": message, "added_count": added_count,
        "updated_count": updated_count, "skipped_count": skipped_count_total,
        "skipped_invalid_format": skipped_invalid_format,
        "skipped_existing_no_update_uc_bi_id_count": skipped_existing_no_update_uc_bi_id_count,
        "skipped_missing_step": skipped_missing_step,
        "skipped_invalid_priority": skipped_invalid_priority,
        "uc_bi_ids_existing_no_update": uc_bi_ids_existing_no_update,
        "missing_step_bi_ids": missing_step_bi_ids,
        "skipped_errors_details": skipped_errors_details
    }


def process_ps_ps_relevance_file(file_stream):
    session = SessionLocal()
    added_count = 0
    skipped_count_total = 0
    skipped_invalid_format = 0
    skipped_existing_link = 0
    skipped_missing_step = 0
    skipped_self_link = 0
    skipped_errors_details = []
    message = ""
    success = False

    processed_pairs_in_file = set()

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
            raise ValueError("Invalid JSON format: Top level must be a list of relevance objects.")

        for i, item in enumerate(data):
            source_bi_id_log = item.get('source_process_step_bi_id', 'N/A')
            target_bi_id_log = item.get('target_process_step_bi_id', 'N/A')
            item_log_string = f"Link {i+1} ('{source_bi_id_log}' -> '{target_bi_id_log}')"

            if not (isinstance(item, dict) and
                    all(k in item for k in ('source_process_step_bi_id', 'target_process_step_bi_id', 'relevance_score')) and
                    isinstance(item['source_process_step_bi_id'], str) and item['source_process_step_bi_id'].strip() and
                    isinstance(item['target_process_step_bi_id'], str) and item['target_process_step_bi_id'].strip()):
                skipped_invalid_format += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Invalid format or missing required fields (source_process_step_bi_id, target_process_step_bi_id, relevance_score).")
                continue

            source_bi_id = item['source_process_step_bi_id'].strip()
            target_bi_id = item['target_process_step_bi_id'].strip()
            relevance_score_raw = item['relevance_score']
            relevance_content = item.get('relevance_content')

            if relevance_content is not None:
                if not isinstance(relevance_content, str):
                    skipped_errors_details.append(f"{item_log_string}: Relevance content was not a string, treated as empty.")
                    relevance_content = None
                else:
                    stripped_content = relevance_content.strip()
                    relevance_content = stripped_content if stripped_content else None

            source_id = step_lookup.get(source_bi_id)
            target_id = step_lookup.get(target_bi_id)

            if source_id is not None and target_id is not None and source_id == target_id:
                skipped_self_link += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Cannot link a Process Step (ID: {source_id}) to itself.")
                continue

            if source_id is None:
                skipped_missing_step += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Source Process Step BI_ID '{source_bi_id}' not found.")
                continue
            if target_id is None:
                skipped_missing_step += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Target Process Step BI_ID '{target_bi_id}' not found.")
                continue

            try:
                score = int(relevance_score_raw)
                if not (0 <= score <= 100):
                    skipped_invalid_format += 1
                    skipped_count_total += 1
                    skipped_errors_details.append(f"{item_log_string}: Invalid relevance score '{relevance_score_raw}' (must be 0-100).")
                    continue
            except (ValueError, TypeError):
                skipped_invalid_format += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Non-integer relevance score '{relevance_score_raw}'.")
                continue

            current_pair = tuple(sorted((source_id, target_id))) # Normalize pair to avoid (A,B) and (B,A) issues if logic were bidirectional
            if current_pair in processed_pairs_in_file:
                skipped_existing_link += 1 # Counts as processed from file
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string} (SourceID: {source_id}, TargetID: {target_id}): Link already processed from this file. Skipped duplicate entry.")
                continue

            existing_link_in_db = session.query(ProcessStepProcessStepRelevance).filter_by(
                source_process_step_id=source_id,
                target_process_step_id=target_id
            ).first()

            if existing_link_in_db:
                skipped_existing_link += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string} (SourceID: {source_id}, TargetID: {target_id}): Link already exists in the database. Skipped.")
                processed_pairs_in_file.add(current_pair)
                continue

            new_link = ProcessStepProcessStepRelevance(
                source_process_step_id=source_id,
                target_process_step_id=target_id,
                relevance_score=score,
                relevance_content=relevance_content
            )
            session.add(new_link)
            processed_pairs_in_file.add(current_pair)
            added_count += 1

        session.commit()
        success = True

        parts = []
        if added_count > 0: parts.append(f"Added: {added_count}")
        if skipped_count_total > 0: parts.append(f"Skipped: {skipped_count_total}")

        if not parts:
            message = "Processing complete. No process step relevance links found or processed."
        else:
            message = f"Processing complete. {', '.join(parts)}."

        if skipped_errors_details:
             message += f" (Details on specific skips available in server logs). "

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error in process_ps_ps_relevance_file: {e}")
        session.rollback()
        success = False
        message = f"Invalid JSON format in the uploaded file: {e}."
    except ValueError as ve:
        print(f"Value Error in process_ps_ps_relevance_file: {ve}")
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
        "success": success, "message": message, "added_count": added_count,
        "skipped_count": skipped_count_total, "skipped_invalid_format": skipped_invalid_format,
        "skipped_existing_link": skipped_existing_link, "skipped_missing_step": skipped_missing_step,
        "skipped_self_link": skipped_self_link, "skipped_errors_details": skipped_errors_details
    }


def process_usecase_area_relevance_file(file_stream):
    session = SessionLocal()
    added_count = 0
    skipped_count_total = 0
    skipped_invalid_format = 0
    skipped_existing_link = 0
    skipped_missing_entities = 0
    skipped_errors_details = []
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

        for i, item in enumerate(data):
            source_uc_bi_id_log = item.get('source_usecase_bi_id', 'N/A')
            target_area_name_log = item.get('target_area_name', 'N/A')
            item_log_string = f"Link {i+1} ('{source_uc_bi_id_log}' -> '{target_area_name_log}')"

            if not (isinstance(item, dict) and
                    all(k in item for k in ('source_usecase_bi_id', 'target_area_name', 'relevance_score')) and
                    isinstance(item['source_usecase_bi_id'], str) and item['source_usecase_bi_id'].strip() and
                    isinstance(item['target_area_name'], str) and item['target_area_name'].strip()):
                skipped_invalid_format += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Invalid format or missing required fields.")
                continue

            source_uc_bi_id = item['source_usecase_bi_id'].strip()
            target_area_name = item['target_area_name'].strip()
            relevance_score_raw = item['relevance_score']
            relevance_content = item.get('relevance_content')

            if relevance_content is not None:
                if not isinstance(relevance_content, str):
                    skipped_errors_details.append(f"{item_log_string}: Relevance content was not a string, treated as empty.")
                    relevance_content = None
                else:
                    stripped_content = relevance_content.strip()
                    relevance_content = stripped_content if stripped_content else None


            source_uc_id = usecase_lookup.get(source_uc_bi_id)
            target_area_id = area_lookup.get(target_area_name)

            if source_uc_id is None:
                skipped_missing_entities += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Source Use Case BI_ID '{source_uc_bi_id}' not found.")
                continue
            if target_area_id is None:
                skipped_missing_entities += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Target Area Name '{target_area_name}' not found.")
                continue

            try:
                score = int(relevance_score_raw)
                if not (0 <= score <= 100):
                    skipped_invalid_format += 1
                    skipped_count_total += 1
                    skipped_errors_details.append(f"{item_log_string}: Invalid score '{relevance_score_raw}' (must be 0-100).")
                    continue
            except (ValueError, TypeError):
                skipped_invalid_format += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Non-integer score '{relevance_score_raw}'.")
                continue

            existing_link = session.query(UsecaseAreaRelevance).filter_by(
                source_usecase_id=source_uc_id,
                target_area_id=target_area_id
            ).first()

            if existing_link:
                skipped_existing_link += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Link already exists. Skipped.")
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
        if skipped_count_total > 0: parts.append(f"Skipped: {skipped_count_total}")

        if not parts:
            message = "Processing complete. No Use Case-Area relevance links found or processed."
        else:
            message = f"Processing complete. {', '.join(parts)}."

        if skipped_errors_details:
             message += f" (Details on specific skips available in server logs). "

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error in process_usecase_area_relevance_file: {e}")
        session.rollback()
        success = False
        message = f"Invalid JSON format in the uploaded file: {e}."
    except ValueError as ve:
        print(f"Value Error in process_usecase_area_relevance_file: {ve}")
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
        "success": success, "message": message, "added_count": added_count,
        "skipped_count": skipped_count_total, "skipped_invalid_format": skipped_invalid_format,
        "skipped_existing_link": skipped_existing_link, "skipped_missing_entities": skipped_missing_entities,
        "skipped_errors_details": skipped_errors_details
    }

def process_usecase_step_relevance_file(file_stream):
    session = SessionLocal()
    added_count = 0
    skipped_count_total = 0
    skipped_invalid_format = 0
    skipped_existing_link = 0
    skipped_missing_entities = 0
    skipped_errors_details = []
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

        for i, item in enumerate(data):
            source_uc_bi_id_log = item.get('source_usecase_bi_id', 'N/A')
            target_ps_bi_id_log = item.get('target_process_step_bi_id', 'N/A')
            item_log_string = f"Link {i+1} ('{source_uc_bi_id_log}' -> '{target_ps_bi_id_log}')"

            if not (isinstance(item, dict) and
                    all(k in item for k in ('source_usecase_bi_id', 'target_process_step_bi_id', 'relevance_score')) and
                    isinstance(item['source_usecase_bi_id'], str) and item['source_usecase_bi_id'].strip() and
                    isinstance(item['target_process_step_bi_id'], str) and item['target_process_step_bi_id'].strip()):
                skipped_invalid_format += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Invalid format or missing required fields.")
                continue

            source_uc_bi_id = item['source_usecase_bi_id'].strip()
            target_ps_bi_id = item['target_process_step_bi_id'].strip()
            relevance_score_raw = item['relevance_score']
            relevance_content = item.get('relevance_content')

            if relevance_content is not None:
                if not isinstance(relevance_content, str):
                    skipped_errors_details.append(f"{item_log_string}: Relevance content was not a string, treated as empty.")
                    relevance_content = None
                else:
                    stripped_content = relevance_content.strip()
                    relevance_content = stripped_content if stripped_content else None


            source_uc_id = usecase_lookup.get(source_uc_bi_id)
            target_ps_id = step_lookup.get(target_ps_bi_id)

            if source_uc_id is None:
                skipped_missing_entities += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Source Use Case BI_ID '{source_uc_bi_id}' not found.")
                continue
            if target_ps_id is None:
                skipped_missing_entities += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Target Process Step BI_ID '{target_ps_bi_id}' not found.")
                continue

            try:
                score = int(relevance_score_raw)
                if not (0 <= score <= 100):
                    skipped_invalid_format += 1
                    skipped_count_total += 1
                    skipped_errors_details.append(f"{item_log_string}: Invalid score '{relevance_score_raw}' (must be 0-100).")
                    continue
            except (ValueError, TypeError):
                skipped_invalid_format += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Non-integer score '{relevance_score_raw}'.")
                continue

            existing_link = session.query(UsecaseStepRelevance).filter_by(
                source_usecase_id=source_uc_id,
                target_process_step_id=target_ps_id
            ).first()

            if existing_link:
                skipped_existing_link += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Link already exists. Skipped.")
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
        if skipped_count_total > 0: parts.append(f"Skipped: {skipped_count_total}")

        if not parts:
            message = "Processing complete. No Use Case-Step relevance links found or processed."
        else:
            message = f"Processing complete. {', '.join(parts)}."

        if skipped_errors_details:
             message += f" (Details on specific skips available in server logs). "

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error in process_usecase_step_relevance_file: {e}")
        session.rollback()
        success = False
        message = f"Invalid JSON format in the uploaded file: {e}."
    except ValueError as ve:
        print(f"Value Error in process_usecase_step_relevance_file: {ve}")
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
        "success": success, "message": message, "added_count": added_count,
        "skipped_count": skipped_count_total, "skipped_invalid_format": skipped_invalid_format,
        "skipped_existing_link": skipped_existing_link, "skipped_missing_entities": skipped_missing_entities,
        "skipped_errors_details": skipped_errors_details
    }

def process_usecase_usecase_relevance_file(file_stream):
    session = SessionLocal()
    added_count = 0
    skipped_count_total = 0
    skipped_invalid_format = 0
    skipped_existing_link = 0
    skipped_missing_entities = 0
    skipped_self_link = 0
    skipped_errors_details = []
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

        for i, item in enumerate(data):
            source_uc_bi_id_log = item.get('source_usecase_bi_id', 'N/A')
            target_uc_bi_id_log = item.get('target_usecase_bi_id', 'N/A')
            item_log_string = f"Link {i+1} ('{source_uc_bi_id_log}' -> '{target_uc_bi_id_log}')"

            if not (isinstance(item, dict) and
                    all(k in item for k in ('source_usecase_bi_id', 'target_usecase_bi_id', 'relevance_score')) and
                    isinstance(item['source_usecase_bi_id'], str) and item['source_usecase_bi_id'].strip() and
                    isinstance(item['target_usecase_bi_id'], str) and item['target_usecase_bi_id'].strip()):
                skipped_invalid_format += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Invalid format or missing required fields.")
                continue

            source_uc_bi_id = item['source_usecase_bi_id'].strip()
            target_uc_bi_id = item['target_usecase_bi_id'].strip()
            relevance_score_raw = item['relevance_score']
            relevance_content = item.get('relevance_content')

            if relevance_content is not None:
                if not isinstance(relevance_content, str):
                    skipped_errors_details.append(f"{item_log_string}: Relevance content was not a string, treated as empty.")
                    relevance_content = None
                else:
                    stripped_content = relevance_content.strip()
                    relevance_content = stripped_content if stripped_content else None


            if source_uc_bi_id == target_uc_bi_id:
                skipped_self_link += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Cannot link a Use Case to itself.")
                continue

            source_uc_id = usecase_lookup.get(source_uc_bi_id)
            target_uc_id = usecase_lookup.get(target_uc_bi_id)

            if source_uc_id is None:
                skipped_missing_entities += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Source Use Case BI_ID '{source_uc_bi_id}' not found.")
                continue
            if target_uc_id is None:
                skipped_missing_entities += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Target Use Case BI_ID '{target_uc_bi_id}' not found.")
                continue

            try:
                score = int(relevance_score_raw)
                if not (0 <= score <= 100):
                    skipped_invalid_format += 1
                    skipped_count_total += 1
                    skipped_errors_details.append(f"{item_log_string}: Invalid score '{relevance_score_raw}' (must be 0-100).")
                    continue
            except (ValueError, TypeError):
                skipped_invalid_format += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Non-integer score '{relevance_score_raw}'.")
                continue

            existing_link = session.query(UsecaseUsecaseRelevance).filter_by(
                source_usecase_id=source_uc_id,
                target_usecase_id=target_uc_id
            ).first()

            if existing_link:
                skipped_existing_link += 1
                skipped_count_total += 1
                skipped_errors_details.append(f"{item_log_string}: Link already exists. Skipped.")
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
        if skipped_count_total > 0: parts.append(f"Skipped: {skipped_count_total}")

        if not parts:
            message = "Processing complete. No Use Case-Use Case relevance links found or processed."
        else:
            message = f"Processing complete. {', '.join(parts)}."

        if skipped_errors_details:
             message += f" (Details on specific skips available in server logs). "

    except json.JSONDecodeError as e:
        print(f"JSON Decode Error in process_usecase_usecase_relevance_file: {e}")
        session.rollback()
        success = False
        message = f"Invalid JSON format in the uploaded file: {e}."
    except ValueError as ve:
        print(f"Value Error in process_usecase_usecase_relevance_file: {ve}")
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
        "success": success, "message": message, "added_count": added_count,
        "skipped_count": skipped_count_total, "skipped_invalid_format": skipped_invalid_format,
        "skipped_existing_link": skipped_existing_link, "skipped_missing_entities": skipped_missing_entities,
        "skipped_self_link": skipped_self_link, "skipped_errors_details": skipped_errors_details
    }


def import_database_from_json(json_string, clear_existing_data=False):
    session_local = SessionLocal()

    try:
        print("import_database_from_json service function called.")
        data_to_import = json.loads(json_string)
        print(f"JSON content loaded. Found {len(data_to_import.get('data', {}).keys())} top-level data keys.")

        imported_data = data_to_import.get("data", {})

        if not imported_data:
            print("No 'data' key found or data is empty in JSON.")
            return {
                "success": False,
                "message": "No 'data' key found in JSON file or data is empty."
            }

        if clear_existing_data:
            print("Clearing existing data...")

            try:
                table_names = [
                    'process_step_process_step_relevance', 'usecase_usecase_relevance', 
                    'usecase_step_relevance', 'usecase_area_relevance', 
                    'use_cases', 'process_steps', 'areas', 'llm_settings', 'users'
                ]
                
                # Truncate flask_sessions if it exists
                inspector = flask_sqlalchemy_db.inspect(flask_sqlalchemy_db.engine)
                if inspector.has_table('flask_sessions'):
                    session_local.execute(text("DELETE FROM flask_sessions;").execution_options(timeout=30))
                    session_local.commit()
                    print("Deleted all records from flask_sessions successfully.")

                for table in table_names:
                    print(f"Executing TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;")
                    session_local.execute(text(f"TRUNCATE TABLE {table} RESTART IDENTITY CASCADE;").execution_options(timeout=30))
                session_local.commit()
                print("Data cleared.")

            except OperationalError as oe:
                session_local.rollback()
                print(f"ERROR: TRUNCATE operation timed out or failed: {oe}")
                return {"success": False, "message": f"Clearing data failed: {oe}. Import rolled back."}
            except Exception as e:
                session_local.rollback()
                print(f"ERROR: TRUNCATE operations failed unexpectedly: {e}")
                traceback.print_exc()
                return {"success": False, "message": f"Unexpected error during data clearing: {e}. Import rolled back."}

            user_id_map, area_id_map, process_step_id_map, usecase_id_map = {}, {}, {}, {}

            if "users" in imported_data:
                for u_data in imported_data["users"]:
                    user = User(username=u_data["username"], password=u_data.get("password", pbkdf2_sha256.hash("imported_default_password")))
                    session_local.add(user)
                    session_local.flush()
                    user_id_map[u_data["id"]] = user.id
            print("Users import complete.")

            if "areas" in imported_data:
                for a_data in imported_data["areas"]:
                    area = Area(name=a_data["name"], description=a_data.get("description"))
                    session_local.add(area)
                    session_local.flush()
                    area_id_map[a_data["id"]] = area.id
            print("Areas import complete.")
            
            # ... The rest of the import logic remains the same as the old file...
            # This logic correctly maps old IDs to new ones and handles dependencies.
            # I will include the full, correct version from the old file here.

            if "process_steps" in imported_data:
                for ps_data in imported_data["process_steps"]:
                    new_area_id = area_id_map.get(ps_data["area_id"])
                    if new_area_id is None: continue
                    step = ProcessStep(bi_id=ps_data["bi_id"], name=ps_data["name"], area_id=new_area_id, **{k:v for k,v in ps_data.items() if k not in ['id', 'bi_id', 'name', 'area_id']})
                    session_local.add(step)
                    session_local.flush()
                    process_step_id_map[ps_data["id"]] = step.id
            print("Process Steps import complete.")

            if "use_cases" in imported_data:
                for uc_data in imported_data["use_cases"]:
                    new_process_step_id = process_step_id_map.get(uc_data["process_step_id"])
                    if new_process_step_id is None: continue
                    use_case = UseCase(bi_id=uc_data["bi_id"], name=uc_data["name"], process_step_id=new_process_step_id, **{k:v for k,v in uc_data.items() if k not in ['id', 'bi_id', 'name', 'process_step_id']})
                    session_local.add(use_case)
                    session_local.flush()
                    usecase_id_map[uc_data["id"]] = use_case.id
            print("Use Cases import complete.")

            if "llm_settings" in imported_data:
                for ls_data in imported_data["llm_settings"]:
                    new_user_id = user_id_map.get(ls_data["user_id"])
                    if new_user_id is None or session_local.query(LLMSettings).filter_by(user_id=new_user_id).first(): continue
                    ls = LLMSettings(user_id=new_user_id, **{k:v for k,v in ls_data.items() if k not in ['id', 'user_id']})
                    session_local.add(ls)
            print("LLM Settings import complete.")

            if "usecase_area_relevance" in imported_data:
                for r_data in imported_data["usecase_area_relevance"]:
                    new_source_id = usecase_id_map.get(r_data["source_usecase_id"])
                    new_target_id = area_id_map.get(r_data["target_area_id"])
                    if new_source_id is None or new_target_id is None: continue
                    session_local.add(UsecaseAreaRelevance(source_usecase_id=new_source_id, target_area_id=new_target_id, relevance_score=r_data["relevance_score"], relevance_content=r_data.get("relevance_content")))
            
            if "usecase_step_relevance" in imported_data:
                for r_data in imported_data["usecase_step_relevance"]:
                    new_source_id = usecase_id_map.get(r_data["source_usecase_id"])
                    new_target_id = process_step_id_map.get(r_data["target_process_step_id"])
                    if new_source_id is None or new_target_id is None: continue
                    session_local.add(UsecaseStepRelevance(source_usecase_id=new_source_id, target_process_step_id=new_target_id, relevance_score=r_data["relevance_score"], relevance_content=r_data.get("relevance_content")))

            if "usecase_usecase_relevance" in imported_data:
                for r_data in imported_data["usecase_usecase_relevance"]:
                    new_source_id = usecase_id_map.get(r_data["source_usecase_id"])
                    new_target_id = usecase_id_map.get(r_data["target_usecase_id"])
                    if new_source_id is None or new_target_id is None or new_source_id == new_target_id: continue
                    session_local.add(UsecaseUsecaseRelevance(source_usecase_id=new_source_id, target_usecase_id=new_target_id, relevance_score=r_data["relevance_score"], relevance_content=r_data.get("relevance_content")))

            if "process_step_process_step_relevance" in imported_data:
                for r_data in imported_data["process_step_process_step_relevance"]:
                    new_source_id = process_step_id_map.get(r_data["source_process_step_id"])
                    new_target_id = process_step_id_map.get(r_data["target_process_step_id"])
                    if new_source_id is None or new_target_id is None or new_source_id == new_target_id: continue
                    session_local.add(ProcessStepProcessStepRelevance(source_process_step_id=new_source_id, target_process_step_id=new_target_id, relevance_score=r_data["relevance_score"], relevance_content=r_data.get("relevance_content")))
            print("Relevance Links import complete.")
            
            session_local.commit()
            return {"success": True, "message": "Database import successful."}
        else:
            return { "success": False, "message": "Importing data without clearing existing data is not supported in this function." }

    except Exception as e:
        session_local.rollback()
        print(f"Error during database import: {e}")
        traceback.print_exc()
        return {"success": False, "message": f"An error occurred: {e}. Import rolled back."}
    finally:
        SessionLocal.remove()