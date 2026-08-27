# Storage and publication design

## Principle

Do not commit raw EEG/MEG or generated CND corpora to Git.

Git contains code, metadata, recipes, manifests, checksums, and small synthetic or legally redistributable fixtures. Large inputs, intermediate files, and outputs belong in versioned object storage or DataLad/git-annex.

## Logical object layout

```text
s3://<bucket>/
├── sources/
│   └── <dataset-id>/<source-version>/...
├── work/
│   └── <dataset-id>/<run-id>/...
├── releases/
│   └── <dataset-id>/<recipe-version>/
│       ├── cnd/
│       │   ├── dataStim.mat
│       │   ├── dataSub1.mat
│       │   └── ...
│       ├── manifest.json
│       ├── checksums.sha256
│       ├── validation.json
│       └── README.md
└── indexes/
    ├── releases.json
    └── latest.json
```

The physical layout may shard subjects into subdirectories for very large corpora, but the manifest must expose a stable logical CND collection.

## Storage classes

| Class | Contents | Retention |
|---|---|---|
| Source cache | Exact downloaded source snapshot | Immutable while referenced by a release |
| Working cache | Decompressed files, features, temporary resampling products | Ephemeral and rebuildable |
| Candidate output | Unpublished CND files and validation reports | Retain until pass/fail resolution |
| Release | Validated CND, manifest, checksums, documentation | Immutable |
| Index | Small catalogue of published releases | Versioned and atomically updated |

## Publication rules

1. Upload objects to a unique candidate prefix.
2. Compute and verify SHA-256 checksums after upload.
3. Run validation against the uploaded objects.
4. Write `validation.json` and the final `manifest.json`.
5. Copy or promote the candidate prefix to an immutable release prefix.
6. Update the release index only after every object is verified.
7. Never overwrite an existing release. Publish a new recipe version instead.

## Naming

Recommended release identifier:

```text
<dataset-id>/cnd-v<recipe-major>.<recipe-minor>.<recipe-patch>
```

Example:

```text
ds006434/cnd-v0.1.0
```

The manifest separately records the upstream dataset version and the converter Git commit.

## Access and licensing

- Keep restricted source data in a private source prefix.
- Do not publish a CND derivative if the source data-use agreement prohibits redistribution.
- Separate neural data from copyrighted stimulus assets when their licenses differ.
- Where permitted, publish extracted features without redistributing the original media.
- Record separate `neural_data_license`, `stimulus_license`, and `derived_release_license` values.

## Backend choices

The layout works with AWS S3, Cloudflare R2, Backblaze B2, institutional S3, MinIO, or another S3-compatible service. DataLad/git-annex is also appropriate when distributed scientific-data versioning is more important than web-native object access.

The backend should support:

- multipart and resumable transfers;
- immutable/versioned objects;
- checksum verification;
- range requests;
- lifecycle rules for working data;
- separate public and controlled-access prefixes;
- inventory export for independent verification.
