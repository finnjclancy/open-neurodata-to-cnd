# ds004574 — one recording

OpenNeuro `ds004574` v1.0.0, subject 001, oddball. This is the one-person fixture we used before converting all 146 recordings.

- **Input:** EEGLAB `.set`/`.fdt` plus seven BIDS metadata/event files
- **Licence:** CC0
- **Size:** 105,265,313 bytes
- **Snapshot SHA-256:** `21fb996b5f6d6b2bd65d196ad90610c2a6771b920397f7c3cf547b009b1710d4`

Each file's hash is in [`recipes/ds004574-sub001-oddball.json`](../../recipes/ds004574-sub001-oddball.json). Metadata URLs are pinned to commit `b7c69a16695968de78a3d1f1277654cc85884261`. The two big signal files are pinned by checksum.

## What CND looks like

The whole 816.2 s recording is one trial: 408,100 samples × 63 EEG channels at 500 Hz. Event times come from the BIDS `sample` column, checked against `onset`. Three `value` codes become one-sample spikes:

| CND feature | BIDS value | Count | Meaning |
|---|---:|---:|---|
| `precue_onset` | `S  1` | 236 | visual + auditory precue |
| `go_arrow_onset` | `S  2` | 236 | GO arrow |
| `response_onset` | `S  3` | 236 | button |

`channels.tsv` says every type is `n/a`, even though the EEG sidecar says 63 EEG channels with coordinates. The recipe has an explicit `all_eeg` correction and the evidence for it. No evidence field, no correction.

## What we did not do

- no filtering or rereferencing
- no resampling
- no artifact rejection
- no epoching, padding, or truncation
- no fuzzy event-name matching
- no stuffing the stimulus media into CND

MNE loads the EEGLAB values as volts. We wrote volts.

## Checks

Source checksums, 500 Hz, BIDS sample vs onset (0 samples off), strict CND before and after write, CND-MNE numbers match, impulses match.

Content hash (arrays only):
`e5b901ad9bf0e5b20c1f51b3617d2664c8925498a2c9870a5f7d110ac960b399`

Local MATLAB v5 output is about 164 MiB neural + 12 KiB stim. Not in git.

## Reproduce

```bash
uv sync --extra dev
uv run neurodata-to-cnd convert recipes/ds004574-sub001-oddball.json \
  --cache-root cache \
  --output-root outputs
```

The pytest for this one downloads ~105 MB:

```bash
RUN_LARGE_PUBLIC_DATA_TESTS=1 \
  uv run pytest tests/test_public_integration.py::test_ds004574_public_bids_vertical_slice -vv
```

All 146 recordings: [CORPUS-DS004574.md](CORPUS-DS004574.md).
