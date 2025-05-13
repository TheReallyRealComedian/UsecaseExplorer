# backend/db.py
from sqlalchemy import create_engine
from sqlalchemy.orm import scoped_session, sessionmaker

# Define SessionLocal at the module level, unconfigured initially
SessionLocal = scoped_session(sessionmaker(autocommit=False, autoflush=False))
engine = None

def init_engine(db_url):
    """Initializes the database engine."""
    global engine
    if not db_url:
        raise ValueError("DATABASE_URL is not set in the configuration!")
    print(f"Initializing database engine with URL: {db_url[:db_url.find('@') + 1]}********") # Mask credentials
    engine = create_engine(db_url)
    SessionLocal.configure(bind=engine) # Bind SessionLocal to the engine
    return engine

def get_engine():
    """Returns the initialized engine."""
    if engine is None:
        raise RuntimeError("Database engine not initialized. Call init_engine first.")
    return engine

def get_session():
    """Provides a SessionLocal instance."""
    # This function might seem redundant if SessionLocal is directly imported,
    # but can be useful for more complex session management or testing.
    # For now, direct import of SessionLocal by routes is fine.
    return SessionLocal()