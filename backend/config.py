# backend/config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file in the project root
# Specify the absolute path to ensure it's found regardless of where the script is run from
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '.env'))

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-hardcoded-fallback-key-change-me' # Fallback for dev if .env not loaded
    # In a real production environment, you should NEVER use a hardcoded fallback.
    # Ensure SECRET_KEY is set via environment variables or a secure config system.

    # Database settings
    # This URL format is for connecting *from within the backend container* to the *db service*
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or 'postgresql://user:password@db:5432/usecase_explorer_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False # Recommended to disable

    # Flask-Login settings
    LOGIN_URL = '/login' # The endpoint name for the login view
    LOGIN_MESSAGE = 'Please log in to access this page.'
    LOGIN_MESSAGE_CATEGORY = 'info'

    # LLM API Keys (Access these via config)
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL')
    MAX_CHAT_HISTORY_LENGTH = int(os.environ.get('MAX_CHAT_HISTORY_LENGTH', 10))

    # Add other configuration variables here
    # Example: UPLOAD_FOLDER = os.path.join(basedir, 'uploads')

class DevelopmentConfig(Config):
    DEBUG = True
    # Override specific settings for development if needed

class ProductionConfig(Config):
    DEBUG = False
    # Ensure SECRET_KEY and DATABASE_URL are set securely in the production environment
    # Example: SQLALCHEMY_DATABASE_URI = os.environ.get('PRODUCTION_DATABASE_URL')


def get_config():
    # Simple function to get the appropriate config based on FLASK_ENV (or default to development)
    flask_env = os.environ.get('FLASK_ENV', 'development')
    if flask_env == 'production':
        return ProductionConfig
    return DevelopmentConfig # Default to DevelopmentConfig