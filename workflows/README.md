# Workflows

## Commands to converge on

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
