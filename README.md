# Open Neurodata to CND

Turn publicly shared EEG into **CND**, the MATLAB layout the Di Liberto lab already uses, without putting terabytes of brain data into git.

[CND-MNE](https://github.com/finnjclancy/cnd-mne-converter) reads and writes those MATLAB files. This repo is the pipeline that *creates* CND from other public formats (OpenNeuro, PhysioNet, and similar).

## Why this exists

A lot of EEG (scalp brain recordings) is already public. It usually arrives as **BIDS** (a folder of recordings plus `events.tsv`) or **EDF** (one recording file). The lab's own work is CND: `dataSubN.mat` for the brain signal and `dataStim.mat` for what was happening at the same time.

If those public datasets are also in CND, you can load them with the same Python tools, keep the event timing, and keep a written record of every conversion choice.

This project:

1. Downloads one pinned public file (checksum checked)
2. Follows a **recipe** — a JSON file that says which channels to keep, what a trial is, and which events become stimulus tracks
3. Writes CND
4. Checks the result with CND-MNE

Git only stores recipes and checksums. The recordings stay in `cache/` and `outputs/` on your machine.

CND here is a copy. Keep the original BIDS/EDF as the source of truth. A licence on the EEG does not mean you can republish the movie, audiobook, or novel people were watching or hearing.

## Words used here

- **Recipe** — the scientific decisions for one dataset, in JSON. Not just CLI flags.
- **Trial** — in the conversions so far, one source recording = one CND trial (the whole run, not cut into ERP epochs).
- **Impulse** — a one-sample spike at a button press or cue.
- **Speech envelope** — a smooth track of how loud the audio was. Not implemented yet.

## What has actually been converted

Local, checked, not published as an official CND release:

- PhysioNet EEGMMIDB — one small example (subject 1, run 3). [Notes](docs/VERTICAL-SLICE-EEGMMIDB.md)
- OpenNeuro `ds004574` — all 146 recordings. [Report](docs/CORPUS-DS004574.md)
- ERP CORE `nm000132` — all 240 recordings, 40 people × 6 tasks. [Report](docs/CORPUS-NM000132.md)

No filtering, rereferencing, or resampling. Features are event impulses only. Continuous speech envelopes are not built yet, so naturalistic attention sets like `ds006434` are still a draft recipe.

Other candidates: [catalog/datasets.json](catalog/datasets.json). Do not reconvert Lalor Natural Speech (`ds004408`) or the KUL attention sets that already exist as CND.

## Download and install

You need [git](https://git-scm.com/), [uv](https://docs.astral.sh/uv/), Python 3.10 or newer, and access to the private [cnd-mne](https://github.com/finnjclancy/cnd-mne-converter) repo (this project installs it as a dependency).

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

Pass `--overwrite` if the output folder already exists. Pass `--source /path/to/file` if you already have the original recording and do not want to download it again.

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

Same pattern for `corpora/nm000132.json`. Each recording has its own state. A failure does not redo the ones that already passed. More: [docs/CORPUS-WORKFLOW.md](docs/CORPUS-WORKFLOW.md).

## Layout

```text
catalog/     what datasets exist and their licences
recipes/     conversion decisions (channels, events, trial cuts)
corpora/     dataset-scale inventories
converters/  notes on the adapters (code is in src/neurodata_cnd)
schemas/     recipe and manifest contracts
outputs/     local CND (gitignored)
docs/        corpus reports and architecture
```

More: [architecture](docs/ARCHITECTURE.md), [recipes](recipes/README.md), [storage](storage/README.md).
