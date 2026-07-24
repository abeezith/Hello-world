# Setup and Runbook

This runbook is for the current Koraput connectivity pipeline and the requested-district workflow.

## What the pipeline does

- builds village-level connectivity estimates
- normalizes provider names to current operators
- uses OpenCellID tower evidence and Ookla tiles as planning inputs
- writes per-district CSV, XLSX, GeoJSON, and HTML map outputs
- keeps a combined requested-district browser up to date

## Prerequisites

- Windows machine with Python available
- project-local virtual environment at `.venv`
- source data under `data/`
- requested district inputs already present on disk

## Fast local setup

```powershell
cd E:\Resources\SecondBrain\koraput_connectivity_pipeline
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

## Run the Koraput base workflow

```powershell
cd E:\Resources\SecondBrain\koraput_connectivity_pipeline
python run_pipeline.py --config .\config.yaml
```

## Run one requested district

```powershell
cd E:\Resources\SecondBrain\koraput_connectivity_pipeline
.venv\Scripts\python.exe .\enrich_requested_districts_from_stoptb.py --requested-state Odisha --requested-district Koraput
```

Replace the state and district with the district you want to process.

## Rebuild the district status and summary

```powershell
cd E:\Resources\SecondBrain\koraput_connectivity_pipeline
.venv\Scripts\python.exe .\report_requested_district_status.py
.venv\Scripts\python.exe .\rebuild_requested_district_summary.py
```

## Safety rules

- Existing district folders are archived before overwrite.
- Existing CSV, XLSX, JSON, and HTML files are archived before replacement.
- Do not delete `outputs/_archive/`; it is the rollback history.

## Data recency fields

The generated outputs now surface recency metadata for:

- OpenCellID evidence
- Ookla evidence
- overall evidence age across the combined district row

If a source file does not include an explicit timestamp, the pipeline falls back to the source file modified time.

## Field feedback template

Use `FIELD_FEEDBACK_TEMPLATE.csv` to capture observed signal quality from the field.

Suggested usage:

- one row per village-provider observation
- record the date observed
- add a short note if the estimate and field reality differ
- keep the file structured so it can be ingested later

## Troubleshooting

- If a district shows no source rows, the issue is upstream source availability, not the pipeline.
- If a district shows tower files but no tower-backed evidence, try the shared tower pool fallback.
- If a map looks stale, rebuild the summary and the combined site after rerunning the district.
- If Excel locks a workbook, the pipeline writes a `_latest` fallback copy instead of failing the whole run.

## Recommended operating pattern

1. Pick one weak district.
2. Prefer districts that still have source rows.
3. Rerun the district.
4. Check the provider CSV, summary workbook, and HTML map.
5. Rebuild the requested-district status and summary.
6. Move to the next district only after the current one is verified.

