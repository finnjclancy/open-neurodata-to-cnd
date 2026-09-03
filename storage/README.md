# Storage

Do not commit raw EEG/MEG or generated CND to git. Git gets code, recipes, manifests, checksums, and tiny fixtures. Everything else belongs on disk or in object storage.

There is no live S3/R2 publisher yet. Local `outputs/<dataset>/<version>/` is the current "release". If we publish later, something like:

```text
s3://<bucket>/
├── sources/<dataset-id>/<source-version>/
├── work/<dataset-id>/<run-id>/
├── releases/<dataset-id>/<recipe-version>/
│   ├── cnd/
│   ├── manifest.json
│   ├── checksums.sha256
│   └── validation.json
└── indexes/
```

Never overwrite a release. Bump the recipe version. Keep neural data and copyrighted stimuli apart when their licences differ.

Naming, if/when this goes public: `ds006434/cnd-v0.1.0`.
