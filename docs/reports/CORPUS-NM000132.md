# ERP CORE corpus

NEMAR `nm000132` ERP CORE v1.1.1, converted locally with corpus recipe 0.4.0. Not a public CND release.

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
| CND bytes | 13.41 GiB (480 MATLAB files) |

Lives at `outputs/nm000132/0.4.0/` (gitignored).

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

BIDS has 30 EEG + 3 EOG. Version 0.4.0 retains the three reviewed EOG channels
in CND `extChan`, with their source names, MNE channel types, explicit units and
MATLAB cell-group layout. They remain separate from the 30-channel EEG matrix.

## `events.tsv` counts from 1

If you treat the sample column as zero-based, every event is about 1.05 samples off. The first pilot failed all six tasks that way. Recipes now say `sample_index_origin: 1`. After that, the worst timing error in the full corpus is 0.00005 s (0.0512 sample). That shift is written in every manifest.

## Checks

All 240 passed: checksums, planned size/rate/duration, strict CND before and
after MATLAB write, CND-MNE numerical comparisons for EEG and EOG, channel
location round trips, and impulse tracks.

The completed corpus contains 139,146,240 EEG samples and 153,677 event
impulses. Its generated output is 14,392,778,346 bytes.

Content hash of the whole corpus:

```text
a8d604f2cc09c55fdb7afbc86973771c6142a4363930d772de015cf786814c68
```

## Cache

Subject/task sources are deleted after each success. Leftover cache is the dataset description plus six event dictionaries, 36 KB.

## Reproduce

```bash
uv run neurodata-to-cnd plan corpora/nm000132.json \
  --output plans/nm000132-v0.4.0.json

uv run neurodata-to-cnd batch plans/nm000132-v0.4.0.json \
  --pilot --cache-root cache/corpus-v0.4 --output-root outputs

uv run neurodata-to-cnd batch plans/nm000132-v0.4.0.json \
  --cache-root cache/corpus-v0.4 --output-root outputs

uv run neurodata-to-cnd status outputs/nm000132/0.4.0
```

## MATLAB compatibility

All 240 final outputs passed the configured MATLAB R2026a validation using
unchanged upstream CNSP and mTRF functions. The check performs 1–8 Hz filtering,
downsampling to 64 Hz, bad-channel detection/interpolation, average reference,
cross-validation and training on four analysis blocks, with the fifth held
out for prediction. The corrected driver uses ridge regularisation for both
parameter selection and final fitting. It uses all
declared stimulus features as separate predictors and removes only the idle tail
after the final event, retaining the 600 ms response window. All model weights
and reported correlations were finite. This is a compatibility check, not a
claim of scientific validity or predictive significance.

The corrected 20 September rerun is documented in
[GIOVANNI-FEEDBACK.md](GIOVANNI-FEEDBACK.md), with per-recording evidence in
[matlab-full-corpus-ridge](giovanni-validation/matlab-full-corpus-ridge/).
