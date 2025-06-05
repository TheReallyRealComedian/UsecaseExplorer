# backend/db.py
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_sqlalchemy import SQLAlchemy
from .models import Base # Make sure this import is present
from sqlalchemy import inspect # <--- NEW IMPORT

db = SQLAlchemy()

SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False))

def init_app_db(app):
    """
    Initializes the Flask-SQLAlchemy extension with the Flask app.
    Also configures the raw SQLAlchemy SessionLocal using Flask-SQLAlchemy's engine.
    Ensures database tables are created (for development convenience).
    """
    db.init_app(app) # Initialize Flask-SQLAlchemy with the Flask app instance

    with app.app_context():
        # Use the engine created by Flask-SQLAlchemy to configure our SessionLocal.
        SessionLocal.configure(bind=db.engine)
        print(f"Initializing database engine with URL: {app.config.get('SQLALCHEMY_DATABASE_URI')[:app.config.get('SQLALCHEMY_DATABASE_URI').find('@') + 1]}********")
        
        # CORRECTED ADDITION FOR SCHEMA CREATION/UPDATE (FOR DEVELOPMENT)
        try:
            # Use inspect to check if the 'llm_settings' table exists
            # This is the correct public API way to check for table existence.
            inspector = inspect(db.engine) # <--- Use inspect on the engine
            if not inspector.has_table("llm_settings"): # <--- Call has_table on the inspector
                print("Database table 'llm_settings' not found. Attempting to create all tables...")
                Base.metadata.create_all(db.engine)
                print("All database tables created successfully based on models.")
            else:
                print("Database tables appear to exist. Skipping create_all.")
        except Exception as e:
            print(f"Error during table creation: {e}")
            # Re-raise the exception as this is a critical setup error
            raise

    # Return the Flask-SQLAlchemy db object
    return db

def get_engine():
    """Returns the engine from the Flask-SQLAlchemy instance."""
    if db.engine is None:
        raise RuntimeError("Database engine not initialized. Call init_app_db first.")
    return db.engine

def get_session():
    """Provides a SessionLocal instance (raw SQLAlchemy session)."""
    return SessionLocal()