# Converter plug-ins

This directory will contain reusable adapters. It should not contain copied datasets or one giant conditional converter.

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

## Initial adapter backlog

1. OpenNeuro/DataLad source adapter
2. BIDS/MNE-BIDS signal adapter
3. BrainVision signal adapter
4. EDF signal adapter
5. CTF MEG signal adapter
6. Audio envelope and spectrogram feature adapter
7. BIDS event impulse adapter
8. Text/word/phoneme feature adapter
9. THINGS image metadata/embedding adapter
10. Clinical interval annotation adapter

The exporter should call the tested writer and strict validator maintained by CND-MNE rather than implementing a second CND serialization stack.
