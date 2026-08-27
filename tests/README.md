# Tests

The test suite will be split into four layers:

1. **Metadata tests:** catalogue, recipe, manifest, and schema validation; no data downloads.
2. **Unit tests:** signal, event, feature, synchronization, and trial helpers using synthetic arrays.
3. **Fixture tests:** tiny legally redistributable source/CND samples covering each adapter family.
4. **Integration tests:** optional network and object-storage tests, excluded from normal CI.

Bulk corpus conversion must never run in GitHub Actions. Full validation reports belong with the object-store release manifest.
