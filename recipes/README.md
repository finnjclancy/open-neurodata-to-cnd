# Recipes

A recipe is the conversion decisions for one dataset. Someone should be able to tell what a CND trial is, which channels were kept, and how events were mapped without reading the Python.

Working examples:

- [`eegmmidb-s001-r03.json`](eegmmidb-s001-r03.json) — one PhysioNet EDF+ file
- [`ds004574-sub001-oddball.json`](ds004574-sub001-oddball.json) — one BIDS/EEGLAB oddball recording
- [`nm000132-*.json`](nm000132-mmn.json) — ERP CORE corpus templates, one per paradigm; run them through a corpus plan rather than `convert`

[`ds006434.example.json`](ds006434.example.json) is a draft for natural speech. It is not runnable until continuous envelopes exist.

The `require_*` and fixed output flags describe checks the pipeline always performs. They are guarantees, not switches.
