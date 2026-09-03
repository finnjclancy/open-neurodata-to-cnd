# ERP CORE corpus

NEMAR `nm000132` ERP CORE v1.1.1, converted locally with corpus recipe 0.3.0. Not a public catalogue release.

| Measure | Result |
|---|---:|
| Participants | 40 |
| Paradigms per participant | 6 |
| Planned recordings | 240 |
| Completed recordings | 240 |
| Failed recordings | 0 |
| EEG channels per recording | 30 |
| Total samples | 139,146,240 |
| Total duration | 135,885 seconds (37.75 hours) |
| Reviewed event impulses | 153,677 |
| Source bytes represented by jobs | 18,719,829,517 |
| CND output bytes | 12,908,616,770 (12.02 GiB) |
| CND MATLAB files | 480 |

The generated corpus is local and ignored by Git at `outputs/nm000132/0.3.0/`.
The code, six experiment recipes, corpus recipe, immutable 240-job plan, tests,
and this report are stored in the repository.

## Experiment coverage

| Task | Recordings | Duration (s) | Reviewed event features |
|---|---:|---:|---|
| MMN | 40 | 24,221 | Context standards, standards, deviants |
| N170 | 40 | 23,613 | Faces, cars, scrambled controls, responses |
| N2pc | 40 | 24,116 | Left/right targets, correct/incorrect responses |
| N400 | 40 | 17,691 | Related/unrelated primes and targets, responses |
| P3 | 40 | 15,359 | Targets, non-targets, responses |
| Flankers | 40 | 30,885 | Congruent/incongruent left/right stimuli, responses |

All recordings use a 1024 Hz source clock. Durations range from 328 seconds
(`sub-006_task-P3`) to 1,049 seconds (`sub-008_task-flankers`). Each recording
remains one continuous CND trial. There is no filtering, resampling,
rereferencing, artifact rejection, epoching, padding, or truncation.

Each BIDS source contains 30 EEG and three EOG channels. The reviewed
`eeg_only` policy preserves the 30 EEG channels in CND and excludes the EOG
channels rather than relabelling them as EEG.

## Format-specific finding

The release's `events.tsv` sample values are effectively one-based. Treating
them as zero-based produced a consistent 1.0512-sample disagreement with the
rounded onset timestamps, and the first pilot attempt correctly rejected all
six recordings.

The recipes now explicitly declare `sample_index_origin: 1`. After subtracting
that origin, the maximum observed event-timing discrepancy across the complete
corpus is 0.00005 seconds, or 0.0512 sample. This transformation is recorded in
every manifest; it is not an implicit correction.

## Validation

Every one of the 240 independent releases passed:

- source-object SHA-256 or Git-blob checksum verification;
- planned channel, sampling-frequency, duration, and sample-count checks;
- strict CND 1.0 validation before writing;
- MATLAB v5 write and read-back;
- strict CND validation after reading;
- CND-to-MNE numerical comparison of the full 30-channel neural matrix;
- exact stimulus-feature comparison;
- transactional publication.

There were zero strict-CND warnings, zero round-trip warnings, and 240 unique
release IDs. A separate final audit independently rehashed all 480 generated
MATLAB files and verified all 12,908,616,770 bytes against their manifests.

The corpus-level canonical scientific-content digest is:

```text
87002049c5850116f3fa064201f37ae8a8d0fdec79c31a22e91fab46632c03c6
```

## Source cleanup

After each successful recording, its subject/task source files were removed
from the cache. The final ERP CORE source cache contains only the dataset
description and six task event dictionaries—36 KB total. No bulk source EEG
remains locally.

## Reproduce

```bash
uv run neurodata-to-cnd plan corpora/nm000132.json \
  --output plans/nm000132-v0.3.0.json

uv run neurodata-to-cnd batch plans/nm000132-v0.3.0.json \
  --pilot --cache-root cache/corpus-v0.3 --output-root outputs

uv run neurodata-to-cnd batch plans/nm000132-v0.3.0.json \
  --cache-root cache/corpus-v0.3 --output-root outputs

uv run neurodata-to-cnd status outputs/nm000132/0.3.0
```
