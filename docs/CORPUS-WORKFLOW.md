# Corpus conversion

Three files, in order:

1. **Corpus recipe** (`corpora/*.json`) — which inventory, which recordings, which experiment recipe(s)
2. **Plan** (`plans/*.json`) — one checksum-pinned job per recording. Generated, metadata only
3. **Batch** — download, convert, validate, write to `outputs/`

Event meanings stay in the experiment recipe, not here. Multi-task jobs look like `sub-001_task-MMN` and pin their own recipe hash, so editing flankers does not silently change MMN.

```text
outputs/<corpus-id>/<corpus-version>/
├── recordings/sub-NNN/dataCND/   # dataSub*.mat + dataStim.mat
├── recordings/sub-NNN/manifest.json
├── state/sub-NNN.json
├── index.jsonl
└── summary.json
```

A recording folder only shows up after checksums, strict CND, MATLAB read-back, and CND-to-MNE number checks all pass.

## Restart

States: `pending`, `running`, `complete`, `failed`. If the process dies mid-job, the next `batch` runs it again. If a valid manifest is already there, it is skipped. `retry` only picks up failures. One failure does not stop the rest.

## Source files

Planning only fetches the inventory plus small BIDS metadata. Conversion downloads one recording, checks it, then deletes the bulky source unless you pass `--keep-source`. Failed jobs keep the verified cache so retry does not download twice.

## Pilots

ds004574's pilot is picked from metadata: every channel count, both groups, shortest and longest. It is a smoke test, not a scientific sample. For ERP CORE, the pilot includes at least one recording from every task.

## Events and channels

A feature can match one `source_value` or a list (`source_values`), e.g. several P3 letter codes → `target_onset`. That list lives in the recipe.

`sample_index_origin` defaults to 0. ERP CORE needed `1`. Timing is still checked after the shift.

`eeg_only` keeps channels already typed as EEG and drops EOG. It does not relabel anything.
