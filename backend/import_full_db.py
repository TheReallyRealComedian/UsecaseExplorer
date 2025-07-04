# UsecaseExplorer/backend/import_full_db.py

import sys
import os
import json
import time
import traceback

# Add the parent directory of backend to the sys.path
# This is necessary for running this script directly inside the container
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from backend.app import create_app
from backend.services.data_management_service import import_database_from_json
from backend.db import SessionLocal

# --- Configuration ---
# Path inside the Docker container
CONTAINER_JSON_PATH = '/app/exported_db.json'


# --- Main Script Logic ---
if __name__ == "__main__":
    print("Starting full database import script...")

    # 1. Load JSON data from the specified path
    if not os.path.exists(CONTAINER_JSON_PATH):
        print(
            f"Error: JSON file not found at '{CONTAINER_JSON_PATH}'. "
            "Please ensure it was copied into the container."
        )
        sys.exit(1)

    print(f"Loading JSON data from {CONTAINER_JSON_PATH}...")
    try:
        with open(CONTAINER_JSON_PATH, 'r', encoding='utf-8') as f:
            json_data = f.read()
        print("JSON data loaded successfully.")
    except Exception as e:
        print(f"Error reading JSON file: {e}")
        sys.exit(1)

    # 2. Create a Flask application context for database operations
    print("Creating Flask application context...")
    app = create_app()
    with app.app_context():
        print("Flask app context entered. Proceeding with database import...")
        
        # Optional: Give database a moment if it just started
        # time.sleep(5)

        # 3. Call the import service function directly
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
            traceback.print_exc()
            sys.exit(1)
        finally:
            # Ensure the SQLAlchemy session is closed
            SessionLocal.remove()
            print("SQLAlchemy session removed.")

    print("Database import script finished.")
    sys.exit(0)