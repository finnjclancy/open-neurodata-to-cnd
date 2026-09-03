# Workflows

What actually exists:

```text
neurodata-to-cnd plan <corpus-recipe> --output <plan>
neurodata-to-cnd batch <plan> [--pilot] [--recording sub-NNN]
neurodata-to-cnd status <corpus-output-directory>
neurodata-to-cnd retry <plan>
```

`batch` runs one recording at a time. Finished jobs are skipped. A failure is recorded and the rest keep going. Source files are deleted after a successful validate unless you pass `--keep-source`.

Not built yet: a separate `publish` command, object-store upload, or `source inspect`.

Jobs are meant to resume. If the inputs have not changed, a completed recording is left alone. Do not guess scientific meaning here — stop and fix the recipe.
