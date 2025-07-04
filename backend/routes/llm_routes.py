# backend/routes/llm_routes.py

import json
import traceback

from flask import Blueprint, g, request, flash, redirect, url_for, render_template, jsonify, current_app
from flask_login import login_required, current_user
from sqlalchemy.orm import joinedload
from sqlalchemy import distinct, or_

from ..services import llm_service
from ..models import ProcessStep, Area, User, UseCase, UsecaseStepRelevance
from ..utils import serialize_for_js

llm_routes = Blueprint(
    'llm',
    __name__,
    template_folder='../templates',
    url_prefix='/llm'
)

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

@llm_routes.route('/data-prep', methods=['GET', 'POST'])
@login_required
def llm_data_prep_page():
    try:
        prepared_data = {"process_steps": [], "use_cases": []}
        total_tokens = 0
        form_data_for_template = {
            'selected_area_ids': [],
            'selected_step_ids': [],
            'selected_usecase_ids': [],
            'selected_step_fields_form': [],
            'selected_usecase_fields_form': [],
            'selected_wave_values_form': [],
            'export_uc_step_relevance': False
        }

        if request.method == 'POST':
            prepared_data, total_tokens = llm_service.prepare_data_for_llm(
                g.db_session, request.form, SELECTABLE_STEP_FIELDS.keys(), SELECTABLE_USECASE_FIELDS.keys()
            )
            # Store selections to re-render the form state
            form_data_for_template = {
                'selected_area_ids': [int(id_str) for id_str in request.form.getlist('area_ids') if id_str.isdigit()],
                'selected_step_ids': [int(id_str) for id_str in request.form.getlist('step_ids') if id_str.isdigit()],
                'selected_usecase_ids': [int(id_str) for id_str in request.form.getlist('usecase_ids') if id_str.isdigit()],
                'selected_step_fields_form': request.form.getlist('step_fields'),
                'selected_usecase_fields_form': request.form.getlist('usecase_fields'),
                'selected_wave_values_form': request.form.getlist('wave_values'),
                'export_uc_step_relevance': request.form.get('export_uc_step_relevance') == 'on'
            }

        # Data for initial page load and for re-rendering the form filters
        areas = g.db_session.query(Area).order_by(Area.name).all()
        all_steps_db = g.db_session.query(ProcessStep).options(joinedload(ProcessStep.area)).order_by(ProcessStep.name).all()
        all_usecases_db = g.db_session.query(UseCase).options(
            joinedload(UseCase.process_step).joinedload(ProcessStep.area)
        ).order_by(UseCase.name).all()

        distinct_waves_query = g.db_session.query(distinct(UseCase.wave)).filter(UseCase.wave.isnot(None)).filter(UseCase.wave != '').order_by(UseCase.wave).all()
        all_wave_values_for_filter = [w[0] for w in distinct_waves_query if w[0]]
        if g.db_session.query(UseCase).filter(or_(UseCase.wave.is_(None), UseCase.wave == '')).first():
            if "N/A" not in all_wave_values_for_filter:
                all_wave_values_for_filter.append("N/A")

        user_system_prompt = current_user.system_prompt if current_user.is_authenticated else ""
        ollama_models = llm_service.get_all_available_llm_models()
        chat_history = list(llm_service.get_chat_history())

        all_areas_flat = serialize_for_js(g.db_session.query(Area).order_by(Area.name).all(), 'area')
        all_steps_flat = serialize_for_js(g.db_session.query(ProcessStep).order_by(ProcessStep.name).all(), 'step')
        all_usecases_flat = serialize_for_js(g.db_session.query(UseCase).order_by(UseCase.name).all(), 'usecase')

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
            all_usecases_flat=all_usecases_flat,
            **form_data_for_template
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
            areas=[], all_steps=[], all_usecases=[], all_wave_values=[],
            selectable_fields_steps=SELECTABLE_STEP_FIELDS,
            selectable_fields_usecases=SELECTABLE_USECASE_FIELDS,
            prepared_data={"process_steps": [], "use_cases": []},
            total_tokens=0,
            ollama_models=[], chat_history=[],
            config=current_app.config,
            user_system_prompt=user_system_prompt_on_error,
            current_item=None, current_area=None, current_step=None, current_usecase=None,
            all_areas_flat=[], all_steps_flat=[], all_usecases_flat=[],
            selected_area_ids=[], selected_step_ids=[], selected_usecase_ids=[],
            selected_step_fields_form=[], selected_usecase_fields_form=[],
            selected_wave_values_form=[], export_uc_step_relevance=False,
        )


@llm_routes.route('/analyze/<int:usecase_id>', methods=['POST', 'GET'])
@login_required
def analyze_usecase(usecase_id):
    """Handles triggering an LLM analysis for a specific Use Case."""
    flash(f"LLM analysis for Use Case ID {usecase_id} requested. Not implemented yet.", "info")
    return redirect(url_for('usecases.view_usecase', usecase_id=usecase_id))


@llm_routes.route('/chat', methods=['POST'])
@login_required
def llm_chat():
    data = request.json
    user_message = data.get('message')
    model_name = data.get('model')
    image_base64 = data.get('image_base64')
    image_mime_type = data.get('image_mime_type')

    system_prompt = current_user.system_prompt if current_user.is_authenticated else None

    if not user_message and not image_base64:
        return jsonify({"success": False, "message": "Message or image is required."}), 400
    if not model_name:
        return jsonify({"success": False, "message": "Model is required."}), 400

    try:
        chat_history = llm_service.get_chat_history()

        response = llm_service.generate_chat_response(
            model_name=model_name,
            user_message=user_message,
            system_prompt=system_prompt,
            image_base64=image_base64,
            image_mime_type=image_mime_type,
            chat_history=chat_history
        )

        if response.get("success"):
            user_message_for_history = user_message or "Image provided."
            llm_service.add_message_to_history('user', user_message_for_history)
            llm_service.add_message_to_history('assistant', response["message"])

        return jsonify(response)

    except Exception as e:
        traceback.print_exc()
        return jsonify({"success": False, "message": f"An unexpected error occurred in the chat route: {e}"}), 500


@llm_routes.route('/system-prompt', methods=['POST'])
@login_required
def save_system_prompt():
    prompt_content = request.json.get('prompt')
    if prompt_content is None:
        return jsonify({"success": False, "message": "Prompt content is required."}), 400

    try:
        success, message = llm_service.save_user_system_prompt(g.db_session, current_user.id, prompt_content)
        return jsonify({"success": success, "message": message}), 200 if success else 404
    except Exception as e:
        g.db_session.rollback()
        print(f"Error saving system prompt for user {current_user.id}: {e}")
        traceback.print_exc()
        return jsonify({"success": False, "message": f"Failed to save system prompt: {e}"}), 500


@llm_routes.route('/chat/clear', methods=['POST'])
@login_required
def llm_chat_clear():
    llm_service.clear_chat_history()
    return jsonify({"success": True, "message": "Chat history cleared."})


@llm_routes.route('/analyze-usecase-image', methods=['POST'])
@login_required
def analyze_usecase_image_with_llm():
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

        usecase = g.db_session.query(UseCase).get(usecase_id)
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
            llm_response_data = llm_service.generate_openai_chat_response(
                model_id, final_llm_prompt_text, None, image_base64, image_mime_type, []
            )
        elif provider == "anthropic":
            llm_response_data = llm_service.generate_anthropic_chat_response(
                model_id, final_llm_prompt_text, None, image_base64, image_mime_type, []
            )
        elif provider == "google":
             llm_response_data = llm_service.generate_google_chat_response(
                 model_id, final_llm_prompt_text, None, image_base64, image_mime_type, []
             )
        elif provider == "ollama":
            llm_response_data = llm_service.generate_ollama_chat_response(
                model_id, final_llm_prompt_text, None, image_base64, image_mime_type, []
            )
        elif provider == "apollo":
            llm_response_data = llm_service.generate_apollo_chat_response(
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


@llm_routes.route('/get_llm_models', methods=['GET'])
@login_required
def get_llm_models_api():
    models = llm_service.get_all_available_llm_models()
    return jsonify({"success": True, "models": models})


@llm_routes.route('/get_chat_history', methods=['GET'])
@login_required
def get_chat_history_api():
    history = llm_service.get_chat_history()
    return jsonify({"success": True, "history": history})