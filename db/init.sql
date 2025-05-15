-- init.sql

-- Drop tables in reverse order of dependency if they exist
DROP TABLE IF EXISTS usecase_usecase_relevance CASCADE;
DROP TABLE IF EXISTS usecase_step_relevance CASCADE;
DROP TABLE IF EXISTS usecase_area_relevance CASCADE;
DROP TABLE IF EXISTS use_cases CASCADE;
DROP TABLE IF EXISTS process_steps CASCADE;
DROP TABLE IF EXISTS areas CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Create the 'users' table for authentication
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL, -- Store hashed passwords!
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create the 'areas' table
CREATE TABLE areas (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create the 'process_steps' table
CREATE TABLE process_steps (
    id SERIAL PRIMARY KEY,
    bi_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    area_id INTEGER NOT NULL REFERENCES areas(id) ON DELETE CASCADE,
    step_description TEXT,
    raw_content TEXT,
    summary TEXT,
    vision_statement TEXT,
    in_scope TEXT,
    out_of_scope TEXT,
    interfaces_text TEXT,
    what_is_actually_done TEXT,
    pain_points TEXT,
    targets_text TEXT,
    -- Add the missing LLM comment columns here
    llm_comment_1 TEXT,
    llm_comment_2 TEXT,
    llm_comment_3 TEXT,
    llm_comment_4 TEXT,
    llm_comment_5 TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
);

-- Create the 'use_cases' table
CREATE TABLE use_cases (
    id SERIAL PRIMARY KEY,
    bi_id VARCHAR(255) UNIQUE NOT NULL, -- Business Identifier
    name VARCHAR(255) NOT NULL,
    process_step_id INTEGER NOT NULL REFERENCES process_steps(id) ON DELETE CASCADE,
    priority INTEGER,
    raw_content TEXT,
    summary TEXT,
    inspiration TEXT,
    -- New Fields Based on Documentation Structure
    wave VARCHAR(255),
    effort_level VARCHAR(255),
    status VARCHAR(255),
    business_problem_solved TEXT,
    target_solution_description TEXT,
    technologies_text TEXT,
    requirements TEXT,
    relevants_text TEXT,
    reduction_time_transfer VARCHAR(255),
    reduction_time_launches VARCHAR(255),
    reduction_costs_supply VARCHAR(255),
    quality_improvement_quant VARCHAR(255),
    ideation_notes TEXT,
    further_ideas TEXT,
    effort_quantification TEXT,
    potential_quantification TEXT,
    dependencies_text TEXT,
    contact_persons_text TEXT,
    related_projects_text TEXT,
    -- End New Fields
    llm_comment_1 TEXT, -- These were already here in use_cases, which is fine
    llm_comment_2 TEXT,
    llm_comment_3 TEXT,
    llm_comment_4 TEXT,
    llm_comment_5 TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT priority_range_check CHECK (priority IS NULL OR (priority >= 1 AND priority <= 4))
);

-- Create the 'usecase_area_relevance' table
CREATE TABLE usecase_area_relevance (
    id SERIAL PRIMARY KEY,
    source_usecase_id INTEGER NOT NULL REFERENCES use_cases(id) ON DELETE CASCADE,
    target_area_id INTEGER NOT NULL REFERENCES areas(id) ON DELETE CASCADE,
    relevance_score INTEGER NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 100),
    relevance_content TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_usecase_id, target_area_id)
);

-- Create the 'usecase_step_relevance' table
CREATE TABLE usecase_step_relevance (
    id SERIAL PRIMARY KEY,
    source_usecase_id INTEGER NOT NULL REFERENCES use_cases(id) ON DELETE CASCADE,
    target_process_step_id INTEGER NOT NULL REFERENCES process_steps(id) ON DELETE CASCADE,
    relevance_score INTEGER NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 100),
    relevance_content TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_usecase_id, target_process_step_id)
);

-- Create the 'usecase_usecase_relevance' table
CREATE TABLE usecase_usecase_relevance (
    id SERIAL PRIMARY KEY,
    source_usecase_id INTEGER NOT NULL REFERENCES use_cases(id) ON DELETE CASCADE,
    target_usecase_id INTEGER NOT NULL REFERENCES use_cases(id) ON DELETE CASCADE,
    relevance_score INTEGER NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 100),
    relevance_content TEXT,
    created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
    CHECK (source_usecase_id != target_usecase_id),
    UNIQUE (source_usecase_id, target_usecase_id)
);

-- Add indexes for performance
CREATE INDEX IF NOT EXISTS idx_users_username ON users (username);
CREATE INDEX IF NOT EXISTS idx_areas_name ON areas (name);
CREATE INDEX IF NOT EXISTS idx_process_steps_area_id ON process_steps (area_id);
CREATE INDEX IF NOT EXISTS idx_process_steps_bi_id ON process_steps (bi_id);
CREATE INDEX IF NOT EXISTS idx_use_cases_process_step_id ON use_cases (process_step_id);
CREATE INDEX IF NOT EXISTS idx_use_cases_bi_id ON use_cases (bi_id);
CREATE INDEX IF NOT EXISTS idx_uc_area_rev_source_uc_id ON usecase_area_relevance (source_usecase_id);
CREATE INDEX IF NOT EXISTS idx_uc_area_rev_target_area_id ON usecase_area_relevance (target_area_id);
CREATE INDEX IF NOT EXISTS idx_uc_step_rev_source_uc_id ON usecase_step_relevance (source_usecase_id);
CREATE INDEX IF NOT EXISTS idx_uc_step_rev_target_step_id ON usecase_step_relevance (target_process_step_id);
CREATE INDEX IF NOT EXISTS idx_uc_uc_rev_source_uc_id ON usecase_usecase_relevance (source_usecase_id);
CREATE INDEX IF NOT EXISTS idx_uc_uc_rev_target_uc_id ON usecase_usecase_relevance (target_usecase_id);

/*
-- Optional: Trigger for automatically updating updated_at on row modification
CREATE OR REPLACE FUNCTION trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = CURRENT_TIMESTAMP;
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Example for one table:
CREATE TRIGGER set_process_steps_updated_at_timestamp
BEFORE UPDATE ON process_steps
FOR EACH ROW
EXECUTE FUNCTION trigger_set_timestamp();
-- Similar triggers can be created for other tables if desired.
*/