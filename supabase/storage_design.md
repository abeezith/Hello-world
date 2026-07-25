# Supabase Storage Design

This design turns the current connectivity pipeline into a small time-series warehouse for district-by-district planning.

## Goals

- keep weekly freshness for recent operational planning
- preserve the last 6 weekly snapshots for short-term drift analysis
- keep monthly rollups for the last 12 months
- avoid storing only averages, because averages hide volatility and missing-data patterns
- keep storage small enough to run across many districts

## Recommended tables

### 1. `connectivity_ingest_runs`

One row per ingestion or sync run.

Use it to answer:

- what ran
- when it ran
- which district or state it covered
- how many rows were written
- what source versions were used

Suggested key columns:

- `run_id`
- `run_type` (`weekly_ingest`, `manual_backfill`, `monthly_rollup`)
- `state_name`
- `district_name`
- `block_name`
- `started_at_utc`
- `completed_at_utc`
- `status`
- `tower_source_as_of`
- `ookla_source_as_of`
- `row_count`
- `notes`

### 2. `connectivity_weekly_village_provider`

This is the main weekly fact table.

Store one row per:

- district
- village
- provider
- week

Suggested key columns:

- `week_start_date`
- `run_id`
- `state_name`
- `district_name`
- `block_name`
- `village_name`
- `lgd_code`
- `provider`
- `coverage_score`
- `tower_count`
- `nearest_tower_km`
- `strongest_signal_dbm`
- `village_ookla_download_mbps`
- `village_ookla_upload_mbps`
- `village_ookla_tests`
- `provider_ookla_download_mbps`
- `provider_ookla_upload_mbps`
- `provider_ookla_tests`
- `data_quality_tier`
- `source_completeness_flag`

This table is the one you will query most often for recent field planning.

### 3. `connectivity_weekly_tower_snapshot`

Optional but useful if you want tower inventory history by district.

Store one row per tower observation extracted during the weekly run.

Suggested key columns:

- `week_start_date`
- `run_id`
- `state_name`
- `district_name`
- `mcc`
- `mnc`
- `provider`
- `radio`
- `lac`
- `cell_id`
- `latitude`
- `longitude`
- `average_signal`

If storage becomes heavy, this is the first table to trim down or restrict to district-scoped extracts only.

### 4. `connectivity_weekly_ookla_tile`

Optional weekly tile summary table.

Store one row per tile or district/provider summary rather than every raw Ookla point.

Suggested key columns:

- `week_start_date`
- `run_id`
- `state_name`
- `district_name`
- `provider`
- `tile_id`
- `avg_download_mbps`
- `avg_upload_mbps`
- `tests`
- `tile_centroid_latitude`
- `tile_centroid_longitude`

### 5. `connectivity_monthly_village_provider`

Monthly rollup of the weekly village-provider facts.

Use this for trend views and historical comparisons.

Suggested key columns:

- `month_start_date`
- `state_name`
- `district_name`
- `block_name`
- `village_name`
- `lgd_code`
- `provider`
- `weeks_observed`
- `mean_download_mbps`
- `median_download_mbps`
- `mean_upload_mbps`
- `median_upload_mbps`
- `mean_nearest_tower_km`
- `best_coverage_score`
- `worst_coverage_score`
- `most_common_data_quality_tier`
- `latest_run_id`

### 6. `connectivity_monthly_district_provider`

District-level rollup for dashboards and quick planning views.

Suggested key columns:

- `month_start_date`
- `state_name`
- `district_name`
- `provider`
- `villages_observed`
- `strong_count`
- `moderate_count`
- `weak_count`
- `unknown_count`
- `mean_download_mbps`
- `mean_upload_mbps`
- `median_nearest_tower_km`

## Retention policy

### Weekly raw

- Keep the latest 6 weekly snapshots in `connectivity_weekly_village_provider`
- Keep the latest 6 weekly tower/tile snapshots if you decide to store those
- Delete older weekly rows after the monthly rollup succeeds

### Monthly rollups

- Refresh the current month on each weekly ingest or rollup
- Keep the latest 12 monthly summaries
- Older monthly rows can be archived or exported if you want long-term history

### Ingest runs

- Keep these much longer, ideally 24 months or more
- Run metadata is tiny and helps with audits and troubleshooting

## Suggested job schedule

Run these as Supabase cron jobs or GitHub Actions scheduled jobs:

1. `weekly_ingest`
   - Frequency: once per week
   - Purpose: capture new weekly snapshot data

2. `weekly_rollup`
   - Frequency: after the ingest run
   - Purpose: refresh the current month in `connectivity_monthly_village_provider` and `connectivity_monthly_district_provider`

3. `weekly_purge`
   - Frequency: after rollup
   - Purpose: delete weekly rows older than 42 days

4. `monthly_purge`
   - Frequency: first day of month
   - Purpose: delete monthly rows older than 12 months if you do not want indefinite history

## Practical recommendation

For this project, the best balance is:

- raw weekly village-provider facts for 6 weeks
- monthly village-provider summaries for 12 months
- district monthly summaries for dashboards
- run metadata retained for auditability

That keeps the system lightweight while still letting you compare trends across districts and across months.
