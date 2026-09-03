# Architecture

This repo turns public EEG into CND. The companion repo, [cnd-mne](https://github.com/finnjclancy/cnd-mne-converter), owns reading, writing, and validating the `.mat` files.

The split is on purpose. Recipes and downloads live here. "Is this even CND" lives there.

```text
catalogue → download a pinned source → load signal → apply recipe
    → write CND → strict validate + round trip → local outputs
```

Nothing gets published until validation passes. Git never holds the recordings.

## The pieces

**Catalogue entry** — what the dataset is, where it lives, licence, size. No conversion decisions.

**Recipe** — the scientific choices for one dataset: which files, which channels, what a trial is, what the stimulus features are, sampling rate, known limitations. If a choice changes the meaning of the experiment, it belongs in the recipe, not as a quiet default in code.

**Adapters** — reusable code:

- Source: find and download a snapshot
- Signal: load BIDS / EDF / BrainVision / etc into MNE
- Features: turn events or audio into CND stimulus streams
- Trials: cut the recording into CND trials

Dataset-specific behaviour belongs in the recipe, not in a giant `if dataset == ...` adapter.

**Manifest** — checksums, recipe version, what was converted, licences, warnings. Every local corpus write has one.

## How a conversion actually runs

One recording (or one subject/session/task/run group) is one job. Jobs are supposed to be resumable and independent. GitHub Actions only runs metadata and small fixtures, not bulk downloads.

Current converters only do EEG, and only `recording_run` as the trial unit. Impulse features from annotations or `events.tsv` work. Continuous envelopes do not yet.

What has been through this for real: one EEGMMIDB fixture, all of `ds004574`, all of ERP CORE `nm000132`. See the main readme.

## Checks before something is "done"

- Source version pinned, files present, checksums match
- Trial cuts and features written down, not inferred
- New CND passes strict 1.0 validation
- Neural and stimulus trial counts agree
- CND-MNE can load it and the numbers match
- Copyrighted media is not stuffed into the release

Publication (object store, DOI, catalogue `published`) is a later step. Local `outputs/` is not that.

## Next, if the lab wants speech

The original plan was `ds006434` as the first naturalistic slice: cortical 1 kHz EEG, attended and unattended envelopes, one source trial = one CND trial. That recipe is still a draft because envelope extraction is not implemented. That is the next engineering piece, not another ERP corpus.
