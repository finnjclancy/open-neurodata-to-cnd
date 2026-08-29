# Corpus plans

A corpus plan is generated from a dataset-level recipe and a checksum-pinned
remote inventory. It contains one immutable job per recording, including exact
source paths, stable download URLs, byte sizes, checksums, expected acquisition
metadata, and the pilot selection.

Plans may contain jobs from multiple tasks. Each such job pins its own reviewed
template recipe and digest when experiment semantics differ within a dataset.

Plans are safe to store in Git because they contain metadata—not neural signal
content. Generated state, downloaded source files, and CND outputs remain under
ignored cache and output directories.

Regenerate the ds004574 plan only when intentionally creating a new corpus
version or reviewing a changed upstream inventory:

```bash
uv run neurodata-to-cnd plan corpora/ds004574.json \
  --output plans/ds004574-v0.2.0.json

uv run neurodata-to-cnd plan corpora/nm000132.json \
  --output plans/nm000132-v0.3.0.json
```

The planner verifies a canonical inventory digest that excludes temporary
signed access URLs. Each individual object is still verified using its declared
SHA-256 or Git blob checksum when inspected or downloaded.
