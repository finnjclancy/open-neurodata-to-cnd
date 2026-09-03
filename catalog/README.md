# Catalogue

[`datasets.json`](datasets.json) is the conversion queue. Add a dataset there once you know the id, access, licence, size, and whether it is worth converting.

## Status

- `candidate` — fine to write a recipe
- `pilot-proposed` — suggested first slice for a new kind of data
- `license-blocked` — can download, should not redistribute
- `stimulus-rights-review` — EEG is ok, the movie/book/audio may not be
- `awaiting-meg-support` — wait until CND-MNE can do MEG
- `converted` — local CND exists, not a public release
- `published` — immutable release + manifest
- `stale` — upstream changed after we converted

## Updating it

Pin the source version. Check neural and stimulus licences separately. Do not list the same dataset twice via a mirror. Then:

```bash
python scripts/validate_catalog.py
```
