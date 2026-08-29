# Resumable corpus conversion

## Contracts

The corpus layer separates three concerns:

1. A **corpus recipe** identifies one immutable remote inventory and defines how
   recordings are discovered.
2. A generated **plan** expands the inventory into independent, checksum-pinned
   jobs while downloading only small metadata files.
3. **Batch execution** instantiates the reviewed experiment recipe for each job,
   validates the result, and maintains a corpus index.

Experiment meaning remains in the conversion recipe. The corpus layer changes
subject-relative paths and provenance; it does not infer new event semantics.

## Output layout

```text
outputs/<corpus-id>/<corpus-version>/
├── recordings/
│   └── sub-NNN/
│       ├── dataCND/
│       │   ├── dataSubNNN.mat
│       │   └── dataStim.mat
│       └── manifest.json
├── state/
│   └── sub-NNN.json
├── index.jsonl
└── summary.json
```

Each recording is built in a staging directory. Its final directory appears
only after source reconciliation, strict CND validation, MATLAB read-back,
CND-to-MNE numerical comparison, and exact stimulus-feature comparison pass.

## State and restart behavior

States are `pending`, `running`, `complete`, or `failed`. A process interruption
may leave a job marked `running`; the next batch invocation safely reruns it.
If a validated manifest exists, it is reconciled into `complete` state and the
job is skipped. A state that claims completion while its manifest is absent is
treated as corruption rather than silently rerun.

`retry` selects failed jobs only. Attempts and full local tracebacks are retained
in state files for diagnosis. A failed job does not prevent subsequent jobs from
running.

## Source lifecycle

Planning retrieves only the inventory, `participants.tsv`, and recording-level
EEG JSON sidecars. During conversion, one job's declared BIDS snapshot is
downloaded and verified. After successful publication, subject-specific source
files are deleted from the cache; tiny shared BIDS metadata remains for reuse.

Failed and interrupted jobs retain any fully verified cached files so retry does
not redownload them. Partial downloads use temporary names and are removed by
the atomic downloader.

Use `--keep-source` only when an audit or repeated development run requires the
original files to remain cached.

## Pilot policy

The ds004574 pilot is selected deterministically from metadata and covers:

- every declared channel count;
- both participant groups;
- the shortest recording;
- the longest recording.

This is a structural gate before full-corpus execution, not a scientific sample.
