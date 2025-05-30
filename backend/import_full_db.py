# UsecaseExplorer/import_full_db.py

import sys
import os
import json
import time # For optional delays

# Add the parent directory of backend to the sys.path
# This allows 'from backend.app import create_app' and 'from backend.injection_service import ...' to work
# when run directly. In Docker, PYTHONPATH is typically set, making this less critical
# but good for local testing environment consistency.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), 'backend')))

from backend.app import create_app
from backend.injection_service import import_database_from_json
from backend.db import SessionLocal # Import to ensure SessionLocal is used properly

# --- Configuration ---
# Path inside the Docker container where the JSON file will be copied
# This must match where you docker cp the file to.
CONTAINER_JSON_PATH = '/app/backend/exported_db.json'


# --- Main Script Logic ---
if __name__ == "__main__":
    print("Starting full database import script...")

    # 1. Load JSON data from the specified path
    if not os.path.exists(CONTAINER_JSON_PATH):
        print(f"Error: JSON file not found at '{CONTAINER_JSON_PATH}'. Please ensure it was copied into the container.")
        sys.exit(1)

    print(f"Loading JSON data from {CONTAINER_JSON_PATH}...")
    try:
        with open(CONTAINER_JSON_PATH, 'r', encoding='utf-8') as f:
            json_data = f.read()
        print("JSON data loaded successfully.")
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)

    # 2. Create a Flask application context
    # This is CRUCIAL because `import_database_from_json` (and SQLAlchemy's SessionLocal)
    # depends on a Flask app being initialized for database configuration.
    print("Creating Flask application context for database operations...")
    app = create_app()
    # Explicitly push the application context
    # This makes `current_app` and `db.engine` (from Flask-SQLAlchemy) available.
    with app.app_context():
        print("Flask app context entered. Proceeding with database import...")
        # Optional: Give database a moment if it just started or stopped/started
        # time.sleep(5) 

        # 3. Call the import service function
        # `clear_existing_data=True` is vital for a full import
        try:
            result = import_database_from_json(json_data, clear_existing_data=True)
            print("\n--- IMPORT RESULT ---")
            print(f"Success: {result['success']}")
            print(f"Message: {result['message']}")
            print("---------------------")

            if not result['success']:
                print("Database import failed. Check messages above for details.")
                sys.exit(1)
        except Exception as e:
            print(f"An unexpected error occurred during database import: {e}")
            sys.exit(1)
        finally:
            # Ensure the SQLAlchemy session is closed.
            # In a Flask request context, `app.teardown_request` handles this.
            # When running standalone, it's good practice to ensure it's removed.
            SessionLocal.remove()
            print("SQLAlchemy session removed.")

    print("Database import script finished.")
    sys.exit(0)