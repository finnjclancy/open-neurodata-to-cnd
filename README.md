# Open Neurodata to CND

Convert public EEG recordings into CND MATLAB files using reviewed JSON recipes.
Python 3.10+. Research software; not yet on PyPI.

**EEG** is voltage recorded at scalp sensors. **CND** stores that signal beside
stimulus tracks. A **recipe** defines channels, event mappings, units, and trial
boundaries. This pipeline downloads pinned source files, converts them through
[CND-MNE](https://github.com/finnjclancy/cnd-mne-converter), then checks the result.

## Start

```bash
git clone https://github.com/finnjclancy/open-neurodata-to-cnd.git
cd open-neurodata-to-cnd
uv sync --locked --extra dev
uv run neurodata-to-cnd convert recipes/eegmmidb-s001-r03.json
uv run cnd-mne inspect outputs/eegmmidb/0.1.0/dataCND --subject 1
```

The example downloads a 2.5 MB recording and writes `dataSub1.mat`,
`dataStim.mat`, and `manifest.json`. The manifest records source checksums,
conversion choices, software versions, and validation results.
CND-MNE is installed automatically. For conversion only, use `--extra conversion`.

One source recording becomes one CND trial. EEG values, sampling rate, and
channel order are retained. Event tracks contain one-sample impulses; WAV audio
can produce an amplitude envelope. Reviewed eye-movement channels (EOG) stay
separate from EEG.

## Whole datasets

```bash
uv run neurodata-to-cnd plan corpora/nm000132.json --output plans/nm000132.json
uv run neurodata-to-cnd batch plans/nm000132.json
uv run neurodata-to-cnd status outputs/nm000132/0.4.0
uv run neurodata-to-cnd retry plans/nm000132.json
```

`batch` skips completed recordings and records failures. `retry` selects failed
jobs. Sources are removed after success unless `--keep-source` is set.
Generated plans stay in local `plans/`. They pin inventory and recipe hashes; create a new version when changing
conversion decisions. Use `--pilot` to check a small metadata-selected subset.

Outputs appear only after checksums, CND validation, MATLAB read-back, and
numerical comparisons pass. Keep original recordings as the source of truth.

## Read next

- [Recipes](recipes/README.md): formats, events, audio, and clocks.
- [Results](docs/results.md): 146 ds004574 and 240 ERP CORE recordings converted locally.
- [Validation](docs/validation.md): reproduce checks and understand their limits.
- [Development](CONTRIBUTING.md): code map and test commands.

`catalog/` records dataset candidates and rights; `corpora/` holds batch recipes;
`schemas/` defines JSON contracts. Recordings and generated reports belong in
local `cache/` and `outputs/`, outside Git. Dataset and stimulus rights are
separate from the code's BSD licence.
