# Tests

Four layers, in theory:

1. Metadata — catalogue, recipes, schemas, no downloads
2. Unit — synthetic arrays
3. Fixtures — tiny legal samples
4. Integration — optional network tests, not in normal CI

Do not run bulk corpus conversion in GitHub Actions.

Right now the offline suite covers event mapping, snapshot integrity, channel corrections, transactional writes, EDF / BrainVision / FIF, and MATLAB v5/v7.3. The full pipeline tests need the private CND-MNE extra.

Optional public downloads:

```bash
RUN_PUBLIC_DATA_TESTS=1 uv run pytest tests/test_public_integration.py -vv

RUN_LARGE_PUBLIC_DATA_TESTS=1 \
  uv run pytest tests/test_public_integration.py::test_ds004574_public_bids_vertical_slice -vv
```

The large one pulls a 105 MB OpenNeuro snapshot and writes ~164 MiB of CND.
