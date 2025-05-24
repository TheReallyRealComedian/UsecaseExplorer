# backend/routes/llm_routes.py
from flask import Blueprint, request, flash, redirect, url_for, render_template
from flask_login import login_required
from sqlalchemy.orm import joinedload
from ..db import SessionLocal
from ..models import ProcessStep, Area
import json # For json.dumps
import tiktoken # For token counting

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

        if request.method == 'POST':
            selected_area_ids_str = request.form.getlist('area_ids')
            selected_step_ids_str = request.form.getlist('step_ids')
            selected_fields_form = request.form.getlist('fields')

            selected_area_ids_int = [int(id_str) for id_str in selected_area_ids_str if id_str.isdigit()]
            selected_step_ids_int = [int(id_str) for id_str in selected_step_ids_str if id_str.isdigit()]

            if not selected_fields_form:
                flash("Please select at least one field to preview.", "warning")
                # Ensure prepared_data remains None if no fields are selected
            else:
                query = session.query(ProcessStep)
                if selected_step_ids_int:
                    query = query.filter(ProcessStep.id.in_(selected_step_ids_int))
                elif selected_area_ids_int: # If no specific steps, but areas are selected
                    query = query.filter(ProcessStep.area_id.in_(selected_area_ids_int))
                # If neither steps nor areas selected, query will fetch all steps.

                steps_for_preview = query.order_by(ProcessStep.area_id, ProcessStep.name).all()

                if not steps_for_preview:
                    flash("No process steps found matching your criteria.", "info")
                    prepared_data = [] # Explicitly set to empty list to differentiate from None
                else:
                    prepared_data = []
                    for step in steps_for_preview:
                        step_data = {'id': step.id} # Always include ID for reference
                        for field_key in selected_fields_form:
                            if hasattr(step, field_key):
                                step_data[field_key] = getattr(step, field_key)
                            else:
                                step_data[field_key] = "N/A (invalid field)"
                        prepared_data.append(step_data)

                    if not prepared_data: # Should not happen if steps_for_preview was not empty, but safety check
                         flash("No data to preview after filtering fields.", "info")
                    else:
                        # Convert the prepared data to a JSON string and count tokens
                        # Only convert to JSON string if prepared_data is not empty
                        json_string_for_tokens = json.dumps(prepared_data, indent=2)
                        total_tokens = count_tokens(json_string_for_tokens)

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
            selected_fields_form=selected_fields_form
        )

    except Exception as e:
        print(f"Error in LLM data prep page: {e}")
        flash("An error occurred while preparing data. Please try again.", "danger")
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
            selected_fields_form=[]
        )
    finally:
        SessionLocal.remove()


@llm_routes.route('/analyze/<int:usecase_id>', methods=['POST', 'GET'])
@login_required
def analyze_usecase(usecase_id):
    """Handles triggering an LLM analysis for a specific Use Case."""
    flash(f"LLM analysis for Use Case ID {usecase_id} requested. Not implemented yet.", "info")
    return redirect(url_for('usecases.view_usecase', usecase_id=usecase_id))

# Add other LLM-related routes here later if needed