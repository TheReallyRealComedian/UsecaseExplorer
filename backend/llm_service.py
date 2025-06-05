# backend/llm_service.py

import requests
import json
import os
import time # Import time for token expiry management
from flask import session as flask_session, current_app
from collections import deque
import logging
from flask_login import current_user
from .db import SessionLocal
from .models import User, LLMSettings
from sqlalchemy.orm import joinedload

import openai
from anthropic import Anthropic
import base64
import google.generativeai as genai

# NEW: Import for Apollo integration (LiteLLM compatibility)
from langchain_openai import ChatOpenAI

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

# --- Global Apollo Token Cache ---
_apollo_access_token = None
_apollo_token_expiry = 0

# --- API Key & URL Retrieval Functions ---

def get_ollama_base_url():
    """
    Retrieves Ollama base URL, prioritizing user-specific settings from the database,
    then falling back to environment variables.
    """
    if current_user.is_authenticated:
        session = SessionLocal()
        try:
            user = session.query(User).options(joinedload(User.llm_settings)).get(current_user.id)
            if user and user.llm_settings and user.llm_settings.ollama_base_url:
                logging.info("Using user-specific Ollama Base URL.")
                return user.llm_settings.ollama_base_url
        except Exception as e:
            logging.error(f"Error fetching user Ollama URL from DB: {e}")
        finally:
            SessionLocal.remove()
    env_url = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    logging.info(f"Using environment variable Ollama Base URL: {env_url} (or default if not set).")
    return env_url

def get_openai_api_key():
    """
    Retrieves OpenAI API key, prioritizing user-specific settings from the database,
    then falling back to environment variables.
    """
    if current_user.is_authenticated:
        session = SessionLocal()
        try:
            user = session.query(User).options(joinedload(User.llm_settings)).get(current_user.id)
            if user and user.llm_settings and user.llm_settings.openai_api_key:
                logging.info("Using user-specific OpenAI API Key.")
                return user.llm_settings.openai_api_key
        except Exception as e:
            logging.error(f"Error fetching user OpenAI API Key from DB: {e}")
        finally:
            SessionLocal.remove()
    env_key = os.environ.get('OPENAI_API_KEY')
    logging.info("Using environment variable OpenAI API Key.")
    return env_key

def get_anthropic_api_key():
    """
    Retrieves Anthropic API key, prioritizing user-specific settings from the database,
    then falling back to environment variables.
    """
    if current_user.is_authenticated:
        session = SessionLocal()
        try:
            user = session.query(User).options(joinedload(User.llm_settings)).get(current_user.id)
            if user and user.llm_settings and user.llm_settings.anthropic_api_key:
                logging.info("Using user-specific Anthropic API Key.")
                return user.llm_settings.anthropic_api_key
        except Exception as e:
            logging.error(f"Error fetching user Anthropic API Key from DB: {e}")
        finally:
            SessionLocal.remove()
    env_key = os.environ.get('ANTHROPIC_API_KEY')
    logging.info("Using environment variable Anthropic API Key.")
    return env_key

def get_google_api_key():
    """
    Retrieves Google API key, prioritizing user-specific settings from the database,
    then falling back to environment variables.
    """
    if current_user.is_authenticated:
        session = SessionLocal()
        try:
            user = session.query(User).options(joinedload(User.llm_settings)).get(current_user.id)
            if user and user.llm_settings and user.llm_settings.google_api_key:
                logging.info("Using user-specific Google API Key.")
                return user.llm_settings.google_api_key
        except Exception as e:
            logging.error(f"Error fetching user Google API Key from DB: {e}")
        finally:
            SessionLocal.remove()
    env_key = os.environ.get('GOOGLE_API_KEY')
    logging.info("Using environment variable Google API Key.")
    return env_key

def get_apollo_client_credentials():
    """
    Retrieves Apollo Client ID and Client Secret, prioritizing user-specific settings,
    then falling back to environment variables.
    Returns: (client_id, client_secret)
    """
    if current_user.is_authenticated:
        session = SessionLocal()
        try:
            user = session.query(User).options(joinedload(User.llm_settings)).get(current_user.id)
            if user and user.llm_settings and user.llm_settings.apollo_client_id and user.llm_settings.apollo_client_secret:
                logging.info("Using user-specific Apollo Client Credentials.")
                return user.llm_settings.apollo_client_id, user.llm_settings.apollo_client_secret
        except Exception as e:
            logging.error(f"Error fetching user Apollo credentials from DB: {e}")
        finally:
            SessionLocal.remove()
    
    env_client_id = current_app.config.get('APOLLO_CLIENT_ID')
    env_client_secret = current_app.config.get('APOLLO_CLIENT_SECRET')
    logging.info("Using environment variable Apollo Client Credentials.")
    return env_client_id, env_client_secret

def get_apollo_access_token():
    """
    Obtains and manages an access token for the Apollo API using client credentials flow.
    Caches the token and refreshes it if expired.
    """
    global _apollo_access_token, _apollo_token_expiry
    
    if _apollo_access_token and time.time() < _apollo_token_expiry:
        logging.debug("Using cached Apollo access token.")
        return _apollo_access_token

    client_id, client_secret = get_apollo_client_credentials()
    token_url = current_app.config.get('APOLLO_TOKEN_URL')

    if not client_id or not client_secret:
        raise ValueError("Apollo CLIENT_ID and CLIENT_SECRET must be configured in settings or .env.")
    if not token_url:
        raise ValueError("Apollo TOKEN_URL is not configured.")

    token_data = {
        "grant_type": "client_credentials",
        "client_id": client_id,
        "client_secret": client_secret,
    }
    
    logging.info(f"Apollo: Attempting to get new access token from: {token_url}")
    try:
        response = requests.post(token_url, data=token_data, timeout=10)
        response.raise_for_status()
        json_response = response.json()
        
        access_token = json_response.get('access_token')
        expires_in = json_response.get('expires_in', 3500) 
        
        if not access_token:
            raise ValueError("Access token not found in the response from Apollo.")
            
        _apollo_access_token = access_token
        _apollo_token_expiry = time.time() + expires_in
        logging.info("Apollo: Access token acquired successfully.")
        return _apollo_access_token
    except requests.exceptions.HTTPError as http_err:
        logging.error(f"Apollo Token Error: HTTP error occurred: {http_err}. Response content: {http_err.response.text}")
        raise ValueError(f"Apollo Token Error: {http_err.response.text}") from http_err
    except requests.exceptions.RequestException as req_err:
        logging.error(f"Apollo Token Error: Request error occurred: {req_err}")
        raise ValueError(f"Apollo Token Error: Network request failed: {req_err}") from req_err
    except Exception as e:
        logging.exception(f"Apollo Token Error: An unexpected error occurred while getting token: {e}")
        raise ValueError(f"Apollo Token Error: An unexpected error occurred: {e}") from e

# --- Chat History Management ---
def _get_history_deque():
    """
    Internal helper to retrieve the chat history from Flask session
    as a deque, applying maxlen.
    Always returns a deque.
    """
    max_history_length = current_app.config.get('MAX_CHAT_HISTORY_LENGTH', 10)
    history_as_list = flask_session.get('llm_chat_history', [])
    return deque(history_as_list, maxlen=max_history_length)

def _save_history_deque(history_deque):
    """
    Internal helper to save the deque back to Flask session as a list.
    """
    flask_session['llm_chat_history'] = list(history_deque)

def get_chat_history():
    """
    Public function to get the current chat history as a list of messages.
    History is stored as text-only strings.
    """
    history_deque = _get_history_deque()
    return list(history_deque)

def add_message_to_history(role, content):
    """Adds a message to the chat history and updates the Flask session.
    For simplicity, only text content is stored in history.
    """
    history_deque = _get_history_deque()
    history_deque.append({'role': role, 'content': content})
    _save_history_deque(history_deque)

def clear_chat_history():
    """Clears the chat history from the Flask session."""
    flask_session.pop('llm_chat_history', None)


# --- Provider-Specific Chat Generation Functions ---

def generate_ollama_chat_response(model_name, user_message, system_prompt=None, image_base64=None, image_mime_type=None, chat_history=None):
    """
    Sends a chat message to Ollama and returns the assistant's response.
    Includes memory from the session. Supports image input for multimodal models.
    """
    ollama_url = get_ollama_base_url()

    messages_for_api = []
    if system_prompt:
        messages_for_api.append({'role': 'system', 'content': system_prompt})

    if chat_history:
        messages_for_api.extend(chat_history)

    current_user_message_content = user_message if user_message else ""
    current_user_message_images = []

    if image_base64:
        logging.info(f"Ollama: Received image_base64 for chat. Length: {len(image_base64)} characters. MIME Type: {image_mime_type}")
        current_user_message_images.append(image_base64)
        if not current_user_message_content:
            current_user_message_content = "Analyze this image."

    if not current_user_message_content and not current_user_message_images:
        return {"success": False, "message": "No message or image provided for LLM."}

    current_user_message = {'role': 'user', 'content': current_user_message_content}
    if current_user_message_images:
        current_user_message['images'] = current_user_message_images
    messages_for_api.append(current_user_message)

    try:
        payload = {
            "model": model_name,
            "messages": messages_for_api,
            "stream": False
        }
        headers = {"Content-Type": "application/json"}
        logging.info(f"Ollama: Sending payload for model '{model_name}'. Message count: {len(payload['messages'])}. Has images: {len(current_user_message_images) > 0}.")
        logging.debug(f"Ollama: Full API PAYLOAD (truncated for images): {json.dumps(payload, indent=2)[:500]}...")

        response = requests.post(f"{ollama_url}/api/chat", json=payload, headers=headers, timeout=300)
        logging.debug(f"Ollama: raw response status code: {response.status_code}")
        response.raise_for_status()

        response_data = response.json()
        assistant_message = response_data['message']['content']

        return {"success": True, "message": assistant_message}

    except requests.exceptions.ConnectionError:
        error_msg = f"Ollama: Connection error to {ollama_url}. Is Ollama running and accessible from backend container?"
        logging.error(error_msg)
        return {"success": False, "message": error_msg}
    except requests.exceptions.Timeout:
        error_msg = f"Ollama: Request to {ollama_url} timed out (300s). Model might be too large or response too slow."
        logging.warning(error_msg)
        return {"success": False, "message": error_msg}
    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response is not None else 'N/A'
        response_text = e.response.text if e.response is not None else 'N/A'
        error_msg = (f"Ollama: API request failed: {e}. Status Code: {status_code}. Response: {response_text}")
        logging.error(error_msg)
        return {"success": False, "message": error_msg}
    except Exception as e:
        error_msg = f"An unexpected error occurred during Ollama chat: {e}"
        logging.exception(error_msg)
        return {"success": False, "message": error_msg}

def generate_openai_chat_response(model_name, user_message, system_prompt=None, image_base64=None, image_mime_type=None, chat_history=None):
    """
    Sends a chat message to OpenAI's API. Supports multimodal input.
    """
    api_key = get_openai_api_key()
    if not api_key:
        return {"success": False, "message": "OpenAI API key is not configured."}

    try:
        client = openai.OpenAI(api_key=api_key)
    except TypeError as e:
        if 'unexpected keyword argument' in str(e):
            client = openai.OpenAI(api_key=api_key, base_url="https://api.openai.com/v1")
        else:
            raise

    messages = []
    if system_prompt:
        messages.append({"role": "system", "content": system_prompt})

    if chat_history:
        messages.extend(chat_history)

    current_user_content_blocks = []
    if user_message:
        current_user_content_blocks.append({"type": "text", "text": user_message})

    if image_base64 and image_mime_type:
        image_url = f"data:{image_mime_type};base64,{image_base64}"
        current_user_content_blocks.append({"type": "image_url", "image_url": {"url": image_url}})
        if not user_message:
            current_user_content_blocks.append({"type": "text", "text": "Analyze this image."})

    if not current_user_content_blocks:
        return {"success": False, "message": "No message or image provided for LLM."}

    messages.append({"role": "user", "content": current_user_content_blocks})

    try:
        logging.info(f"OpenAI: Sending payload for model '{model_name}'. Message count: {len(messages)}. Has images: {bool(image_base64)}.")
        logging.debug(f"OpenAI: Full API PAYLOAD (truncated for images): {json.dumps(messages, indent=2)[:500]}...")

        response = client.chat.completions.create(
            model=model_name,
            messages=messages,
            temperature=0.7,
            max_tokens=1024,
        )
        assistant_message = response.choices[0].message.content
        return {"success": True, "message": assistant_message}

    except openai.APIConnectionError as e:
        error_msg = f"OpenAI: Connection error: {e.human_readable_message}"
        logging.error(error_msg)
        return {"success": False, "message": error_msg}
    except openai.RateLimitError as e:
        error_msg = f"OpenAI: Rate limit exceeded: {e.human_readable_message}"
        logging.warning(error_msg)
        return {"success": False, "message": error_msg}
    except openai.APIStatusError as e:
        error_msg = f"OpenAI: API error: {e.status_code} - {e.response}"
        logging.error(error_msg)
        return {"success": False, "message": error_msg}
    except Exception as e:
        error_msg = f"An unexpected error occurred during OpenAI chat: {e}"
        logging.exception(error_msg)
        return {"success": False, "message": error_msg}

def generate_anthropic_chat_response(model_name, user_message, system_prompt=None, image_base64=None, image_mime_type=None, chat_history=None):
    """
    Sends a chat message to Anthropic's API. Supports multimodal input.
    """
    api_key = get_anthropic_api_key()
    if not api_key:
        return {"success": False, "message": "Anthropic API key is not configured."}

    try:
        client = Anthropic(api_key=api_key)
    except TypeError as e:
        if 'unexpected keyword argument' in str(e):
            client = Anthropic(api_key=api_key, base_url="https://api.anthropic.com")
        else:
            raise

    anthropic_messages = []
    
    if chat_history:
        for msg in chat_history:
            anthropic_messages.append({"role": msg['role'], "content": [{"type": "text", "text": msg['content']}]})

    current_user_content_blocks = []
    if user_message:
        current_user_content_blocks.append({"type": "text", "text": user_message})

    if image_base64 and image_mime_type:
        anthropic_image_data = {
            "type": "image",
            "source": {
                "type": "base64",
                "media_type": image_mime_type,
                "data": image_base64,
            },
        }
        current_user_content_blocks.append(anthropic_image_data)
        if not user_message:
            current_user_content_blocks.append({"type": "text", "text": "Analyze this image."})

    if not current_user_content_blocks:
        return {"success": False, "message": "No message or image provided for LLM."}

    anthropic_messages.append({"role": "user", "content": current_user_content_blocks})

    try:
        logging.info(f"Anthropic: Sending payload for model '{model_name}'. Message count: {len(anthropic_messages)}. Has images: {bool(image_base64)}.")
        logging.debug(f"Anthropic: Full API PAYLOAD (truncated for images): {json.dumps(anthropic_messages, indent=2)[:500]}...")

        response = client.messages.create(
            model=model_name,
            max_tokens=1024,
            system=system_prompt,
            messages=anthropic_messages,
        )
        assistant_message = response.content[0].text
        return {"success": True, "message": assistant_message}

    except Anthropic.APIConnectionError as e:
        error_msg = f"Anthropic: Connection error: {e}"
        logging.error(error_msg)
        return {"success": False, "message": error_msg}
    except Anthropic.RateLimitError as e:
        error_msg = f"Anthropic: Rate limit exceeded: {e}"
        logging.warning(error_msg)
        return {"success": False, "message": error_msg}
    except Anthropic.APIStatusError as e:
        error_msg = f"Anthropic: API error: {e.status_code} - {e.response}"
        logging.error(error_msg)
        return {"success": False, "message": error_msg}
    except Exception as e:
        error_msg = f"An unexpected error occurred during Anthropic chat: {e}"
        logging.exception(error_msg)
        return {"success": False, "message": error_msg}

def generate_google_chat_response(model_name, user_message, system_prompt=None, image_base64=None, image_mime_type=None, chat_history=None):
    """
    Sends a chat message to Google Gemini's API. Supports multimodal input.
    """
    api_key = get_google_api_key()
    if not api_key:
        return {"success": False, "message": "Google API key is not configured."}

    genai.configure(api_key=api_key)

    google_history = []
    if chat_history:
        for msg in chat_history:
            google_history.append({"role": msg['role'], "parts": [msg['content']]})

    parts = []
    if user_message:
        parts.append(user_message)

    if image_base64 and image_mime_type:
        try:
            image_bytes = base64.b64decode(image_base64)
            from PIL import Image
            from io import BytesIO
            img_part = Image.open(BytesIO(image_bytes))
            parts.append(img_part)
        except Exception as e:
            logging.error(f"Google Gemini: Error processing image for API: {e}")
            return {"success": False, "message": "Failed to process image for Google Gemini."}

        if not user_message:
            parts.append("Analyze this image.")

    if not parts:
        return {"success": False, "message": "No message or image provided for LLM."}

    try:
        model_config = {}
        if system_prompt:
             model_config['system_instruction'] = system_prompt

        model = genai.GenerativeModel(model_name=model_name, **model_config)
        
        chat = model.start_chat(history=google_history)

        logging.info(f"Google: Sending payload for model '{model_name}'. Message count: {len(google_history) + 1}. Has images: {bool(image_base64)}.")
        logging.debug(f"Google: Current message parts: {parts}. History: {google_history}")

        response = chat.send_message(parts)
        response.resolve()
        
        assistant_message = response.text
        return {"success": True, "message": assistant_message}

    except genai.APIError as e: # Updated to use genai exceptions
        error_msg = f"Google Gemini: API error: {e}"
        logging.error(error_msg)
        return {"success": False, "message": error_msg}
    except genai.client.ClientError as e: # Updated to use genai exceptions
        error_msg = f"Google Gemini: Client error: {e}"
        logging.error(error_msg)
        return {"success": False, "message": error_msg}
    except Exception as e:
        error_msg = f"An unexpected error occurred during Google Gemini chat: {e}"
        logging.exception(error_msg)
        return {"success": False, "message": error_msg}

def generate_apollo_chat_response(model_group_name, user_message, system_prompt=None, image_base64=None, image_mime_type=None, chat_history=None):
    """
    Sends a chat message to Apollo LLM API using LiteLLM/langchain-openai compatibility.
    Handles multimodal input if the model supports it.
    """
    try:
        access_token = get_apollo_access_token()
    except ValueError as e:
        logging.error(f"Apollo: Failed to get access token: {e}")
        return {"success": False, "message": f"Apollo Authentication Error: {e}"}

    apollo_llm_api_base_url = current_app.config.get('APOLLO_LLM_API_BASE_URL')
    if not apollo_llm_api_base_url:
        return {"success": False, "message": "Apollo LLM API base URL is not configured."}

    try:
        llm_model = ChatOpenAI(
            model=model_group_name,
            base_url=apollo_llm_api_base_url,
            api_key=access_token,
            temperature=0.01,
            timeout=300
        )

        messages_for_api = []
        if system_prompt:
            messages_for_api.append({"role": "system", "content": system_prompt})

        if chat_history:
            for msg in chat_history:
                messages_for_api.append({"role": msg['role'], "content": msg['content']})

        current_user_content_blocks = []
        if user_message:
            current_user_content_blocks.append({"type": "text", "text": user_message})

        if image_base64 and image_mime_type:
            image_url = f"data:{image_mime_type};base64,{image_base64}"
            current_user_content_blocks.append({"type": "image_url", "image_url": {"url": image_url}})
            if not user_message:
                current_user_content_blocks.append({"type": "text", "text": "Analyze this image."})

        if not current_user_content_blocks:
            return {"success": False, "message": "No message or image provided for LLM."}

        messages_for_api.append({"role": "user", "content": current_user_content_blocks})

        logging.info(f"Apollo: Sending payload for model '{model_group_name}'. Message count: {len(messages_for_api)}. Has images: {bool(image_base64)}.")
        logging.debug(f"Apollo: Full API PAYLOAD (truncated for images): {json.dumps(messages_for_api, indent=2)[:500]}...")

        response = llm_model.invoke(messages_for_api)

        assistant_message = response.content
        return {"success": True, "message": assistant_message}

    except openai.APICallError as e:
        error_msg = f"Apollo API Call Error: {e.status_code} - {e.response.text if e.response else 'No response text'}"
        logging.error(error_msg)
        return {"success": False, "message": error_msg}
    except requests.exceptions.RequestException as e:
        error_msg = f"Apollo Network Error: {e}"
        logging.error(error_msg)
        return {"success": False, "message": error_msg}
    except Exception as e:
        error_msg = f"An unexpected error occurred during Apollo chat: {e}"
        logging.exception(error_msg)
        return {"success": False, "message": error_msg}


# --- Model Discovery Functions ---

def get_available_ollama_models():
    """Fetches available models from the Ollama API."""
    ollama_url = get_ollama_base_url()
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        models_data = response.json()
        return [f"ollama-{model['name']}" for model in models_data.get('models', [])]
    except requests.exceptions.ConnectionError:
        logging.error(f"Ollama: Connection error to {ollama_url}. Is Ollama running?")
        return ["ollama-Error: Not reachable"]
    except requests.exceptions.Timeout:
        logging.warning(f"Ollama: Timeout connecting to {ollama_url}.")
        return ["ollama-Error: Timeout"]
    except requests.exceptions.RequestException as e:
        logging.error(f"Ollama: An unexpected error occurred: {e}")
        return [f"ollama-Error: {e}"]
    except Exception as e:
        logging.error(f"Ollama: Failed to parse models: {e}")
        return ["ollama-Error: Failed to parse models"]

def get_available_openai_models():
    """Returns a list of common OpenAI chat models."""
    api_key = get_openai_api_key()
    if not api_key:
        return []
    
    models = [
        "gpt-4o",
        "gpt-4o-mini",
        "gpt-4-turbo",
        "gpt-3.5-turbo",
    ]
    return [f"openai-{model}" for model in models]

def get_available_anthropic_models():
    """Returns a list of common Anthropic chat models."""
    api_key = get_anthropic_api_key()
    if not api_key:
        return []
    
    models = [
        "claude-3-opus-20240229",
        "claude-3-sonnet-20240229",
        "claude-3-haiku-20240307",
    ]
    return [f"anthropic-{model}" for model in models]

def get_available_google_models():
    """Returns a list of common Google Gemini chat models, or queries the API if needed."""
    api_key = get_google_api_key()
    if not api_key:
        return []

    models = [
        "gemini-pro",
        "gemini-pro-vision",
        "gemini-1.5-pro-latest",
        "gemini-1.5-flash-latest",
    ]
    return [f"google-{model}" for model in models]

def get_available_apollo_models():
    """
    Fetches available LLM models from the Apollo API's model_group/info endpoint.
    Filters for 'chat' mode models.
    """
    apollo_llm_api_base_url = current_app.config.get('APOLLO_LLM_API_BASE_URL')
    if not apollo_llm_api_base_url:
        logging.warning("Apollo LLM API base URL not configured. Cannot fetch Apollo models.")
        return []

    try:
        access_token = get_apollo_access_token()
    except ValueError as e:
        logging.warning(f"Apollo: Skipping model discovery due to authentication error: {e}")
        return [f"apollo-Error: Auth failed ({e})"]

    model_info_endpoint = f"{apollo_llm_api_base_url}/model_group/info"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }

    try:
        response = requests.get(model_info_endpoint, headers=headers, timeout=10)
        response.raise_for_status()
        models_info = response.json()

        apollo_models = []
        if models_info and isinstance(models_info, dict) and 'data' in models_info:
            for model in models_info['data']:
                if model.get('mode') == 'chat':
                    apollo_models.append(f"apollo-{model.get('model_group')}")
        return apollo_models
    except requests.exceptions.ConnectionError:
        error_msg = f"Apollo: Connection error to {apollo_llm_api_base_url}. Is Apollo API accessible?"
        logging.error(error_msg)
        return ["apollo-Error: Not reachable"]
    except requests.exceptions.Timeout:
        error_msg = f"Apollo: Timeout connecting to {apollo_llm_api_base_url} for model info."
        logging.warning(error_msg)
        return ["apollo-Error: Timeout"]
    except requests.exceptions.RequestException as e:
        status_code = e.response.status_code if e.response is not None else 'N/A'
        response_text = e.response.text if e.response is not None else 'N/A'
        error_msg = (f"Apollo: API request failed for model info: {e}. Status Code: {status_code}. Response: {response_text}")
        logging.error(error_msg)
        return [f"apollo-Error: {e}"]
    except Exception as e:
        error_msg = f"An unexpected error occurred during Apollo model discovery: {e}"
        logging.exception(error_msg)
        return [f"apollo-Error: {e}"]

def get_all_available_llm_models():
    """Aggregates models from all configured LLM providers."""
    all_models = []
    
    all_models.extend(get_available_openai_models())
    all_models.extend(get_available_anthropic_models())
    all_models.extend(get_available_google_models())
    
    all_models.extend(get_available_apollo_models())
    all_models.extend(get_available_ollama_models())

    all_models = [m for m in all_models if m]
    all_models = list(dict.fromkeys(all_models))
    return all_models