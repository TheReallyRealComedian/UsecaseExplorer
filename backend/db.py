# backend/db.py
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_sqlalchemy import SQLAlchemy

# Initialize Flask-SQLAlchemy extension. It will be bound to the app later.
db = SQLAlchemy()

# This SessionLocal will be explicitly configured by db.engine once Flask-SQLAlchemy is initialized.
# This maintains compatibility with existing code that uses SessionLocal.
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False))

def init_app_db(app):
    """
    Initializes the Flask-SQLAlchemy extension with the Flask app.
    Also configures the raw SQLAlchemy SessionLocal using Flask-SQLAlchemy's engine.
    """
    db.init_app(app) # Initialize Flask-SQLAlchemy with the Flask app instance

    # --- START OF CHANGE ---
    # Push an application context to allow db.engine to resolve current_app
    with app.app_context():
        # Use the engine created by Flask-SQLAlchemy to configure our SessionLocal.
        # This ensures that SessionLocal and db.session are working with the same underlying engine.
        SessionLocal.configure(bind=db.engine)
        print(f"Initializing database engine with URL: {app.config.get('SQLALCHEMY_DATABASE_URI')[:app.config.get('SQLALCHEMY_DATABASE_URI').find('@') + 1]}********")
    # --- END OF CHANGE ---
    
    # Return the Flask-SQLAlchemy db object (which has the .Model attribute)
    return db

def get_engine():
    """Returns the engine from the Flask-SQLAlchemy instance."""
    if db.engine is None:
        raise RuntimeError("Database engine not initialized. Call init_app_db first.")
    return db.engine

def get_session():
    """Provides a SessionLocal instance (raw SQLAlchemy session)."""
    return SessionLocal()