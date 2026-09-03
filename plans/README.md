# Corpus plans

A plan is one checksum-pinned job per recording. It is generated from a corpus recipe plus a remote inventory. Plans are metadata only, so they can live in git. The EEG itself does not.

```bash
uv run neurodata-to-cnd plan corpora/ds004574.json \
  --output plans/ds004574-v0.2.0.json

uv run neurodata-to-cnd plan corpora/nm000132.json \
  --output plans/nm000132-v0.3.0.json
```

Only regenerate a plan when you mean to start a new corpus version. The planner hashes the inventory with signed URLs stripped. Each file is still checked against its SHA-256 or git blob when downloaded.
