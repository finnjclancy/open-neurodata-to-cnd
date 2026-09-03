# Corpus conversion

Three files, in order:

1. **Corpus recipe** (`corpora/*.json`) — which remote inventory, which recordings, which experiment recipe(s)
2. **Plan** (`plans/*.json`) — one checksum-pinned job per recording. Generated, metadata only
3. **Batch** — download one recording, convert, validate, write to `outputs/`

The corpus layer does not invent event meanings. That stays in the experiment recipe. Multi-task jobs look like `sub-001_task-MMN` and pin their own recipe digest, so editing flankers does not silently change MMN.

```text
outputs/<corpus-id>/<corpus-version>/
├── recordings/sub-NNN/dataCND/   # dataSub*.mat + dataStim.mat
├── recordings/sub-NNN/manifest.json
├── state/sub-NNN.json
├── index.jsonl
└── summary.json
```

A recording directory only appears after source checksums, strict CND validation, MATLAB read-back, and CND-to-MNE numerical checks all pass.

## Restart

States: `pending`, `running`, `complete`, `failed`. If a process dies mid-job, the next `batch` reruns it. If a valid manifest is already there, the job is skipped. `retry` only picks up failures. One failure does not stop the rest.

## Source files

Planning only downloads inventory + small BIDS metadata. Conversion downloads one recording, checks it, then deletes the bulky source unless you pass `--keep-source`. Failed jobs keep verified cache files so retry does not fetch them again.

## Pilots

ds004574's pilot is picked from metadata: every channel count, both groups, shortest and longest recording. It is a structural smoke test, not a scientific sample. For ERP CORE, the pilot includes at least one recording from every task.

## Events and channels

A feature can match one `source_value` or a reviewed `source_values` list (e.g. several P3 letter codes → `target_onset`). The list is stored in the recipe.

`sample_index_origin` defaults to 0. ERP CORE needed `1`. Timing is still checked after that shift.

`eeg_only` keeps channels already typed as EEG and drops EOG. It does not relabel anything.
