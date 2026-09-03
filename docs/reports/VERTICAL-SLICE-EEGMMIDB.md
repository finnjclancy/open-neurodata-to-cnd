# EEGMMIDB — one recording

PhysioNet EEG Motor Movement/Imagery v1.0.0, subject 1, run 3 (`S001R03.edf`). Left/right fist movements and rest. First public file we converted, because it is small.

- **Input:** EDF+ with an annotation channel
- **Licence:** ODC-By 1.0
- **Size:** 2,596,896 bytes
- **SHA-256:** `3427c8d01bff1380bc9ab9f27a35ece2af5dfadf3e291bbc05eb66e4dadbfe2e`

Choices are in [`recipes/eegmmidb-s001-r03.json`](../../recipes/eegmmidb-s001-r03.json).

## What CND looks like

The whole 125 s run is one trial. 20,000 samples × 64 EEG channels at 160 Hz. Channel names and positions come from MNE's EEGBCI labels and the 10-05 montage.

EDF annotations become three one-sample spikes on that same 160 Hz clock:

| CND feature | EDF annotation | Count | Meaning in run 3 |
|---|---:|---:|---|
| `rest_onset` | `T0` | 15 | rest starts |
| `left_fist_execution_onset` | `T1` | 8 | left-fist cue |
| `right_fist_execution_onset` | `T2` | 7 | right-fist cue |

T1/T2 mean different things on other PhysioNet runs, so the recipe names them. We do not guess from the letters alone.

## What we did not do

- no filtering or rereferencing
- no resampling
- no artifact rejection
- no padding, truncation, or epoching
- no unit guessing

MNE reads EDF EEG as volts. The CND file says volts.

## Checks

All passed: source checksum, 160 Hz, annotations land on the right samples, strict CND 1.0 before and after write, MATLAB round trip, numbers match in CND-MNE, impulses match.

Content hash (the arrays, not MATLAB header timestamps):
`bdc411eb498fee53d53158d59c24fecdf345f499ddb0796e0bc1579b149f122b`

Output is local: `outputs/eegmmidb/0.1.0/`. Checksums are in that folder's manifest.

## Reproduce

```bash
uv sync --extra dev
uv run neurodata-to-cnd convert recipes/eegmmidb-s001-r03.json \
  --cache-root cache \
  --output-root outputs
```

Offline tests: `uv run pytest -m 'not integration'`

Same public file, on the network:

```bash
RUN_PUBLIC_DATA_TESTS=1 uv run pytest tests/test_public_integration.py -vv
```

BIDS / `events.tsv` is [ds004574](VERTICAL-SLICE-DS004574.md). Still missing: speech envelopes.
