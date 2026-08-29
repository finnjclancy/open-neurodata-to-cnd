# Workflows

## Implemented corpus commands

```text
neurodata-to-cnd plan <corpus-recipe> --output <plan>
neurodata-to-cnd batch <plan> [--pilot] [--recording sub-NNN]
neurodata-to-cnd status <corpus-output-directory>
neurodata-to-cnd retry <plan>
```

`batch` is sequential by default to bound memory, disk, and remote-service load.
Completed manifests are reconciled with state and skipped. Failures are recorded
per recording and do not stop later jobs. Successfully validated subject source
files are removed unless `--keep-source` is provided.

## Longer-term commands

```text
neurodata-cnd catalog validate
neurodata-cnd source inspect ds006434
neurodata-cnd source fetch ds006434 --subject diotic01
neurodata-cnd recipe validate recipes/ds006434.json
neurodata-cnd convert recipes/ds006434.json --subject diotic01
neurodata-cnd validate <candidate-output>
neurodata-cnd publish <candidate-output> --release cnd-v0.1.0
```

## Execution modes

- **Fixture mode:** tiny committed or downloaded sample used by tests.
- **Pilot mode:** one complete participant processed locally.
- **Batch mode:** independent subject/session/task/run jobs executed locally, on HPC, or through cloud batch.
- **Audit mode:** metadata and validation only; no source download.

## Resumability

Every stage writes a small state record with input checksums, parameters, output checksums, start/end times, software commit, and outcome. A completed stage is reused only when those inputs still match.

## Failure policy

- Download failures are retried without discarding verified parts.
- Scientific ambiguity stops the recipe; it is never guessed silently.
- One participant failure does not invalidate completed independent jobs.
- Outputs with failed validation remain under a non-public candidate prefix.
- Publication is an explicit final action, not a side effect of conversion.
