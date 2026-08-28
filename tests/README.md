# Tests

The test suite will be split into four layers:

1. **Metadata tests:** catalogue, recipe, manifest, and schema validation; no data downloads.
2. **Unit tests:** signal, event, feature, synchronization, and trial helpers using synthetic arrays.
3. **Fixture tests:** tiny legally redistributable source/CND samples covering each adapter family.
4. **Integration tests:** optional network and object-storage tests, excluded from normal CI.

Bulk corpus conversion must never run in GitHub Actions. Full validation reports belong with the object-store release manifest.

The current offline suite covers annotation and BIDS-event semantics,
multi-file snapshot integrity, evidence-bearing channel corrections,
missing-event failures, transactional publication, immutable outputs, canonical
content hashes, EDF, BrainVision, FIF, and CND MATLAB v5/v7.3.

The small opt-in public integration test downloads the pinned EEGMMIDB EDF:

```bash
RUN_PUBLIC_DATA_TESTS=1 uv run pytest tests/test_public_integration.py -vv
```

The separate large test downloads the 105 MB OpenNeuro BIDS/EEGLAB snapshot and
creates an approximately 164 MiB CND derivative:

```bash
RUN_LARGE_PUBLIC_DATA_TESTS=1 \
  uv run pytest tests/test_public_integration.py::test_ds004574_public_bids_vertical_slice -vv
```
