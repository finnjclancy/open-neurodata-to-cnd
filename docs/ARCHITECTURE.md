# Architecture

This repo turns public EEG into CND. The companion repo, [cnd-mne](https://github.com/finnjclancy/cnd-mne-converter), is the thing that reads, writes, and checks the `.mat` files.

Split on purpose: recipes and downloads here. "Is this even CND" there.

```text
catalogue → download a pinned source → load signal → apply recipe
    → write CND → strict validate + round trip → local outputs
```

Git never holds the recordings. Nothing is treated as published until those checks pass.

## Pieces

**Catalogue entry** — what it is, where to get it, licence, size. No conversion choices.

**Recipe** — the scientific choices: which files, which channels, what a trial is, what the events become, sampling rate, known mess. If a choice changes the meaning of the experiment, it belongs here, not as a quiet default in Python.

**Adapters** — reusable code (find/download, load BIDS/EDF/etc, turn events into features, cut trials). Dataset-specific behaviour stays in the recipe, not `if dataset == ...`.

**Manifest** — checksums, recipe version, what was converted, licences, warnings.

## What a run looks like

One recording is one job. Jobs can restart independently. GitHub Actions only runs metadata and tiny fixtures, not the bulk downloads.

Right now: EEG only, one source recording = one CND trial. Event impulses from annotations or `events.tsv` work. Speech envelopes do not.

Actually converted: one EEGMMIDB file, all of `ds004574`, all of ERP CORE `nm000132`. See the main readme.

## Before we call it done

- Source version pinned, files present, checksums match
- Trial cuts and features written down, not inferred
- New CND passes strict 1.0
- Neural and stimulus trial counts agree
- CND-MNE can load it and the numbers match
- Copyrighted media is not stuffed into the release

Putting it on object storage with a DOI is a later step. Local `outputs/` is just local.

## If the lab wants speech next

The plan was `ds006434`: 1 kHz EEG, attended and unattended envelopes, one source trial = one CND trial. That recipe is still a draft because envelope extraction is not written. That is the next engineering piece, not another ERP set.
