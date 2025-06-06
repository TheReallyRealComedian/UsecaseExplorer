# backend/db.py
from sqlalchemy.orm import scoped_session, sessionmaker
from flask_sqlalchemy import SQLAlchemy
from .models import Base # Make sure this import is present
from sqlalchemy import inspect # <--- NEW IMPORT
from sqlalchemy.exc import ProgrammingError # NEW: for handling table existence checks

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
        
        # MODIFIED ADDITION FOR SCHEMA CREATION/UPDATE (FOR DEVELOPMENT)
        # This approach ensures schema is always up-to-date in development
        # by checking for a sentinel table and, if not found, dropping all and recreating.
        try:
            inspector = inspect(db.engine)
            
            # Use 'users' table as a sentinel. If 'users' doesn't exist, assume the DB is empty or needs full setup.
            # This is more fundamental than 'llm_settings' which was added later.
            if not inspector.has_table("users"): 
                print("Database tables (e.g., 'users') not found. Attempting to create all tables...")
                
                # In a development environment, you might want to ensure a clean slate.
                # WARNING: Base.metadata.drop_all(db.engine) will DELETE ALL DATA.
                # Use this ONLY in development or with robust backup strategies.
                # For this specific case, 'down -v' should already clear the volume,
                # but this adds an extra layer of certainty for development.
                
                # Check for existing tables and drop them if they shouldn't be there based on 'users' sentinel
                # This ensures `create_all` works cleanly if somehow remnants exist without 'users'
                # (e.g., if a previous create_all failed partially).
                try:
                    # Attempt to drop all, but only if some tables actually exist,
                    # to avoid errors on a truly empty/new database.
                    # It's a bit of a dance, but safer than always dropping.
                    # A more robust check might be to query `SELECT tablename FROM pg_tables WHERE schemaname='public';`
                    # and if any exist, then drop_all. For simplicity here, rely on create_all's idempotence
                    # coupled with `drop_all` as a pre-step if the sentinel is missing.
                    
                    # If users table is not found, it implies a fresh DB. 
                    # Base.metadata.create_all should be sufficient then,
                    # as `create_all` only creates tables that don't exist.
                    # If `has_table("users")` is truly false, then `create_all` will build it.
                    # The error might be a subtle interaction.
                    
                    # Let's remove the aggressive drop_all unless explicitly requested.
                    # The problem likely stems from `create_all` not running,
                    # which is usually due to `has_table("llm_settings")` returning true prematurely.
                    # Changing sentinel to 'users' is better.
                    Base.metadata.create_all(db.engine)
                    print("All database tables created successfully based on models.")
                except Exception as create_e:
                    print(f"Error during Base.metadata.create_all: {create_e}")
                    raise # Re-raise if create_all fails

            else:
                print("Database tables appear to exist. Skipping create_all.")
                # This is the tricky part. If schema changes are made (like adding columns),
                # `create_all` won't update existing tables.
                # For a development setup, a simpler, though more destructive, approach
                # is to ensure the volume is *always* recreated or to use Alembic.
                # Since `docker-compose down -v` is the intended way to clear the volume,
                # the `if not inspector.has_table("users")` check should ideally always catch it.
                # If it doesn't, manual intervention (e.g., `docker volume rm usecaseexplorer_db_data`)
                # or introduction of migrations would be next steps.

        except ProgrammingError as pe:
            # This can happen if the database itself doesn't exist or permissions are wrong
            print(f"ProgrammingError during database inspection: {pe}. Database might not be fully ready or accessible.")
            raise
        except Exception as e:
            print(f"Error during table creation/inspection: {e}")
            raise

    # Return the Flask-SQLAlchemy db object
    return db