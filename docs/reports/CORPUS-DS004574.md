# ds004574 corpus

OpenNeuro `ds004574` oddball EEG, converted locally with corpus recipe 0.2.0. This is not a public CND release.

| | |
|---|---:|
| planned | 146 |
| done | 146 |
| failed | 0 |
| Parkinson's group | 98 |
| control | 48 |
| samples | 55,877,200 |
| duration | 31.04 hours |
| source bytes | 14,468,170,746 |
| CND bytes | 21.92 GiB (292 files) |

Lives at `outputs/ds004574/0.2.0/` (gitignored).

## Signal

| Channels | Recordings |
|---:|---:|
| 63 | 116 |
| 64 | 29 |
| 66 | 1 |

All 500 Hz. Shortest is `sub-108` (318.3 s), longest `sub-025` (1,394.08 s). Each recording stays one CND trial. No filtering, resampling, rereferencing, artifact rejection, padding, or epoching.

## Events

| CND feature | Count |
|---|---:|
| `precue_onset` | 34,797 |
| `go_arrow_onset` | 34,704 |
| `response_onset` | 33,925 |
| **total** | **103,426** |

Counts differ by person, which is fine — we kept the BIDS events as they were. Timing error vs BIDS onsets: 0 samples.

## Checks

All 146 passed: source checksums, planned duration/channels/rate, strict CND before and after MATLAB write, CND-MNE numbers, impulse tracks, and the output folder only appeared after that.

Then I rehashed all 292 files (23,539,685,522 bytes) against the manifests. No warnings, no bad manifests.

Content hash of the whole corpus (who it is + array hash, not MATLAB headers):

```text
d13cd98fa4f56835a7d1d7665ccaacaf66da7d7fa0316b232bddcd57738c6831
```

## The first run died on the network

85 recordings finished, then NEMAR timed out and DNS went weird. The finished ones stayed. I retried the 61 failures after adding backoff; they completed without touching the first 85.

## Cache

After each success the seven subject BIDS files are deleted. Failed jobs keep the verified download so retry does not fetch again. At the end the cache is two shared metadata files, 8 KB. No bulk EEG left on disk.

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
