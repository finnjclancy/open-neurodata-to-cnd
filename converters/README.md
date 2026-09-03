# Converters

The adapters live in `src/neurodata_cnd`. This folder is just notes. Do not put datasets here.

```text
SourceAdapter   find / fetch a pinned snapshot
SignalAdapter   load into MNE
FeatureAdapter  events or audio → stimulus features
TrialAdapter    cut recordings into CND trials
```

CND writing and strict validation go through CND-MNE. There is no second writer.

## What exists

Checksum-pinned HTTP downloads. EDF/BDF, BrainVision, FIF, EEGLAB, GDF. Impulses from annotations or BIDS `events.tsv`. Strict CND write + round trip. Local outputs only appear after that.

## Still to do

- Audio envelope / spectrogram features
- OpenNeuro / DataLad niceties
- CTF MEG (blocked on CND-MNE)
- Text / word / phoneme features
- THINGS image metadata
- Clinical interval annotations
