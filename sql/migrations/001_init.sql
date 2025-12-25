-- MCP Metrics Database Schema
-- Phase 1: Minimal schema for GitHub workflow metrics collection

-- job_metrics: 1 row per workflow run/job
CREATE TABLE IF NOT EXISTS job_metrics (
  run_id varchar PRIMARY KEY,
  repository varchar,
  organization varchar,
  branch varchar,
  project_id varchar,
  app_cat_id varchar,
  workflow_name varchar,
  workflow_version varchar,
  job_name varchar,
  job_status varchar,
  job_error_message varchar,
  job_failure_category varchar,
  job_start_time timestamptz,
  job_end_time timestamptz,
  job_duration_seconds int,
  app_runtime varchar,
  base_image varchar,
  exception_codes jsonb
);

-- job_step_metrics: N rows per run_id
CREATE TABLE IF NOT EXISTS job_step_metrics (
  step_id varchar PRIMARY KEY,
  run_id varchar NOT NULL REFERENCES job_metrics(run_id),
  step_name varchar,
  step_index int,
  step_status varchar,
  step_start_time timestamptz,
  step_end_time timestamptz,
  step_duration_seconds int
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_job_metrics_repo_start ON job_metrics(repository, job_start_time DESC);
CREATE INDEX IF NOT EXISTS idx_job_metrics_status_start ON job_metrics(job_status, job_start_time DESC);
CREATE INDEX IF NOT EXISTS idx_steps_run_step ON job_step_metrics(run_id, step_index);
