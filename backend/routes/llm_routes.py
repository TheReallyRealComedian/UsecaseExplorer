# backend/routes/llm_routes.py

import json
import tiktoken
import traceback

from flask import Blueprint, request, flash, redirect, url_for, render_template, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import select

from ..llm_service import get_available_ollama_models, generate_ollama_chat_response, clear_chat_history, get_chat_history
from ..db import SessionLocal
from ..models import ProcessStep, Area, User, UseCase, UsecaseStepRelevance 

# Helper function to count tokens (existing, no change needed)
def count_tokens(text: str, model_name: str = "cl100k_base") -> int:
    """
    Counts tokens in a given text using tiktoken.
    Default model 'cl100k_base' is used for GPT-4, GPT-3.5-turbo, etc.
    """
    try:
        # For robustness, try to get the specified encoding, fall back to a common one.
        encoding = tiktoken.get_encoding(model_name)
    except KeyError:
        # Fallback if the model_name encoding is not found
        encoding = tiktoken.get_encoding("cl100k_base") 
    return len(encoding.encode(text))


# Define the blueprint (existing)
llm_routes = Blueprint('llm', __name__,
                       template_folder='../templates',
                       url_prefix='/llm')

# Define which ProcessStep fields are selectable by the user (existing)
SELECTABLE_STEP_FIELDS = {
    'name': "Name",
    'bi_id': "Business ID (BI_ID)",
    'step_description': "Short Description",
    'raw_content': "Raw Content",
    'summary': "Generic Summary",
    'vision_statement': "Vision Statement",
    'in_scope': "In Scope",
    'out_of_scope': "Out of Scope",
    'interfaces_text': "Interfaces",
    'what_is_actually_done': "What is Actually Done",
    'pain_points': "Pain Points",
    'targets_text': "Targets",
    # Add more fields from ProcessStep model as needed
}

# NEW: Define which UseCase fields are selectable by the user
SELECTABLE_USECASE_FIELDS = {
    'name': "Name",
    'bi_id': "Business ID (BI_ID)",
    'priority': "Priority",
    'summary': "Summary",
    'inspiration': "Inspiration",
    'raw_content': "Raw Content",
    'wave': "Wave",
    'effort_level': "Effort Level",
    'status': "Status",
    'business_problem_solved': "Business Problem Solved",
    'target_solution_description': "Target / Solution Description",
    'technologies_text': "Technologies",
    'requirements': "Requirements",
    'relevants_text': "Relevants (Tags)",
    'reduction_time_transfer': "Time Reduction (Transfer)",
    'reduction_time_launches': "Time Reduction (Launches)",
    'reduction_costs_supply': "Cost Reduction (Supply)",
    'quality_improvement_quant': "Quality Improvement",
    'ideation_notes': "Ideation Notes",
    'further_ideas': "Further Ideas",
    'effort_quantification': "Effort Quantification",
    'potential_quantification': "Potential Quantification",
    'dependencies_text': "Dependencies",
    'contact_persons_text': "Contact Persons",
    'related_projects_text': "Related Projects",
    # LLM comments, if desired for export (optional to add to form)
    # 'llm_comment_1': "LLM Comment 1",
    # 'llm_comment_2': "LLM Comment 2",
    # 'llm_comment_3': "LLM Comment 3",
    # 'llm_comment_4': "LLM Comment 4",
    # 'llm_comment_5': "LLM Comment 5",
}


@llm_routes.route('/data-prep', methods=['GET', 'POST'])
@login_required
def llm_data_prep_page():
    session = SessionLocal()
    try:
        areas = session.query(Area).order_by(Area.name).all()
        # Fetch steps with their area for potential filtering display
        all_steps = session.query(ProcessStep).options(joinedload(ProcessStep.area)).order_by(ProcessStep.name).all()
        # NEW: Fetch use cases with their process step and area for filtering display
        all_usecases = session.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area)
        ).order_by(UseCase.name).all()

        # NEW: prepared_data is now a dictionary containing lists for different entity types
        prepared_data = {"process_steps": [], "use_cases": []} 
        
        selected_area_ids_int = []
        selected_step_ids_int = []
        selected_usecase_ids_int = [] # NEW
        selected_step_fields_form = [] # RENAMED 'selected_fields_form' for clarity
        selected_usecase_fields_form = [] # NEW

        # NEW: Initialize export_uc_step_relevance for GET request
        export_uc_step_relevance = False # Default to unchecked

        total_tokens = 0

        print("--- LLM Data Prep Page Access ---")
        print(f"Request Method: {request.method}")

        if request.method == 'POST':
            print("--- Processing POST request for LLM data prep ---")
            print(f"Full form data: {request.form}")

            selected_area_ids_str = request.form.getlist('area_ids')
            selected_step_ids_str = request.form.getlist('step_ids')
            selected_usecase_ids_str = request.form.getlist('usecase_ids') # NEW
            selected_step_fields_form = request.form.getlist('step_fields') # RENAMED
            selected_usecase_fields_form = request.form.getlist('usecase_fields') # NEW

            # NEW: Parse relevance link export option
            export_uc_step_relevance = request.form.get('export_uc_step_relevance') == 'on'

            selected_area_ids_int = [int(id_str) for id_str in selected_area_ids_str if id_str.isdigit()]
            selected_step_ids_int = [int(id_str) for id_str in selected_step_ids_str if id_str.isdigit()]
            selected_usecase_ids_int = [int(id_str) for id_str in selected_usecase_ids_str if id_str.isdigit()] # NEW

            print(f"Parsed area_ids (int): {selected_area_ids_int}")
            print(f"Parsed step_ids (int): {selected_step_ids_int}")
            print(f"Parsed usecase_ids (int): {selected_usecase_ids_int}") # NEW
            print(f"Export UC-Step Relevance: {export_uc_step_relevance}") # NEW debug

            # --- MODIFIED LOGIC FOR FIELD SELECTION ---
            # Define default fields if none are explicitly selected.
            # This ensures that even if user checks no fields, some basic info is always included.
            default_step_fields = ['bi_id', 'name', 'step_description'] # Common essential fields for steps
            default_usecase_fields = ['bi_id', 'name', 'summary'] # Common essential fields for use cases

            # Use selected fields if provided, otherwise fallback to defaults
            fields_to_export_steps = selected_step_fields_form if selected_step_fields_form else default_step_fields
            fields_to_export_usecases = selected_usecase_fields_form if selected_usecase_fields_form else default_usecase_fields

            # Flash a warning if no fields were explicitly selected, so user knows defaults were applied.
            if not selected_step_fields_form and (selected_step_ids_int or selected_area_ids_int):
                flash("No Process Step fields explicitly selected. Including default fields (BI_ID, Name, Short Description) for selected steps.", "info")
            if not selected_usecase_fields_form and (selected_usecase_ids_int or selected_step_ids_int or selected_area_ids_int):
                flash("No Use Case fields explicitly selected. Including default fields (BI_ID, Name, Summary) for selected use cases.", "info")
            # --- END MODIFIED LOGIC ---


            # --- Prepare Process Step Data ---
            # Removed the 'if not selected_step_fields_form: else:' block that previously wrapped this.
            step_query = session.query(ProcessStep)
            if selected_step_ids_int: # If specific steps are selected, use them
                step_query = step_query.filter(ProcessStep.id.in_(selected_step_ids_int))
            elif selected_area_ids_int: # Else, if areas are selected, get steps from those areas
                step_query = step_query.filter(ProcessStep.area_id.in_(selected_area_ids_int))
            # If neither are selected, the query will return all steps, then filtered by field selection.

            steps_for_preview = step_query.options(joinedload(ProcessStep.area)).order_by(ProcessStep.area_id, ProcessStep.name).all()
            
            for step in steps_for_preview:
                step_data = {
                    'id': step.id,
                    'area_id': step.area_id,
                    'area_name': step.area.name if step.area else 'N/A'
                }
                for field_key in fields_to_export_steps: # Use the resolved fields list
                    if hasattr(step, field_key):
                        step_data[field_key] = getattr(step, field_key)
                    else:
                        step_data[field_key] = "N/A" # or None, depending on desired output
                prepared_data["process_steps"].append(step_data)

            # NEW: --- Prepare Use Case Data ---
            # Removed the 'if not selected_usecase_fields_form: else:' block that previously wrapped this.
            usecase_query = session.query(UseCase)
            if selected_usecase_ids_int: # If specific UCs are selected, use them
                usecase_query = usecase_query.filter(UseCase.id.in_(selected_usecase_ids_int))
            elif selected_step_ids_int: # Else if steps are selected, get UCs from those steps
                usecase_query = usecase_query.filter(UseCase.process_step_id.in_(selected_step_ids_int))
            elif selected_area_ids_int: # Else if areas are selected, get UCs from steps in those areas
                # Subquery to get step IDs in selected areas
                subquery_step_ids = select(ProcessStep.id).where(ProcessStep.area_id.in_(selected_area_ids_int)).scalar_subquery()
                usecase_query = usecase_query.filter(UseCase.process_step_id.in_(subquery_step_ids))
            # If none are selected, the query will return all use cases, then filtered by field selection.

            usecases_for_preview = usecase_query.options(
                joinedload(UseCase.process_step).joinedload(ProcessStep.area)
            ).order_by(UseCase.process_step_id, UseCase.name).all()
            
            for uc in usecases_for_preview:
                uc_data = {
                    'id': uc.id,
                    'process_step_id': uc.process_step_id,
                    'process_step_name': uc.process_step.name if uc.process_step else 'N/A',
                    'area_id': uc.process_step.area.id if uc.process_step and uc.process_step.area else 'N/A',
                    'area_name': uc.process_step.area.name if uc.process_step and uc.process_step.area else 'N/A'
                }
                for field_key in fields_to_export_usecases: # Use the resolved fields list
                    if hasattr(uc, field_key):
                        uc_data[field_key] = getattr(uc, field_key)
                    else:
                        uc_data[field_key] = "N/A"
                prepared_data["use_cases"].append(uc_data)

            # NEW: --- Prepare Use Case to Step Relevance Data ---
            prepared_data["usecase_step_relevance"] = [] # Initialize the list

            if export_uc_step_relevance:
                print("Exporting Use Case to Step Relevance links...")
                relevance_query = session.query(UsecaseStepRelevance).options(
                    joinedload(UsecaseStepRelevance.source_usecase),
                    joinedload(UsecaseStepRelevance.target_process_step)
                )

                # Get the actual IDs of use cases and steps that ended up in `prepared_data`
                # These sets will be used to ensure only relevance links between exported entities are included.
                actual_exported_uc_ids = {uc['id'] for uc in prepared_data["use_cases"]}
                actual_exported_step_ids = {ps['id'] for ps in prepared_data["process_steps"]}

                # Apply basic filters based on UI selections
                if selected_usecase_ids_int:
                    relevance_query = relevance_query.filter(
                        UsecaseStepRelevance.source_usecase_id.in_(selected_usecase_ids_int)
                    )
                if selected_step_ids_int:
                    relevance_query = relevance_query.filter(
                        UsecaseStepRelevance.target_process_step_id.in_(selected_step_ids_int)
                    )

                uc_step_relevances = relevance_query.all()
                
                for rel in uc_step_relevances:
                    # Final check: Ensure both the source Use Case and target Process Step
                    # are actually present in the primary exported data (process_steps/use_cases lists).
                    if rel.source_usecase_id in actual_exported_uc_ids and \
                       rel.target_process_step_id in actual_exported_step_ids:
                        rel_data = {
                            "id": rel.id,
                            "source_usecase_id": rel.source_usecase_id,
                            "source_usecase_bi_id": rel.source_usecase.bi_id if rel.source_usecase else "N/A",
                            "source_usecase_name": rel.source_usecase.name if rel.source_usecase else "N/A",
                            "target_process_step_id": rel.target_process_step_id,
                            "target_process_step_bi_id": rel.target_process_step.bi_id if rel.target_process_step else "N/A",
                            "target_process_step_name": rel.target_process_step.name if rel.target_process_step else "N/A",
                            "relevance_score": rel.relevance_score,
                            "relevance_content": rel.relevance_content,
                            "created_at": rel.created_at.isoformat() if rel.created_at else None,
                            "updated_at": rel.updated_at.isoformat() if rel.updated_at else None,
                        }
                        prepared_data["usecase_step_relevance"].append(rel_data)
                print(f"Exported {len(prepared_data['usecase_step_relevance'])} UC-Step Relevance links.")

            # Recalculate total tokens with the new relevance data
            json_string_for_tokens = json.dumps(prepared_data, indent=2)
            total_tokens = count_tokens(json_string_for_tokens)

        # Get the current user's system prompt for the template (existing)
        user_system_prompt = current_user.system_prompt if current_user.is_authenticated else ""

        # Get available Ollama models (existing)
        ollama_models = get_available_ollama_models()
        # Get current chat history for initial render (existing)
        chat_history = list(get_chat_history())

        return render_template(
            'llm_data_prep.html',
            title="LLM Data Preparation",
            areas=areas,
            all_steps=all_steps,
            all_usecases=all_usecases, # NEW: Pass all use cases to the template
            selectable_fields_steps=SELECTABLE_STEP_FIELDS, # RENAMED
            selectable_fields_usecases=SELECTABLE_USECASE_FIELDS, # NEW: Pass use case fields
            prepared_data=prepared_data,
            total_tokens=total_tokens,
            selected_area_ids=selected_area_ids_int,
            selected_step_ids=selected_step_ids_int,
            selected_usecase_ids=selected_usecase_ids_int, # NEW
            selected_step_fields_form=selected_step_fields_form, # RENAMED
            selected_usecase_fields_form=selected_usecase_fields_form, # NEW
            export_uc_step_relevance=export_uc_step_relevance, # NEW: Pass this to template
            ollama_models=ollama_models,
            chat_history=chat_history,
            config=current_app.config,
            user_system_prompt=user_system_prompt
        )

    except Exception as e:
        print("\n--- CRITICAL ERROR IN LLM DATA PREP PAGE ---")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {e}")
        traceback.print_exc()
        print("-------------------------------------------\n")

        flash("An error occurred while preparing data. Please try again.", "danger")
        user_system_prompt_on_error = current_user.system_prompt if current_user.is_authenticated else ""
        return render_template(
            'llm_data_prep.html',
            title="LLM Data Preparation",
            areas=[],
            all_steps=[],
            all_usecases=[], # NEW: Empty list on error
            selectable_fields_steps=SELECTABLE_STEP_FIELDS, # RENAMED
            selectable_fields_usecases=SELECTABLE_USECASE_FIELDS, # NEW: Keep as full dict on error
            prepared_data={"process_steps": [], "use_cases": []}, # Default to empty dict on error
            total_tokens=0,
            selected_area_ids=[],
            selected_step_ids=[],
            selected_usecase_ids=[], # NEW
            selected_step_fields_form=[], # RENAMED
            selected_usecase_fields_form=[], # NEW
            export_uc_step_relevance=False, # On error, ensure it's false
            ollama_models=[],
            chat_history=[],
            config=current_app.config,
            user_system_prompt=user_system_prompt_on_error
        )
    finally:
        SessionLocal.remove()


@llm_routes.route('/analyze/<int:usecase_id>', methods=['POST', 'GET'])
@login_required
def analyze_usecase(usecase_id):
    """Handles triggering an LLM analysis for a specific Use Case."""
    flash(f"LLM analysis for Use Case ID {usecase_id} requested. Not implemented yet.", "info")
    return redirect(url_for('usecases.view_usecase', usecase_id=usecase_id))

# NEW ROUTE: Chat endpoint for LLM interaction
@llm_routes.route('/chat', methods=['POST'])
@login_required
def llm_chat():
    user_message = request.json.get('message')
    model_name = request.json.get('model')
    
    # NEW: Get system prompt from current_user
    system_prompt = current_user.system_prompt if current_user.is_authenticated else None
    if system_prompt == "": # Treat empty string as None
        system_prompt = None

    if not user_message or not model_name:
        return jsonify({"success": False, "message": "Message and model are required."}), 400

    # Pass system_prompt to the service function
    response = generate_ollama_chat_response(model_name, user_message, system_prompt)
    return jsonify(response)

# NEW ROUTE: Save System Prompt
@llm_routes.route('/system-prompt', methods=['POST'])
@login_required
def save_system_prompt():
    prompt_content = request.json.get('prompt')
    if prompt_content is None: # Allow empty string, but treat None as error
        return jsonify({"success": False, "message": "Prompt content is required."}), 400

    session = SessionLocal()
    try:
        user = session.query(User).get(current_user.id)
        if user:
            user.system_prompt = prompt_content.strip() if prompt_content else None # Save as None if empty
            session.commit()
            return jsonify({"success": True, "message": "System prompt saved."})
        else:
            return jsonify({"success": False, "message": "User not found."}), 404
    except Exception as e:
        session.rollback()
        print(f"Error saving system prompt for user {current_user.id}: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Failed to save system prompt: {e}"}), 500
    finally:
        SessionLocal.remove()

# NEW ROUTE: Clear chat history
@llm_routes.route('/chat/clear', methods=['POST'])
@login_required
def llm_chat_clear():
    clear_chat_history()
    return jsonify({"success": True, "message": "Chat history cleared."})