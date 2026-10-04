# Validation

Run offline checks from [development](../CONTRIBUTING.md). Public conversion
tests download checksum-pinned recordings:

```bash
RUN_PUBLIC_DATA_TESTS=1 RUN_LARGE_PUBLIC_DATA_TESTS=1 \
  uv run pytest tests/test_public_integration.py
```

## Python analysis smoke check

```bash
uv run neurodata-to-cnd check-analysis \
  outputs/eegmmidb/0.1.0/dataCND/dataSub1.mat \
  outputs/eegmmidb/0.1.0/dataCND/dataStim.mat --feature rest_onset
```

Checks only trial 0 and at most 20,000 samples. It aligns stimulus rates, builds
a matrix of delayed stimulus values, and solves ridge regression. Constant
predictors, oversized lags, and non-finite data fail. A finite fit is a software
check, not evidence of predictive value or MATLAB workflow compatibility.

## MATLAB / CNSP

Requires MATLAB with Signal Processing Toolbox and converted ERP CORE outputs.
Clone the upstream functions at the revision used for the recorded check:

```bash
git clone https://github.com/CNSP-Workshop/CNSP-resources.git ../CNSP-resources
git -C ../CNSP-resources checkout 74d26e5b7ded8eb80f56aa26517b7e73ba4a83a7
uv run python scripts/validation/run_validation.py \
  --data-root outputs/nm000132/0.4.0/recordings --all-recordings \
  --upstream ../CNSP-resources --output outputs/matlab-check \
  --engine matlab --preprocess
```

Put MATLAB on `PATH`. The driver supplies dataset-specific paths, average
reference, feature selection, and timing choices; upstream functions stay intact.
[Recorded scope and results](results.md).

## Installed wheel

```bash
uv build
uv venv /tmp/neurodata-wheel
uv pip install --python /tmp/neurodata-wheel/bin/python \
  'dist/open_neurodata_to_cnd-0.1.0.dev0-py3-none-any.whl[dev]'
/tmp/neurodata-wheel/bin/python -m pytest -m 'not integration'
```

A coordinate round trip checks numerical preservation, not anatomical accuracy.
Dataset licences do not automatically cover accompanying audio or other stimuli.
