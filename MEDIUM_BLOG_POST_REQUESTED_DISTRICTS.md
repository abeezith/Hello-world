# From Patchy Rural Data to a Usable Village Connectivity Map: Building a District-by-District Mobile Network Pipeline for India

When people talk about digital inclusion, rural service delivery, or last-mile health systems, connectivity usually appears as a background assumption. A team is expected to report through an app, sync beneficiary records, upload a photo, join a training call, or send a WhatsApp update. But on the ground, that assumption often breaks first.

That was the starting point for this project.

I wanted a practical way to estimate village-level mobile connectivity for India, while keeping the workflow manageable enough to run one district at a time. The goal was not to build a perfect telecom engineering model. The goal was to build something decision-useful: a pipeline that could take village lists, fill missing coordinates, combine tower evidence with mobile speed evidence, and produce outputs that people could actually use in planning conversations.

The result is a Python-based village connectivity pipeline that produces provider-wise coverage estimates, spreadsheet summaries, GeoJSON outputs, and an interactive map. It started with Koraput in Odisha, but the workflow was later adapted to support a larger set of requested districts across multiple states.

## The practical problem

Many program teams already have village names in Excel sheets. What they usually do not have is a reliable way to answer questions like:

- Which villages appear to have at least some usable mobile coverage?
- Which provider is more likely to be available nearby?
- Which places should be treated as higher risk for app-based workflows?
- Where should field operations plan for offline-first data capture?

This becomes especially important for public health, community programs, surveys, tele-support, and any operational model that depends on field staff using mobile devices.

The difficulty is that no single dataset answers this cleanly.

- Village lists may be incomplete or inconsistently spelled.
- Latitude and longitude may be missing.
- OpenCellID tower data is useful but crowd-sourced and incomplete.
- Ookla open data gives mobile performance context, but not always in a provider-specific way.
- Historical telecom operator codes can introduce noise unless they are normalized carefully.

So the problem was really an integration problem.

## What the pipeline does

At a high level, the pipeline takes an input table of villages with these columns:

`state, district, block, village, lgd_code, latitude, longitude`

It then performs the following steps:

1. Fill missing coordinates using LGD or village master data.
2. Load or query OpenCellID tower data.
3. Find towers within a configurable radius of each village centroid.
4. Map MCC/MNC combinations to Indian operators.
5. Estimate nearest-tower distance by provider.
6. Join Ookla mobile open data tiles as supplemental evidence.
7. Produce a provider-wise coverage score for each village:
   `Strong`, `Moderate`, `Weak`, or `Unknown`.
8. Export usable outputs:
   - `village_provider_signal_estimate.csv`
   - `village_connectivity_summary.xlsx`
   - GeoJSON for map use
   - interactive HTML maps

The stack is intentionally simple and familiar: `pandas`, `geopandas`, `shapely`, `pyproj`, `requests`, and `openpyxl`, with configuration kept in `config.yaml`.

## Why district-by-district matters

One of the early design choices was to avoid pretending that “all-India at once” is the most practical execution mode.

India is simply too large and too messy for that to be the best default workflow when the source data itself is uneven. A district-by-district pipeline is slower in ambition, but faster in practice. It gives you:

- smaller files
- faster reruns
- more targeted geocoding and QC
- lower API cost and lower token cost
- easier debugging when village names or blocks are inconsistent

In other words, it is a better operational unit of work.

That design decision turned out to matter a lot when the workflow expanded beyond Koraput to requested districts across Andhra Pradesh, Jharkhand, Odisha, and Telangana.

## What was built beyond Koraput

After the original Koraput-focused pipeline was working, I extended the workflow to enrich a list of requested districts using available screening data and GPS traces.

In the current batch:

- `14` districts were requested
- `9` were present in the available source screening data
- `10,605` screening rows were processed
- `702` distinct village records were generated
- `447` of those villages had GPS-derived centroids usable for mapping

The districts successfully processed in this run were:

- Andhra Pradesh: Alluri Sitarama Raju, Parvathipuram Manyam
- Jharkhand: Dumka, Pakur, Sahibganj
- Odisha: Koraput, Malkangiri, Nabarangapur
- Telangana: Bhadradri Kothagudem

The requested districts that were not present in the available source file were:

- Karnataka: Bidar
- Madhya Pradesh: Barwani, Dhar, Khargone
- Telangana: Adilabad

That is an important lesson in itself: often the bottleneck is not computation, but source availability and source quality.

## The map was not the end product. It was the conversation tool.

One of the most useful parts of the project was the map.

At first, the map displayed provider-specific symbols in a more conventional way. But that quickly became cluttered, especially when villages were close together. The visual design had to become simpler:

- one compact box per village
- only current operators shown
- one letter per provider:
  `A`, `B`, `J`, `V`
- color determined by signal category
- hover showing only the village name
- click opening fuller provider details

That sounds like a small design decision, but it made the output much more usable. A map that tries to say everything at once usually says nothing clearly.

Later, I merged the outputs into a single combined page with state and district selectors, so users no longer had to open separate HTML files district by district. That turned the deliverable from a technical export into something closer to a field-planning interface.

## What this is useful for

I see at least five concrete use cases for this kind of pipeline.

### 1. Planning field operations

If a district team knows which villages are more likely to have weak or uncertain connectivity, they can design better workflows:

- offline data capture first
- scheduled sync windows
- network fallback plans
- different app expectations by geography

### 2. Public health and community programs

Programs that rely on mobile data entry, referral tracking, tele-support, or remote supervision can use this as a risk layer. It helps answer where digital workflows may fail not because of staff effort, but because of infrastructure reality.

### 3. Prioritizing telecom verification

A village flagged as `Unknown` is not necessarily uncovered. It may simply be under-observed in the data. That makes the output a good shortlist for ground-truthing, not a final verdict.

### 4. Better targeting of digital inclusion investments

This kind of map can support discussions around:

- device strategy
- offline-first app design
- connectivity subsidies
- booster requirements
- location prioritization for network strengthening

### 5. Making fragmented data more actionable

The biggest value may be that it brings together multiple incomplete datasets into one operational view. In many real-world settings, “good enough to guide the next decision” is far more useful than waiting for perfect data.

## What I learned while building it

### First, data integration is the real work

The code was important, but the harder part was making heterogeneous sources talk to each other:

- village spellings
- block aliases
- partial coordinates
- missing provider context
- old operator codes that should no longer appear

Much of the usefulness came from patient normalization rather than clever modeling.

### Second, historical telecom data needs policy decisions

Seeing names like Aircel or Tata Docomo in outputs is technically possible when historical or legacy identifiers are still present in raw telecom-related data. But showing them in a present-day operational map is often misleading.

So the pipeline was explicitly patched to show only current operators:

- Airtel
- BSNL
- Jio
- Vodafone Idea

Legacy codes were either suppressed or reassigned where there was a reasonable operational mapping.

This was not just cleanup. It was a reminder that data products need policy choices, not only transformations.

### Third, map usability matters as much as model logic

A technically correct output can still fail if users cannot read it quickly.

The move from overlapping shapes to a single village box with color-coded letters made the whole output calmer and easier to interpret. That is a small example of a broader truth: when the audience is operational, readability is part of rigor.

### Fourth, speed matters when iteration is the real workflow

This project became much more useful after it was optimized for repeated reruns:

- cached OpenCellID extent pulls
- slimmer HTML payloads
- district-wise subsets instead of giant files
- a fast rerun path for rebuilding outputs after code changes

Optimization was not just about runtime. It was also about reducing friction, reducing token burn, and making it realistic to keep improving the outputs.

## Important limitations

This pipeline is helpful, but it should not be oversold.

- OpenCellID is crowd-sourced and incomplete.
- Tower presence does not equal reliable user experience.
- Ookla evidence is supplemental and may not always be provider-specific.
- A village marked `Unknown` may simply be poorly observed in the available data.
- Provider-wise scoring here is heuristic, not a formal RF propagation model.
- Villages without usable coordinates cannot be mapped until geocoding improves.

So this should be treated as a planning and prioritization layer, not as a regulatory coverage map.

## Why I still think this is worth doing

Because operational reality is usually decided in imperfect conditions.

Field teams do not need a PhD-grade telecom model before they change how they sync an app, plan a visit, or decide which villages need extra support. They need a sensible, transparent estimate built from whatever evidence is available today.

That is what this project tries to provide.

It does not eliminate uncertainty. It makes uncertainty more visible and more structured.

And that, in itself, is useful.

## Way forward

There are several natural next steps that could make this much stronger.

### 1. Expand district coverage with better source inputs

The current requested-district workflow could process only the districts present in the source screening file. The next obvious step is to bring in additional district-level village sources so the remaining districts can be added cleanly.

### 2. Improve village matching and geocoding recovery

A stronger fuzzy matching and alias strategy would recover more unresolved villages, especially where GPS is missing but nearby variants exist in block-level source data or LGD master data.

### 3. Add time-awareness

Tower observations and Ookla performance both age over time. A future version should show data currency clearly and allow quarter-wise or period-wise comparison.

### 4. Add validation loops

Ground-truth feedback from field staff could be folded back into the model:

- works reliably
- works partially
- only one operator works
- no usable signal

That would make the scoring progressively more realistic.

### 5. Move toward a reusable national workflow

The long-term opportunity is a repeatable India workflow that:

- ingests one district at a time
- caches reusable tower and tile subsets
- standardizes village matching
- outputs a combined national browsing surface
- supports periodic refreshes with minimal manual work

That would make this not just a one-off project, but a reusable public-interest data product.

## Closing reflection

What I like most about this project is that it sits at the boundary between technical work and practical decision-making.

It uses code, geospatial joins, and configuration files. But its value is not in technical elegance alone. Its value is in helping someone ask a better question before sending a field worker into a village with a mobile-first plan that may not actually work there.

That is the kind of data work I find meaningful: not perfect, not final, but useful enough to change how decisions are made.

If you are working on public systems, rural delivery, digital health, last-mile operations, or telecom-informed planning, this kind of district-wise connectivity estimation can be a very pragmatic addition to your toolkit.

## Project note

This workflow was built in Python using `pandas`, `geopandas`, `shapely`, `pyproj`, `requests`, and `openpyxl`, with configuration managed through `config.yaml`. The current implementation lives in:

- [README.md](E:/Resources/SecondBrain/koraput_connectivity_pipeline/README.md)
- [run_pipeline.py](E:/Resources/SecondBrain/koraput_connectivity_pipeline/run_pipeline.py)
- [generate_provider_map.py](E:/Resources/SecondBrain/koraput_connectivity_pipeline/generate_provider_map.py)
- [generate_requested_districts_site.py](E:/Resources/SecondBrain/koraput_connectivity_pipeline/generate_requested_districts_site.py)
- [enrich_requested_districts_from_stoptb.py](E:/Resources/SecondBrain/koraput_connectivity_pipeline/enrich_requested_districts_from_stoptb.py)

If needed, this draft can easily be adapted into:

- a shorter LinkedIn article
- a more technical engineering write-up
- a project README narrative
- a donor or program-facing concept note
