# /backend/models.py

from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, CheckConstraint, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base, sessionmaker, scoped_session
from sqlalchemy.sql import func
from passlib.hash import pbkdf2_sha256
from flask_login import UserMixin

# Base class for declarative models
Base = declarative_base()

# --- User Model ---
class User(UserMixin, Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(255), nullable=False) # Storing hashed password
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    def set_password(self, password):
        self.password = pbkdf2_sha256.hash(password)

    def check_password(self, password):
        return pbkdf2_sha256.verify(password, self.password)

    def __repr__(self):
        return f"<User(username='{self.username}')>"

# --- Area Model ---
class Area(Base):
    __tablename__ = 'areas'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), unique=True, nullable=False)
    description = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    process_steps = relationship("ProcessStep", back_populates="area")
    usecase_relevance = relationship("UsecaseAreaRelevance", back_populates="target_area")

    def __repr__(self):
        return f"<Area(name='{self.name}')>"

# --- ProcessStep Model ---
class ProcessStep(Base):
    __tablename__ = 'process_steps'

    id = Column(Integer, primary_key=True)
    bi_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    area_id = Column(Integer, ForeignKey('areas.id'), nullable=False)

    # Existing descriptive fields
    step_description = Column(Text, nullable=True) # Can hold the "Short Description"
    raw_content = Column(Text, nullable=True) # Can hold the full original markdown/text if needed
    summary = Column(Text, nullable=True)     # Existing field, you can decide its new purpose or deprecate

    # New structured fields
    vision_statement = Column(Text, nullable=True)
    in_scope = Column(Text, nullable=True) # For "In Scope" markdown
    out_of_scope = Column(Text, nullable=True) # For "Out-of-scope" markdown
    interfaces_text = Column(Text, nullable=True) # For "Interfaces" markdown
    what_is_actually_done = Column(Text, nullable=True) # For "What is actually done in this step" markdown
    pain_points = Column(Text, nullable=True) # For "Pain Points" markdown
    targets_text = Column(Text, nullable=True) # For "Targets" markdown

    # LLM comments
    llm_comment_1 = Column(Text, nullable=True)
    llm_comment_2 = Column(Text, nullable=True)
    llm_comment_3 = Column(Text, nullable=True)
    llm_comment_4 = Column(Text, nullable=True)
    llm_comment_5 = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    area = relationship("Area", back_populates="process_steps")
    use_cases = relationship("UseCase", back_populates="process_step") # This handles the "## Use Cases" section by linking actual UseCase objects
    usecase_relevance = relationship("UsecaseStepRelevance", back_populates="target_process_step")

    def __repr__(self):
        return f"<ProcessStep(name='{self.name}', bi_id='{self.bi_id}')>"

# --- UseCase Model ---
class UseCase(Base):
    __tablename__ = 'use_cases'

    id = Column(Integer, primary_key=True)
    bi_id = Column(String(255), unique=True, nullable=False)
    name = Column(String(255), nullable=False)
    process_step_id = Column(Integer, ForeignKey('process_steps.id'), nullable=False)
    priority = Column(Integer, nullable=True)
    raw_content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)
    inspiration = Column(Text, nullable=True)
    llm_comment_1 = Column(Text, nullable=True)
    llm_comment_2 = Column(Text, nullable=True)
    llm_comment_3 = Column(Text, nullable=True)
    llm_comment_4 = Column(Text, nullable=True)
    llm_comment_5 = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        CheckConstraint('priority IS NULL OR (priority >= 1 AND priority <= 4)', name='priority_range_check'),
    )

    process_step = relationship("ProcessStep", back_populates="use_cases")

    relevant_to_areas = relationship(
        "UsecaseAreaRelevance",
        back_populates="source_usecase",
        cascade="all, delete-orphan"
    )
    relevant_to_steps = relationship(
        "UsecaseStepRelevance",
        back_populates="source_usecase",
        cascade="all, delete-orphan"
    )
    relevant_to_usecases_as_source = relationship(
        "UsecaseUsecaseRelevance",
        foreign_keys='[UsecaseUsecaseRelevance.source_usecase_id]',
        back_populates="source_usecase",
        cascade="all, delete-orphan"
    )
    relevant_to_usecases_as_target = relationship(
        "UsecaseUsecaseRelevance",
        foreign_keys='[UsecaseUsecaseRelevance.target_usecase_id]',
        back_populates="target_usecase",
        cascade="all, delete-orphan"
    )

    @property
    def area(self):
        return self.process_step.area if self.process_step and self.process_step.area else None

    def __repr__(self):
        return f"<UseCase(name='{self.name}', bi_id='{self.bi_id}')>"

# --- Relevance Models ---

class UsecaseAreaRelevance(Base):
    __tablename__ = 'usecase_area_relevance'

    id = Column(Integer, primary_key=True)
    source_usecase_id = Column(Integer, ForeignKey('use_cases.id'), nullable=False)
    target_area_id = Column(Integer, ForeignKey('areas.id'), nullable=False)
    relevance_score = Column(Integer, nullable=False)
    relevance_content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        CheckConstraint("relevance_score >= 0 AND relevance_score <= 100", name='relevance_score_check'),
        UniqueConstraint('source_usecase_id', 'target_area_id', name='unique_usecase_area_relevance')
    )

    source_usecase = relationship("UseCase", back_populates="relevant_to_areas")
    target_area = relationship("Area", back_populates="usecase_relevance")

    def __repr__(self):
        return f"<UCAreaRelevance(uc_id={self.source_usecase_id}, area_id={self.target_area_id}, score={self.relevance_score})>"

class UsecaseStepRelevance(Base):
    __tablename__ = 'usecase_step_relevance'

    id = Column(Integer, primary_key=True)
    source_usecase_id = Column(Integer, ForeignKey('use_cases.id'), nullable=False)
    target_process_step_id = Column(Integer, ForeignKey('process_steps.id'), nullable=False)
    relevance_score = Column(Integer, nullable=False)
    relevance_content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        CheckConstraint("relevance_score >= 0 AND relevance_score <= 100", name='relevance_step_score_check'),
        UniqueConstraint('source_usecase_id', 'target_process_step_id', name='unique_usecase_step_relevance')
    )

    source_usecase = relationship("UseCase", back_populates="relevant_to_steps")
    target_process_step = relationship("ProcessStep", back_populates="usecase_relevance")

    def __repr__(self):
        return f"<UCStepRelevance(uc_id={self.source_usecase_id}, step_id={self.target_process_step_id}, score={self.relevance_score})>"

class UsecaseUsecaseRelevance(Base):
    __tablename__ = 'usecase_usecase_relevance'

    id = Column(Integer, primary_key=True)
    source_usecase_id = Column(Integer, ForeignKey('use_cases.id'), nullable=False)
    target_usecase_id = Column(Integer, ForeignKey('use_cases.id'), nullable=False)
    relevance_score = Column(Integer, nullable=False)
    relevance_content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        CheckConstraint("relevance_score >= 0 AND relevance_score <= 100", name='relevance_uc_score_check'),
        CheckConstraint("source_usecase_id != target_usecase_id", name='no_self_relevance'),
        UniqueConstraint('source_usecase_id', 'target_usecase_id', name='unique_usecase_usecase_relevance')
    )

    source_usecase = relationship(
        "UseCase",
        foreign_keys=[source_usecase_id],
        back_populates="relevant_to_usecases_as_source"
    )
    target_usecase = relationship(
        "UseCase",
        foreign_keys=[target_usecase_id],
        back_populates="relevant_to_usecases_as_target"
    )

    def __repr__(self):
        return f"<UCUCRelevance(source_uc_id={self.source_usecase_id}, target_uc_id={self.target_usecase_id}, score={self.relevance_score})>"

# --- DB Engine and Session (Setup in app.py) ---
# DATABASE_URL = "postgresql://user:password@db:5432/usecase_explorer_db"
# engine = create_engine(DATABASE_URL)
# Base.metadata.create_all(engine)
# SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)