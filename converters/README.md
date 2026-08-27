# Converter plug-ins

Reusable adapters now live in `src/neurodata_cnd`. This directory documents
their design and backlog; it must not contain copied datasets or one giant
conditional converter.

## Proposed interfaces

```text
SourceAdapter
  resolve(dataset, version) -> SourceSnapshot
  fetch(snapshot, selection, cache) -> LocalSource

SignalAdapter
  inspect(source, entities) -> SignalSummary
  load(source, entities) -> MNE Raw | MNE Epochs

FeatureAdapter
  extract(stimulus, events, recipe) -> FeatureTrials

TrialAdapter
  build(signal, events, recipe) -> NeuralTrials + TrialMetadata

CNDExporter
  export(neural_trials, feature_trials, metadata, destination)
```

## Implemented first slice

- checksum-pinned HTTP source acquisition with atomic caching;
- EDF/BDF, BrainVision, FIF, EEGLAB, and GDF reader dispatch;
- EEGBCI channel-label standardization and explicit montage application;
- annotation-to-impulse stimulus features;
- strict CND writing through CND-MNE;
- exact stimulus and numerical neural round-trip checks;
- transactional versioned output and provenance manifests.

## Adapter backlog

1. OpenNeuro/DataLad source adapter
2. BIDS/MNE-BIDS signal adapter
3. CTF MEG signal adapter
4. Audio envelope and spectrogram feature adapter
5. BIDS `events.tsv` impulse adapter
6. Text/word/phoneme feature adapter
7. THINGS image metadata/embedding adapter
8. Clinical interval annotation adapter

The exporter should call the tested writer and strict validator maintained by CND-MNE rather than implementing a second CND serialization stack.
