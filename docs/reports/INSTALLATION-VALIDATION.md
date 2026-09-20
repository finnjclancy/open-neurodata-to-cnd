# Installation validation — 20 September 2026

The pipeline now pins published CND-MNE revision
`c1682e187bbb31b4bc652646f598e172af9ce63b` in both the `conversion` and `dev`
extras and in `uv.lock`. This includes the MATLAB external-channel cell layout
and EEGLAB Cartesian, spherical and polar coordinate export. No local converter
checkout or editable converter override is required by the pipeline.

## Checks completed

| Installation | Result |
| --- | --- |
| New environment from `uv sync --locked --extra dev` | 50 offline tests and both live public-data conversion tests passed. |
| Built pipeline wheel in another new environment, with its `dev` extra | All 50 offline tests passed; the pipeline and converter were installed into site-packages, not imported from editable checkouts. |
| Fresh ERP CORE P3 conversion through the installed wheel | 478,208 samples, 30 EEG channels and three external EOG channels; source reconciliation, strict CND, MATLAB read-back and MNE round trips passed. |
| Coordinate export through the installed dependency | Cartesian, spherical and polar fields were present and finite; spherical radii matched Cartesian norms. Offline regression checks exercise both MATLAB v5 and v7.3. |
| Fresh P3 compared with the existing validated corpus | EEG, EOG and stimulus arrays were exactly equal. MNE 1–40 Hz filtering and power-spectrum computation produced finite values. |
| Fresh P3 through the corrected MATLAB driver | CNSP preprocessing, ridge cross-validation/training and held-out prediction passed with finite weights and correlations. |
| Companion converter checkout in a new locked environment with `dev` and `gui` extras | All 136 tests passed. The real Lalor GUI numerical audit completed; an offscreen Qt check loaded 20 trials, navigated between them and generated sensor/PSD plots. |

The locked pipeline environment used Python 3.13.5, MNE 1.12.1 and NumPy 2.5.2.
The wheel installation resolved MNE 1.13.2 and NumPy 2.5.3 and also passed the
checks above. Use the lockfile when reproducing the exact development dependency
set; installing a wheel with unconstrained transitive versions is a separate
compatibility check.

Fresh-recording results, package versions and converter Git provenance are in
[`giovanni-validation/installation-p3.json`](giovanni-validation/installation-p3.json).
The fresh P3 MATLAB result is in
[`installation-p3-matlab.json`](giovanni-validation/installation-p3-matlab.json);
the repeated Lalor audit is in
[`installation-gui-audit.json`](giovanni-validation/installation-gui-audit.json),
with the offscreen GUI check in
[`installation-gui-smoke.json`](giovanni-validation/installation-gui-smoke.json).
The offscreen check does not replace manual desktop interaction testing.
The full-corpus MATLAB validation and its scope are described in
[`GIOVANNI-FEEDBACK.md`](GIOVANNI-FEEDBACK.md).

## Reproduce the installation and tests

From the pipeline repository, choose a new environment path:

```sh
UV_PROJECT_ENVIRONMENT=/tmp/cnd-pipeline-clean uv sync --locked --extra dev
RUN_PUBLIC_DATA_TESTS=1 RUN_LARGE_PUBLIC_DATA_TESTS=1 \
  /tmp/cnd-pipeline-clean/bin/python -m pytest -q
```

The live tests download the pinned PhysioNet EDF and OpenNeuro BIDS fixtures.
To run just the offline tests, omit the environment flags and add
`-m 'not integration'`.

For a separate wheel installation:

```sh
uv build
uv venv /tmp/cnd-pipeline-wheel
uv pip install --python /tmp/cnd-pipeline-wheel/bin/python \
  'dist/open_neurodata_to_cnd-0.1.0.dev0-py3-none-any.whl[dev]'
/tmp/cnd-pipeline-wheel/bin/python -m pytest -q -m 'not integration'
```

Verify that the installed converter comes from the pinned Git revision:

```sh
/tmp/cnd-pipeline-wheel/bin/python -c \
  "from importlib.metadata import distribution; print(distribution('cnd-mne-converter').read_text('direct_url.json'))"
```

Convert one real ERP CORE recording to a new output directory:

```sh
/tmp/cnd-pipeline-wheel/bin/neurodata-to-cnd batch \
  plans/nm000132-v0.4.0.json --recording sub-001_task-P3 \
  --cache-root /tmp/cnd-p3-cache --output-root /tmp/cnd-p3-output
```

Using a new output directory is necessary: the batch command deliberately skips
previously completed recordings. This one-recording check does not rebuild or
replace the existing 240-recording corpus.

For the companion GUI, use the converter repository's documented
`uv sync --locked --extra gui` and `uv run cnd-mne gui` commands. The GUI is a
separate companion application; it is not an upstream MNE import menu.
Its Lalor example uses explicitly documented assumptions for units and head
radius, not a newly established physical calibration.
