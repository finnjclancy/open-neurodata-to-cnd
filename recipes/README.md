# Recipes

A recipe states what a trial means, which channels to retain, and how stimulus
tracks align with EEG. Read an example before editing the schema.

| Example | Input / use |
| --- | --- |
| [eegmmidb-s001-r03.json](eegmmidb-s001-r03.json) | One PhysioNet EDF recording |
| [ds004574-sub001-oddball.json](ds004574-sub001-oddball.json) | One BIDS recording (files plus metadata) |
| [nm000132-p3.json](nm000132-p3.json) | ERP CORE batch template; use a corpus plan |
| [ds006434.example.json](ds006434.example.json) | Draft speech recipe; not executable |

Sources need a version and checksums. Supported readers: EDF, BDF, BrainVision,
FIF, EEGLAB, GDF, and BIDS. Current recipes support EEG and one full run per trial.

- `annotation_impulse`: match an annotation label.
- `bids_event_impulse`: match `source_column` with `source_value` or `source_values`.
- `audio_envelope`: read WAV; choose `hilbert` or `rectified`, positive compression,
  and `none`, `peak`, or `zscore` normalization.

`sample_index_origin` defaults to 0; ERP CORE uses 1. An impulse marks an event
at one sample. Two selected events landing on the same sample are rejected.

`stimulus_sampling_rate_hz` may differ from EEG; both start at sample zero.
Audio `offset_seconds` trims the audio start before alignment. It cannot place
sound at an arbitrary EEG onset. Review source timing before activating a recipe.

`eeg_with_external` retains reviewed auxiliary channel types in CND `extChan`.
The `require_*` flags and fixed output flags record guarantees, not switches.
Validate edits with `uv run python scripts/validate_catalog.py`.
