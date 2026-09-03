# ERP CORE corpus

NEMAR `nm000132` ERP CORE v1.1.1, converted locally with corpus recipe 0.3.0. Not a public CND release.

| | |
|---|---:|
| people | 40 |
| tasks each | 6 |
| planned | 240 |
| done | 240 |
| failed | 0 |
| EEG channels | 30 |
| samples | 139,146,240 |
| duration | 37.75 hours |
| event impulses | 153,677 |
| source bytes | 18,719,829,517 |
| CND bytes | 12.02 GiB (480 MATLAB files) |

Lives at `outputs/nm000132/0.3.0/` (gitignored).

## Tasks

| Task | Recordings | Duration (s) | Event features |
|---|---:|---:|---|
| MMN | 40 | 24,221 | context standards, standards, deviants |
| N170 | 40 | 23,613 | faces, cars, scrambled, responses |
| N2pc | 40 | 24,116 | left/right targets, correct/incorrect |
| N400 | 40 | 17,691 | related/unrelated primes and targets, responses |
| P3 | 40 | 15,359 | targets, non-targets, responses |
| Flankers | 40 | 30,885 | congruent/incongruent left/right, responses |

All 1024 Hz. Shortest `sub-006_task-P3` (328 s), longest `sub-008_task-flankers` (1,049 s). One CND trial per recording. No filtering, resampling, rereferencing, artifact rejection, epoching, padding.

BIDS has 30 EEG + 3 EOG. We kept the 30 EEG (`eeg_only`) and dropped EOG rather than relabelling them.

## `events.tsv` counts from 1

If you treat the sample column as zero-based, every event is about 1.05 samples off. The first pilot failed all six tasks that way. Recipes now say `sample_index_origin: 1`. After that, the worst timing error in the full corpus is 0.00005 s (0.0512 sample). That shift is written in every manifest.

## Checks

All 240 passed: checksums, planned size/rate/duration, strict CND before and after MATLAB write, CND-MNE numbers on the 30-channel matrix, impulse tracks.

Rehashed all 480 MATLAB files (12,908,616,770 bytes) against the manifests. No warnings.

Content hash of the whole corpus:

```text
87002049c5850116f3fa064201f37ae8a8d0fdec79c31a22e91fab46632c03c6
```

## Cache

Subject/task sources are deleted after each success. Leftover cache is the dataset description plus six event dictionaries, 36 KB.

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
