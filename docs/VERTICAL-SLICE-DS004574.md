# OpenNeuro ds004574 vertical slice

## Outcome

The second executable conversion deliberately differs from the first: it uses
a multi-file OpenNeuro BIDS recording rather than a single annotated EDF file.

- **Dataset:** Cross-modal oddball task, OpenNeuro `ds004574` v1.0.0
- **Source:** subject 001, task Oddball
- **Input:** EEGLAB `.set`/`.fdt` plus seven BIDS metadata and event files
- **License:** CC0
- **Pinned source size:** 105,265,313 bytes
- **Source snapshot SHA-256:**
  `21fb996b5f6d6b2bd65d196ad90610c2a6771b920397f7c3cf547b009b1710d4`

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

The source `channels.tsv` records all types as `n/a`, although the EEG sidecar
declares 63 EEG channels and all 63 named channels have electrode coordinates.
The recipe therefore contains a reviewed, evidence-bearing `all_eeg` correction.
The reader rejects that correction if the evidence field is absent; it is not a
global guess.

## Transformations deliberately not performed

- no filtering or rereferencing;
- no resampling;
- no artifact rejection;
- no epoching, padding, or truncation;
- no inferred or fuzzy event-name matching;
- no embedded stimulus media.

EEGLAB values loaded by MNE are represented in volts, and CND records volts.

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

The canonical scientific-content digest is
`e5b901ad9bf0e5b20c1f51b3617d2664c8925498a2c9870a5f7d110ac960b399`.
The local MATLAB v5 outputs are approximately 164 MiB for neural data and 12
KiB for stimulus features. Generated data remain outside Git.

## Reproduce

```bash
uv sync --extra dev
uv run neurodata-to-cnd convert recipes/ds004574-sub001-oddball.json \
  --cache-root cache \
  --output-root outputs
```

The public-data regression test is deliberately opt-in because it downloads
approximately 105 MB and creates a roughly 164 MiB CND output:

```bash
RUN_LARGE_PUBLIC_DATA_TESTS=1 \
  uv run pytest tests/test_public_integration.py::test_ds004574_public_bids_vertical_slice -vv
```

## Scope and next step

This recipe proves the reusable BIDS/EEGLAB/events path for one participant; it
does not claim that all 146 participants have been converted or audited. The
next structural milestone is continuous stimulus features (for example an audio
envelope aligned to naturalistic EEG), followed by batch planning and resumable
subject-level execution using the same immutable recipe and manifest contracts.
