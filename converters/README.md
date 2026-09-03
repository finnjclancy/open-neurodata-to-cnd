# Converters

The actual adapters live in `src/neurodata_cnd`. This folder is just notes. Do not put datasets here.

## Shape

```text
SourceAdapter   resolve / fetch a pinned snapshot
SignalAdapter   load into MNE
FeatureAdapter  events or audio → stimulus features
TrialAdapter    cut recordings into CND trials
```

CND writing and strict validation go through CND-MNE. There is no second writer.

## What exists

Checksum-pinned HTTP downloads, EDF/BDF, BrainVision, FIF, EEGLAB, GDF, annotation impulses, BIDS `events.tsv` impulses, strict CND write + round trip, transactional local outputs.

## Still to do

- Audio envelope / spectrogram features
- OpenNeuro / DataLad source niceties
- CTF MEG (blocked on CND-MNE MEG support)
- Text / word / phoneme features
- THINGS image metadata
- Clinical interval annotations
