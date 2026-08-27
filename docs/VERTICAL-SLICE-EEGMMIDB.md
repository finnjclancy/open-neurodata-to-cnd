# EEGMMIDB vertical slice

## Outcome

The first executable conversion uses one small, versioned public recording:

- **Dataset:** PhysioNet EEG Motor Movement/Imagery Dataset v1.0.0
- **Source:** subject 1, run 3 (`S001R03.edf`)
- **Task:** executed left- and right-fist movements separated by rest
- **Input:** EDF+ with an embedded annotation channel
- **License:** Open Data Commons Attribution License v1.0
- **Source size:** 2,596,896 bytes
- **Source SHA-256:**
  `3427c8d01bff1380bc9ab9f27a35ece2af5dfadf3e291bbc05eb66e4dadbfe2e`

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

## Transformations deliberately not performed

- no filtering;
- no rereferencing;
- no resampling;
- no artifact rejection;
- no padding or truncation;
- no epoching;
- no unit guessing.

MNE reads EDF EEG into volts, and the CND file records volts explicitly.

## Validation result

The local reference build completed all gates without warnings:

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

The canonical scientific-content digest is
`bdc411eb498fee53d53158d59c24fecdf345f499ddb0796e0bc1579b149f122b`.
This digest normalizes array representation and excludes MAT-file header
timestamps, allowing equivalent MATLAB v5 and v7.3 builds to be compared.

Large/generated files remain ignored by Git. The local output is written under
`outputs/eegmmidb/0.1.0/`, with exact output-file checksums in its manifest.

## Reproduce

```bash
uv sync --extra dev
uv run neurodata-to-cnd convert recipes/eegmmidb-s001-r03.json \
  --cache-root cache \
  --output-root outputs
```

The downloader resumes from a verified cache. Publication is transactional:
conversion and validation happen in a staging directory, and the versioned
release becomes visible only after all gates pass.

Run all offline format and conversion tests with:

```bash
uv run pytest -m 'not integration'
```

Run the pinned public-data test explicitly with:

```bash
RUN_PUBLIC_DATA_TESTS=1 uv run pytest tests/test_public_integration.py -vv
```

## Format coverage established

- real public EDF+ input;
- synthetic EDF input;
- synthetic BrainVision input;
- synthetic FIF input;
- MATLAB v5 CND output;
- MATLAB v7.3/HDF5 CND output.

The next important format is not another synthetic file. It should be one small
OpenNeuro BIDS/BrainVision recording using `events.tsv`, followed by a
naturalistic audio dataset with continuous rather than impulse features.
