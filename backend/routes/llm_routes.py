# backend/routes/llm_routes.py
from flask import Blueprint, request, flash, redirect, url_for, render_template, jsonify, current_app
from flask_login import login_required
from sqlalchemy.orm import joinedload
import json # For json.dumps
import tiktoken # For token counting
import traceback # Import traceback for detailed error logging

# NEW: Import llm_service
from ..llm_service import get_available_ollama_models, generate_ollama_chat_response, clear_chat_history, get_chat_history

# Helper function to count tokens
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


from ..db import SessionLocal
from ..models import ProcessStep, Area

# Define the blueprint
llm_routes = Blueprint('llm', __name__,
                       template_folder='../templates', # Ensure templates can be found
                       url_prefix='/llm')

# Define which ProcessStep fields are selectable by the user
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
    # 'llm_comment_1': "LLM Comment 1", # Example if you want to include these
}


@llm_routes.route('/data-prep', methods=['GET', 'POST'])
@login_required
def llm_data_prep_page():
    session = SessionLocal()
    try:
        areas = session.query(Area).order_by(Area.name).all()
        # Fetch steps with their area for potential filtering display
        all_steps = session.query(ProcessStep).options(joinedload(ProcessStep.area)).order_by(ProcessStep.name).all()

        prepared_data = None # Initialize as None, will be list only if data is found
        selected_area_ids_int = []
        selected_step_ids_int = []
        selected_fields_form = []
        total_tokens = 0 # Initialize token count

        print("--- LLM Data Prep Page Access ---") # General access log
        print(f"Request Method: {request.method}")

        if request.method == 'POST':
            print("--- Processing POST request for LLM data prep ---") # POST specific log
            print(f"Full form data: {request.form}") # Log all form data

            selected_area_ids_str = request.form.getlist('area_ids')
            selected_step_ids_str = request.form.getlist('step_ids')
            selected_fields_form = request.form.getlist('fields')

            print(f"area_ids from form: {selected_area_ids_str}")
            print(f"step_ids from form: {selected_step_ids_str}")
            print(f"fields from form: {selected_fields_form}")

            selected_area_ids_int = [int(id_str) for id_str in selected_area_ids_str if id_str.isdigit()]
            selected_step_ids_int = [int(id_str) for id_str in selected_step_ids_str if id_str.isdigit()]

            print(f"Parsed area_ids (int): {selected_area_ids_int}")
            print(f"Parsed step_ids (int): {selected_step_ids_int}")

            if not selected_fields_form:
                flash("Please select at least one field to preview.", "warning")
                print("Warning: No fields selected in form.") # Specific warning log
                # Ensure prepared_data remains None if no fields are selected
            else:
                query = session.query(ProcessStep)
                if selected_step_ids_int:
                    query = query.filter(ProcessStep.id.in_(selected_step_ids_int))
                    print(f"Querying for specific steps: {selected_step_ids_int}")
                elif selected_area_ids_int: # If no specific steps, but areas are selected
                    query = query.filter(ProcessStep.area_id.in_(selected_area_ids_int))
                    print(f"Querying for steps in areas: {selected_area_ids_int}")
                else:
                    print("No specific steps or areas selected, querying all steps.")
                # If neither steps nor areas selected, query will fetch all steps.

                steps_for_preview = query.options(joinedload(ProcessStep.area)).order_by(ProcessStep.area_id, ProcessStep.name).all()

                print(f"Found {len(steps_for_preview)} steps for preview.")

                if not steps_for_preview:
                    flash("No process steps found matching your criteria.", "info")
                    prepared_data = [] # Explicitly set to empty list to differentiate from None
                    print("Info: No steps found matching criteria.")
                else:
                    prepared_data = []
                    for step in steps_for_preview:
                        step_data = {'id': step.id} # Always include ID for reference
                        for field_key in selected_fields_form:
                            if hasattr(step, field_key):
                                step_data[field_key] = getattr(step, field_key)
                            else:
                                step_data[field_key] = "N/A (invalid field or not loaded)"
                                print(f"Warning: Step {step.id} missing attribute {field_key}.") # Log if field not found on model
                        prepared_data.append(step_data)
                    
                    if not prepared_data: # Should not happen if steps_for_preview was not empty, but safety check
                         flash("No data to preview after filtering fields.", "info")
                         print("Info: No data to preview after filtering fields.")
                    else:
                        # Convert the prepared data to a JSON string and count tokens
                        # Only convert to JSON string if prepared_data is not empty
                        json_string_for_tokens = json.dumps(prepared_data, indent=2)
                        total_tokens = count_tokens(json_string_for_tokens)
                        print(f"Prepared data for {len(prepared_data)} steps. Total tokens: {total_tokens}")

        # NEW: Get available Ollama models
        ollama_models = get_available_ollama_models()
        # NEW: Get current chat history for initial render
        chat_history = list(get_chat_history()) # Convert deque to list

        return render_template(
            'llm_data_prep.html',
            title="LLM Data Preparation",
            areas=areas,
            all_steps=all_steps,
            selectable_fields=SELECTABLE_STEP_FIELDS,
            prepared_data=prepared_data, # This will be None, [], or a list of dicts
            total_tokens=total_tokens, # Pass token count to template
            selected_area_ids=selected_area_ids_int,
            selected_step_ids=selected_step_ids_int,
            selected_fields_form=selected_fields_form,
            ollama_models=ollama_models, # NEW: Pass models to template
            chat_history=chat_history, # NEW: Pass chat history to template
            config=current_app.config # NEW: Pass the Flask application config
        )

    except Exception as e:
        # VERY IMPORTANT: Print the full traceback to Docker logs
        print("\n--- CRITICAL ERROR IN LLM DATA PREP PAGE ---")
        print(f"Exception Type: {type(e).__name__}")
        print(f"Exception Message: {e}")
        traceback.print_exc() # This will print the detailed stack trace
        print("-------------------------------------------\n")

        flash("An error occurred while preparing data. Please try again.", "danger")
        # Ensure current_app is available for config even in an error state
        # from flask import current_app # Import current_app here to access config in except block - not needed, already imported globally
        return render_template(
            'llm_data_prep.html',
            title="LLM Data Preparation",
            areas=[],
            all_steps=[],
            selectable_fields=SELECTABLE_STEP_FIELDS,
            prepared_data=None, # Default to None on error
            total_tokens=0,
            selected_area_ids=[],
            selected_step_ids=[],
            selected_fields_form=[],
            ollama_models=[], # NEW: Empty list on error
            chat_history=[], # NEW: Empty list on error
            config=current_app.config # NEW: Pass the Flask application config on error
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
    
    if not user_message or not model_name:
        return jsonify({"success": False, "message": "Message and model are required."}), 400

    response = generate_ollama_chat_response(model_name, user_message)
    return jsonify(response)

# NEW ROUTE: Clear chat history
@llm_routes.route('/chat/clear', methods=['POST'])
@login_required
def llm_chat_clear():
    clear_chat_history()
    return jsonify({"success": True, "message": "Chat history cleared."})