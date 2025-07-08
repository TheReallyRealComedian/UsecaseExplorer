# backend/services/data_management_service.py
import json
import traceback
from sqlalchemy import text
from passlib.hash import pbkdf2_sha256
from sqlalchemy.exc import IntegrityError, OperationalError
from ..db import SessionLocal, db as flask_sqlalchemy_db
from ..models import (
    Base, User, Area, ProcessStep, UseCase, LLMSettings,
    UsecaseAreaRelevance, UsecaseStepRelevance, UsecaseUsecaseRelevance,
    ProcessStepProcessStepRelevance, Tag
)
from datetime import datetime
from sqlalchemy.orm import Session

def datetime_serializer(obj):
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} not serializable")

def _get_or_create_tags(db_session: Session, tag_string: str, category: str, tag_cache: dict):
    """
    Efficiently gets or creates tags from a comma-separated string, using a
    per-request cache to avoid duplicate creation within a single transaction.
    """
    if not tag_string or not isinstance(tag_string, str):
        return []

    tag_names = {name.strip() for name in tag_string.split(',') if name.strip()}
    if not tag_names:
        return []

    tags_to_return = []
    tags_to_query = []

    # First, check the cache
    for name in tag_names:
        cache_key = (name, category)
        if cache_key in tag_cache:
            tags_to_return.append(tag_cache[cache_key])
        else:
            tags_to_query.append(name)
    
    # If there are tags not in the cache, query the DB
    if tags_to_query:
        existing_tags_from_db = db_session.query(Tag).filter(
            Tag.category == category,
            Tag.name.in_(tags_to_query)
        ).all()

        for tag in existing_tags_from_db:
            cache_key = (tag.name, tag.category)
            tag_cache[cache_key] = tag
            tags_to_return.append(tag)
        
        existing_names_from_db = {t.name for t in existing_tags_from_db}

        # Create new tags for those that were not in cache and not in DB
        for name in tags_to_query:
            if name not in existing_names_from_db:
                new_tag = Tag(name=name, category=category)
                db_session.add(new_tag) # Add to session, will be flushed
                cache_key = (name, category)
                tag_cache[cache_key] = new_tag
                tags_to_return.append(new_tag)

    return tags_to_return


def process_area_file(file_stream):
    session = SessionLocal()
    added_count = 0
    updated_count = 0
    skipped_count = 0
    duplicates_not_updated = []
    skipped_errors_details = []

    # --- START MODIFICATION: Track names processed within this single file/transaction ---
    processed_names_in_this_run = set()

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
            
            # --- START MODIFICATION: Check for duplicates within the file itself ---
            if area_name in processed_names_in_this_run:
                skipped_count += 1
                skipped_errors_details.append(f"{item_identifier}: Duplicate name found within the uploaded file. Skipping subsequent entry.")
                continue
            
            # Add to the set to mark it as processed for this run
            processed_names_in_this_run.add(area_name)
            # --- END MODIFICATION ---

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
                # --- START MODIFICATION: More permissive update logic ---
                # Update description if it's different, not just if it was empty.
                db_desc = existing_area.description or ""
                json_desc = description_from_json or ""
                
                if description_from_json is not None and db_desc != json_desc:
                    existing_area.description = description_from_json
                    item_updated = True
                # --- END MODIFICATION ---

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
        if skipped_errors_details: # The route handler will now display these details.
            print("Skipped item details:", skipped_errors_details) # Keep server-side logging for debug.

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


def analyze_json_import(json_data, model_class, unique_key_field='bi_id'):
    """
    Analyzes a list of JSON objects against existing data in the database.
    This function performs the comparison and generates a detailed preview.
    """
    session = SessionLocal()
    preview_data = []
    
    # Create a lookup for existing items for efficiency
    existing_items_query = session.query(model_class).all()
    existing_items_map = {getattr(item, unique_key_field): item for item in existing_items_query}
    
    for json_item in json_data:
        identifier = json_item.get(unique_key_field)
        entry = {
            'status': 'error',
            'action': 'skip',
            'identifier': identifier,
            'json_item': json_item,
            'db_item': None,
            'diff': {},
            'messages': []
        }

        if not identifier:
            entry['messages'].append(f"Skipped: Item is missing the unique identifier field '{unique_key_field}'.")
            preview_data.append(entry)
            continue

        existing_item = existing_items_map.get(identifier)

        if existing_item:
            # --- Item exists, check for updates ---
            entry['status'] = 'no_change'
            entry['action'] = 'skip' # Default for no_change
            entry['db_item'] = {c.name: getattr(existing_item, c.name) for c in existing_item.__table__.columns}
            
            is_dirty = False
            for key, new_value in json_item.items():
                if hasattr(existing_item, key):
                    old_value = getattr(existing_item, key)
                    # Simple comparison, can be made more sophisticated
                    if str(old_value) != str(new_value):
                        is_dirty = True
                        entry['diff'][key] = {'old': old_value, 'new': new_value}

            if is_dirty:
                entry['status'] = 'update'
                entry['action'] = 'update' # Propose update by default
                changed_fields = ", ".join(entry['diff'].keys())
                entry['messages'].append(f"Will update fields: {changed_fields}.")
            else:
                entry['messages'].append("Item already exists and matches the database.")
        else:
            # --- Item is new ---
            entry['status'] = 'new'
            entry['action'] = 'add'
            entry['messages'].append("This is a new item that will be created.")

        preview_data.append(entry)
        
    session.close()
    return {"success": True, "preview_data": preview_data}


def finalize_import(resolved_data, model_class, unique_key_field='bi_id'):
    """
    Takes user-approved changes from the preview and commits them to the DB.
    """
    session = SessionLocal()
    added_count, updated_count, skipped_count, failed_count = 0, 0, 0, 0
    
    try:
        for item in resolved_data:
            action = item.get('action')
            identifier = item.get('identifier')
            data = item.get('data')

            if action == 'skip':
                skipped_count += 1
                continue
            
            if action == 'add':
                try:
                    new_obj = model_class(**data)
                    session.add(new_obj)
                    session.flush() # Flush to catch integrity errors early
                    added_count += 1
                except Exception as e:
                    failed_count += 1
                    print(f"Failed to add item {identifier}: {e}") # Log error
            
            elif action == 'update':
                try:
                    obj_to_update = session.query(model_class).filter(getattr(model_class, unique_key_field) == identifier).first()
                    if obj_to_update:
                        for key, value in data.items():
                            setattr(obj_to_update, key, value)
                        updated_count += 1
                    else:
                        failed_count += 1 # Cannot update if it doesn't exist
                except Exception as e:
                    failed_count += 1
                    print(f"Failed to update item {identifier}: {e}") # Log error

        if failed_count > 0:
            session.rollback()
            return {"success": False, "message": f"Import failed. {failed_count} errors occurred. No changes were saved."}

        session.commit()
        return {
            "success": True, 
            "message": f"Import successful! Added: {added_count}, Updated: {updated_count}, Skipped: {skipped_count}."
        }
    except Exception as e:
        session.rollback()
        return {"success": False, "message": f"A critical error occurred: {e}. All changes have been rolled back."}
    finally:
        session.close()


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
        'usecase_type_category': 'usecase_type_category',
        'llm_comment_1': 'llm_comment_1', 'llm_comment_2': 'llm_comment_2',
        'llm_comment_3': 'llm_comment_3', 'llm_comment_4': 'llm_comment_4',
        'llm_comment_5': 'llm_comment_5'
    }

    try:
        print("Processing use case file (with update logic)")
        tag_cache = {}
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
                if json_key in item: 
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
                for model_attr, json_val in uc_fields_from_json.items():
                    db_value = getattr(existing_usecase, model_attr, None)
                    db_value_normalized = db_value.strip() if isinstance(db_value, str) else db_value
                    if db_value_normalized == '': db_value_normalized = None

                    if json_val != db_value_normalized:
                        setattr(existing_usecase, model_attr, json_val)
                        item_updated = True
                
                new_process_step_id = step_lookup.get(process_step_bi_id)
                if new_process_step_id and new_process_step_id != existing_usecase.process_step_id:
                    existing_usecase.process_step_id = new_process_step_id
                    item_updated = True

                tags_to_update = {
                    'it_systems': 'it_system',
                    'data_types': 'data_type',
                }
                
                current_tags = list(existing_usecase.tags)
                tags_have_changed_in_json = any(key in item for key in tags_to_update)

                if tags_have_changed_in_json:
                    final_tags = [tag for tag in current_tags if tag.category not in tags_to_update.values()]
                    for json_key, category in tags_to_update.items():
                         if json_key in item:
                            new_tags_for_category = _get_or_create_tags(session, item[json_key], category, tag_cache)
                            final_tags.extend(new_tags_for_category)
                    
                    existing_usecase.tags = final_tags
                    item_updated = True

                if item_updated:
                    updated_count += 1
                else:
                    skipped_existing_no_update_uc_bi_id_count += 1
                    skipped_count_total += 1
                    if uc_bi_id not in uc_bi_ids_existing_no_update:
                        uc_bi_ids_existing_no_update.append(uc_bi_id)
                    skipped_errors_details.append(f"{item_log_string}: Already exists with no fields to update. Skipped.")
            else: # New use case
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
                new_uc_data.update(uc_fields_from_json)
                
                new_uc = UseCase(**new_uc_data)
                
                it_system_tags = _get_or_create_tags(session, item.get('it_systems', ''), 'it_system', tag_cache)
                data_type_tags = _get_or_create_tags(session, item.get('data_types', ''), 'data_type', tag_cache)
                new_uc.tags = it_system_tags + data_type_tags

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

        if skipped_errors_details: # The route handler will now display these details.
             print("Skipped item details:", skipped_errors_details) # Keep server-side logging for debug.

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

        if skipped_errors_details: # The route handler will now display these details.
             print("Skipped item details:", skipped_errors_details) # Keep server-side logging for debug.

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

        if skipped_errors_details: # The route handler will now display these details.
             print("Skipped item details:", skipped_errors_details) # Keep server-side logging for debug.

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

        if skipped_errors_details: # The route handler will now display these details.
             print("Skipped item details:", skipped_errors_details) # Keep server-side logging for debug.

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

        if skipped_errors_details: # The route handler will now display these details.
             print("Skipped item details:", skipped_errors_details) # Keep server-side logging for debug.

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