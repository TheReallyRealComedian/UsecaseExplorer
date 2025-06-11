# backend/routes/llm_routes.py

import json
import tiktoken
import traceback

from flask import Blueprint, request, flash, redirect, url_for, render_template, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import select, distinct, or_, and_ # Added distinct, or_, and_

from ..llm_service import (
    get_all_available_llm_models,
    generate_ollama_chat_response,
    generate_openai_chat_response,
    generate_anthropic_chat_response,
    generate_google_chat_response,
    generate_apollo_chat_response,
    clear_chat_history,
    get_chat_history,
    add_message_to_history
)
from ..db import SessionLocal
from ..models import ProcessStep, Area, User, UseCase, UsecaseStepRelevance
from ..utils import serialize_for_js


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
    'pilot_site_factory_text': "Pilot Site, Factory",
    'usecase_type_category': "Use Case Type Category",
}

# Specialized system prompt for image-to-field update
AI_ASSIST_IMAGE_SYSTEM_PROMPT_TEMPLATE = """
You are an expert business analyst tasked with updating use case documentation based on the provided image.
The image contains various details about a use case.
The user will provide an image and the current textual data for a use case.
Your goal is to analyze the image and suggest updates to the use case fields.

Current Use Case Data (for context, do not just copy existing values if image provides new info):
---
Name: {usecase_name}
Summary: {usecase_summary}
As-is situation and business need (mapped to business_problem_solved): {usecase_business_problem_solved}
Target and solution (mapped to target_solution_description): {usecase_target_solution_description}
Pilot Site, Factory: {usecase_pilot_site_factory_text}
Effort Quantification: {usecase_effort_quantification}
Potential Quantification (Benefits/Comments): {usecase_potential_quantification}
Dependencies: {usecase_dependencies_text}
Use Case Type: {usecase_usecase_type_category}
---

Based on the provided image, propose updates ONLY for the fields you are confident about.
If the image does not provide clear information for a field, omit it from the JSON object.
Do not suggest an update for fields if the image content is identical to the current value.
DO NOT DEVIATE FROM THE CONTENT IN THE IMAGE; e.g. DO NOT INTERPRETE THAT WHAT THE POTENTIAL QUANTIFICATION OR EFFORT IS BASED ON ANY TEXT YOU HAVE - YOU MUST ONLY RETURN THE CONTENT FROM THE PICTURE.

Extract information from the image and map it to the following fields.

1.  **name**: From "Use Case Summary: MXX 'Name'".
2.  **summary**: From "Short Description" section.
3.  **business_problem_solved**: From "As-is situation and business need" section.
4.  **target_solution_description**: From "Target and solution" section.
5.  **pilot_site_factory_text**: From "Pilot site, factory" section. **IMPORTANT: If the text is exactly "<Site, Factory>", DO NOT ENTER ANYTHING for this field.**
6.  **usecase_type_category**: Identify the text next to the 'X' checkbox under "Use case type" (e.g., "Strategic", "Improvement", "Fundamental"). **IMPORTANT: Only return the category if a clear 'X' is visible next to it. If no 'X' is visible, DO NOT ENTER ANYTHING for this field.**
7.  **effort_quantification**: Summarize the "Effort" section (Project cost, Run costs (p.a.), Time for implementation). This information is indicated by small dark dots on one of 3 segments. IMPORTANT: if the 3 dots are all in a perfect vertical line to the right of the indicator rectangles this means nothing has been selected - don't return anything in that case! You should challenge your result double if it is "Project cost: >€1.000k, Run costs: >€500k, Time for implementation: >3y" This rather happens rarely, so check if you might have the case of a non-selection.
    *   **Project cost segments:** "<€500k", "€500k-€1.000k", ">€1.000k"
    *   **Run costs (p.a.) segments:** "<€200k", "€200k-€500k", ">€500k"
    *   **Time for implementation segments:** "<1y", "1-3y", ">3y"
    **IMPORTANT: Return the segment value ONLY IF a dark dot is positioned DIRECTLY ON one of the gray rectangles for that segment.
    Example: "Project cost: <€500k, Run costs: <€200k, Time for implementation: <1y."
8.  **potential_quantification**: Summarize the "Benefits" and "Prerequisites and dependencies" sections.
    *   **Benefits (checkmarked):** Identify benefits with a clear "x" next to them. The potential benefits are: "Time red. for product transfer/launch", "Batch cycle time red.", "Batch yield increase", "Total cost red.", "Inventory destruction red.", "Right-first-time increase", "Compliance".
    *   **Comments:** Include any text in the "Comments" column next to the benefits.
    **IMPORTANT: Only include a benefit in your summary if there is a clear "x" checkmark next to it. Do not list benefits that are not checked.** Format this as a single coherent text. Be careful with the first benefit ("Time red. for product transfer/launch" as it is two-lined, here be extra careful to check if there is a "x" in the respective box

Return your suggestions strictly as a JSON object, where keys are the field names as listed above (e.g., "summary", "effort_quantification"). Values should be your proposed new text for these fields.
Example JSON output:
{{
  "name": "Updated Plant Modeling Tool",
  "summary": "A refined description of plant optimization.",
  "business_problem_solved": "Addressing inefficiencies in new building planning.",
  "target_solution_description": "Implementing a digital twin for plant simulation and optimization.",
  "pilot_site_factory_text": "Pilot site: XYZ Factory",
  "usecase_type_category": "Improvement",
  "effort_quantification": "Project cost: <€500k, Run costs: <€200k, Time for implementation: <1y.",
  "potential_quantification": "Benefits include Time reduction for product transfer/launch, Batch cycle time reduction. Dependencies: Same Database as M01. Tools need to be interlinked."
}}
MOST IMPORTANT OF ALL: Output ONLY the JSON object and nothing else!!!!!
"""


@llm_routes.route('/chat-dedicated')
@login_required
def llm_chat_page():
    session_db = SessionLocal()
    user_system_prompt = current_user.system_prompt if current_user.is_authenticated else ""

    all_areas_flat = []
    all_steps_flat = []
    all_usecases_flat = []

    try:
        all_areas_flat = serialize_for_js(session_db.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session_db.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session_db.query(UseCase).order_by(UseCase.name).all(), 'usecase')

        return render_template(
            'llm_chat.html',
            title="LLM Chat",
            config=current_app.config,
            user_system_prompt=user_system_prompt,
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
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
            all_areas_flat=[],
            all_steps_flat=[],
            all_usecases_flat=[]
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

        distinct_waves_query = session.query(distinct(UseCase.wave)).filter(UseCase.wave.isnot(None)).filter(UseCase.wave != '').order_by(UseCase.wave).all()
        all_wave_values_for_filter = [w[0] for w in distinct_waves_query if w[0]]
        # Add "N/A" if there are use cases with NULL or empty wave, to allow filtering for them
        # This check could be more precise if needed, e.g., by querying count of UCs with NULL/empty wave
        if session.query(UseCase).filter(or_(UseCase.wave.is_(None), UseCase.wave == '')).first():
            if "N/A" not in all_wave_values_for_filter: # Ensure "N/A" is for actual empty/null values
                 all_wave_values_for_filter.append("N/A")


        prepared_data = {"process_steps": [], "use_cases": []}

        selected_area_ids_int = []
        selected_step_ids_int = []
        selected_usecase_ids_int = []
        selected_step_fields_form = []
        selected_usecase_fields_form = []
        export_uc_step_relevance = False
        selected_wave_values_form = []

        total_tokens = 0

        if request.method == 'POST':
            selected_area_ids_str = request.form.getlist('area_ids')
            selected_step_ids_str = request.form.getlist('step_ids')
            selected_usecase_ids_str = request.form.getlist('usecase_ids')
            selected_step_fields_form = request.form.getlist('step_fields')
            selected_usecase_fields_form = request.form.getlist('usecase_fields')
            selected_wave_values_form = request.form.getlist('wave_values')

            export_uc_step_relevance = request.form.get('export_uc_step_relevance') == 'on'

            selected_area_ids_int = [int(id_str) for id_str in selected_area_ids_str if id_str.isdigit()]
            selected_step_ids_int = [int(id_str) for id_str in selected_step_ids_str if id_str.isdigit()]
            selected_usecase_ids_int = [int(id_str) for id_str in selected_usecase_ids_str if id_str.isdigit()]

            default_step_fields = ['bi_id', 'name', 'step_description']
            default_usecase_fields = ['bi_id', 'name', 'summary']

            fields_to_export_steps = selected_step_fields_form if selected_step_fields_form else default_step_fields
            fields_to_export_usecases = selected_usecase_fields_form if selected_usecase_fields_form else default_usecase_fields

            if not selected_step_fields_form and (selected_step_ids_int or selected_area_ids_int):
                flash("No Process Step fields explicitly selected. Including default fields (BI_ID, Name, Short Description) for selected steps.", "info")
            if not selected_usecase_fields_form and \
               (selected_usecase_ids_int or selected_step_ids_int or selected_area_ids_int or selected_wave_values_form):
                flash("No Use Case fields explicitly selected. Including default fields (BI_ID, Name, Summary) for selected use cases.", "info")

            step_query = session.query(ProcessStep)
            if selected_step_ids_int:
                step_query = step_query.filter(ProcessStep.id.in_(selected_step_ids_int))
            elif selected_area_ids_int:
                step_query = step_query.filter(ProcessStep.area_id.in_(selected_area_ids_int))

            steps_for_preview = step_query.options(joinedload(ProcessStep.area)).order_by(ProcessStep.area_id, ProcessStep.name).all()
            
            if selected_step_ids_int or selected_area_ids_int or not (selected_usecase_ids_int or selected_wave_values_form):
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
            
            if selected_wave_values_form:
                actual_wave_filters = []
                has_na_wave_filter = False
                for w_val in selected_wave_values_form:
                    if w_val == "N/A":
                        has_na_wave_filter = True
                    else:
                        actual_wave_filters.append(w_val)
                
                wave_conditions = []
                if actual_wave_filters:
                    wave_conditions.append(UseCase.wave.in_(actual_wave_filters))
                if has_na_wave_filter:
                    wave_conditions.append(or_(UseCase.wave.is_(None), UseCase.wave == ''))
                
                if wave_conditions:
                    usecase_query = usecase_query.filter(or_(*wave_conditions))

            usecases_for_preview = usecase_query.options(
                joinedload(UseCase.process_step).joinedload(ProcessStep.area)
            ).order_by(UseCase.process_step_id, UseCase.name).all()

            for uc in usecases_for_preview:
                uc_data = {
                    'id': uc.id,
                    'process_step_id': uc.process_step_id,
                    'process_step_name': uc.process_step.name if uc.process_step else 'N/A',
                    'area_id': uc.process_step.area.id if uc.process_step and uc.process_step.area else 'N/A',
                    'area_name': uc.process_step.area.name if uc.process_step and uc.process_step.area else 'N/A',
                    'wave': uc.wave
                }
                for field_key in fields_to_export_usecases:
                    if hasattr(uc, field_key):
                        uc_data[field_key] = getattr(uc, field_key)
                    else:
                        uc_data[field_key] = "N/A"
                prepared_data["use_cases"].append(uc_data)

            prepared_data["usecase_step_relevance"] = []
            if export_uc_step_relevance:
                relevance_query = session.query(UsecaseStepRelevance).options(
                    joinedload(UsecaseStepRelevance.source_usecase),
                    joinedload(UsecaseStepRelevance.target_process_step)
                )
                actual_exported_uc_ids = {uc_item['id'] for uc_item in prepared_data["use_cases"]}
                actual_exported_step_ids = {ps_item['id'] for ps_item in prepared_data["process_steps"]}

                relevance_filter_conditions = []
                if actual_exported_uc_ids:
                    relevance_filter_conditions.append(UsecaseStepRelevance.source_usecase_id.in_(actual_exported_uc_ids))
                if actual_exported_step_ids:
                     relevance_filter_conditions.append(UsecaseStepRelevance.target_process_step_id.in_(actual_exported_step_ids))
                
                if relevance_filter_conditions:
                    relevance_query = relevance_query.filter(and_(*relevance_filter_conditions))
                else: 
                    relevance_query = relevance_query.filter(False)


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


            json_string_for_tokens = json.dumps(prepared_data, indent=2)
            total_tokens = count_tokens(json_string_for_tokens)

        user_system_prompt = current_user.system_prompt if current_user.is_authenticated else ""
        ollama_models = get_all_available_llm_models()
        chat_history = list(get_chat_history())

        all_areas_flat = serialize_for_js(session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(session.query(UseCase).order_by(UseCase.name).all(), 'usecase')

        return render_template(
            'llm_data_prep.html',
            title="Data Mining",
            areas=areas,
            all_steps=all_steps_db,
            all_usecases=all_usecases_db,
            all_wave_values=all_wave_values_for_filter,
            selectable_fields_steps=SELECTABLE_STEP_FIELDS,
            selectable_fields_usecases=SELECTABLE_USECASE_FIELDS,
            prepared_data=prepared_data,
            total_tokens=total_tokens,
            selected_area_ids=selected_area_ids_int,
            selected_step_ids=selected_step_ids_int,
            selected_usecase_ids=selected_usecase_ids_int,
            selected_step_fields_form=selected_step_fields_form,
            selected_usecase_fields_form=selected_usecase_fields_form,
            selected_wave_values_form=selected_wave_values_form,
            export_uc_step_relevance=export_uc_step_relevance,
            ollama_models=ollama_models,
            chat_history=chat_history,
            config=current_app.config,
            user_system_prompt=user_system_prompt,
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            all_areas_flat=all_areas_flat,
            all_steps_flat=all_steps_flat,
            all_usecases_flat=all_usecases_flat
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
            all_wave_values=[],
            selectable_fields_steps=SELECTABLE_STEP_FIELDS,
            selectable_fields_usecases=SELECTABLE_USECASE_FIELDS,
            prepared_data={"process_steps": [], "use_cases": []},
            total_tokens=0,
            selected_area_ids=[],
            selected_step_ids=[],
            selected_usecase_ids=[],
            selected_step_fields_form=[],
            selected_usecase_fields_form=[],
            selected_wave_values_form=[],
            export_uc_step_relevance=False,
            ollama_models=[],
            chat_history=[],
            config=current_app.config,
            user_system_prompt=user_system_prompt_on_error,
            current_item=None,
            current_area=None,
            current_step=None,
            current_usecase=None,
            all_areas_flat=[],
            all_steps_flat=[],
            all_usecases_flat=[]
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
    user_message = request.json.get('message')
    model_name = request.json.get('model')
    image_base64 = request.json.get('image_base64')
    image_mime_type = request.json.get('image_mime_type')

    system_prompt = current_user.system_prompt if current_user.is_authenticated else None
    if system_prompt == "":
        system_prompt = None

    if not user_message and not image_base64:
        return jsonify({"success": False, "message": "Message or image is required."}), 400

    if not model_name:
        return jsonify({"success": False, "message": "Model is required."}), 400

    chat_history = get_chat_history()

    parts = model_name.split('-', 1)
    provider = parts[0] if len(parts) > 0 else "unknown"
    model_id = parts[1] if len(parts) > 1 else model_name

    response = {"success": False, "message": "Unsupported LLM provider or no response."}

    try:
        if provider == "ollama":
            response = generate_ollama_chat_response(
                model_id, user_message, system_prompt, image_base64, image_mime_type, chat_history
            )
        elif provider == "openai":
            response = generate_openai_chat_response(
                model_id, user_message, system_prompt, image_base64, image_mime_type, chat_history
            )
        elif provider == "anthropic":
            response = generate_anthropic_chat_response(
                model_id, user_message, system_prompt, image_base64, image_mime_type, chat_history
            )
        elif provider == "google":
            response = generate_google_chat_response(
                model_id, user_message, system_prompt, image_base64, image_mime_type, chat_history
            )
        elif provider == "apollo":
            response = generate_apollo_chat_response(
                model_id, user_message, system_prompt, image_base64, image_mime_type, chat_history
            )
        else:
            response = {"success": False, "message": f"Unknown or unsupported LLM provider: {provider}"}

    except Exception as e:
        response = {"success": False, "message": f"Server error calling LLM: {e}"}
        traceback.print_exc()

    if response["success"]:
        user_message_for_history = user_message
        if not user_message_for_history and image_base64:
            user_message_for_history = "Image provided."
        add_message_to_history('user', user_message_for_history)
        add_message_to_history('assistant', response["message"])

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


@llm_routes.route('/analyze-usecase-image', methods=['POST'])
@login_required
def analyze_usecase_image_with_llm():
    session_db = SessionLocal()
    try:
        data = request.json
        usecase_id = data.get('usecase_id')
        image_base64 = data.get('image_base64')
        image_mime_type = data.get('image_mime_type')
        selected_model_name = data.get('model')
        system_prompt_override = data.get('system_prompt_override')

        if not all([usecase_id, image_base64, image_mime_type, selected_model_name]):
            return jsonify({
                "success": False, "message": "Missing required data: usecase_id, image_base64, image_mime_type, or model."
            }), 400

        usecase = session_db.query(UseCase).get(usecase_id)
        if not usecase:
            return jsonify({"success": False, "message": "Use Case not found."}), 404

        prompt_context = {
            "usecase_name": usecase.name or "N/A",
            "usecase_summary": usecase.summary or "N/A",
            "usecase_business_problem_solved": usecase.business_problem_solved or "N/A",
            "usecase_target_solution_description": usecase.target_solution_description or "N/A",
            "usecase_pilot_site_factory_text": usecase.pilot_site_factory_text or "N/A",
            "usecase_effort_quantification": usecase.effort_quantification or "N/A",
            "usecase_potential_quantification": usecase.potential_quantification or "N/A",
            "usecase_dependencies_text": usecase.dependencies_text or "N/A",
            "usecase_usecase_type_category": usecase.usecase_type_category or "N/A",
        }
        
        active_system_prompt_template = system_prompt_override if system_prompt_override else AI_ASSIST_IMAGE_SYSTEM_PROMPT_TEMPLATE
        
        try:
            final_llm_prompt_text = active_system_prompt_template.format(**prompt_context)
        except KeyError as e:
            print(f"KeyError formatting prompt template: {e}. Context: {prompt_context}. Template: {active_system_prompt_template}")
            return jsonify({
                "success": False,
                "message": f"Error formatting the prompt template. A placeholder like '{{{e}}}' might be missing from the provided context or the template is malformed."
            }), 500
        
        parts = selected_model_name.split('-', 1)
        provider = parts[0].lower()
        model_id = parts[1] if len(parts) > 1 else selected_model_name

        llm_response_data = {"success": False, "message": "LLM provider not supported or error."}

        if provider == "openai":
            llm_response_data = generate_openai_chat_response(
                model_id, final_llm_prompt_text, None, image_base64, image_mime_type, []
            )
        elif provider == "anthropic":
            llm_response_data = generate_anthropic_chat_response(
                model_id, final_llm_prompt_text, None, image_base64, image_mime_type, []
            )
        elif provider == "google":
             llm_response_data = generate_google_chat_response(
                 model_id, final_llm_prompt_text, None, image_base64, image_mime_type, []
             )
        elif provider == "ollama":
            llm_response_data = generate_ollama_chat_response(
                model_id, final_llm_prompt_text, None, image_base64, image_mime_type, []
            )
        elif provider == "apollo":
            llm_response_data = generate_apollo_chat_response(
                model_id, final_llm_prompt_text, None, image_base64, image_mime_type, []
            )
        else:
            return jsonify({"success": False, "message": f"Unsupported LLM provider: {provider}"}), 400

        if llm_response_data.get("success"):
            try:
                response_message = llm_response_data["message"]
                if response_message.startswith("```json"):
                    response_message = response_message[len("```json"):].strip()
                if response_message.startswith("```"): 
                     response_message = response_message[len("```"):].strip()
                if response_message.endswith("```"):
                    response_message = response_message[:-len("```")].strip()

                suggested_updates = json.loads(response_message)
                if not isinstance(suggested_updates, dict):
                    raise ValueError("LLM did not return a JSON object.")
                return jsonify({"success": True, "suggestions": suggested_updates})
            except json.JSONDecodeError:
                print(f"LLM response was not valid JSON: {llm_response_data['message']}")
                return jsonify({
                    "success": False,
                    "message": "LLM response was not valid JSON. Please check the LLM's output format. It might have included explanations or markdown.",
                    "raw_response": llm_response_data["message"]
                }), 500
            except ValueError as ve:
                 print(f"LLM JSON validation error: {ve}")
                 return jsonify({
                     "success": False,
                     "message": str(ve),
                     "raw_response": llm_response_data["message"]
                 }), 500
        else:
            return jsonify(llm_response_data), 500

    except Exception as e:
        print(f"Error in /analyze-usecase-image: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": f"An internal server error occurred: {str(e)}"}), 500
    finally:
        session_db.close()


@llm_routes.route('/get_llm_models', methods=['GET'])
@login_required
def get_llm_models_api():
    models = get_all_available_llm_models()
    return jsonify({"success": True, "models": models})


@llm_routes.route('/get_chat_history', methods=['GET'])
@login_required
def get_chat_history_api():
    history = get_chat_history()
    return jsonify({"success": True, "history": history})