# EEGMMIDB — one recording

PhysioNet EEG Motor Movement/Imagery v1.0.0, subject 1, run 3 (`S001R03.edf`). Left/right fist movements and rest. One small public file, used as the first fixture.

- **Input:** EDF+ with an embedded annotation channel
- **Licence:** ODC-By 1.0
- **Source size:** 2,596,896 bytes
- **Source SHA-256:** `3427c8d01bff1380bc9ab9f27a35ece2af5dfadf3e291bbc05eb66e4dadbfe2e`

The exact scientific and technical choices are declared in
[`recipes/eegmmidb-s001-r03.json`](../recipes/eegmmidb-s001-r03.json).

## CND representation

The complete 125-second recording remains one CND trial. No artificial epochs
or joins are introduced. The neural matrix contains 20,000 samples by 64 EEG
channels at 160 Hz. MNE's EEGBCI label standardization and the standard 10-05
montage provide explicit channel labels and positions.

The EDF+ annotations become three one-sample binary stimulus features at the
same 160 Hz clock:

| CND feature | EDF annotation | Event count | Meaning in run 3 |
|---|---:|---:|---|
| `rest_onset` | `T0` | 15 | Start of a rest period |
| `left_fist_execution_onset` | `T1` | 8 | Left-fist execution cue |
| `right_fist_execution_onset` | `T2` | 7 | Right-fist execution cue |

The run number is semantically important: PhysioNet documents different T1/T2
meanings for other runs. The mapping is therefore explicit in the recipe and
is never inferred from the annotation labels alone.

## What we did not do

- no filtering or rereferencing
- no resampling
- no artifact rejection
- no padding, truncation, or epoching
- no unit guessing

MNE reads EDF EEG into volts, and the CND file records volts.

## Validation result

All checks passed:

| Gate | Result |
|---|---|
| Official source checksum | Pass |
| Reviewed sampling frequency, 160 Hz | Pass |
| Annotation-to-sample quantization | Pass; maximum error 0 samples |
| Strict CND 1.0 validation before writing | Pass |
| MATLAB write/read | Pass |
| Strict CND 1.0 validation after reading | Pass |
| CND-to-MNE neural numerical comparison | Pass |
| Stimulus impulse exact comparison | Pass |

The content hash (arrays only, ignoring MATLAB header timestamps) is
`bdc411eb498fee53d53158d59c24fecdf345f499ddb0796e0bc1579b149f122b`.
v5 and v7.3 writes of the same numbers should match.

Output is local, gitignored: `outputs/eegmmidb/0.1.0/`. File checksums are in that folder's manifest.

## Reproduce

```bash
uv sync --extra dev
uv run neurodata-to-cnd convert recipes/eegmmidb-s001-r03.json \
  --cache-root cache \
  --output-root outputs
```

Download resumes from a checksum-checked cache. The versioned output folder only appears after conversion and validation pass.

Offline tests:

```bash
uv run pytest -m 'not integration'
```

This same public file, on the network:

```bash
RUN_PUBLIC_DATA_TESTS=1 uv run pytest tests/test_public_integration.py -vv
```

BIDS/`events.tsv` is already covered by [ds004574](VERTICAL-SLICE-DS004574.md). The remaining gap is continuous speech envelopes, not another impulse ERP set.
