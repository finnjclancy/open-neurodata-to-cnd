# Complete ds004574 CND corpus

## Outcome

The complete OpenNeuro `ds004574` cross-modal oddball EEG dataset has been
converted locally using corpus recipe version 0.2.0.

| Measure | Result |
|---|---:|
| Planned recordings | 146 |
| Completed recordings | 146 |
| Failed recordings | 0 |
| Parkinson's disease group | 98 |
| Control group | 48 |
| Total samples | 55,877,200 |
| Total duration | 111,754.4 seconds (31.04 hours) |
| Source bytes represented by jobs | 14,468,170,746 |
| CND output bytes | 23,539,685,522 (21.92 GiB) |
| Output files | 292 |

The generated corpus is local and ignored by Git at `outputs/ds004574/0.2.0/`.
The code, corpus recipe, immutable job plan, tests, and this report are stored in
the repository.

## Signal variation covered

| Channels | Recordings |
|---:|---:|
| 63 | 116 |
| 64 | 29 |
| 66 | 1 |

All recordings use a 500 Hz source clock. Durations range from 318.3 seconds
(`sub-108`) to 1,394.08 seconds (`sub-025`). Every recording remains one
continuous CND trial; there is no epoching, resampling, filtering, rereferencing,
artifact rejection, padding, or truncation.

## Event features

| CND feature | Corpus count |
|---|---:|
| `precue_onset` | 34,797 |
| `go_arrow_onset` | 34,704 |
| `response_onset` | 33,925 |
| **Total impulses** | **103,426** |

Counts legitimately vary by recording. The converter preserves the explicit
BIDS events rather than requiring every precue, GO cue, and response count to be
equal. All event samples reconcile exactly with BIDS onset times; the maximum
observed timing error is 0 samples.

## Validation

Every one of the 146 independent releases passed:

- declared source-object checksum verification;
- planned channel, sampling-frequency, duration, and sample-count checks;
- strict CND 1.0 validation before writing;
- MATLAB v5 write and read-back;
- strict CND validation after reading;
- CND-to-MNE numerical comparison of the full neural matrix;
- exact stimulus-feature comparison;
- transactional publication.

There were zero strict-CND warnings, zero round-trip warnings, and zero invalid
manifests. A final audit independently rehashed all 292 generated files and
verified 23,539,685,522 bytes against the checksums in their manifests.

The corpus-level canonical scientific-content digest is:

```text
d13cd98fa4f56835a7d1d7665ccaacaf66da7d7fa0316b232bddcd57738c6831
```

This digest hashes each ordered recording identity and its representation-neutral
scientific-content digest. It does not depend on MATLAB header timestamps.

## Resilience demonstrated

The first full run completed 85 recordings before the NEMAR endpoint experienced
a read timeout followed by temporary DNS failures. Completed releases remained
intact, while failures were isolated to individual state files.

The downloader was then hardened with four attempts and exponential backoff.
The batch runner now stops after three consecutive transient network failures,
preventing an outage from misclassifying every remaining recording. The `retry`
command selected only the 61 affected states; all 61 subsequently completed
without touching the first 85 releases.

## Source cleanup

After each successful recording, its seven subject-specific BIDS files were
removed from the cache. Failed or interrupted jobs retained fully verified files
for reuse. At completion, the source cache contains only the two shared BIDS
metadata files—8 KB total. No bulk source EEG remains locally.

## Reproduce

```bash
uv sync --extra dev

uv run neurodata-to-cnd plan corpora/ds004574.json \
  --output plans/ds004574-v0.2.0.json

uv run neurodata-to-cnd batch plans/ds004574-v0.2.0.json \
  --pilot --cache-root cache/corpus-v0.2 --output-root outputs

uv run neurodata-to-cnd batch plans/ds004574-v0.2.0.json \
  --cache-root cache/corpus-v0.2 --output-root outputs

uv run neurodata-to-cnd retry plans/ds004574-v0.2.0.json \
  --cache-root cache/corpus-v0.2 --output-root outputs

uv run neurodata-to-cnd status outputs/ds004574/0.2.0
```
