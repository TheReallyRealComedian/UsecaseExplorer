-- db/init.sql
-- Drop tables in reverse dependency order (ensure this order for clean slate)
DROP TABLE IF EXISTS process_step_process_step_relevance CASCADE;
DROP TABLE IF EXISTS usecase_usecase_relevance CASCADE;
DROP TABLE IF EXISTS usecase_step_relevance CASCADE;
DROP TABLE IF EXISTS usecase_area_relevance CASCADE;
DROP TABLE IF EXISTS use_cases CASCADE;
DROP TABLE IF EXISTS process_steps CASCADE;
DROP TABLE IF EXISTS areas CASCADE;
DROP TABLE IF EXISTS llm_settings CASCADE;
DROP TABLE IF EXISTS users CASCADE;
DROP TABLE IF EXISTS flask_sessions CASCADE;

-- Create tables

CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    system_prompt TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE areas (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    description TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

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
    llm_comment_1 TEXT,
    llm_comment_2 TEXT,
    llm_comment_3 TEXT,
    llm_comment_4 TEXT,
    llm_comment_5 TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE use_cases (
    id SERIAL PRIMARY KEY,
    bi_id VARCHAR(255) UNIQUE NOT NULL,
    name VARCHAR(255) NOT NULL,
    process_step_id INTEGER NOT NULL REFERENCES process_steps(id) ON DELETE CASCADE,
    priority INTEGER,
    raw_content TEXT,
    summary TEXT,
    inspiration TEXT,
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
    llm_comment_1 TEXT,
    llm_comment_2 TEXT,
    llm_comment_3 TEXT,
    llm_comment_4 TEXT,
    llm_comment_5 TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT priority_range_check CHECK (priority IS NULL OR (priority >= 1 AND priority <= 4))
);

CREATE TABLE usecase_area_relevance (
    id SERIAL PRIMARY KEY,
    source_usecase_id INTEGER NOT NULL REFERENCES use_cases(id) ON DELETE CASCADE,
    target_area_id INTEGER NOT NULL REFERENCES areas(id) ON DELETE CASCADE,
    relevance_score INTEGER NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 100),
    relevance_content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_usecase_id, target_area_id)
);

CREATE TABLE usecase_step_relevance (
    id SERIAL PRIMARY KEY,
    source_usecase_id INTEGER NOT NULL REFERENCES use_cases(id) ON DELETE CASCADE,
    target_process_step_id INTEGER NOT NULL REFERENCES process_steps(id) ON DELETE CASCADE,
    relevance_score INTEGER NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 100),
    relevance_content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (source_usecase_id, target_process_step_id)
);

CREATE TABLE usecase_usecase_relevance (
    id SERIAL PRIMARY KEY,
    source_usecase_id INTEGER NOT NULL REFERENCES use_cases(id) ON DELETE CASCADE,
    target_usecase_id INTEGER NOT NULL REFERENCES use_cases(id) ON DELETE CASCADE,
    relevance_score INTEGER NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 100),
    relevance_content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CHECK (source_usecase_id != target_usecase_id),
    UNIQUE (source_usecase_id, target_usecase_id)
);

CREATE TABLE process_step_process_step_relevance (
    id SERIAL PRIMARY KEY,
    source_process_step_id INTEGER NOT NULL REFERENCES process_steps(id) ON DELETE CASCADE,
    target_process_step_id INTEGER NOT NULL REFERENCES process_steps(id) ON DELETE CASCADE,
    relevance_score INTEGER NOT NULL CHECK (relevance_score >= 0 AND relevance_score <= 100),
    relevance_content TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CHECK (source_process_step_id != target_process_step_id),
    UNIQUE (source_process_step_id, target_process_step_id)
);

CREATE TABLE llm_settings (
    id SERIAL PRIMARY KEY,
    user_id INTEGER UNIQUE NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    openai_api_key VARCHAR(255),
    anthropic_api_key VARCHAR(255),
    google_api_key VARCHAR(255),
    ollama_base_url VARCHAR(255),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE flask_sessions (
    id SERIAL NOT NULL,
    session_id VARCHAR(255) UNIQUE,
    data BYTEA,
    expiry TIMESTAMP WITHOUT TIME ZONE,
    PRIMARY KEY (id)
);

-- Add initial user if not exists (for development)
DO $$ BEGIN
    IF NOT EXISTS (SELECT 1 FROM users WHERE username = 'admin') THEN
        INSERT INTO users (username, password) VALUES ('admin', '$pbkdf2-sha256$29000$8a927a445ee1023d8c11e03a95d43a6d2f342f0a8274618e7e1451f2249c118b$c97ee2e7428f57277862086e330554289895318d18d4512e2c2f70624a080826'); -- password is 'admin'
    END IF;
END $$;

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
CREATE INDEX IF NOT EXISTS idx_ps_ps_rev_source_ps_id ON process_step_process_step_relevance (source_process_step_id);
CREATE INDEX IF NOT EXISTS idx_ps_ps_rev_target_ps_id ON process_step_process_step_relevance (target_process_step_id);
CREATE INDEX IF NOT EXISTS idx_llm_settings_user_id ON llm_settings (user_id);

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