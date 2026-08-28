# Conversion recipes

Each dataset receives a versioned recipe before full conversion.

Recipes declare scientific and technical decisions; they are not merely configuration shortcuts. A reviewer should be able to understand what one CND trial means, which signal representation was selected, what every feature contains, and how synchronization was established without reading converter code.

## Required recipe sections

- recipe and source versions;
- dataset identifier and source snapshot;
- input selection filters;
- modality, channels, units, and signal representation;
- trial-boundary policy;
- stimulus feature definitions;
- synchronization and trigger-delay corrections;
- neural and stimulus sampling rate;
- exclusions and failure policy;
- CND output layout;
- validation requirements;
- licensing restrictions.

[`eegmmidb-s001-r03.json`](eegmmidb-s001-r03.json) converts one pinned PhysioNet
EDF+ recording and embedded annotations. The structurally different
[`ds004574-sub001-oddball.json`](ds004574-sub001-oddball.json) converts a pinned
multi-file BIDS/EEGLAB snapshot and maps explicit `events.tsv` values. Both
avoid neural preprocessing and require strict CND plus numerical round-trip
validation. See
[`ds006434.example.json`](ds006434.example.json) for the proposed natural-speech
recipe that will follow it.
