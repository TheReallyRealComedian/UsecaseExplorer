# backend/services/llm_service.py
import requests
import tiktoken
import json
import os
import time
import traceback
from io import BytesIO
from flask import session as flask_session, current_app
from collections import deque
import logging
from flask_login import current_user
from ..db import SessionLocal
from ..models import User, LLMSettings, ProcessStep, UseCase, UsecaseStepRelevance
from sqlalchemy.orm import joinedload, selectinload
from sqlalchemy import or_

# --- SDK Imports ---
import openai
from anthropic import Anthropic
import google.generativeai as genai
from langchain_openai import ChatOpenAI
import base64

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Global Apollo Token Cache ---
_apollo_access_token = None
_apollo_token_expiry = 0

# --- API Key & URL Retrieval Functions ---
def get_ollama_base_url():
    if current_user.is_authenticated:
        session = SessionLocal()
        user = session.query(User).options(joinedload(User.llm_settings)).get(current_user.id)
        if user and user.llm_settings and user.llm_settings.ollama_base_url:
            return user.llm_settings.ollama_base_url
        SessionLocal.remove()
    return os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')

def get_openai_api_key():
    if current_user.is_authenticated:
        session = SessionLocal()
        user = session.query(User).options(joinedload(User.llm_settings)).get(current_user.id)
        if user and user.llm_settings and user.llm_settings.openai_api_key:
            return user.llm_settings.openai_api_key
        SessionLocal.remove()
    return os.environ.get('OPENAI_API_KEY')

def get_anthropic_api_key():
    if current_user.is_authenticated:
        session = SessionLocal()
        user = session.query(User).options(joinedload(User.llm_settings)).get(current_user.id)
        if user and user.llm_settings and user.llm_settings.anthropic_api_key:
            return user.llm_settings.anthropic_api_key
        SessionLocal.remove()
    return os.environ.get('ANTHROPIC_API_KEY')

def get_google_api_key():
    if current_user.is_authenticated:
        session = SessionLocal()
        user = session.query(User).options(joinedload(User.llm_settings)).get(current_user.id)
        if user and user.llm_settings and user.llm_settings.google_api_key:
            return user.llm_settings.google_api_key
        SessionLocal.remove()
    return os.environ.get('GOOGLE_API_KEY')

def get_apollo_client_credentials():
    if current_user.is_authenticated:
        session = SessionLocal()
        user = session.query(User).options(joinedload(User.llm_settings)).get(current_user.id)
        if user and user.llm_settings and user.llm_settings.apollo_client_id and user.llm_settings.apollo_client_secret:
            return user.llm_settings.apollo_client_id, user.llm_settings.apollo_client_secret
        SessionLocal.remove()
    return current_app.config.get('APOLLO_CLIENT_ID'), current_app.config.get('APOLLO_CLIENT_SECRET')

def get_apollo_access_token():
    global _apollo_access_token, _apollo_token_expiry
    if _apollo_access_token and time.time() < _apollo_token_expiry:
        return _apollo_access_token
    client_id, client_secret = get_apollo_client_credentials()
    token_url = current_app.config.get('APOLLO_TOKEN_URL')
    if not client_id or not client_secret:
        raise ValueError("Apollo credentials not configured.")
    if not token_url:
        raise ValueError("Apollo TOKEN_URL not configured.")
    try:
        response = requests.post(
            token_url,
            data={"grant_type": "client_credentials", "client_id": client_id, "client_secret": client_secret},
            timeout=10
        )
        response.raise_for_status()
        json_response = response.json()
        _apollo_access_token = json_response['access_token']
        _apollo_token_expiry = time.time() + json_response.get('expires_in', 3500)
        return _apollo_access_token
    except requests.exceptions.HTTPError as e:
        raise ValueError(f"Apollo Token Error: {e.response.text}") from e
    except requests.exceptions.RequestException as e:
        raise ValueError(f"Apollo Token Error: Network request failed: {e}") from e

# --- Chat History Management ---
def _get_history_deque():
    max_len = current_app.config.get('MAX_CHAT_HISTORY_LENGTH', 10)
    return deque(flask_session.get('llm_chat_history', []), maxlen=max_len)

def _save_history_deque(history_deque):
    flask_session['llm_chat_history'] = list(history_deque)

def get_chat_history():
    return list(_get_history_deque())

def add_message_to_history(role, content):
    history_deque = _get_history_deque()
    history_deque.append({'role': role, 'content': content})
    _save_history_deque(history_deque)

def clear_chat_history():
    flask_session.pop('llm_chat_history', None)

# --- Data Preparation Service Logic ---

def prepare_data_for_llm(db_session, form_data, selectable_step_fields, selectable_uc_fields):
    """
    Prepares data based on form selections for LLM analysis.
    """
    # Parse form data
    area_ids = [int(id_str) for id_str in form_data.getlist('area_ids') if id_str.isdigit()]
    step_ids = [int(id_str) for id_str in form_data.getlist('step_ids') if id_str.isdigit()]
    usecase_ids = [int(id_str) for id_str in form_data.getlist('usecase_ids') if id_str.isdigit()]
    wave_values = form_data.getlist('wave_values')
    selected_step_fields = form_data.getlist('step_fields')
    selected_uc_fields = form_data.getlist('usecase_fields')
    export_relevance = form_data.get('export_uc_step_relevance') == 'on'

    prepared_data = {"process_steps": [], "use_cases": []}
    
    # Base queries
    steps_query = db_session.query(ProcessStep).options(selectinload(ProcessStep.area))
    usecases_query = db_session.query(UseCase).options(selectinload(UseCase.process_step).selectinload(ProcessStep.area))

    # Apply filters
    if usecase_ids:
        usecases_query = usecases_query.filter(UseCase.id.in_(usecase_ids))
    elif step_ids:
        usecases_query = usecases_query.filter(UseCase.process_step_id.in_(step_ids))
    elif area_ids:
        usecases_query = usecases_query.join(ProcessStep).filter(ProcessStep.area_id.in_(area_ids))

    if wave_values:
        # Handle 'N/A' as a filter for NULL or empty strings
        if "N/A" in wave_values:
            wave_conditions = [UseCase.wave.in_(wave_values), UseCase.wave.is_(None), UseCase.wave == '']
            usecases_query = usecases_query.filter(or_(*wave_conditions))
        else:
            usecases_query = usecases_query.filter(UseCase.wave.in_(wave_values))
        
    final_usecases = usecases_query.all()

    if step_ids:
        steps_query = steps_query.filter(ProcessStep.id.in_(step_ids))
    elif area_ids:
        steps_query = steps_query.filter(ProcessStep.area_id.in_(area_ids))
        
    final_steps = steps_query.all()

    # Serialize selected data
    for step in final_steps:
        step_data = {"id": step.id, "area_name": step.area.name if step.area else "N/A"}
        for field in selected_step_fields:
            if hasattr(step, field):
                step_data[field] = getattr(step, field)
        prepared_data["process_steps"].append(step_data)

    for uc in final_usecases:
        uc_data = {
            "id": uc.id, 
            "area_name": uc.area.name if uc.area else "N/A",
            "process_step_name": uc.process_step.name if uc.process_step else "N/A"
        }
        for field in selected_uc_fields:
            if hasattr(uc, field):
                uc_data[field] = getattr(uc, field)
        prepared_data["use_cases"].append(uc_data)
        
    if export_relevance:
        prepared_data["usecase_step_relevance"] = []
        # Get IDs of selected items for efficient filtering
        final_uc_ids = [uc.id for uc in final_usecases]
        final_step_ids = [step.id for step in final_steps]

        if final_uc_ids and final_step_ids:
            relevance_query = db_session.query(UsecaseStepRelevance).options(
                selectinload(UsecaseStepRelevance.source_usecase),
                selectinload(UsecaseStepRelevance.target_process_step)
            ).filter(
                UsecaseStepRelevance.source_usecase_id.in_(final_uc_ids),
                UsecaseStepRelevance.target_process_step_id.in_(final_step_ids)
            )
            relevance_links = relevance_query.all()
            for rel in relevance_links:
                prepared_data["usecase_step_relevance"].append({
                    "source_usecase_name": rel.source_usecase.name,
                    "source_usecase_bi_id": rel.source_usecase.bi_id,
                    "target_process_step_name": rel.target_process_step.name,
                    "target_process_step_bi_id": rel.target_process_step.bi_id,
                    "relevance_score": rel.relevance_score,
                    "relevance_content": rel.relevance_content
                })

    # Calculate token count
    json_string = json.dumps(prepared_data, default=str)
    try:
        encoding = tiktoken.get_encoding("cl100k_base")
        total_tokens = len(encoding.encode(json_string))
    except Exception:
        total_tokens = len(json_string) // 4  # Fallback approximation

    return prepared_data, total_tokens

# --- REFACTORED: Provider-Specific Chat Generation Functions ---
# These functions are now simpler, only handling the direct API call.

def _call_ollama(model_id, messages, **kwargs):
    api_url = f"{get_ollama_base_url()}/api/chat"
    payload = {"model": model_id, "messages": messages, "stream": False}
    response = requests.post(api_url, json=payload, headers={"Content-Type": "application/json"}, timeout=300)
    response.raise_for_status()
    return response.json()['message']['content']

def _call_openai(model_id, messages, **kwargs):
    client = openai.OpenAI(api_key=get_openai_api_key())
    response = client.chat.completions.create(model=model_id, messages=messages, temperature=0.7, max_tokens=1024)
    return response.choices[0].message.content

def _call_anthropic(model_id, messages, **kwargs):
    client = Anthropic(api_key=get_anthropic_api_key())
    system_prompt = kwargs.get('system_prompt', '')
    response = client.messages.create(model=model_id, max_tokens=1024, system=system_prompt, messages=messages)
    return response.content[0].text

def _call_google(model_id, messages, **kwargs):
    genai.configure(api_key=get_google_api_key())
    model_config = {}
    if kwargs.get('system_prompt'):
        model_config['system_instruction'] = kwargs.get('system_prompt')
    model = genai.GenerativeModel(model_name=model_id, **model_config)
    chat = model.start_chat(history=kwargs.get('history_for_google', []))
    response = chat.send_message(messages[-1]['parts'])
    response.resolve()
    return response.text

def _call_apollo(model_id, messages, **kwargs):
    llm_model = ChatOpenAI(
        model=model_id,
        base_url=current_app.config.get('APOLLO_LLM_API_BASE_URL'),
        api_key=get_apollo_access_token(),
        temperature=0.01,
        timeout=300
    )
    response = llm_model.invoke(messages)
    return response.content

# --- REFACTORED: Main dispatcher function ---

PROVIDER_HANDLERS = {
    "ollama": _call_ollama,
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "google": _call_google,
    "apollo": _call_apollo,
}

def generate_chat_response(model_name, user_message, system_prompt, image_base64, image_mime_type, chat_history):
    """
    Main dispatcher for generating chat responses from any provider.
    Handles message preparation and calls the appropriate provider handler.
    """
    provider, model_id = model_name.split('-', 1) if '-' in model_name else ("unknown", model_name)
    handler = PROVIDER_HANDLERS.get(provider)
    if not handler:
        return {"success": False, "message": f"Unsupported LLM provider: {provider}"}

    # --- Prepare messages based on provider requirements ---
    messages_for_api = []
    
    # Common message prep
    if provider not in ['google', 'anthropic']:
        if system_prompt:
            messages_for_api.append({'role': 'system', 'content': system_prompt})
        if chat_history:
            messages_for_api.extend(chat_history)

    # User message content preparation
    user_content_blocks = []
    if user_message:
        user_content_blocks.append({"type": "text", "text": user_message})
    if image_base64 and image_mime_type:
        if provider == "ollama":
            user_content_blocks.insert(0, {"type": "image_base64", "data": image_base64})
        elif provider in ["openai", "apollo"]:
            user_content_blocks.append({"type": "image_url", "image_url": {"url": f"data:{image_mime_type};base64,{image_base64}"}})
        elif provider == "anthropic":
            user_content_blocks.append({"type": "image", "source": {"type": "base64", "media_type": image_mime_type, "data": image_base64}})
        elif provider == "google":
            img_part = genai.upload_file(paths=[BytesIO(base64.b64decode(image_base64))], mime_type=image_mime_type)
            user_content_blocks.append(img_part)

    if not user_message and image_base64:
        user_content_blocks.append({"type": "text", "text": "Analyze this image."})

    # Provider-specific message formatting
    history_for_google = None # Initialize
    if provider == "google":
        history_for_google = [{"role": msg['role'], "parts": [msg['content']]} for msg in chat_history]
        google_parts = [block['text'] if block['type'] == 'text' else block for block in user_content_blocks]
        messages_for_api.append({'role': 'user', 'parts': google_parts})
    elif provider == "ollama":
        user_message_content = next((item['text'] for item in user_content_blocks if item['type'] == 'text'), "")
        user_message_images = [item['data'] for item in user_content_blocks if item['type'] == 'image_base64']
        user_msg = {'role': 'user', 'content': user_message_content}
        if user_message_images:
            user_msg['images'] = user_message_images
        messages_for_api.append(user_msg)
    elif provider == "anthropic":
        for msg in chat_history:
            messages_for_api.append({"role": msg['role'], "content": [{"type": "text", "text": msg['content']}]})
        messages_for_api.append({"role": "user", "content": user_content_blocks})
    else: # OpenAI / Apollo
        messages_for_api.append({"role": "user", "content": user_content_blocks})

    # --- Call the handler and handle exceptions ---
    try:
        logging.info(f"Calling provider '{provider}' with model '{model_id}'...")
        assistant_message = handler(
            model_id=model_id, 
            messages=messages_for_api, 
            system_prompt=system_prompt, 
            history_for_google=history_for_google
        )
        return {"success": True, "message": assistant_message}
    except Exception as e:
        error_msg = f"Error from {provider.capitalize()} API: {e}"
        logging.error(f"{error_msg}\n{traceback.format_exc()}")
        return {"success": False, "message": error_msg}


# --- Model Discovery Functions ---
def get_available_ollama_models():
    ollama_url = get_ollama_base_url()
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        return [f"ollama-{model['name']}" for model in response.json().get('models', [])]
    except requests.exceptions.RequestException as e:
        return [f"ollama-Error: {e.__class__.__name__}"]

def get_available_openai_models():
    return [f"openai-{m}" for m in ["gpt-4o", "gpt-4o-mini", "gpt-4-turbo", "gpt-3.5-turbo"]] if get_openai_api_key() else []

def get_available_anthropic_models():
    return [f"anthropic-{m}" for m in ["claude-3-opus-20240229", "claude-3-sonnet-20240229", "claude-3-haiku-20240307"]] if get_anthropic_api_key() else []

def get_available_google_models():
    return [f"google-{m}" for m in ["gemini-pro", "gemini-pro-vision", "gemini-1.5-pro-latest", "gemini-1.5-flash-latest"]] if get_google_api_key() else []

def get_available_apollo_models():
    apollo_url = current_app.config.get('APOLLO_LLM_API_BASE_URL')
    if not apollo_url:
        return []
    try:
        access_token = get_apollo_access_token()
        response = requests.get(f"{apollo_url}/model_group/info", headers={"Authorization": f"Bearer {access_token}"}, timeout=10)
        response.raise_for_status()
        return [f"apollo-{model['model_group']}" for model in response.json().get('data', []) if model.get('mode') == 'chat']
    except Exception as e:
        return [f"apollo-Error: {e.__class__.__name__}"]

def get_all_available_llm_models():
    all_models = []
    all_models.extend(get_available_openai_models())
    all_models.extend(get_available_anthropic_models())
    all_models.extend(get_available_google_models())
    all_models.extend(get_available_apollo_models())
    all_models.extend(get_available_ollama_models())
    return list(dict.fromkeys(filter(None, all_models)))