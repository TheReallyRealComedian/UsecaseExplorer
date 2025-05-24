# backend/llm_service.py
import requests
import json
import os
from flask import session as flask_session, current_app # Use flask's session to store chat history and current_app for config
from collections import deque # For a limited-length chat history
import traceback # Added to provide more context for unexpected errors


def get_ollama_base_url():
    """Retrieves Ollama base URL from environment variable."""
    return os.environ.get('OLLAMA_BASE_URL', 'http://localhost:11434') # Default for local Ollama

def get_available_ollama_models():
    """Fetches available models from the Ollama API."""
    ollama_url = get_ollama_base_url()
    try:
        response = requests.get(f"{ollama_url}/api/tags", timeout=5)
        response.raise_for_status() # Raise an exception for bad status codes
        models_data = response.json()
        return [model['name'] for model in models_data.get('models', [])]
    except requests.exceptions.ConnectionError:
        print(f"Ollama: Connection error to {ollama_url}. Is Ollama running?")
        return ["Error: Ollama not reachable"]
    except requests.exceptions.Timeout:
        print(f"Ollama: Timeout connecting to {ollama_url}.")
        return ["Error: Ollama timeout"]
    except requests.exceptions.RequestException as e:
        print(f"Ollama: An unexpected error occurred: {e}")
        return [f"Error: {e}"]
    except Exception as e:
        print(f"Ollama: Failed to parse models: {e}")
        return ["Error: Failed to parse models"]

def _get_history_deque():
    """
    Internal helper to retrieve the chat history from Flask session
    as a deque, applying maxlen.
    Always returns a deque.
    """
    max_history_length = current_app.config.get('MAX_CHAT_HISTORY_LENGTH', 10)
    # Retrieve as a list, default to empty list if not present
    history_as_list = flask_session.get('llm_chat_history', [])
    # Create a deque from the list, with the specified maxlen
    return deque(history_as_list, maxlen=max_history_length)

def _save_history_deque(history_deque):
    """
    Internal helper to save the deque back to Flask session as a list.
    """
    flask_session['llm_chat_history'] = list(history_deque) # Convert to list for serialization

def get_chat_history():
    """
    Public function to get the current chat history as a list of messages
    (for API response or template rendering).
    """
    return list(_get_history_deque()) # Return a list copy for external use

def add_message_to_history(role, content):
    """Adds a message to the chat history and updates the Flask session."""
    history_deque = _get_history_deque()
    history_deque.append({'role': role, 'content': content})
    _save_history_deque(history_deque)

def clear_chat_history():
    """Clears the chat history from the Flask session."""
    flask_session.pop('llm_chat_history', None)

def generate_ollama_chat_response(model_name, user_message, system_prompt=None):
    """
    Sends a chat message to Ollama and returns the assistant's response.
    Includes memory from the session.
    """
    ollama_url = get_ollama_base_url()
    
    history_deque = _get_history_deque()
    
    # Add the current user message to history. This ensures it's saved in the session
    # and is included in the history for the LLM API call.
    history_deque.append({'role': 'user', 'content': user_message})
    _save_history_deque(history_deque) # Save updated history immediately

    # Construct messages for Ollama, starting with system prompt if provided
    messages_to_send = []
    if system_prompt:
        messages_to_send.append({'role': 'system', 'content': system_prompt})

    # Add the full chat history (which now includes the latest user message)
    # The final `messages_to_send` for the API call will be:
    # [system_prompt (if any), ...old_history..., user_message]
    messages_to_send.extend(list(history_deque))

    try:
        payload = {
            "model": model_name,
            "messages": messages_to_send, # Use the combined list
            "stream": False # We want the full response at once
        }
        
        headers = {"Content-Type": "application/json"}
        
        # Changed timeout from 420 to 120 as per instructions
        response = requests.post(f"{ollama_url}/api/chat", json=payload, headers=headers, timeout=120)
        response.raise_for_status()
        
        response_data = response.json()
        assistant_message = response_data['message']['content']
        
        history_deque.append({'role': 'assistant', 'content': assistant_message})
        _save_history_deque(history_deque)
        
        return {"success": True, "message": assistant_message}

    except requests.exceptions.ConnectionError:
        error_msg = f"Ollama: Connection error to {ollama_url}. Is Ollama running and accessible from backend container?"
        print(error_msg)
        return {"success": False, "message": error_msg}
    except requests.exceptions.Timeout:
        error_msg = f"Ollama: Request to {ollama_url} timed out. Model might be too large or response too slow."
        print(error_msg)
        return {"success": False, "message": error_msg}
    except requests.exceptions.RequestException as e:
        error_msg = f"Ollama: API request failed: {e}. Response: {e.response.text if e.response else 'N/A'}"
        print(error_msg)
        return {"success": False, "message": error_msg}
    except Exception as e:
        error_msg = f"An unexpected error occurred during Ollama chat: {e}"
        print(f"Error: {e}, Trace: {traceback.format_exc()}")
        return {"success": False, "message": error_msg}