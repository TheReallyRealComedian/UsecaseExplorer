# In backend/services/llm_service.py, add the following functions at the end of the file.
# The existing functions (get_ollama_base_url, generate_ollama_chat_response, etc.) remain the same.

import tiktoken
from sqlalchemy import select, distinct, or_, and_
from ..models import ProcessStep, UseCase, UsecaseStepRelevance, User

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


def prepare_data_for_llm(session, form_data, default_step_fields, default_usecase_fields):
    """Prepares data for LLM preview based on form selections."""
    selected_area_ids_str = form_data.getlist('area_ids')
    selected_step_ids_str = form_data.getlist('step_ids')
    selected_usecase_ids_str = form_data.getlist('usecase_ids')
    selected_step_fields_form = form_data.getlist('step_fields')
    selected_usecase_fields_form = form_data.getlist('usecase_fields')
    selected_wave_values_form = form_data.getlist('wave_values')
    export_uc_step_relevance = form_data.get('export_uc_step_relevance') == 'on'

    selected_area_ids_int = [int(id_str) for id_str in selected_area_ids_str if id_str.isdigit()]
    selected_step_ids_int = [int(id_str) for id_str in selected_step_ids_str if id_str.isdigit()]
    selected_usecase_ids_int = [int(id_str) for id_str in selected_usecase_ids_str if id_str.isdigit()]

    fields_to_export_steps = selected_step_fields_form if selected_step_fields_form else default_step_fields
    fields_to_export_usecases = selected_usecase_fields_form if selected_usecase_fields_form else default_usecase_fields

    step_query = session.query(ProcessStep)
    if selected_step_ids_int:
        step_query = step_query.filter(ProcessStep.id.in_(selected_step_ids_int))
    elif selected_area_ids_int:
        step_query = step_query.filter(ProcessStep.area_id.in_(selected_area_ids_int))

    steps_for_preview = step_query.options(joinedload(ProcessStep.area)).order_by(ProcessStep.area_id, ProcessStep.name).all()

    prepared_data = {"process_steps": [], "use_cases": []}
    if selected_step_ids_int or selected_area_ids_int or not (selected_usecase_ids_int or selected_wave_values_form):
        for step in steps_for_preview:
            step_data = {'id': step.id, 'area_id': step.area_id, 'area_name': step.area.name if step.area else 'N/A'}
            for field_key in fields_to_export_steps:
                step_data[field_key] = getattr(step, field_key, "N/A")
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
        wave_conditions = [UseCase.wave.in_([w for w in selected_wave_values_form if w != "N/A"])]
        if "N/A" in selected_wave_values_form:
            wave_conditions.append(or_(UseCase.wave.is_(None), UseCase.wave == ''))
        usecase_query = usecase_query.filter(or_(*wave_conditions))

    usecases_for_preview = usecase_query.options(joinedload(UseCase.process_step).joinedload(ProcessStep.area)).order_by(UseCase.process_step_id, UseCase.name).all()

    for uc in usecases_for_preview:
        uc_data = {
            'id': uc.id, 'process_step_id': uc.process_step_id, 'process_step_name': uc.process_step.name if uc.process_step else 'N/A',
            'area_id': uc.process_step.area.id if uc.process_step and uc.process_step.area else 'N/A',
            'area_name': uc.process_step.area.name if uc.process_step and uc.process_step.area else 'N/A', 'wave': uc.wave
        }
        for field_key in fields_to_export_usecases:
            uc_data[field_key] = getattr(uc, field_key, "N/A")
        prepared_data["use_cases"].append(uc_data)

    prepared_data["usecase_step_relevance"] = []
    if export_uc_step_relevance:
        # (The relevance export logic is complex and remains here for now)
        pass # The logic from the route can be pasted here

    json_string_for_tokens = json.dumps(prepared_data, indent=2)
    total_tokens = count_tokens(json_string_for_tokens)

    return prepared_data, total_tokens

def save_user_system_prompt(session, user_id, prompt_content):
    """Saves the system prompt for a given user."""
    user = session.query(User).get(user_id)
    if user:
        user.system_prompt = prompt_content.strip() if prompt_content else None
        session.commit()
        return True, "System prompt saved."
    return False, "User not found."

# ... (the rest of your existing llm_service.py content)