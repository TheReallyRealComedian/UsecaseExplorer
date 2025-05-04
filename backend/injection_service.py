# backend/injection_service.py
import json
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
    error_message = None
    success = False # Default to False

    try:
        # Ensure the stream is read correctly
        try:
            data = json.load(file_stream)
        except UnicodeDecodeError:
             file_stream.seek(0)
             data = json.loads(file_stream.read().decode('utf-8'))

        if not isinstance(data, list):
            raise ValueError("Invalid JSON format: Top level must be a list.")

        # Get existing area names for duplicate checking
        existing_names = {name[0] for name in session.query(Area.name).all()}

        for item in data:
            # Validate item structure
            if not isinstance(item, dict):
                skipped_count += 1
                continue
            if 'name' not in item:
                skipped_count += 1
                continue

            area_name = item['name']
            if not isinstance(area_name, str) or not area_name.strip():
                skipped_count += 1
                continue

            area_name = area_name.strip()

            # Check for duplicates
            if area_name in existing_names:
                if area_name not in duplicates:
                     duplicates.append(area_name)
                skipped_count += 1
            else:
                # Add new Area
                new_area = Area(name=area_name)
                session.add(new_area)
                existing_names.add(area_name) # Add to set to catch intra-file duplicates
                added_count += 1

        session.commit()
        success = True

        # Construct result message
        if added_count == 0 and skipped_count > 0:
             message = "Processing complete. No new areas were added."
             if duplicates:
                message += f" {len(duplicates)} duplicate name(s) found."
        elif added_count > 0 and skipped_count == 0:
             message = f"Successfully added {added_count} new area(s)."
        else: # Mix of added and skipped or only skipped with no duplicates
             message = f"Processing complete. Added: {added_count}, Skipped: {skipped_count}."
             if duplicates:
                message += f" Duplicate name(s) found: {len(duplicates)}."
        if added_count == 0 and skipped_count == 0 and not duplicates:
            message = "Processing complete. No data found or processed in the file."


    except json.JSONDecodeError:
        success = False
        message = "Error: Invalid JSON file. Could not decode content."
        session.rollback()
    except ValueError as ve:
        success = False
        message = f"Error: {ve}"
        session.rollback()
    except Exception as e:
        success = False
        message = f"An unexpected error occurred: {e}"
        print(f"Area Injection Error: {e}")
        session.rollback()
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
    error_message = None
    success = False

    try:
        # Pre-fetch existing data for efficiency
        area_lookup = {
            area.name: area.id for area in session.query(Area.name, Area.id).all()
        }
        existing_bi_ids = {
            step.bi_id for step in session.query(ProcessStep.bi_id).all()
        }

        # Load and parse JSON data
        try:
            data = json.load(file_stream)
        except UnicodeDecodeError:
            file_stream.seek(0)
            data = json.loads(file_stream.read().decode('utf-8'))

        if not isinstance(data, list):
            raise ValueError("Invalid JSON format: Top level must be a list.")

        for item in data:
            # Validate item format
            if not isinstance(item, dict):
                skipped_invalid_format += 1
                continue
            if not all(k in item for k in ('bi_id', 'name', 'area_name')):
                skipped_invalid_format += 1
                continue

            bi_id = item['bi_id']
            name = item['name']
            area_name = item['area_name']

            # Validate required field types and content
            if not (isinstance(bi_id, str) and bi_id.strip() and
                    isinstance(name, str) and name.strip() and
                    isinstance(area_name, str) and area_name.strip()):
                skipped_invalid_format += 1
                continue

            bi_id = bi_id.strip()
            name = name.strip()
            area_name = area_name.strip()

            # Get optional fields safely
            raw_content = item.get('raw_content')
            summary = item.get('summary')
            if raw_content is not None and not isinstance(raw_content, str):
                raw_content = None
            if summary is not None and not isinstance(summary, str):
                summary = None

            # Check for duplicate bi_id
            if bi_id in existing_bi_ids:
                skipped_duplicate_bi_id += 1
                if bi_id not in duplicates_bi_ids:
                    duplicates_bi_ids.append(bi_id)
                continue

            # Check if Area exists
            if area_name not in area_lookup:
                skipped_missing_area += 1
                if area_name not in missing_area_names:
                    missing_area_names.append(area_name)
                continue

            # If all checks pass, add the new Process Step
            area_id = area_lookup[area_name]
            new_step = ProcessStep(
                bi_id=bi_id,
                name=name,
                area_id=area_id,
                raw_content=raw_content if raw_content else None,
                summary=summary if summary else None
            )
            session.add(new_step)
            existing_bi_ids.add(bi_id) # Add to set to catch intra-file duplicates
            added_count += 1

        session.commit()
        success = True

    except json.JSONDecodeError:
        error_message = "Error: Invalid JSON file. Could not decode content."
        session.rollback()
    except ValueError as ve:
        error_message = f"Error: {ve}"
        session.rollback()
    except Exception as e:
        error_message = f"An unexpected error occurred during processing: {e}"
        print(f"Step Injection Error: {e}")
        session.rollback()
    finally:
        SessionLocal.remove()

    # Construct the result message
    if error_message:
         message = error_message
    else:
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
             message += f" Duplicates found: {', '.join(duplicates_bi_ids)}."
         if missing_area_names:
             message += f" Missing areas: {', '.join(missing_area_names)}."

    # Final result dictionary
    return {
        "success": success and error_message is None,
        "message": message,
        "added_count": added_count,
        "skipped_count": skipped_invalid_format + skipped_duplicate_bi_id + skipped_missing_area,
        "skipped_invalid_format": skipped_invalid_format,
        "skipped_duplicate_bi_id": skipped_duplicate_bi_id,
        "skipped_missing_area": skipped_missing_area,
        "duplicates_bi_ids": duplicates_bi_ids,
        "missing_area_names": missing_area_names
    }

# --- ADD NEW FUNCTION for Use Cases ---
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
    error_message = None
    success = False # Default to False

    try:
        # Pre-fetch existing data
        step_lookup = {
            step.bi_id: step.id
            for step in session.query(ProcessStep.bi_id, ProcessStep.id).all()
        }
        existing_uc_bi_ids = {
            uc.bi_id for uc in session.query(UseCase.bi_id).all()
        }

        # Load and parse JSON
        try:
            data = json.load(file_stream)
        except UnicodeDecodeError:
            file_stream.seek(0)
            data = json.loads(file_stream.read().decode('utf-8'))

        if not isinstance(data, list):
            raise ValueError("Invalid JSON format: Top level must be a list.")

        for item in data:
            # Validate item format
            if not isinstance(item, dict):
                skipped_invalid_format += 1
                continue
            if not all(k in item for k in ('bi_id', 'name', 'process_step_bi_id')):
                skipped_invalid_format += 1
                continue

            uc_bi_id = item['bi_id']
            name = item['name']
            process_step_bi_id = item['process_step_bi_id']

            # Validate required field types/content
            if not (isinstance(uc_bi_id, str) and uc_bi_id.strip() and
                    isinstance(name, str) and name.strip() and
                    isinstance(process_step_bi_id, str) and process_step_bi_id.strip()):
                skipped_invalid_format += 1
                continue

            uc_bi_id = uc_bi_id.strip()
            name = name.strip()
            process_step_bi_id = process_step_bi_id.strip()

            # Get optional fields
            raw_content = item.get('raw_content')
            summary = item.get('summary')
            inspiration = item.get('inspiration')
            # Ensure optional fields are strings or None
            if raw_content is not None and not isinstance(raw_content, str):
                raw_content = None
            if summary is not None and not isinstance(summary, str):
                summary = None
            if inspiration is not None and not isinstance(inspiration, str):
                inspiration = None


            # Check for duplicate Use Case bi_id
            if uc_bi_id in existing_uc_bi_ids:
                skipped_duplicate_uc_bi_id += 1
                if uc_bi_id not in duplicate_uc_bi_ids:
                    duplicate_uc_bi_ids.append(uc_bi_id)
                continue

            # Check if Process Step exists
            if process_step_bi_id not in step_lookup:
                skipped_missing_step += 1
                if process_step_bi_id not in missing_step_bi_ids:
                    missing_step_bi_ids.append(process_step_bi_id)
                continue

            # All checks pass, add new Use Case
            process_step_id = step_lookup[process_step_bi_id]
            new_uc = UseCase(
                bi_id=uc_bi_id,
                name=name,
                process_step_id=process_step_id,
                raw_content=raw_content,
                summary=summary,
                inspiration=inspiration
            )
            session.add(new_uc)
            existing_uc_bi_ids.add(uc_bi_id) # Add to set for intra-file check
            added_count += 1

        session.commit()
        success = True

    except json.JSONDecodeError:
        error_message = "Error: Invalid JSON file. Could not decode content."
        session.rollback()
    except ValueError as ve:
        error_message = f"Error: {ve}"
        session.rollback()
    except Exception as e:
        error_message = f"An unexpected error occurred during Use Case processing: {e}"
        print(f"Use Case Injection Error: {e}")
        session.rollback()
    finally:
        SessionLocal.remove()

    # Construct result message
    if error_message:
         message = error_message
    else:
         parts = []
         if added_count > 0:
             parts.append(f"Added: {added_count}")
         if skipped_invalid_format > 0:
             parts.append(f"Skipped (Invalid Format): {skipped_invalid_format}")
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

    # Final result
    return {
        "success": success and error_message is None,
        "message": message,
        "added_count": added_count,
        "skipped_count": skipped_invalid_format + skipped_duplicate_uc_bi_id + skipped_missing_step,
        "skipped_invalid_format": skipped_invalid_format,
        "skipped_duplicate_uc_bi_id": skipped_duplicate_uc_bi_id,
        "skipped_missing_step": skipped_missing_step,
        "duplicate_uc_bi_ids": duplicate_uc_bi_ids,
        "missing_step_bi_ids": missing_step_bi_ids
    }
# --- END Use Case Function ---