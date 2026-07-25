-- Supabase schema for the connectivity sync workflow.
-- Run this in the Supabase SQL Editor after setting up your project secrets.

create table if not exists public.connectivity_runs (
  run_id text primary key,
  generated_at_utc text,
  village_count integer,
  provider_count integer,
  provider_row_count integer,
  opencellid_data_as_of text,
  opencellid_recency_basis text,
  ookla_data_as_of text,
  ookla_recency_basis text,
  data_as_of text
);

create table if not exists public.connectivity_provider_rows (
  run_id text not null,
  village_id bigint not null,
  state text,
  district text,
  block text,
  village text,
  lgd_code text,
  latitude double precision,
  longitude double precision,
  coordinate_source text,
  provider text not null,
  tower_count integer,
  nearest_tower_km double precision,
  strongest_signal_dbm double precision,
  village_ookla_download_mbps double precision,
  village_ookla_upload_mbps double precision,
  village_ookla_tests bigint,
  village_ookla_distance_km double precision,
  provider_ookla_download_mbps double precision,
  provider_ookla_upload_mbps double precision,
  provider_ookla_tests bigint,
  opencellid_data_as_of text,
  opencellid_recency_basis text,
  ookla_data_as_of text,
  ookla_recency_basis text,
  data_as_of text,
  pipeline_generated_at_utc text,
  coverage_score text,
  assessment_note text,
  synced_at_utc text,
  primary key (run_id, village_id, provider)
);

create table if not exists public.connectivity_village_summary (
  run_id text not null,
  village_id bigint not null,
  state text,
  district text,
  block text,
  village text,
  lgd_code text,
  latitude double precision,
  longitude double precision,
  coordinate_source text,
  airtel_coverage_score text,
  bsnl_coverage_score text,
  jio_coverage_score text,
  vodafone_idea_coverage_score text,
  opencellid_data_as_of text,
  opencellid_recency_basis text,
  ookla_data_as_of text,
  ookla_recency_basis text,
  data_as_of text,
  pipeline_generated_at_utc text,
  synced_at_utc text,
  primary key (run_id, village_id)
);

create index if not exists connectivity_provider_rows_village_idx
  on public.connectivity_provider_rows (village_id);

create index if not exists connectivity_provider_rows_provider_idx
  on public.connectivity_provider_rows (provider);

create index if not exists connectivity_village_summary_district_idx
  on public.connectivity_village_summary (district);
