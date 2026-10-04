# Development

```bash
uv sync --locked --extra dev
uv run python scripts/validate_catalog.py
uv run pytest -m 'not integration'
uv run ruff check .
uv run ruff format --check .
uv run mypy src
uv build
```

Follow `recipe.py` → `source.py` → `readers.py` → `pipeline.py`.

| Responsibility | Module |
|---|---|
| Features and recording construction | `features.py`, `preparation.py` |
| MATLAB writing and checks | `output.py`, `round_trip.py` |
| Directory publication and rollback | `publication.py` |
| Provenance and content hashes | `manifest.py` |
| Corpus recipes and inventory plans | `corpus_recipe.py`, `planning.py` |
| Batch execution and aggregate reports | `corpus.py`, `corpus_index.py` |
| State-file persistence | `_storage.py` |

`analysis_check.py` tests a small lagged regression fit. CND-MNE owns MATLAB
encoding and CND validation.

Use small synthetic fixtures. Test changes to units, timing, channels, and
serialization with numerical round trips. Keep participant data out of Git.
Public download tests are opt-in; see [validation](docs/validation.md).
