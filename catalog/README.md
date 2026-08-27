# Dataset catalogue

[`datasets.json`](datasets.json) is the machine-readable conversion queue. The main README contains the broader researched directory; entries move into the JSON catalogue when their identity, access status, license, scale, and priority have been reviewed.

## Status meanings

- `candidate`: suitable for recipe development.
- `pilot-proposed`: recommended for the first vertical conversion slice.
- `license-blocked`: downloadable, but redistribution or derivative rights are unresolved.
- `stimulus-rights-review`: neural data are available but stimulus rights need separate review.
- `awaiting-meg-support`: conversion should wait for validated MEG support in CND-MNE.
- `converted`: a candidate release exists but has not passed every publication gate.
- `published`: an immutable validated CND release and manifest are available.
- `stale`: the upstream dataset changed after conversion.

## Updating the catalogue

1. Verify the canonical dataset identifier and URL.
2. Pin or record the source version.
3. Verify neural and stimulus licenses independently.
4. De-duplicate mirrors and derivatives.
5. Add the entry with a unique contiguous priority.
6. Run `python scripts/validate_catalog.py`.
