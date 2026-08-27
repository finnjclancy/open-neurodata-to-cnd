# Architecture

## Objective

Build reproducible CND derivatives from public EEG, MEG, and selected iEEG datasets while preserving source provenance, licensing boundaries, experiment semantics, and validation evidence.

The project is intentionally split from the CND-MNE converter:

- **Open Neurodata to CND** discovers data, downloads sources, interprets experiments, extracts stimulus features, defines CND trials, runs conversions, and publishes corpora.
- **CND-MNE** owns CND parsing, writing, strict conformance checks, and CND-to-MNE interoperability.

## Processing model

```text
catalogue entry
    │
    ▼
source resolver ───────────────► immutable source cache
    │                               │
    ▼                               │
signal loader ◄─────────────────────┘
    │
    ├──► event parser
    ├──► stimulus resolver
    └──► participant/task metadata
            │
            ▼
      dataset recipe
            │
            ├──► trial builder
            ├──► feature plug-ins
            ├──► synchronization policy
            └──► resampling/unit policy
                    │
                    ▼
              CND package writer
                    │
                    ▼
       strict validation + round trip
                    │
                    ▼
          immutable object-store release
                    │
                    ▼
       index + checksums + provenance manifest
```

## Core objects

### Catalogue entry

A stable description of a source dataset. It records identity, source, modality, access, license, scale, structure, and conversion priority. It must not contain conversion decisions that change between processing versions.

### Conversion recipe

A versioned declaration of scientific and technical choices for one dataset:

- source snapshot and files selected;
- raw versus derivative signals;
- modality and channel selection;
- unit policy;
- CND trial boundaries;
- stimulus features;
- trigger corrections and synchronization;
- output sampling rate;
- participant/session/task/run filters;
- exclusions and known limitations.

Recipes are reviewed scientific artifacts. Silent inference is not permitted when a choice changes the interpretation of the experiment.

### Converter plug-in

Reusable code belongs to one of four interfaces:

1. **Source adapter:** resolves and downloads OpenNeuro, NEMAR, OSF, PhysioNet, DataLad, or custom archives.
2. **Signal adapter:** returns a standardized MNE object plus source metadata from BIDS, EDF, BrainVision, CTF, EEGLAB, MATLAB, NumPy, or other formats.
3. **Feature adapter:** creates synchronized continuous or impulse stimulus features from audio, video, images, text, events, eye tracking, or clinical annotations.
4. **Trial adapter:** maps source runs/blocks/events into CND trials and records every boundary decision.

Dataset names must not be hard-coded into generic adapters. Dataset-specific behavior belongs in recipes or narrowly scoped recipe helpers.

### Release manifest

Every generated corpus has a machine-readable manifest recording:

- source dataset and version;
- recipe and converter Git commit;
- environment or container digest;
- input and output checksums;
- subjects, sessions, tasks, runs, trials, features, channels, durations, and sizes;
- validation results and warnings;
- output object-store locations;
- neural and stimulus licenses;
- known limitations.

## Workflow stages

1. **Discover:** add and validate a catalogue entry.
2. **Qualify:** verify access, licenses, event completeness, stimuli, and CND suitability.
3. **Sample:** download one small subject/session/run and inspect it manually.
4. **Specify:** create a reviewed conversion recipe.
5. **Convert fixture:** build a tiny deterministic CND fixture and add tests.
6. **Pilot:** convert one complete participant and review features and synchronization.
7. **Batch:** process subjects independently with resumable jobs.
8. **Validate:** run strict CND checks, source/output reconciliation, and CND-to-MNE round trips.
9. **Publish:** upload immutable objects, then write the final manifest and catalogue status.
10. **Monitor:** detect upstream dataset revisions and mark stale derivatives.

## Batch execution

The natural unit of work is one source recording or one participant/session/task/run group. Each job must be:

- deterministic;
- independently retryable;
- idempotent;
- bounded in memory and local disk;
- safe to execute concurrently;
- able to resume from verified outputs;
- unable to publish until validation passes.

Large conversions should run on HPC, cloud batch, or local workstations against object storage. GitHub Actions should validate metadata and small fixtures only.

## Validation gates

### Source gate

- source version is pinned;
- all expected files are present and checksummed;
- source-level BIDS or format validation passes;
- access and redistribution rules are recorded.

### Semantic gate

- trial boundaries are documented;
- neural/stimulus synchronization is demonstrated;
- feature names, units, axes, and sampling rates are documented;
- no copyrighted stimulus is embedded without permission;
- no unsupported inference is hidden in code.

### CND gate

- CND 1.0 strict validation passes for new output;
- neural and stimulus sampling rates satisfy the chosen policy;
- feature and neural trial counts agree;
- lengths and durations reconcile within documented tolerances;
- units and channel metadata are explicit;
- CND-to-MNE loading succeeds;
- numerical checks pass on sampled round trips.

### Publication gate

- all files have SHA-256 checksums;
- the release is immutable;
- the manifest points to exact object versions;
- catalogue status and output index are updated atomically;
- failed or partial outputs are not visible as complete releases.

## First implementation slice

The recommended first vertical slice is `ds006434`:

1. download a single participant and one run;
2. load the BIDS EEG through MNE-BIDS;
3. select the cortical 1 kHz representation;
4. create attended and unattended speech envelopes plus trial/attention metadata;
5. define one source trial as one CND trial;
6. write a strict CND 1.0 package;
7. load it with CND-MNE and compare channels, samples, events, and feature timing;
8. publish only the tiny fixture until the recipe is scientifically reviewed.

Once this passes, scale to the full dataset and then reuse the auditory feature adapters for `ds007808`, MEG-MASC, and MEG-SCANS.
