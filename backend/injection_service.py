# backend/injection_service.py
import json
import traceback
from sqlalchemy.exc import IntegrityError
from .app import SessionLocal
from .models import Area, ProcessStep, UseCase # Add UseCase here

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
        # Ensure the stream is read correctly
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
        elif added_count > 0 or skipped_count > 0 or duplicates: # Catches various combinations
             message = f"Processing complete. Added: {added_count}, Skipped: {skipped_count}."
             if duplicates:
                message += f" Duplicate name(s) found: {len(duplicates)}."
        else: # No data processed implies added_count=0, skipped_count=0, no duplicates
            message = "Processing complete. No data found or processed in the file."


    except json.JSONDecodeError:
        print("JSON Decode Error in process_area_file") # Debug log
        session.rollback()
        success = False
        message = "Invalid JSON format in the uploaded file."
        added_count = 0
        skipped_count = 0
        duplicates = []
    except ValueError as ve: # Keep specific ValueError for format issues as in original
        session.rollback()
        success = False
        message = f"Error: {ve}"
        added_count = 0
        skipped_count = 0
        duplicates = []
    except Exception as e:
        traceback.print_exc() # This will print the full stack trace
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
        print("Processing step file") # Debug log
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
        print("JSON Decode Error in process_step_file") # Debug log
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
        traceback.print_exc() # This will print the full stack trace
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
        print("Processing use case file") # Debug log
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
            if not (isinstance(item, dict) and
                    all(k in item for k in ('bi_id', 'name', 'process_step_bi_id')) and
                    isinstance(item['bi_id'], str) and item['bi_id'].strip() and
                    isinstance(item['name'], str) and item['name'].strip() and
                    isinstance(item['process_step_bi_id'], str) and item['process_step_bi_id'].strip()):
                skipped_invalid_format += 1
                continue

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
                    if 1 <= priority_val <= 4: # Assuming priority 1-4
                        priority = priority_val
                    else:
                        print(f"Skipping item with invalid priority value '{priority_str}': {item}")
                        skipped_invalid_format += 1
                        continue
                except ValueError:
                    print(f"Skipping item with non-integer priority '{priority_str}': {item}")
                    skipped_invalid_format += 1
                    continue
            
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
                bi_id=uc_bi_id, name=name, process_step_id=process_step_id,
                priority=priority, raw_content=raw_content,
                summary=summary, inspiration=inspiration
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
        print("JSON Decode Error in process_usecase_file") # Debug log
        session.rollback()
        success = False
        message = "Invalid JSON format in the uploaded file."
        added_count = 0
        skipped_invalid_format = 0
        skipped_duplicate_uc_bi_id = 0
        skipped_missing_step = 0
        duplicate_uc_bi_ids = []
        missing_step_bi_ids = []
    except ValueError as ve:
        session.rollback()
        success = False
        message = f"Error: {ve}"
        added_count = 0
        skipped_invalid_format = 0
        skipped_duplicate_uc_bi_id = 0
        skipped_missing_step = 0
        duplicate_uc_bi_ids = []
        missing_step_bi_ids = []
    except Exception as e:
        traceback.print_exc() # This will print the full stack trace
        session.rollback()
        success = False
        message = f"An error occurred: {str(e)}"
        added_count = 0
        skipped_invalid_format = 0
        skipped_duplicate_uc_bi_id = 0
        skipped_missing_step = 0
        duplicate_uc_bi_ids = []
        missing_step_bi_ids = []
    finally:
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