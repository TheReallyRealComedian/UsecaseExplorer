# backend/config.py
import os
from dotenv import load_dotenv

basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '..', '.env'))

class Config:
    # Flask settings
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'a-hardcoded-fallback-key-change-me'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16 Megabytes

    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
                              'postgresql://user:password@db:5432/usecase_explorer_db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    #SQLALCHEMY_DATABASE_URI = 'sqlite:///temp_for_init.db'
    #SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Flask-Login settings
    LOGIN_URL = '/login'
    LOGIN_MESSAGE = 'Please log in to access this page.'
    LOGIN_MESSAGE_CATEGORY = 'info'

    # LLM API Keys (Access these via config)
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    ANTHROPIC_API_KEY = os.environ.get('ANTHROPIC_API_KEY')
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY')
    OLLAMA_BASE_URL = os.environ.get('OLLAMA_BASE_URL')
    MAX_CHAT_HISTORY_LENGTH = int(os.environ.get('MAX_CHAT_HISTORY_LENGTH', 10))

    # Apollo LLM API settings
    APOLLO_CLIENT_ID = os.environ.get('APOLLO_CLIENT_ID')
    APOLLO_CLIENT_SECRET = os.environ.get('APOLLO_CLIENT_SECRET')
    APOLLO_TOKEN_URL = os.environ.get(
        'APOLLO_TOKEN_URL',
        "https://api-gw.boehringer-ingelheim.com/api/oauth/token"
    )
    APOLLO_LLM_API_BASE_URL = os.environ.get(
        'APOLLO_LLM_API_BASE_URL',
        "https://api-gw.boehringer-ingelheim.com/apollo/llm-api"
    )

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
    flask_env = os.environ.get('FLASK_ENV', 'development')
    if flask_env == 'production':
        return ProductionConfig
    return DevelopmentConfig