# ds004574 — one recording

OpenNeuro `ds004574` v1.0.0, subject 001, oddball. This is the fixture that was used before converting the whole 146-recording corpus.

- **Input:** EEGLAB `.set`/`.fdt` plus seven BIDS metadata/event files
- **Licence:** CC0
- **Pinned source size:** 105,265,313 bytes
- **Source snapshot SHA-256:** `21fb996b5f6d6b2bd65d196ad90610c2a6771b920397f7c3cf547b009b1710d4`

Every constituent file has its own SHA-256 in
[`recipes/ds004574-sub001-oddball.json`](../recipes/ds004574-sub001-oddball.json).
Metadata URLs are pinned to repository commit
`b7c69a16695968de78a3d1f1277654cc85884261`; the two large signal files are
content-pinned by checksum.

## CND representation

The complete 816.2-second recording remains one CND trial: 408,100 samples by
63 EEG channels at 500 Hz. The BIDS `sample` column is the authoritative event
index and is reconciled against `onset`. Three explicit `value` mappings become
one-sample binary features:

| CND feature | BIDS value | Count | Meaning |
|---|---:|---:|---|
| `precue_onset` | `S  1` | 236 | Simultaneous visual and auditory precue |
| `go_arrow_onset` | `S  2` | 236 | Directional GO arrow |
| `response_onset` | `S  3` | 236 | Participant response marker |

The source `channels.tsv` lists every channel type as `n/a`, even though the EEG sidecar says 63 EEG channels and all 63 have coordinates. The recipe therefore has an explicit `all_eeg` correction, with the evidence attached. The reader refuses that correction if the evidence field is missing.

## What we did not do

- no filtering or rereferencing
- no resampling
- no artifact rejection
- no epoching, padding, or truncation
- no fuzzy event-name matching
- no embedded stimulus media

EEGLAB values loaded by MNE are in volts, and the CND we wrote records volts.

## Validation result

| Gate | Result |
|---|---|
| Nine source-file checksums | Pass |
| Multi-file snapshot digest | Pass |
| Reviewed sampling frequency, 500 Hz | Pass |
| BIDS sample/onset reconciliation | Pass; maximum error 0 samples |
| Strict CND 1.0 before and after writing | Pass |
| CND-to-MNE neural numerical comparison | Pass |
| Stimulus impulse exact comparison | Pass |

The content hash (arrays only, ignoring MATLAB header timestamps) is
`e5b901ad9bf0e5b20c1f51b3617d2664c8925498a2c9870a5f7d110ac960b399`.
Local MATLAB v5 output is about 164 MiB of neural data and 12 KiB of stimulus features. Not in git.

## Reproduce

```bash
uv sync --extra dev
uv run neurodata-to-cnd convert recipes/ds004574-sub001-oddball.json \
  --cache-root cache \
  --output-root outputs
```

The public pytest is opt-in because it downloads about 105 MB and writes about 164 MiB of CND:

```bash
RUN_LARGE_PUBLIC_DATA_TESTS=1 \
  uv run pytest tests/test_public_integration.py::test_ds004574_public_bids_vertical_slice -vv
```

## Scope

This is the one-participant recipe. The full 146-recording conversion is in [CORPUS-DS004574.md](CORPUS-DS004574.md).
