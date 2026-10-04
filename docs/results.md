# Recorded results

Local conversions, not published dataset releases. These results precede the
repository cleanup; they are not a fresh run of every corpus.

| Dataset | Recordings | Samples | Layout |
| --- | ---: | ---: | --- |
| PhysioNet EEGMMIDB, subject 1 / run 3 | 1 | 20,000 | 64 EEG channels, 160 Hz |
| OpenNeuro ds004574, conversion 0.2.0 | 146 | 55,877,200 | 63–66 EEG channels, 500 Hz |
| ERP CORE nm000132, conversion 0.4.0 | 240 | 139,146,240 | 30 EEG + 3 EOG channels, 1024 Hz |

All passed source checksums, planned dimensions, CND checks, MATLAB read-back,
and numerical comparisons. ERP CORE also passed auxiliary-channel and electrode
coordinate round trips. Conversion retains source EEG without preprocessing.

ERP CORE contains 40 participants across six tasks: MMN, N170, N2pc, N400, P3,
and flankers. Its event tables use one-based sample indices; recipes subtract one.
Maximum recorded onset error: 0.00005 s. ds004574's recorded error was zero.

## MATLAB check

All 240 ERP CORE outputs passed configured CNSP preprocessing and mTRF execution
in MATLAB R2026a. A temporal response function (TRF) is a regression using delayed
stimulus values to predict EEG. The driver filters to 1–8 Hz, downsamples to
64 Hz, interpolates bad channels, and uses average reference. It uses all stimulus
features, trims the idle tail, then fits ridge regression on four blocks and
predicts a fifth with lags −100 to 600 ms.

This establishes format and execution compatibility. Preprocessing occurs before
blocking; it is not a leakage-controlled scientific performance evaluation.
The interactive upstream tutorials were not run unchanged.

[Audit](evidence/matlab-audit.json) records the pinned upstream revision and
historical script hashes. [Installation summary](evidence/installation.json)
records the clean environment and wheel checks from 20 September 2026.
Detailed per-recording logs and historical plans remain in Git history; new runs write to `outputs/`.
Reproduction commands are in [validation](validation.md).

## Corpus content hashes

These hash recording identities and arrays, excluding MATLAB header timestamps.

```text
ds004574  d13cd98fa4f56835a7d1d7665ccaacaf66da7d7fa0316b232bddcd57738c6831
nm000132  a8d604f2cc09c55fdb7afbc86973771c6142a4363930d772de015cf786814c68
```
