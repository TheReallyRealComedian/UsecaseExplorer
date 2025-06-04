# backend/routes/llm_routes.py

import json
import tiktoken
import traceback

from flask import Blueprint, request, flash, redirect, url_for, render_template, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import select

# Updated imports for llm_service functions
from ..llm_service import (
    get_all_available_llm_models, # NEW: Master model list getter
    generate_ollama_chat_response,
    generate_openai_chat_response, # NEW
    generate_anthropic_chat_response, # NEW
    generate_google_chat_response, # NEW
    clear_chat_history,
    get_chat_history,
    add_message_to_history # NEW: Imported for use in `llm_chat`
)
from ..db import SessionLocal
from ..models import ProcessStep, Area, User, UseCase, UsecaseStepRelevance
# NEW IMPORT FOR BREADCRUMBS DATA
from ..utils import serialize_for_js
# END NEW IMPORT

# Helper function to count tokens
def count_tokens(text: str, model_name: str = "cl100k_base") -> int:
    """
    Counts tokens in a given text using tiktoken.
    Default model 'cl100k_base' is used for GPT-4, GPT-3.5-turbo, etc.
    """
    try:
        encoding = tiktoken.get_encoding(model_name)
    except KeyError:
        encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


# Define the blueprint
llm_routes = Blueprint('llm', __name__,
                       template_folder='../templates',
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
}

# Define which UseCase fields are selectable by the user
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
}

@llm_routes.route('/chat-dedicated') # New route for the dedicated LLM Chat page
@login_required
def llm_chat_page():
    session_db = SessionLocal()
    user_system_prompt = current_user.system_prompt if current_user.is_authenticated else ""

    # NEW BREADCRUMB DATA FETCHING
    all_areas_flat = []
    all_steps_flat = []
    all_usecases_flat = []
    # END NEW BREADCRUMB DATA FETCHING

    try:
        # These are fetched by JS now, but kept for consistency in parameters if needed
        # ollama_models = get_available_ollama_models()
        # chat_history = list(get_chat_history())

        # NEW BREADCRUMB DATA FETCHING
        all_areas_flat = serialize_for_js(session_db.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session_db.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session_db.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        # END NEW BREADCRUMB DATA FETCHING

        return render_template(
            'llm_chat.html', # Render the new template
            title="LLM Chat",
            config=current_app.config,
            user_system_prompt=user_system_prompt,
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            # NEW BREADCRUMB DATA PASSING
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
            # END NEW BREADCRUMB DATA PASSING
        )
    except Exception as e:
        print(f"Error loading LLM Chat page: {e}")
        flash("An error occurred while loading the LLM Chat page.", "danger")
        return render_template(
            'llm_chat.html',
            title="LLM Chat",
            config=current_app.config,
            user_system_prompt=user_system_prompt,
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            # NEW BREADCRUMB DATA PASSING (empty if error)
            all_areas_flat=[],
            all_steps_flat=[],
            all_usecases_flat=[]
            # END NEW BREADCRUMB DATA PASSING
        )
    finally:
        SessionLocal.remove()

@llm_routes.route('/data-prep', methods=['GET', 'POST'])
@login_required
def llm_data_prep_page():
    session = SessionLocal()
    try:
        areas = session.query(Area).order_by(Area.name).all()
        all_steps_db = session.query(ProcessStep).options(joinedload(ProcessStep.area)).order_by(ProcessStep.name).all()
        all_usecases_db = session.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area)
        ).order_by(UseCase.name).all()

        prepared_data = {"process_steps": [], "use_cases": []}

        selected_area_ids_int = []
        selected_step_ids_int = []
        selected_usecase_ids_int = []
        selected_step_fields_form = []
        selected_usecase_fields_form = []
        export_uc_step_relevance = False

        total_tokens = 0

        print("--- LLM Data Prep Page Access ---")
        print(f"Request Method: {request.method}")

        if request.method == 'POST':
            print("--- Processing POST request for LLM data prep ---")
            print(f"Full form data: {request.form}")

            selected_area_ids_str = request.form.getlist('area_ids')
            selected_step_ids_str = request.form.getlist('step_ids')
            selected_usecase_ids_str = request.form.getlist('usecase_ids')
            selected_step_fields_form = request.form.getlist('step_fields')
            selected_usecase_fields_form = request.form.getlist('usecase_fields')

            export_uc_step_relevance = request.form.get('export_uc_step_relevance') == 'on'

            selected_area_ids_int = [int(id_str) for id_str in selected_area_ids_str if id_str.isdigit()]
            selected_step_ids_int = [int(id_str) for id_str in selected_step_ids_str if id_str.isdigit()]
            selected_usecase_ids_int = [int(id_str) for id_str in selected_usecase_ids_str if id_str.isdigit()]

            print(f"Parsed area_ids (int): {selected_area_ids_int}")
            print(f"Parsed step_ids (int): {selected_step_ids_int}")
            print(f"Parsed usecase_ids (int): {selected_usecase_ids_int}")
            print(f"Export UC-Step Relevance: {export_uc_step_relevance}")

            default_step_fields = ['bi_id', 'name', 'step_description']
            default_usecase_fields = ['bi_id', 'name', 'summary']

            fields_to_export_steps = selected_step_fields_form if selected_step_fields_form else default_step_fields
            fields_to_export_usecases = selected_usecase_fields_form if selected_usecase_fields_form else default_usecase_fields

            if not selected_step_fields_form and (selected_step_ids_int or selected_area_ids_int):
                flash("No Process Step fields explicitly selected. Including default fields (BI_ID, Name, Short Description) for selected steps.", "info")
            if not selected_usecase_fields_form and (selected_usecase_ids_int or selected_step_ids_int or selected_area_ids_int):
                flash("No Use Case fields explicitly selected. Including default fields (BI_ID, Name, Summary) for selected use cases.", "info")

            step_query = session.query(ProcessStep)
            if selected_step_ids_int:
                step_query = step_query.filter(ProcessStep.id.in_(selected_step_ids_int))
            elif selected_area_ids_int:
                step_query = step_query.filter(ProcessStep.area_id.in_(selected_area_ids_int))

            steps_for_preview = step_query.options(joinedload(ProcessStep.area)).order_by(ProcessStep.area_id, ProcessStep.name).all()

            for step in steps_for_preview:
                step_data = {
                    'id': step.id,
                    'area_id': step.area_id,
                    'area_name': step.area.name if step.area else 'N/A'
                }
                for field_key in fields_to_export_steps:
                    if hasattr(step, field_key):
                        step_data[field_key] = getattr(step, field_key)
                    else:
                        step_data[field_key] = "N/A"
                prepared_data["process_steps"].append(step_data)

            usecase_query = session.query(UseCase)
            if selected_usecase_ids_int:
                usecase_query = usecase_query.filter(UseCase.id.in_(selected_usecase_ids_int))
            elif selected_step_ids_int:
                usecase_query = usecase_query.filter(UseCase.process_step_id.in_(selected_step_ids_int))
            elif selected_area_ids_int:
                subquery_step_ids = select(ProcessStep.id).where(ProcessStep.area_id.in_(selected_area_ids_int)).scalar_subquery()
                usecase_query = usecase_query.filter(UseCase.process_step_id.in_(subquery_step_ids))

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
                for field_key in fields_to_export_usecases:
                    if hasattr(uc, field_key):
                        uc_data[field_key] = getattr(uc, field_key)
                    else:
                        uc_data[field_key] = "N/A"
                prepared_data["use_cases"].append(uc_data)

            prepared_data["usecase_step_relevance"] = []

            if export_uc_step_relevance:
                print("Exporting Use Case to Step Relevance links...")
                relevance_query = session.query(UsecaseStepRelevance).options(
                    joinedload(UsecaseStepRelevance.source_usecase),
                    joinedload(UsecaseStepRelevance.target_process_step)
                )

                actual_exported_uc_ids = {uc['id'] for uc in prepared_data["use_cases"]}
                actual_exported_step_ids = {ps['id'] for ps in prepared_data["process_steps"]}

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

            json_string_for_tokens = json.dumps(prepared_data, indent=2)
            total_tokens = count_tokens(json_string_for_tokens)

        user_system_prompt = current_user.system_prompt if current_user.is_authenticated else ""

        # NOTE: ollama_models and chat_history are now fetched via API calls by common_llm_chat.js
        #       These variables in the render_template are no longer strictly needed for the LLM chat window itself
        #       but kept for existing template structure.
        ollama_models = get_all_available_llm_models() # NEW: Get ALL models
        chat_history = list(get_chat_history())

        # NEW BREADCRUMB DATA FETCHING
        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')
        # END NEW BREADCRUMB DATA PASSING

        return render_template(
            'llm_data_prep.html',
            title="Data Mining",
            areas=areas,
            all_steps=all_steps_db, # Use all_steps_db here
            all_usecases=all_usecases_db, # Use all_usecases_db here
            selectable_fields_steps=SELECTABLE_STEP_FIELDS,
            selectable_fields_usecases=SELECTABLE_USECASE_FIELDS,
            prepared_data=prepared_data,
            total_tokens=total_tokens,
            selected_area_ids=selected_area_ids_int,
            selected_step_ids=selected_step_ids_int,
            selected_usecase_ids=selected_usecase_ids_int,
            selected_step_fields_form=selected_step_fields_form,
            selected_usecase_fields_form=selected_usecase_fields_form,
            export_uc_step_relevance=export_uc_step_relevance,
            ollama_models=ollama_models,
            chat_history=chat_history,
            config=current_app.config,
            user_system_prompt=user_system_prompt,
            current_item=None, # Indicates this is a top-level page
            current_area=None, # Ensure consistency
            current_step=None, # Ensure consistency
            current_usecase=None, # Ensure consistency
            # NEW BREADCRUMB DATA PASSING
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
            # END NEW BREADCRUMB DATA PASSING
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
            title="Data Mining",
            areas=[],
            all_steps=[],
            all_usecases=[],
            selectable_fields_steps=SELECTABLE_STEP_FIELDS,
            selectable_fields_usecases=SELECTABLE_USECASE_FIELDS,
            prepared_data={"process_steps": [], "use_cases": []},
            total_tokens=0,
            selected_area_ids=[],
            selected_step_ids=[],
            selected_usecase_ids=[],
            selected_step_fields_form=[],
            selected_usecase_fields_form=[],
            export_uc_step_relevance=False,
            ollama_models=[],
            chat_history=[],
            config=current_app.config,
            user_system_prompt=user_system_prompt_on_error,
            current_item=None, # Indicates this is a top-level page
            current_area=None, # Ensure consistency
            current_step=None, # Ensure consistency
            current_usecase=None, # Ensure consistency
            # NEW BREADCRUMB DATA PASSING (empty if error)
            all_areas_flat=[],
            all_steps_flat=[],
            all_usecases_flat=[]
            # END NEW BREADCRUMB DATA PASSING
        )
    finally:
        SessionLocal.remove()

@llm_routes.route('/analyze/<int:usecase_id>', methods=['POST', 'GET'])
@login_required
def analyze_usecase(usecase_id):
    """Handles triggering an LLM analysis for a specific Use Case."""
    flash(f"LLM analysis for Use Case ID {usecase_id} requested. Not implemented yet.", "info")
    return redirect(url_for('usecases.view_usecase', usecase_id=usecase_id))

@llm_routes.route('/chat', methods=['POST'])
@login_required
def llm_chat():
    user_message = request.json.get('message') # Correctly retrieve 'message' from frontend
    model_name = request.json.get('model')
    image_base64 = request.json.get('image_base64')
    image_mime_type = request.json.get('image_mime_type')

    system_prompt = current_user.system_prompt if current_user.is_authenticated else None
    if system_prompt == "":
        system_prompt = None

    if not user_message and not image_base64: # If no text and no image
        return jsonify({"success": False, "message": "Message or image is required."}), 400

    if not model_name:
        return jsonify({"success": False, "message": "Model is required."}), 400

    # Get current chat history for this user
    chat_history = get_chat_history()

    # Determine provider and model_id from the model_name string (e.g., "openai-gpt-4o")
    # Split only on the first hyphen in case model names themselves contain hyphens
    parts = model_name.split('-', 1)
    provider = parts[0] if len(parts) > 0 else "unknown"
    model_id = parts[1] if len(parts) > 1 else model_name # Fallback to full name if no hyphen

    response = {"success": False, "message": "Unsupported LLM provider or no response."}

    try:
        if provider == "ollama":
            response = generate_ollama_chat_response(model_id, user_message, system_prompt, image_base64, image_mime_type, chat_history)
        elif provider == "openai":
            response = generate_openai_chat_response(model_id, user_message, system_prompt, image_base64, image_mime_type, chat_history)
        elif provider == "anthropic":
            response = generate_anthropic_chat_response(model_id, user_message, system_prompt, image_base64, image_mime_type, chat_history)
        elif provider == "google":
            response = generate_google_chat_response(model_id, user_message, system_prompt, image_base64, image_mime_type, chat_history)
        else:
            response = {"success": False, "message": f"Unknown or unsupported LLM provider: {provider}"}

    except Exception as e:
        response = {"success": False, "message": f"Server error calling LLM: {e}"}
        traceback.print_exc()

    # Add messages to history only if the API call was successful
    if response["success"]:
        # The 'user_message' passed here is the original text from the frontend.
        # If the original user_message was empty but an image was provided, add a placeholder text for history.
        user_message_for_history = user_message
        if not user_message_for_history and image_base64:
            user_message_for_history = "Image provided."
        add_message_to_history('user', user_message_for_history)
        add_message_to_history('assistant', response["message"])
    else:
        # If the API call failed, but it wasn't due to missing message/model,
        # you might want to log the error in the chat display for the user.
        # For simplicity, we just pass the error message from the response.
        pass # The frontend `common_llm_chat.js` already handles displaying `data.message` for errors.

    return jsonify(response)

@llm_routes.route('/system-prompt', methods=['POST'])
@login_required
def save_system_prompt():
    prompt_content = request.json.get('prompt')
    if prompt_content is None:
        return jsonify({"success": False, "message": "Prompt content is required."}), 400

    session = SessionLocal()
    try:
        user = session.query(User).get(current_user.id)
        if user:
            user.system_prompt = prompt_content.strip() if prompt_content else None
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

@llm_routes.route('/chat/clear', methods=['POST'])
@login_required
def llm_chat_clear():
    clear_chat_history()
    return jsonify({"success": True, "message": "Chat history cleared."})


@llm_routes.route('/get_llm_models', methods=['GET'])
@login_required
def get_llm_models_api():
    models = get_all_available_llm_models() # NEW: Calls the aggregated model list
    return jsonify({"success": True, "models": models})

@llm_routes.route('/get_chat_history', methods=['GET'])
@login_required
def get_chat_history_api():
    history = get_chat_history()
    return jsonify({"success": True, "history": history})
