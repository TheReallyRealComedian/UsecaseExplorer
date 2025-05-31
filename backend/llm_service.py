# backend/llm_service.py

import requests
import json
import os
from flask import session as flask_session, current_app
from collections import deque
import logging 
from flask_login import current_user
from .db import SessionLocal
from .models import User, LLMSettings
from sqlalchemy.orm import joinedload

# Configure basic logging for debugging (if not already done globally)
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

def get_ollama_base_url():
    """
    Retrieves Ollama base URL, prioritizing user-specific settings from the database,
    then falling back to environment variables.
    """
    # Check current_user for settings if authenticated
    if current_user.is_authenticated:
        session = SessionLocal()
        try:
            # Eager load llm_settings for the current user
            user = session.query(User).options(joinedload(User.llm_settings)).get(current_user.id)
            if user and user.llm_settings and user.llm_settings.ollama_base_url:
                logging.info(f"Using user-specific Ollama Base URL.")
                return user.llm_settings.ollama_base_url
        except Exception as e:
            logging.error(f"Error fetching user Ollama URL from DB: {e}")
        finally:
            # session.remove() # Ensure session is closed
            pass

    # Fallback to environment variable if no user setting or error
    env_url = os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434')
    logging.info(f"Using environment variable Ollama Base URL: {env_url} (or default if not set).")
    return env_url

def get_available_ollama_models():
    """Fetches available models from the Ollama API."""
    ollama_url = get_ollama_base_url()
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status()
        models_data = response.json()
        return [model['name'] for model in models_data.get('models', [])]
    except requests.exceptions.ConnectionError:
        logging.error(f"Ollama: Connection error to {ollama_url}. Is Ollama running?")
        return ["Error: Ollama not reachable"]
    except requests.exceptions.Timeout:
        logging.warning(f"Ollama: Timeout connecting to {ollama_url}.")
        return ["Error: Ollama timeout"]
    except requests.exceptions.RequestException as e:
        logging.error(f"Ollama: An unexpected error occurred: {e}")
        return [f"Error: {e}"]
    except Exception as e:
        logging.error(f"Ollama: Failed to parse models: {e}")
        return ["Error: Failed to parse models"]

# Helper function to get OpenAI API key
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
                logging.info(f"Using user-specific OpenAI API Key.")
                return user.llm_settings.openai_api_key
        except Exception as e:
            logging.error(f"Error fetching user OpenAI API Key from DB: {e}")
        finally:
            # session.remove()
            pass
    
    env_key = os.environ.get('OPENAI_API_KEY')
    logging.info(f"Using environment variable OpenAI API Key.")
    return env_key

# Helper function to get Anthropic API key
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
                logging.info(f"Using user-specific Anthropic API Key.")
                return user.llm_settings.anthropic_api_key
        except Exception as e:
            logging.error(f"Error fetching user Anthropic API Key from DB: {e}")
        finally:
            # session.remove()
            pass
    
    env_key = os.environ.get('ANTHROPIC_API_KEY')
    logging.info(f"Using environment variable Anthropic API Key.")
    return env_key

# Helper function to get Google API key
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
                logging.info(f"Using user-specific Google API Key.")
                return user.llm_settings.google_api_key
        except Exception as e:
            logging.error(f"Error fetching user Google API Key from DB: {e}")
        finally:
            # session.remove()
            pass
    
    env_key = os.environ.get('GOOGLE_API_KEY')
    logging.info(f"Using environment variable Google API Key.")
    return env_key


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

def generate_ollama_chat_response(model_name, user_message, system_prompt=None, image_base64=None, image_mime_type=None):
    """
    Sends a chat message to Ollama and returns the assistant's response.
    Includes memory from the session. Supports image input for multimodal models.
    """
    ollama_url = get_ollama_base_url()
    
    # Construct messages list for Ollama API payload.
    messages_for_api = []
    if system_prompt:
        messages_for_api.append({'role': 'system', 'content': system_prompt})

    # Add historical messages from session. These are text-only strings (`msg['content']` is a string).
    # Ollama API allows `content` to be a string for text-only messages.
    for msg in _get_history_deque():
        messages_for_api.append({'role': msg['role'], 'content': msg['content']})

    # Prepare the current user message - Ollama format
    # In Ollama, content is always a string, images go in separate 'images' field
    current_user_message_content = user_message if user_message else ""
    current_user_message_images = []
    
    if image_base64:
        # Add a log for the size of the base64 string and MIME type
        logging.info(f"Received image_base64 in backend. Length: {len(image_base64)} characters. MIME Type: {image_mime_type}")
        
        try:
            # For Ollama, we just need the base64 data without the data URL prefix
            current_user_message_images.append(image_base64)
            logging.info(f"Image added to Ollama images array. Base64 length: {len(image_base64)}")
        except Exception as e:
            logging.error(f"Error processing base64 image data: {e}")
            return {"success": False, "message": "Invalid image data provided."}

        # If message is empty but image is present, add a default text prompt
        if not current_user_message_content:
            current_user_message_content = "Analyze this image."

    # Check if we have any content
    if not current_user_message_content and not current_user_message_images:
        return {"success": False, "message": "No message or image provided for LLM."}

    # Build the current user message using Ollama's format
    current_user_message = {'role': 'user', 'content': current_user_message_content}
    if current_user_message_images:
        current_user_message['images'] = current_user_message_images
    
    # Add the current user message to the messages array
    messages_for_api.append(current_user_message)

    try:
        payload = {
            "model": model_name,
            "messages": messages_for_api,
            "stream": False
        }
        
        headers = {"Content-Type": "application/json"}
        
        logging.info(f"Sending Ollama API Payload for model '{model_name}'. Message count: {len(payload['messages'])}. "
                     f"Current user message content type: string. "
                     f"Has images: {len(current_user_message_images) > 0}. "
                     f"Payload size (approx): {len(json.dumps(payload))} bytes.")
        logging.debug(f"Full Ollama API PAYLOAD: {json.dumps(payload, indent=2)}")

        # Send the request
        response = requests.post(f"{ollama_url}/api/chat", json=payload, headers=headers, timeout=300)

        # Log detailed response BEFORE raising for status
        logging.debug(f"Ollama API raw response status code: {response.status_code}")
        logging.debug(f"Ollama API raw response headers: {response.headers}")
        logging.debug(f"Ollama API raw response text (first 500 chars): {response.text[:500]}...")

        response.raise_for_status()  # This will raise an HTTPError for 4xx/5xx responses
        
        # Attempt to parse JSON only if status is OK
        response_data = response.json()
        assistant_message = response_data['message']['content']
        
        # Add the user's *text* message and assistant's response to history *only after successful API call*.
        # The 'user_message' passed here is the original text from the frontend.
        # If the original user_message was empty but an image was provided, add a placeholder text for history.
        user_message_for_history = user_message
        if not user_message_for_history and current_user_message_images:
            user_message_for_history = "Image provided."  # Or "Analyze this image." for clarity in history
        
        add_message_to_history('user', user_message_for_history)
        add_message_to_history('assistant', assistant_message)
        
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
        # e.response should now be populated here if an HTTP error occurred
        status_code = e.response.status_code if e.response is not None else 'N/A'
        response_text = e.response.text if e.response is not None else 'N/A'

        error_msg = (f"Ollama: API request failed: {e}. Status Code: {status_code}. Response: {response_text}")
        logging.error(error_msg)

        if e.response is not None:
            try:
                detailed_response_content = e.response.json()
                logging.error(f"Ollama detailed error JSON response: {json.dumps(detailed_response_content, indent=2)}")
            except json.JSONDecodeError:
                logging.error(f"Ollama detailed error raw text response (non-JSON): {e.response.text}") 
        return {"success": False, "message": error_msg}
    except Exception as e:
        error_msg = f"An unexpected error occurred during Ollama chat: {e}"
        logging.exception(error_msg)
        return {"success": False, "message": error_msg}