-- Connectivity storage design for Supabase.
-- This is a concrete blueprint for weekly raw retention + monthly rollups.

create table if not exists public.connectivity_ingest_runs (
  run_id text primary key,
  run_type text not null,
  state_name text,
  district_name text,
  block_name text,
  started_at_utc timestamptz,
  completed_at_utc timestamptz,
  status text,
  tower_source_as_of text,
  ookla_source_as_of text,
  row_count bigint,
  notes text
);

create table if not exists public.connectivity_weekly_village_provider (
  week_start_date date not null,
  run_id text not null,
  state_name text,
  district_name text,
  block_name text,
  village_name text,
  lgd_code text,
  provider text not null,
  coverage_score text,
  tower_count integer,
  nearest_tower_km double precision,
  strongest_signal_dbm double precision,
  village_ookla_download_mbps double precision,
  village_ookla_upload_mbps double precision,
  village_ookla_tests bigint,
  provider_ookla_download_mbps double precision,
  provider_ookla_upload_mbps double precision,
  provider_ookla_tests bigint,
  data_quality_tier text,
  source_completeness_flag text,
  synced_at_utc timestamptz default now(),
  primary key (week_start_date, state_name, district_name, block_name, village_name, provider)
);

create table if not exists public.connectivity_weekly_tower_snapshot (
  week_start_date date not null,
  run_id text not null,
  state_name text,
  district_name text,
  provider text,
  radio text,
  mcc text,
  mnc text,
  lac text,
  cell_id text,
  latitude double precision,
  longitude double precision,
  average_signal double precision,
  synced_at_utc timestamptz default now(),
  primary key (week_start_date, district_name, provider, mcc, mnc, lac, cell_id, latitude, longitude)
);

create table if not exists public.connectivity_weekly_ookla_tile (
  week_start_date date not null,
  run_id text not null,
  state_name text,
  district_name text,
  provider text,
  tile_id text,
  avg_download_mbps double precision,
  avg_upload_mbps double precision,
  tests bigint,
  tile_centroid_latitude double precision,
  tile_centroid_longitude double precision,
  synced_at_utc timestamptz default now(),
  primary key (week_start_date, district_name, provider, tile_id)
);

create table if not exists public.connectivity_monthly_village_provider (
  month_start_date date not null,
  state_name text,
  district_name text,
  block_name text,
  village_name text,
  lgd_code text,
  provider text not null,
  weeks_observed integer,
  mean_download_mbps double precision,
  median_download_mbps double precision,
  mean_upload_mbps double precision,
  median_upload_mbps double precision,
  mean_nearest_tower_km double precision,
  best_coverage_score text,
  worst_coverage_score text,
  most_common_data_quality_tier text,
  latest_run_id text,
  refreshed_at_utc timestamptz default now(),
  primary key (month_start_date, state_name, district_name, block_name, village_name, provider)
);

create table if not exists public.connectivity_monthly_district_provider (
  month_start_date date not null,
  state_name text,
  district_name text,
  provider text not null,
  villages_observed integer,
  strong_count integer,
  moderate_count integer,
  weak_count integer,
  unknown_count integer,
  mean_download_mbps double precision,
  mean_upload_mbps double precision,
  median_nearest_tower_km double precision,
  refreshed_at_utc timestamptz default now(),
  primary key (month_start_date, state_name, district_name, provider)
);

create index if not exists connectivity_weekly_village_provider_district_idx
  on public.connectivity_weekly_village_provider (district_name, provider);

create index if not exists connectivity_monthly_village_provider_district_idx
  on public.connectivity_monthly_village_provider (district_name, provider);

create index if not exists connectivity_monthly_district_provider_district_idx
  on public.connectivity_monthly_district_provider (district_name, provider);

create or replace function public.connectivity_score_rank(score text)
returns integer
language sql
immutable
as $$
  select case upper(coalesce(score, ''))
    when 'STRONG' then 4
    when 'MODERATE' then 3
    when 'WEAK' then 2
    else 1
  end
$$;

create or replace function public.connectivity_score_from_rank(score_rank integer)
returns text
language sql
immutable
as $$
  select case coalesce(score_rank, 1)
    when 4 then 'Strong'
    when 3 then 'Moderate'
    when 2 then 'Weak'
    else 'Unknown'
  end
$$;

create or replace function public.refresh_connectivity_monthly_rollups()
returns void
language plpgsql
as $$
declare
  current_month date := date_trunc('month', current_date)::date;
begin
  delete from public.connectivity_monthly_village_provider
  where month_start_date = current_month;

  insert into public.connectivity_monthly_village_provider (
    month_start_date,
    state_name,
    district_name,
    block_name,
    village_name,
    lgd_code,
    provider,
    weeks_observed,
    mean_download_mbps,
    median_download_mbps,
    mean_upload_mbps,
    median_upload_mbps,
    mean_nearest_tower_km,
    best_coverage_score,
    worst_coverage_score,
    most_common_data_quality_tier,
    latest_run_id,
    refreshed_at_utc
  )
  select
    date_trunc('month', week_start_date)::date as month_start_date,
    state_name,
    district_name,
    block_name,
    village_name,
    lgd_code,
    provider,
    count(distinct week_start_date)::integer as weeks_observed,
    avg(village_ookla_download_mbps) as mean_download_mbps,
    percentile_cont(0.5) within group (order by village_ookla_download_mbps) as median_download_mbps,
    avg(village_ookla_upload_mbps) as mean_upload_mbps,
    percentile_cont(0.5) within group (order by village_ookla_upload_mbps) as median_upload_mbps,
    avg(nearest_tower_km) as mean_nearest_tower_km,
    public.connectivity_score_from_rank(max(public.connectivity_score_rank(coverage_score))) as best_coverage_score,
    public.connectivity_score_from_rank(min(public.connectivity_score_rank(coverage_score))) as worst_coverage_score,
    mode() within group (order by coalesce(data_quality_tier, 'Unknown')) as most_common_data_quality_tier,
    max(run_id) as latest_run_id,
    now() as refreshed_at_utc
  from public.connectivity_weekly_village_provider
  where week_start_date >= current_month
    and week_start_date < (current_month + interval '1 month')::date
  group by 1, 2, 3, 4, 5, 6, 7;

  delete from public.connectivity_monthly_district_provider
  where month_start_date = current_month;

  insert into public.connectivity_monthly_district_provider (
    month_start_date,
    state_name,
    district_name,
    provider,
    villages_observed,
    strong_count,
    moderate_count,
    weak_count,
    unknown_count,
    mean_download_mbps,
    mean_upload_mbps,
    median_nearest_tower_km,
    refreshed_at_utc
  )
  select
    date_trunc('month', week_start_date)::date as month_start_date,
    state_name,
    district_name,
    provider,
    count(distinct village_name)::integer as villages_observed,
    count(*) filter (where coverage_score = 'Strong')::integer as strong_count,
    count(*) filter (where coverage_score = 'Moderate')::integer as moderate_count,
    count(*) filter (where coverage_score = 'Weak')::integer as weak_count,
    count(*) filter (where coverage_score = 'Unknown')::integer as unknown_count,
    avg(village_ookla_download_mbps) as mean_download_mbps,
    avg(village_ookla_upload_mbps) as mean_upload_mbps,
    percentile_cont(0.5) within group (order by nearest_tower_km) as median_nearest_tower_km,
    now() as refreshed_at_utc
  from public.connectivity_weekly_village_provider
  where week_start_date >= current_month
    and week_start_date < (current_month + interval '1 month')::date
  group by 1, 2, 3, 4;
end;
$$;

create or replace function public.purge_connectivity_weekly_rows()
returns void
language plpgsql
as $$
begin
  delete from public.connectivity_weekly_village_provider
  where week_start_date < (current_date - interval '42 days')::date;

  delete from public.connectivity_weekly_tower_snapshot
  where week_start_date < (current_date - interval '42 days')::date;

  delete from public.connectivity_weekly_ookla_tile
  where week_start_date < (current_date - interval '42 days')::date;
end;
$$;

create or replace function public.purge_connectivity_monthly_rows()
returns void
language plpgsql
as $$
begin
  delete from public.connectivity_monthly_village_provider
  where month_start_date < (date_trunc('month', current_date)::date - interval '12 months')::date;

  delete from public.connectivity_monthly_district_provider
  where month_start_date < (date_trunc('month', current_date)::date - interval '12 months')::date;
end;
$$;
