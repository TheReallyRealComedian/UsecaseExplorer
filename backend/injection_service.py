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
                # Order matters due to foreign key constraints. Start with tables that depend on others.
                print("Executing TRUNCATE TABLE process_step_process_step_relevance RESTART IDENTITY CASCADE;")
                session_local.execute(text("TRUNCATE TABLE process_step_process_step_relevance RESTART IDENTITY CASCADE;").execution_options(timeout=30))
                session_local.commit()

                print("Executing TRUNCATE TABLE usecase_usecase_relevance RESTART IDENTITY CASCADE;")
                session_local.execute(text("TRUNCATE TABLE usecase_usecase_relevance RESTART IDENTITY CASCADE;").execution_options(timeout=30))
                session_local.commit()

                print("Executing TRUNCATE TABLE usecase_step_relevance RESTART IDENTITY CASCADE;")
                session_local.execute(text("TRUNCATE TABLE usecase_step_relevance RESTART IDENTITY CASCADE;").execution_options(timeout=30))
                session_local.commit()

                print("Executing TRUNCATE TABLE usecase_area_relevance RESTART IDENTITY CASCADE;")
                session_local.execute(text("TRUNCATE TABLE usecase_area_relevance RESTART IDENTITY CASCADE;").execution_options(timeout=30))
                session_local.commit()

                print("Executing TRUNCATE TABLE use_cases RESTART IDENTITY CASCADE;")
                session_local.execute(text("TRUNCATE TABLE use_cases RESTART IDENTITY CASCADE;").execution_options(timeout=30))
                session_local.commit()

                print("Executing TRUNCATE TABLE process_steps RESTART IDENTITY CASCADE;")
                session_local.execute(text("TRUNCATE TABLE process_steps RESTART IDENTITY CASCADE;").execution_options(timeout=30))
                session_local.commit()

                print("Executing TRUNCATE TABLE areas RESTART IDENTITY CASCADE;")
                session_local.execute(text("TRUNCATE TABLE areas RESTART IDENTITY CASCADE;").execution_options(timeout=30))
                session_local.commit()

                # flask_sessions might not exist or be managed differently, handle potential error
                try:
                    print("Attempting to clear flask_sessions.")
                    session_local.execute(text("DELETE FROM flask_sessions;").execution_options(timeout=30))
                    session_local.commit()
                    print("Deleted all records from flask_sessions successfully.")
                except Exception as e: # Catch a more general exception if table doesn't exist or other issues
                    session_local.rollback() # Rollback the attempt to delete from flask_sessions
                    print(f"Warning: Failed to clear flask_sessions table during import: {e}. This might be non-critical if the table doesn't exist or is unused.")
                    # Continue with the import as this might not be a fatal error for the core data.

                print("Executing TRUNCATE TABLE llm_settings RESTART IDENTITY CASCADE;")
                session_local.execute(text("TRUNCATE TABLE llm_settings RESTART IDENTITY CASCADE;").execution_options(timeout=30))
                session_local.commit()

                print("Executing TRUNCATE TABLE users RESTART IDENTITY CASCADE;")
                session_local.execute(text("TRUNCATE TABLE users RESTART IDENTITY CASCADE;").execution_options(timeout=30))
                session_local.commit()

                print("Data cleared.")

            except OperationalError as oe:
                session_local.rollback()
                print(f"ERROR: TRUNCATE operation timed out or failed with operational error: {oe}")
                return {"success": False, "message": f"Clearing data failed: {oe}. Import rolled back."}
            except Exception as e:
                session_local.rollback()
                print(f"ERROR: TRUNCATE operations failed unexpectedly: {e}")
                traceback.print_exc() # Print full traceback for unexpected errors
                return {"success": False, "message": f"Unexpected error during data clearing: {e}. Import rolled back."}


            user_id_map = {}
            area_id_map = {}
            process_step_id_map = {}
            usecase_id_map = {}

            print("Importing Users...")
            if "users" in imported_data:
                for u_data in imported_data["users"]:
                    user = User(username=u_data["username"])
                    if 'password' in u_data and u_data['password'] :
                        user.password = u_data['password'] # Assumes password is already hashed if stored directly
                    else:
                        user.set_password("imported_default_password") # Set a default password

                    session_local.add(user)
                    session_local.flush() # To get user.id
                    user_id_map[u_data["id"]] = user.id
            print("Users import complete.")

            print("Importing Areas...")
            if "areas" in imported_data:
                for a_data in imported_data["areas"]:
                    area = Area(
                        name=a_data["name"],
                        description=a_data.get("description")
                    )
                    session_local.add(area)
                    session_local.flush()
                    area_id_map[a_data["id"]] = area.id
            print("Areas import complete.")

            print("Importing Process Steps...")
            if "process_steps" in imported_data:
                for ps_data in imported_data["process_steps"]:
                    old_area_id = ps_data["area_id"]
                    new_area_id = area_id_map.get(old_area_id)

                    if new_area_id is None:
                        print(f"Warning: Original Area ID {old_area_id} for step '{ps_data.get('name', 'N/A')}' (BI_ID: {ps_data.get('bi_id', 'N/A')}) not found in new mapping. Skipping step.")
                        continue

                    step = ProcessStep(
                        bi_id=ps_data["bi_id"],
                        name=ps_data["name"],
                        area_id=new_area_id,
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
                    session_local.add(step)
                    session_local.flush()
                    process_step_id_map[ps_data["id"]] = step.id
            print("Process Steps import complete.")

            print("Importing Use Cases...")
            if "use_cases" in imported_data:
                for uc_data in imported_data["use_cases"]:
                    old_process_step_id = uc_data["process_step_id"]
                    new_process_step_id = process_step_id_map.get(old_process_step_id)

                    if new_process_step_id is None:
                        print(f"Warning: Process Step ID {old_process_step_id} for use case '{uc_data.get('name', 'N/A')}' (BI_ID: {uc_data.get('bi_id', 'N/A')}) not found in new mapping. Skipping UC.")
                        continue

                    use_case = UseCase(
                        bi_id=uc_data["bi_id"],
                        name=uc_data["name"],
                        process_step_id=new_process_step_id,
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
                    session_local.add(use_case)
                    session_local.flush()
                    usecase_id_map[uc_data["id"]] = use_case.id
            print("Use Cases import complete.")

            if "llm_settings" in imported_data:
                print("Importing LLM Settings...")
                for ls_data in imported_data["llm_settings"]:
                    old_user_id = ls_data["user_id"]
                    new_user_id = user_id_map.get(old_user_id)

                    if new_user_id is None:
                        print(f"Warning: Original User ID {old_user_id} for LLM settings not found in new mapping. Skipping LLM settings entry.")
                        continue

                    # Check if settings for this new_user_id already exist (e.g., if multiple entries mapped to same new user)
                    existing_ls = session_local.query(LLMSettings).filter_by(user_id=new_user_id).first()
                    if existing_ls:
                        print(f"Warning: LLM settings for new User ID {new_user_id} (original old ID {old_user_id}) already exist. Skipping duplicate import for this entry.")
                        continue

                    ls = LLMSettings(
                        user_id=new_user_id,
                        openai_api_key=ls_data.get("openai_api_key"),
                        anthropic_api_key=ls_data.get("anthropic_api_key"),
                        google_api_key=ls_data.get("google_api_key"),
                        ollama_base_url=ls_data.get("ollama_base_url")
                    )
                    session_local.add(ls)
            print("LLM Settings import complete.")


            print("Importing Relevance Links...")
            if "usecase_area_relevance" in imported_data:
                for r_data in imported_data["usecase_area_relevance"]:
                    new_source_usecase_id = usecase_id_map.get(r_data["source_usecase_id"])
                    new_target_area_id = area_id_map.get(r_data["target_area_id"])

                    if new_source_usecase_id is None or new_target_area_id is None:
                        print(f"Warning: Skipping UsecaseAreaRelevance link for old UC ID {r_data['source_usecase_id']} to old Area ID {r_data['target_area_id']} due to missing mapped entity.")
                        continue

                    rel = UsecaseAreaRelevance(
                        source_usecase_id=new_source_usecase_id,
                        target_area_id=new_target_area_id,
                        relevance_score=r_data["relevance_score"],
                        relevance_content=r_data.get("relevance_content")
                    )
                    session_local.add(rel)

            if "usecase_step_relevance" in imported_data:
                for r_data in imported_data["usecase_step_relevance"]:
                    new_source_usecase_id = usecase_id_map.get(r_data["source_usecase_id"])
                    new_target_process_step_id = process_step_id_map.get(r_data["target_process_step_id"])

                    if new_source_usecase_id is None or new_target_process_step_id is None:
                        print(f"Warning: Skipping UsecaseStepRelevance link for old UC ID {r_data['source_usecase_id']} to old PS ID {r_data['target_process_step_id']} due to missing mapped entity.")
                        continue

                    rel = UsecaseStepRelevance(
                        source_usecase_id=new_source_usecase_id,
                        target_process_step_id=new_target_process_step_id,
                        relevance_score=r_data["relevance_score"],
                        relevance_content=r_data.get("relevance_content")
                    )
                    session_local.add(rel)

            if "usecase_usecase_relevance" in imported_data:
                for r_data in imported_data["usecase_usecase_relevance"]:
                    new_source_usecase_id = usecase_id_map.get(r_data["source_usecase_id"])
                    new_target_usecase_id = usecase_id_map.get(r_data["target_usecase_id"])

                    if new_source_usecase_id is None or new_target_usecase_id is None:
                        print(f"Warning: Skipping UsecaseUsecaseRelevance link for old UC ID {r_data['source_usecase_id']} to old UC ID {r_data['target_usecase_id']} due to missing mapped entity.")
                        continue
                    if new_source_usecase_id == new_target_usecase_id: # Prevent self-links
                        print(f"Warning: Skipping UsecaseUsecaseRelevance self-link for new UC ID {new_source_usecase_id} (original old source ID {r_data['source_usecase_id']}).")
                        continue


                    rel = UsecaseUsecaseRelevance(
                        source_usecase_id=new_source_usecase_id,
                        target_usecase_id=new_target_usecase_id,
                        relevance_score=r_data["relevance_score"],
                        relevance_content=r_data.get("relevance_content")
                    )
                    session_local.add(rel)

            if "process_step_process_step_relevance" in imported_data:
                for r_data in imported_data["process_step_process_step_relevance"]:
                    new_source_process_step_id = process_step_id_map.get(r_data["source_process_step_id"])
                    new_target_process_step_id = process_step_id_map.get(r_data["target_process_step_id"])

                    if new_source_process_step_id is None or new_target_process_step_id is None:
                        print(f"Warning: Skipping ProcessStepProcessStepRelevance link for old PS ID {r_data['source_process_step_id']} to old PS ID {r_data['target_process_step_id']} due to missing mapped entity.")
                        continue
                    if new_source_process_step_id == new_target_process_step_id: # Prevent self-links
                        print(f"Warning: Skipping ProcessStepProcessStepRelevance self-link for new PS ID {new_source_process_step_id} (original old source ID {r_data['source_process_step_id']}).")
                        continue

                    rel = ProcessStepProcessStepRelevance(
                        source_process_step_id=new_source_process_step_id,
                        target_process_step_id=new_target_process_step_id,
                        relevance_score=r_data["relevance_score"],
                        relevance_content=r_data.get("relevance_content")
                    )
                    session_local.add(rel)
            print("Relevance Links import complete.")

            print("Attempting final session.commit() for database import.")
            session_local.commit()
            print("session_local.commit() successful.")
            return {"success": True, "message": "Database import successful."}
        else: # Not clearing data - this mode is not fully supported by current design for full import.
              # A full import without clearing requires merging, which is complex.
              # This path should ideally not be taken for a "full database import".
            print("Warning: Attempting to import data without clearing existing data. This is not fully supported and may lead to conflicts or unintended behavior.")
            # For simplicity, returning an error or a specific message here might be better.
            return {
                "success": False,
                "message": "Importing data without clearing existing data is not supported in this function. Please use clear_existing_data=True or use individual entity import functions."
            }


    except IntegrityError as ie:
        session_local.rollback()
        print(f"Database integrity error during import: {ie}")
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Database integrity error: {ie}. Import rolled back."
        }
    except json.JSONDecodeError as je:
        session_local.rollback() # Ensure rollback on JSON error too
        print(f"JSON Decode Error during import_database_from_json: {je}")
        traceback.print_exc()
        return {
            "success": False,
            "message": f"Invalid JSON format in the uploaded file: {je}. Import rolled back."
        }
    except Exception as e:
        session_local.rollback()
        print(f"Error during database import: {e}")
        traceback.print_exc()
        return {
            "success": False,
            "message": f"An error occurred: {e}. Import rolled back."
        }
    finally:
        SessionLocal.remove()