# Superseded validation results

These historical results used ridge cross-validation followed by Tikhonov
final training. They demonstrate that the files loaded and the upstream
functions executed, but parameter selection and final fitting were inconsistent.

The corrected driver explicitly uses ridge for both stages. Its rerun is in
[`matlab-preprocessing-ridge`](../matlab-preprocessing-ridge/). Keep these older results only as
an audit trail; do not use their prediction scores as the current validation.
