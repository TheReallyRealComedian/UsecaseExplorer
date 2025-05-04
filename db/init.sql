-- init.sql

-- Drop tables if they exist (useful for development/testing)
DROP TABLE IF EXISTS usecase_usecase_relevance CASCADE;
DROP TABLE IF EXISTS usecase_step_relevance CASCADE;
DROP TABLE IF EXISTS usecase_area_relevance CASCADE;
DROP TABLE IF EXISTS use_cases CASCADE;
DROP TABLE IF EXISTS process_steps CASCADE;
DROP TABLE IF EXISTS areas CASCADE;
DROP TABLE IF EXISTS users CASCADE;

-- Enable UUID generation if needed later (though we'll use SERIAL for PKs)
-- CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Create the 'users' table for authentication
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(80) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL, -- Store hashed passwords!
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create the 'areas' table
CREATE TABLE areas (
    id SERIAL PRIMARY KEY,
    name VARCHAR(255) UNIQUE NOT NULL,
    -- Add other area-specific fields if needed later
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create the 'process_steps' table
CREATE TABLE process_steps (
    id SERIAL PRIMARY KEY,
    bi_id VARCHAR(255) UNIQUE NOT NULL, -- Business Identifier
    name VARCHAR(255) NOT NULL,
    area_id INTEGER NOT NULL,
    raw_content TEXT,
    summary TEXT,
    llm_comment_1 TEXT, -- Placeholder 1
    llm_comment_2 TEXT, -- Placeholder 2
    llm_comment_3 TEXT, -- Placeholder 3
    llm_comment_4 TEXT, -- Placeholder 4
    llm_comment_5 TEXT, -- Placeholder 5
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (area_id) REFERENCES areas (id) ON DELETE CASCADE
);

-- Create the 'use_cases' table
CREATE TABLE use_cases (
    id SERIAL PRIMARY KEY,
    bi_id VARCHAR(255) UNIQUE NOT NULL, -- Business Identifier
    name VARCHAR(255) NOT NULL,
    process_step_id INTEGER NOT NULL,
    raw_content TEXT,
    summary TEXT,
    inspiration TEXT,
    llm_comment_1 TEXT, -- Placeholder 1
    llm_comment_2 TEXT, -- Placeholder 2
    llm_comment_3 TEXT, -- Placeholder 3
    llm_comment_4 TEXT, -- Placeholder 4
    llm_comment_5 TEXT, -- Placeholder 5
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (process_step_id) REFERENCES process_steps (id) ON DELETE CASCADE
);

-- Create the 'usecase_area_relevance' table
CREATE TABLE usecase_area_relevance (
    id SERIAL PRIMARY KEY,
    source_usecase_id INTEGER NOT NULL,
    target_area_id INTEGER NOT NULL,
    relevance_score INTEGER CHECK (relevance_score >= 0 AND relevance_score <= 100), -- Score between 0 and 100
    relevance_content TEXT, -- Markdown description of relevance
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (source_usecase_id) REFERENCES use_cases (id) ON DELETE CASCADE,
    FOREIGN KEY (target_area_id) REFERENCES areas (id) ON DELETE CASCADE,

    -- Ensure a specific use case has only one relevance entry towards a specific area
    UNIQUE (source_usecase_id, target_area_id)
);

-- Create the 'usecase_step_relevance' table
CREATE TABLE usecase_step_relevance (
    id SERIAL PRIMARY KEY,
    source_usecase_id INTEGER NOT NULL,
    target_process_step_id INTEGER NOT NULL,
    relevance_score INTEGER CHECK (relevance_score >= 0 AND relevance_score <= 100), -- Score between 0 and 100
    relevance_content TEXT, -- Markdown description of relevance
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (source_usecase_id) REFERENCES use_cases (id) ON DELETE CASCADE,
    FOREIGN KEY (target_process_step_id) REFERENCES process_steps (id) ON DELETE CASCADE,

    -- Ensure a specific use case has only one relevance entry towards a specific step
    UNIQUE (source_usecase_id, target_process_step_id)
);

-- Create the 'usecase_usecase_relevance' table
CREATE TABLE usecase_usecase_relevance (
    id SERIAL PRIMARY KEY,
    source_usecase_id INTEGER NOT NULL,
    target_usecase_id INTEGER NOT NULL,
    relevance_score INTEGER CHECK (relevance_score >= 0 AND relevance_score <= 100), -- Score between 0 and 100
    relevance_content TEXT, -- Markdown description of relevance
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,

    FOREIGN KEY (source_usecase_id) REFERENCES use_cases (id) ON DELETE CASCADE,
    FOREIGN KEY (target_usecase_id) REFERENCES use_cases (id) ON DELETE CASCADE,

    -- Prevent a use case from being relevant to itself via this table
    CHECK (source_usecase_id != target_usecase_id),

    -- Ensure a specific use case has only one relevance entry towards another specific use case
    UNIQUE (source_usecase_id, target_usecase_id)
);

-- Add indexes for performance on frequently queried columns
CREATE INDEX idx_users_username ON users (username);
CREATE INDEX idx_areas_name ON areas (name);
CREATE INDEX idx_process_steps_area_id ON process_steps (area_id);
CREATE INDEX idx_process_steps_bi_id ON process_steps (bi_id);
CREATE INDEX idx_use_cases_process_step_id ON use_cases (process_step_id);
CREATE INDEX idx_use_cases_bi_id ON use_cases (bi_id);
CREATE INDEX idx_uc_area_rev_source_uc_id ON usecase_area_relevance (source_usecase_id);
CREATE INDEX idx_uc_area_rev_target_area_id ON usecase_area_relevance (target_area_id);
CREATE INDEX idx_uc_step_rev_source_uc_id ON usecase_step_relevance (source_usecase_id);
CREATE INDEX idx_uc_step_rev_target_step_id ON usecase_step_relevance (target_process_step_id);
CREATE INDEX idx_uc_uc_rev_source_uc_id ON usecase_usecase_relevance (source_usecase_id);
CREATE INDEX idx_uc_uc_rev_target_uc_id ON usecase_usecase_relevance (target_usecase_id);

-- Add triggers to automatically update `updated_at` timestamp (optional but good practice)
-- Note: Adding triggers via init.sql might be more complex depending on PG version and image.
-- SQLAlchemy handles updates, so this is less critical initially.