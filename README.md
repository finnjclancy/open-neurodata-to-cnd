# Open Neurodata to CND

Turn publicly shared EEG into **CND**, the MATLAB layout the Di Liberto lab already uses, without putting terabytes of brain data into git.

[CND-MNE](https://github.com/finnjclancy/cnd-mne-converter) reads and writes those MATLAB files. This repo is the pipeline that *creates* CND from other public formats (OpenNeuro, PhysioNet, and similar).

A lot of EEG is already public, usually as **BIDS** or **EDF**. The [Di Liberto lab](https://www.diliberg.net/) stores its own work as CND. Collections that are already CND are on the [CNSP dataset catalogue](https://cnsp-resources.readthedocs.io/en/latest/datasetsPage.html).

This project downloads one pinned public file, follows a **recipe** (which channels, what a trial is, which events become stimulus tracks), writes CND, and checks it with CND-MNE. Git only stores recipes and checksums. Recordings stay in `cache/` and `outputs/` on your machine.

CND here is a copy. Keep the original BIDS/EDF as the source of truth. A licence on the EEG does not mean you can republish the movie, audiobook, or novel people were watching or hearing.

## What has actually been converted

Local, checked, not published as an official CND release:

- PhysioNet EEGMMIDB — one small example (subject 1, run 3). [Notes](docs/reports/VERTICAL-SLICE-EEGMMIDB.md)
- OpenNeuro `ds004574` — all 146 recordings. [Report](docs/reports/CORPUS-DS004574.md)
- ERP CORE `nm000132` — all 240 recordings, 40 people × 6 tasks. [Report](docs/reports/CORPUS-NM000132.md)

No filtering, rereferencing, or resampling. Features are event impulses only. Continuous speech envelopes are not built yet, so naturalistic attention sets like `ds006434` are still a draft recipe.

Other candidates: [catalog/datasets.json](catalog/datasets.json) (`candidate`, `converted`, `license-blocked`, `stimulus-rights-review`, …). After editing it: `python scripts/validate_catalog.py`. Do not reconvert Lalor Natural Speech (`ds004408`) or the KUL attention sets that already exist as CND on the [catalogue](https://cnsp-resources.readthedocs.io/en/latest/datasetsPage.html).

## Install

You need [git](https://git-scm.com/), [uv](https://docs.astral.sh/uv/), Python 3.10 or newer, and access to the private [cnd-mne](https://github.com/finnjclancy/cnd-mne-converter) repo.

```bash
git clone https://github.com/finnjclancy/open-neurodata-to-cnd.git
cd open-neurodata-to-cnd
uv sync --extra dev
```

`uv sync --extra test` skips CND-MNE and only runs the metadata tests. You cannot convert without CND-MNE.

## Convert one recording

This downloads a 2.5 MB PhysioNet EDF, writes CND, and checks it. Needs the network the first time:

```bash
uv run neurodata-to-cnd convert recipes/eegmmidb-s001-r03.json \
  --cache-root cache \
  --output-root outputs
```

You should get `outputs/eegmmidb/0.1.0/dataCND/dataSub1.mat` and `dataStim.mat`. Open that folder with CND-MNE:

```bash
uv run cnd-mne inspect outputs/eegmmidb/0.1.0/dataCND --subject 1
```

A larger one-recording example (about 105 MB) is OpenNeuro `ds004574` subject 001:

```bash
uv run neurodata-to-cnd convert recipes/ds004574-sub001-oddball.json \
  --cache-root cache \
  --output-root outputs
```

Pass `--overwrite` if the output folder already exists. Pass `--source /path/to/file` if you already have the original recording.

## Convert a whole dataset

```bash
uv run neurodata-to-cnd plan corpora/ds004574.json \
  --output plans/ds004574-v0.2.0.json
uv run neurodata-to-cnd batch plans/ds004574-v0.2.0.json \
  --cache-root cache/corpus-v0.2 --output-root outputs
uv run neurodata-to-cnd status outputs/ds004574/0.2.0
uv run neurodata-to-cnd retry plans/ds004574-v0.2.0.json \
  --cache-root cache/corpus-v0.2 --output-root outputs
```

Same pattern for `corpora/nm000132.json`. `batch` runs one recording at a time. Finished jobs are skipped. A failure is recorded and the rest keep going. `retry` only picks up failures. Source files are deleted after a successful validate unless you pass `--keep-source`. Only regenerate a plan when you mean to start a new corpus version.

```text
outputs/<corpus-id>/<corpus-version>/
├── recordings/sub-NNN/dataCND/
├── recordings/sub-NNN/manifest.json
├── state/sub-NNN.json
├── index.jsonl
└── summary.json
```

A recording folder only appears after checksums, strict CND, MATLAB read-back, and CND-to-MNE number checks all pass.

Recipe gotchas: a feature can match one `source_value` or a list (`source_values`); `sample_index_origin` defaults to 0 (ERP CORE needed `1`); `eeg_only` keeps EEG-typed channels and drops EOG, it does not relabel; ds004574 `--pilot` is a smoke test from metadata, not a scientific sample.

## Layout

```text
catalog/        what datasets exist and their licences
recipes/        conversion decisions (channels, events, trial cuts)
corpora/        dataset-scale inventories
src/            adapters (download, load, events, trials)
schemas/        recipe and manifest contracts
outputs/        local CND (gitignored)
docs/reports/   what we actually converted
```

CND writing and strict validation go through CND-MNE. There is no second writer. Git never holds the recordings.
