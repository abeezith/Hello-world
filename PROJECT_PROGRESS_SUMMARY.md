# Koraput Connectivity Pipeline Progress Summary

Date: 2026-07-13

## 1. What This Project Is Doing

This pipeline enriches village-level connectivity records for requested Indian districts using:

- LGD / village master matching for missing coordinates
- OpenCellID India tower data
- Ookla mobile open data tiles where available
- provider normalization for current Indian operators
- district-level map and summary outputs

The workflow is designed to run one district at a time, preserve prior runs, and avoid losing earlier outputs. It also produces a combined site for browsing all requested districts in one place.

## 2. Core Inputs And Outputs

### Main input shape

The source village file expects columns similar to:

- `state`
- `district`
- `block`
- `village`
- `lgd_code`
- `latitude`
- `longitude`

### Main outputs

The pipeline now writes:

- `outputs/requested_districts/requested_district_rows_enriched.csv`
- `outputs/requested_districts/requested_district_status.csv`
- `outputs/requested_districts/requested_district_status.md`
- `outputs/requested_districts/requested_district_status.json`
- `outputs/requested_districts/requested_district_summary.csv`
- `outputs/requested_districts/requested_district_summary.json`
- per-district files under `outputs/requested_districts/<state>__<district>/outputs/`
- combined browsing site at `outputs/requested_districts_site/index.html`

Per district, the key artifacts are:

- `village_provider_signal_estimate.csv`
- `village_connectivity_summary.xlsx`
- `village_connectivity.geojson`
- `village_connectivity_map.html`

## 3. Major Code And Workflow Changes

### A. Enrichment pipeline improvements

The main enrichment flow in `enrich_requested_districts_from_stoptb.py` was extended to:

- preserve full district village rows instead of dropping columns
- annotate orphan-like or proxy-like records
- generate map and provider outputs per district
- reuse earlier district outputs where possible
- archive existing district directories before overwrite

### B. Shared tower pool fallback

One of the most important improvements was the shared OpenCellID tower pool strategy:

- district-specific tower fetches can fail or produce no tower evidence
- when that happens, the pipeline can build and reuse a shared pool from other districts
- the fallback uses a wider search radius for pooled towers
- this helped recover coverage in districts that otherwise remained empty or weak

This was especially important for districts with source rows but poor local tower evidence.

### C. Current-operator filtering

The mapping layer was tightened so the map and provider logic focus on current operators:

- Airtel
- Jio
- BSNL
- Vodafone Idea

Legacy / deprecated codes are suppressed or remapped so the map does not overstate inactive providers.

### D. Status and summary reporting

The reporting scripts were improved to expose:

- district status
- confidence level
- source row counts
- whether tower enrichment exists
- whether OpenCellID data exists

The summary rebuild step now keeps the district-level site in sync with the latest rerun.

### E. Safety and versioning

To reduce the risk of losing prior work:

- existing district trees are archived before replacement
- the config file was backed up before tuning the shared-pool search radius

Backup created:

- `E:\Resources\SecondBrain\koraput_connectivity_pipeline\config.yaml.bak-20260713-1`

## 4. District Progress So Far

Current requested district totals:

- 27 requested districts in the status table
- 27 districts present in the summary table

Current status counts:

- `completed_tower_enriched`: 8
- `fallback_tower_enriched`: 4
- `fetched_no_tower_evidence`: 2
- `fallback_no_tower_evidence`: 13

### Districts that now have real tower enrichment

Examples that were verified during the run:

- `Jharkhand / Sahibganj`
- `Odisha / Nabarangapur`
- `Odisha / Koraput`
- `Jharkhand / Dumka`
- `Andhra Pradesh / Alluri Sita Ramaraju`
- `Andhra Pradesh / Parvathipuram`

These districts now have usable `village_provider_signal_estimate.csv` outputs with tower-linked evidence in at least part of the district.

### Districts that still have no tower evidence

The remaining weak districts fall into two groups:

#### No source rows at all

These are still `fallback_no_tower_evidence` and currently cannot be enriched from the existing requested source set:

- Gujarat / The Dangs
- Gujarat / Valsad
- Karnataka / Bidar
- Karnataka / Raichur
- Madhya Pradesh / Barwani
- Madhya Pradesh / Dhar
- Madhya Pradesh / Khargone (West Nimar)
- Maharashtra / Nandurbar
- Maharashtra / Nashik
- Rajasthan / Banswara
- Rajasthan / Dungarpur
- Rajasthan / Pratapgarh
- Telangana / Adilabad

#### Very small source set, but still weak

These have source rows but still need more evidence or a better fallback path:

- Maharashtra / Dhule
- Telangana / Bhadradri Kothagudem

## 5. Notable District Case Notes

### Sahibganj

This was a successful district-level enrichment pass. It now shows:

- `completed_tower_enriched`
- `high` confidence
- tower evidence present in the provider CSV
- updated summary output after rebuild

### Nabarangapur

This district initially stayed weak, but after widening the shared-pool fallback radius and rerunning it, the district now shows:

- `completed_tower_enriched`
- `high` confidence
- tower evidence present in the district provider file

### Malkangiri

This district was a useful earlier proof point for the shared tower pool strategy. It showed that a district with weak or missing local evidence can still gain usable provider-level signal estimates once pooled OpenCellID towers are allowed into the search.

## 6. Files Updated Or Added During The Work

### Scripts and config

- `E:\Resources\SecondBrain\koraput_connectivity_pipeline\enrich_requested_districts_from_stoptb.py`
- `E:\Resources\SecondBrain\koraput_connectivity_pipeline\generate_provider_map.py`
- `E:\Resources\SecondBrain\koraput_connectivity_pipeline\generate_requested_districts_site.py`
- `E:\Resources\SecondBrain\koraput_connectivity_pipeline\report_requested_district_status.py`
- `E:\Resources\SecondBrain\koraput_connectivity_pipeline\rebuild_requested_district_summary.py`
- `E:\Resources\SecondBrain\koraput_connectivity_pipeline\archive_utils.py`
- `E:\Resources\SecondBrain\koraput_connectivity_pipeline\config.yaml`

### New summary file

- `E:\Resources\SecondBrain\koraput_connectivity_pipeline\PROJECT_PROGRESS_SUMMARY.md`

## 7. How The Current Process Works

The current recommended district-by-district loop is:

1. Pick one district with remaining weakness.
2. Prefer a district that has actual source rows.
3. Run the single-district enrichment script.
4. Use the shared OpenCellID pool if the district fetch is weak.
5. Rebuild the district summary.
6. Verify the provider CSV and the map output.
7. Move to the next weak district only after the current one is checked.

This keeps the work controlled and makes it easier to see whether a district failed because of data coverage, source sparsity, or a code-path issue.

## 8. Practical Limitations Observed

- Some districts have no source rows at all, so there is nothing meaningful to enrich yet.
- Some districts have very sparse rows and remain weak even after fallback logic.
- OpenCellID tower coverage is uneven by geography, so tower evidence is not guaranteed.
- Provider labels and signal scores should be treated as estimates, not ground truth.

## 9. Recommended Next Steps

If continuing the district run:

- handle `Maharashtra / Dhule` and `Telangana / Bhadradri Kothagudem` next, since they still have source rows
- leave the zero-row fallback districts for a separate source-acquisition pass
- keep the archived district trees intact before any overwrite
- rebuild the requested district summary after each successful district run

## 10. Bottom Line

The pipeline is now in a much safer and more useful state:

- it preserves old outputs before overwriting
- it can recover signal evidence from shared tower pools
- it produces a clean district browsing site
- it has already converted several weak districts into usable tower-enriched outputs
- the remaining weak districts are now clearly separated between "no source rows" and "needs a better enrichment path"

