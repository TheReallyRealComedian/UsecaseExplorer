# /backend/models.py
from sqlalchemy import create_engine, Column, Integer, String, Text, ForeignKey, DateTime, CheckConstraint, UniqueConstraint, Table
from sqlalchemy.orm import relationship, declarative_base, sessionmaker, scoped_session
from sqlalchemy.sql import func
from passlib.hash import pbkdf2_sha256
from flask_login import UserMixin

# Base class for declarative models
Base = declarative_base()

# --- NEW: Association Table for UseCase <-> Tag ---
usecase_tag_association = Table('usecase_tag_association', Base.metadata,
    Column('usecase_id', Integer, ForeignKey('use_cases.id', ondelete='CASCADE'), primary_key=True),
    Column('tag_id', Integer, ForeignKey('tags.id', ondelete='CASCADE'), primary_key=True)
)

# --- NEW: Tag Model ---
class Tag(Base):
    __tablename__ = 'tags'

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    # Category helps us differentiate between 'it_system', 'data_type', 'tag', etc.
    category = Column(String(50), nullable=False, default='tag', index=True)

    use_cases = relationship(
        "UseCase",
        secondary=usecase_tag_association,
        back_populates="tags"
    )

    __table_args__ = (
        UniqueConstraint('name', 'category', name='unique_name_category_in_tags'),
    )

    def __repr__(self):
        return f"<Tag(name='{self.name}', category='{self.category}')>"


# --- User Model ---
class User(UserMixin, Base):
    __tablename__ = 'users'

    id = Column(Integer, primary_key=True)
    username = Column(String(80), unique=True, nullable=False)
    password = Column(String(255), nullable=False) # Storing hashed password
    system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # One-to-one relationship with LLMSettings
    llm_settings = relationship("LLMSettings", back_populates="user", uselist=False, cascade="all, delete-orphan")

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

    process_steps = relationship("ProcessStep", back_populates="area", cascade="all, delete-orphan")
    usecase_relevance = relationship("UsecaseAreaRelevance", back_populates="target_area", cascade="all, delete-orphan")

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
    step_description = Column(Text, nullable=True)
    raw_content = Column(Text, nullable=True)
    summary = Column(Text, nullable=True)

    # New structured fields
    vision_statement = Column(Text, nullable=True)
    in_scope = Column(Text, nullable=True)
    out_of_scope = Column(Text, nullable=True)
    interfaces_text = Column(Text, nullable=True)
    what_is_actually_done = Column(Text, nullable=True)
    pain_points = Column(Text, nullable=True)
    targets_text = Column(Text, nullable=True)

    # LLM comments
    llm_comment_1 = Column(Text, nullable=True)
    llm_comment_2 = Column(Text, nullable=True)
    llm_comment_3 = Column(Text, nullable=True)
    llm_comment_4 = Column(Text, nullable=True)
    llm_comment_5 = Column(Text, nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    area = relationship("Area", back_populates="process_steps")
    use_cases = relationship("UseCase", back_populates="process_step", cascade="all, delete-orphan")
    usecase_relevance = relationship("UsecaseStepRelevance", back_populates="target_process_step", cascade="all, delete-orphan")

    # Relationships for ProcessStepProcessStepRelevance
    relevant_to_steps_as_source = relationship(
        "ProcessStepProcessStepRelevance",
        foreign_keys='[ProcessStepProcessStepRelevance.source_process_step_id]',
        back_populates="source_process_step",
        cascade="all, delete-orphan"
    )
    relevant_to_steps_as_target = relationship(
        "ProcessStepProcessStepRelevance",
        foreign_keys='[ProcessStepProcessStepRelevance.target_process_step_id]',
        back_populates="target_process_step",
        cascade="all, delete-orphan"
    )

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

    wave = Column(String(255), nullable=True)
    effort_level = Column(String(255), nullable=True) # e.g., 'Low', 'Medium', 'High'
    status = Column(String(255), nullable=True) # e.g., 'Ideated', 'Waiting List', 'Ongoing', 'Completed'
    business_problem_solved = Column(Text, nullable=True)
    target_solution_description = Column(Text, nullable=True)
    technologies_text = Column(Text, nullable=True)
    requirements = Column(Text, nullable=True)
    relevants_text = Column(Text, nullable=True)
    reduction_time_transfer = Column(String(255), nullable=True) # e.g., 'Low (days)', 'Medium (weeks)', 'High (month)'
    reduction_time_launches = Column(String(255), nullable=True) # e.g., 'Low (weeks)', 'High (month)'
    reduction_costs_supply = Column(String(255), nullable=True) # e.g., 'Low', 'Medium', 'High'
    quality_improvement_quant = Column(String(255), nullable=True) # e.g., 'Low', 'Medium', 'High'
    ideation_notes = Column(Text, nullable=True)
    further_ideas = Column(Text, nullable=True)
    effort_quantification = Column(Text, nullable=True)
    potential_quantification = Column(Text, nullable=True)
    dependencies_text = Column(Text, nullable=True)
    contact_persons_text = Column(Text, nullable=True)
    related_projects_text = Column(Text, nullable=True)

    pilot_site_factory_text = Column(Text, nullable=True)
    usecase_type_category = Column(String(255), nullable=True) # (Strategic, Improvement, Fundamental)

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

    # UPDATE: Add relationship to the Tag model
    tags = relationship(
        "Tag",
        secondary=usecase_tag_association,
        back_populates="use_cases",
        cascade="all, delete"  # Optional: Deleting a use case doesn't delete the tag, just the link.
    )

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
        
    # NEW: Convenience properties to access categorized tags easily
    @property
    def it_systems(self):
        return [tag for tag in self.tags if tag.category == 'it_system']

    @property
    def data_types(self):
        return [tag for tag in self.tags if tag.category == 'data_type']

    @property
    def generic_tags(self):
        return [tag for tag in self.tags if tag.category == 'tag']


    def __repr__(self):
        return f"<UseCase(name='{self.name}', bi_id='{self.bi_id}', wave='{self.wave}', status='{self.status}')>"


# --- Relevance Models ---

class UsecaseAreaRelevance(Base):
    __tablename__ = 'usecase_area_relevance'

    id = Column(Integer, primary_key=True)
    source_usecase_id = Column(Integer, ForeignKey('use_cases.id', ondelete='CASCADE'), nullable=False)
    target_area_id = Column(Integer, ForeignKey('areas.id', ondelete='CASCADE'), nullable=False)
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
    source_usecase_id = Column(Integer, ForeignKey('use_cases.id', ondelete='CASCADE'), nullable=False)
    target_process_step_id = Column(Integer, ForeignKey('process_steps.id', ondelete='CASCADE'), nullable=False)
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
    source_usecase_id = Column(Integer, ForeignKey('use_cases.id', ondelete='CASCADE'), nullable=False)
    target_usecase_id = Column(Integer, ForeignKey('use_cases.id', ondelete='CASCADE'), nullable=False)
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

class ProcessStepProcessStepRelevance(Base):
    __tablename__ = 'process_step_process_step_relevance'

    id = Column(Integer, primary_key=True)
    source_process_step_id = Column(Integer, ForeignKey('process_steps.id', ondelete='CASCADE'), nullable=False)
    target_process_step_id = Column(Integer, ForeignKey('process_steps.id', ondelete='CASCADE'), nullable=False)
    relevance_score = Column(Integer, nullable=False)
    relevance_content = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    __table_args__ = (
        CheckConstraint("relevance_score >= 0 AND relevance_score <= 100", name='relevance_ps_ps_score_check'),
        CheckConstraint("source_process_step_id != target_process_step_id", name='no_self_step_relevance'),
        UniqueConstraint('source_process_step_id', 'target_process_step_id', name='unique_process_step_process_step_relevance')
    )

    source_process_step = relationship(
        "ProcessStep",
        foreign_keys=[source_process_step_id],
        back_populates="relevant_to_steps_as_source"
    )
    target_process_step = relationship(
        "ProcessStep",
        foreign_keys=[target_process_step_id],
        back_populates="relevant_to_steps_as_target"
    )

    def __repr__(self):
        return f"<PSPSRelevance(source_ps_id={self.source_process_step_id}, target_ps_id={self.target_process_step_id}, score={self.relevance_score})>"

# LLMSettings Model
class LLMSettings(Base):
    __tablename__ = 'llm_settings'

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id', ondelete='CASCADE'), unique=True, nullable=False)
    
    openai_api_key = Column(String(255), nullable=True)
    anthropic_api_key = Column(String(255), nullable=True)
    google_api_key = Column(String(255), nullable=True)
    ollama_base_url = Column(String(255), nullable=True)

    # Apollo credentials
    apollo_client_id = Column(String(255), nullable=True)
    apollo_client_secret = Column(String(length=255), nullable=True)

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now(), server_default=func.now())

    user = relationship("User", back_populates="llm_settings")

    def __repr__(self):
        return f"<LLMSettings(user_id={self.user_id})>"