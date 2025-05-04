# backend/injection_service.py
import json
from .app import SessionLocal # Import the session manager from app.py
from .models import Area      # Import the Area model

def process_area_file(file_stream):
    """
    Processes an uploaded JSON file stream to add new Areas to the database.

    Args:
        file_stream: A file-like object containing the JSON data.

    Returns:
        A dictionary containing processing results:
        {
            "success": bool,
            "message": str,
            "added_count": int,
            "skipped_count": int,
            "duplicates": list[str]
        }
    """
    session = SessionLocal()
    added_count = 0
    skipped_count = 0
    duplicates = []
    error_message = None

    try:
        # Ensure the stream is read correctly (uploaded files might need decoding)
        try:
            data = json.load(file_stream)
        except UnicodeDecodeError:
             # If direct load fails, try reading as bytes and decoding explicitly
             file_stream.seek(0) # Go back to the start of the stream
             data = json.loads(file_stream.read().decode('utf-8'))


        # Basic structure validation: should be a list
        if not isinstance(data, list):
            raise ValueError("Invalid JSON format: Top level must be a list.")

        # Get existing area names for duplicate checking (efficiently)
        existing_names = {name[0] for name in session.query(Area.name).all()}

        for item in data:
            # Validate item structure
            if not isinstance(item, dict):
                print(f"Skipping invalid item (not a dict): {item}")
                skipped_count += 1
                continue
            if 'name' not in item:
                print(f"Skipping item missing 'name' key: {item}")
                skipped_count += 1
                continue

            area_name = item['name']
            if not isinstance(area_name, str) or not area_name.strip():
                print(f"Skipping item with invalid or empty name: {item}")
                skipped_count += 1
                continue

            area_name = area_name.strip() # Clean whitespace

            # Check for duplicates
            if area_name in existing_names:
                # print(f"Skipping duplicate Area: {area_name}")
                if area_name not in duplicates: # Only record duplicate name once
                     duplicates.append(area_name)
                skipped_count += 1
            else:
                # Add new Area
                new_area = Area(name=area_name)
                session.add(new_area)
                existing_names.add(area_name) # Add to our set to catch duplicates within the file itself
                added_count += 1
                # print(f"Adding new Area: {area_name}")

        # Commit all added areas
        session.commit()
        success = True
        if added_count == 0 and skipped_count > 0:
             message = f"Processing complete. No new areas were added."
             if duplicates:
                message += f" {len(duplicates)} duplicate name(s) found."
        elif added_count > 0 and skipped_count == 0:
             message = f"Successfully added {added_count} new area(s)."
        else:
             message = f"Processing complete. Added: {added_count}, Skipped: {skipped_count}."
             if duplicates:
                message += f" Duplicate name(s) found: {len(duplicates)}."

    except json.JSONDecodeError:
        success = False
        message = "Error: Invalid JSON file. Could not decode content."
        session.rollback() # Rollback any potential partial adds if commit failed somehow before error
    except ValueError as ve:
        success = False
        message = f"Error: {ve}"
        session.rollback()
    except Exception as e:
        success = False
        message = f"An unexpected error occurred: {e}"
        print(f"Area Injection Error: {e}") # Log the full error
        session.rollback()
    finally:
        SessionLocal.remove() # Ensure session is closed

    return {
        "success": success,
        "message": message,
        "added_count": added_count,
        "skipped_count": skipped_count,
        "duplicates": duplicates
    }