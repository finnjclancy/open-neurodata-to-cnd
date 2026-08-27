# Open Neurodata to CND

A catalogue and reproducible workflow for converting public, structured EEG, MEG, and selected iEEG datasets into the Continuous-event Neural Data (CND) format.

**Last reviewed:** 28 August 2026

> [!IMPORTANT]
> CND should be generated as a documented analysis derivative. BIDS or the original structured dataset should remain the authoritative source. A neural-data license does not necessarily grant permission to redistribute accompanying movies, audiobooks, novels, or images.

## Executive summary

There is enough structured public EEG/MEG data to build a reusable conversion system rather than a collection of one-off scripts.

The opportunity spans three kinds of scale:

- **Recording hours:** dense naturalistic speech datasets, particularly [EEG-Speech Brain Decoding](https://nemar.org/dataset/on007808).
- **Participants:** the [Healthy Brain Network EEG releases](https://nemar.org/dataset/on005505), clinical EEG archives, sleep studies, and large MEG cohorts.
- **Stimulus trials:** [THINGS-EEG1/2](https://things-initiative.org/) and [Alljoined-1.6M](https://things-initiative.org/).

The highest-leverage engineering approach is:

```text
BIDS / structured source
    -> dataset and license inventory
    -> MNE-BIDS or format-specific loader
    -> subject/session/task/run segmentation
    -> experiment-specific stimulus feature plug-in
    -> time synchronization and resampling
    -> CND dataStim.mat + dataSub*.mat
    -> CND schema and CND-to-MNE round-trip validation
```

## Working vertical slice

The repository now contains an executable, checksum-pinned conversion of
PhysioNet EEG Motor Movement/Imagery subject 1, run 3. It converts a real
64-channel EDF+ recording and its embedded annotations into a strict CND 1.0
neural/stimulus pair, then performs numerical CND-to-MNE reconciliation before
publishing an immutable local manifest.

```bash
uv sync --extra dev
uv run neurodata-to-cnd convert recipes/eegmmidb-s001-r03.json \
  --cache-root cache \
  --output-root outputs
```

The full conversion extra currently resolves CND-MNE from its pinned companion
repository. Public CI therefore runs the metadata, feature, EDF, BrainVision,
and FIF tests without that private dependency; the complete pipeline and public
data integration test run locally. Making CND-MNE publicly installable is the
remaining packaging decision before third parties can execute conversions from
a clean public environment.

The offline suite also exercises EDF, BrainVision, and FIF readers plus MATLAB
v5 and v7.3 CND outputs. See the
[validated vertical-slice report](docs/VERTICAL-SLICE-EEGMMIDB.md) for exact
event counts, checksums, transformations, limitations, and reproduction steps.

## Project structure

The Git repository stores metadata and reproducible instructions—not terabytes of neural recordings.

```text
open-neurodata-to-cnd/
├── catalog/                 # Machine-readable dataset registry and schema
├── recipes/                 # Dataset-specific conversion decisions
├── converters/              # Reusable source and stimulus-feature adapters
├── workflows/               # Local, HPC, and batch orchestration entry points
├── manifests/               # Example and generated provenance manifests
├── schemas/                 # Machine-readable recipe and manifest contracts
├── storage/                 # Object layout and publication rules
├── scripts/                 # Catalogue and repository validation tools
├── tests/                   # Unit, integration, and small-fixture tests
├── docs/                    # Architecture and operating documentation
└── .github/workflows/       # Continuous validation; never bulk data processing
```

See [Architecture](docs/ARCHITECTURE.md), [Storage design](storage/README.md),
and [Recipe format](recipes/README.md).

### Separation of responsibilities

| Layer | Stored in Git | Stored outside Git |
|---|---|---|
| Discovery | Dataset IDs, URLs, versions, licenses, scale estimates | Nothing |
| Source acquisition | Download instructions and checksums | BIDS/EDF/BrainVision/CTF source files |
| Conversion | Recipes, adapters, feature definitions, software environment | Temporary working files |
| Validation | Tests, schemas, expected summaries | Large validation artifacts and logs |
| Publication | Immutable manifests, indexes, checksums | Versioned CND datasets and optional derived features |

The recommended storage backend is an S3-compatible object store or DataLad/git-annex. GitHub Releases may be used for small fixtures, manifests, and documentation, but not for multi-gigabyte corpora.

## Repository-scale discovery sources

These catalogues provide the raw material for a corpus-wide workflow.

| Source | Current scope | Why it matters |
|---|---:|---|
| [NEMAR](https://ww2.nemar.org/) | 755 BIDS datasets, approximately 39,000 participants, 58 TB | Open EEG, MEG, iEEG, and EMG data; mirrors many OpenNeuro datasets and provides quality/HED information. |
| [EEGDash catalogue and API](https://eegdash.org/api/api.html) | Hundreds of indexed public datasets | Machine-readable search by modality, task, subject count, source, and license. |
| [OpenNeuro](https://docs.openneuro.org/user-guide/) | Large public BIDS archive | Public datasets can be browsed and downloaded without an account. |
| [MOABB](https://moabb.neurotechx.com/docs/dataset_summary.html) | 160 curated BCI EEG datasets; 3,627 participants | Dataset-specific loaders already normalize many sources into MNE `Raw`. |
| [PhysioNet](https://physionet.org/about/database/) | Clinical, motor, and sleep physiology archives | Major source for structured EDF EEG and time-aligned annotations. |

NEMAR mirrors OpenNeuro, and catalogues may index raw data, derivatives, or alternate representations separately. Counts and storage sizes must therefore be de-duplicated before aggregation.

## Priority conversion shortlist

### 1. EEG-Speech Brain Decoding — OpenNeuro `ds007808`

- **Dataset:** [NEMAR on007808](https://nemar.org/dataset/on007808) · [OpenNeuro DOI](https://doi.org/10.18112/openneuro.ds007808.v1.0.0)
- **Scale:** approximately 1.575 TB on NEMAR, 312 sessions, and roughly 1,000 recording hours.
- **Content:** synchronized EEG and audio for overt speech production, listening, and covert speech imagery.
- **Structure:** BIDS; multiple EEG acquisition systems; CC0.
- **CND features:** waveform, envelope, spectrogram, speech-production events, word/phoneme events, task condition, and speech embeddings.
- **Caution:** only three densely recorded participants; device and montage normalization will be important.

### 2. Healthy Brain Network EEG — OpenNeuro `ds005505`–`ds005516`

- **Starting point:** [HBN EEG Release 1](https://nemar.org/dataset/on005505)
- **Scale:** eleven releases, approximately 3,155 participants and approximately 2 TB in the indexed releases.
- **Content:** 129-channel EGI EEG across rest, cognitive tasks, sequence learning, visual paradigms, and movie watching.
- **Structure:** BIDS with behavioral data and Hierarchical Event Descriptor annotations; CC BY-SA 4.0.
- **CND features:** event impulses, condition labels, performance variables, visual events, HED-derived features, and—where legally available—movie/audio features.
- **Caution:** commercial movie stimuli may have rights separate from the EEG license.

Release series:

- [`ds005505`](https://openneuro.org/datasets/ds005505)
- [`ds005506`](https://openneuro.org/datasets/ds005506)
- [`ds005507`](https://openneuro.org/datasets/ds005507)
- [`ds005508`](https://openneuro.org/datasets/ds005508)
- [`ds005509`](https://openneuro.org/datasets/ds005509)
- [`ds005510`](https://openneuro.org/datasets/ds005510)
- [`ds005511`](https://openneuro.org/datasets/ds005511)
- [`ds005512`](https://openneuro.org/datasets/ds005512)
- [`ds005513`](https://openneuro.org/datasets/ds005513)
- [`ds005514`](https://openneuro.org/datasets/ds005514)
- [`ds005516`](https://openneuro.org/datasets/ds005516)

### 3. Alljoined-1.6M

- **Dataset:** [THINGS project entry](https://things-initiative.org/) · [Hugging Face repository](https://huggingface.co/datasets/Alljoined/Alljoined-1.6M)
- **Scale:** more than 1.6 million trials, 20 participants, four sessions per participant, approximately 136 GB.
- **Content:** 32-channel EEG sampled at 256 Hz during presentation of 16,740 unique THINGS images.
- **Structure:** raw EEG plus preprocessed NumPy arrays, Parquet metadata, stimuli, questionnaires, and presentation material.
- **CND features:** image onset, concept/category, image identity, semantic dimensions, and model embeddings.
- **Caution:** the THINGS project page currently says license confirmation is pending. Do not redistribute converted data until this is resolved.

### 4. THINGS-EEG2

- **Dataset:** [THINGS-EEG2 project page](https://things-initiative.org/) · [OSF data](https://osf.io/3jk45/)
- **Scale:** 10 participants × 82,160 trials = 821,600 trials over 16,740 image conditions.
- **Content:** raw 64-channel BrainVision EEG, preprocessed occipital data, image set, resting-state data, and pre-extracted model feature maps.
- **CND features:** image onset impulses, category labels, semantic features, and DNN embeddings.
- **Caution:** retain stimulus-image provenance and license metadata separately from the neural data.

### 5. THINGS-EEG1 — OpenNeuro `ds003825`

- **Dataset:** [THINGS-EEG1 project page](https://things-initiative.org/) · [OpenNeuro ds003825](https://openneuro.org/datasets/ds003825)
- **Scale:** 50 participants viewing 22,248 images across 1,854 object concepts.
- **Content:** rapid serial visual presentation at 10 Hz.
- **Structure:** raw BIDS EEG, stimulus presentation logs, and analysis code.
- **CND features:** image onset, object concept, exemplar identity, semantic dimension, and image/model embeddings.
- **Caution:** the high presentation rate requires an explicit convention for continuous runs versus individual CND trials.

### 6. ChineseEEG — OpenNeuro `ds004952`

- **Dataset:** [OpenNeuro mirror and documentation](https://github.com/OpenNeuroDatasets/ds004952)
- **Scale:** 10 participants, each reading Chinese text for approximately 11 hours.
- **Content:** high-density EEG, simultaneous eye tracking, two novels, 115,233 presented characters, character/row/chapter triggers, and text embeddings.
- **Structure:** EEG-BIDS; raw 1 kHz data and several 256 Hz derivatives.
- **CND features:** character/word onset, row and chapter boundaries, lexical variables, eye position, and BERT embeddings.
- **Caution:** verify the redistribution rights for the full novel texts independently of the EEG license.

### 7. Selective-attention natural-speech EEG — OpenNeuro `ds006434`

- **Dataset:** [OpenNeuro ds006434 mirror](https://github.com/OpenNeuroDatasets/ds006434)
- **Scale:** 66 subjects across three experiments and approximately 103 GB in the catalogue.
- **Content:** audiobook listening under diotic, dichotic, attended, and passive conditions.
- **Structure:** EEG-BIDS with detailed events, audio stimuli, analysis code, and precomputed HDF5 regressors.
- **CND features:** attended/unattended envelopes, speech features, trial cues, narrator identity, and attention direction.
- **Caution:** cortical and subcortical montages are represented at different sampling rates, including 1 kHz, 10 kHz, and original 25 kHz acquisitions.

### 8. MEG-MASC

- **Dataset:** [Scientific Data descriptor](https://www.nature.com/articles/s41597-023-02752-5) · [OSF data](https://osf.io/ag3kj/)
- **Scale:** 27 English speakers listening to approximately two hours of stories.
- **Content:** four fictional stories, randomized word lists, and comprehension questions.
- **Structure:** BIDS MEG with public audio, text, word/phoneme onset and offset times, and linguistic annotations; CC0.
- **CND features:** audio envelope/spectrogram, word and phoneme impulses, frequency, surprisal, syntax, and semantic embeddings.
- **Caution:** MEG channel and metadata support must be completed and validated in the CND-MNE converter.

### 9. MEG-SCANS — OpenNeuro `ds006468`

- **Dataset:** [NEMAR on006468](https://www.nemar.org/dataset/on006468) · [OpenNeuro DOI](https://doi.org/10.18112/openneuro.ds006468.v1.1.2)
- **Scale:** 24 participants and approximately 204 GB.
- **Content:** audiobooks, noisy sentences, chirps, hearing screens, MRIs, and empty-room recordings.
- **Structure:** BIDS with raw and MaxFiltered MEG, audio materials, and audio envelopes; CC0.
- **CND features:** audio envelopes, audiobook annotations, intelligibility/noise condition, sentence/chirp events, and hearing measures.
- **Caution:** the pipeline must record whether raw or MaxFiltered data were used.

### 10. THINGS-MEG — OpenNeuro `ds004212`

- **Dataset:** [THINGS-MEG project page](https://things-initiative.org/) · [OpenNeuro ds004212](https://openneuro.org/datasets/ds004212)
- **Scale:** four participants × twelve sessions; approximately 377 GB.
- **Content:** 272-channel CTF MEG with concurrent eye tracking while viewing 22,448 THINGS images.
- **Structure:** BIDS with anatomical MRI and MNE-Python epoch derivatives.
- **CND features:** image onset, object concepts, exemplar identity, eye position, semantic dimensions, and image-model embeddings.
- **Caution:** dense within-participant sampling but only four participants.

### 11. Le Petit Prince Multi-talker — OpenNeuro `ds005345`

- **Dataset:** [OpenNeuro ds005345 mirror](https://github.com/OpenNeuroDatasets/ds005345)
- **Scale:** 25 native Mandarin participants with EEG and fMRI; the EEG experiment is approximately 40 minutes per participant.
- **Content:** single-talker and mixed-talker natural speech, attention conditions, audio, quizzes, and annotations.
- **Structure:** BIDS; 64-channel EEG sampled at 500 Hz.
- **CND features:** attended/unattended speech envelopes, talker identity, linguistic events, visual features, and comprehension responses.
- **Caution:** the full archive size includes 7T fMRI, and book/audio/visual rights require inspection.

### 12. NIMH Healthy Research Volunteer — OpenNeuro `ds005752`

- **Dataset:** [OpenNeuro ds005752 mirror](https://github.com/OpenNeuroDatasets/ds005752) · [NIMH description](https://www.nimh.nih.gov/news/science-updates/2023/nimh-creates-publicly-accessible-resource-with-data-from-healthy-volunteers)
- **Scale:** 1,859 deeply characterized volunteers overall; approximately 633 GB for the multimodal archive. MEG is an optional subset.
- **Content:** MEG battery, MRI, clinical assessments, mood measures, cognition, and physiology.
- **Structure:** BIDS; CC0.
- **CND features:** task events, rest/task condition, sensory stimuli, cognition, and participant covariates.
- **Caution:** do not report the overall participant count as the MEG participant count.

## Additional speech, language, and reading corpora

These datasets are strong CND candidates because their events or continuous stimuli can become synchronized envelopes, spectrograms, word/phoneme impulses, attention labels, or language-model features.

| Dataset | Modality and approximate scale | Potential CND features |
|---|---|---|
| [Continuous-speech masking / subcortical EEG — `ds005407` / `on005408`](https://nemar.org/dataset/on005408) | EEG; 25 participants | Speech envelope, masker condition, attended stream, ABR features |
| [Multiband ABRs to continuous speech — `ds008065`](https://openneuro.org/datasets/ds008065) | EEG; 62 participants | Speech envelope, frequency band, stimulus condition |
| [Music and speech subcortical responses — `ds004356`](https://nemar.org/dataset/on004356) | EEG; 22 participants; approximately 229 GB | Envelope, spectrogram, music/speech condition |
| [Chimeric music — `ds006735`](https://nemar.org/dataset/on006735) | EEG; 27 participants; approximately 207 GB | Acoustic features and chimeric condition variables |
| [Speech decoding: phonemes, words, pseudowords — `ds006104`](https://github.com/OpenNeuroDatasets/ds006104) | EEG; 24 participants | Phoneme/word onset and lexical condition |
| [Inner Speech — `ds003626`](https://ww2.nemar.org/dataset/on003626) | EEG; 10 participants; about 5,640 trials | Cue, imagined word/direction, overt versus inner speech |
| [Chinese Pinyin overt/silent/imagined speech — `ds006465`](https://nemar.org/dataset/on006465) | EEG; 20 participants | Pinyin class, task mode, cue and production timing |
| [Passive natural speech sEEG — `ds004703`](https://nemar.org/dataset/on004703) | iEEG; 10 participants | Envelope, phoneme/word timing, linguistic features |
| [Syntactic and lexical frequency-tagging — `ds003703`](https://nemar.org/dataset/on003703) | MEG; 34 participants; approximately 209 GB | Syntax, lexical variables, frequency-tag structure |
| [Cantonese Little Prince EEG — `ds004718`](https://nemar.org/dataset/on004718) | EEG; 51 older participants; approximately 117 GB | Acoustic and linguistic annotations |
| [French Little Prince listening — `ds007523`](https://nemar.org/dataset/on007523) | MEG; 58 participants; approximately 479 GB | Envelope, word/phoneme timing, linguistic embeddings |
| [French Little Prince reading — `ds007524`](https://nemar.org/dataset/on007524) | MEG; 50 participants; approximately 322 GB | Word onset, visual presentation, language features |
| [BCCWJ Japanese reading EEG — `ds007753`](https://nemar.org/dataset/on007753) | EEG; 41 participants; approximately 96 GB | Word/character timing, Japanese lexical features |
| [BCCWJ Japanese reading MEG — `ds007763`](https://nemar.org/dataset/on007763) | MEG; 35 participants; approximately 178 GB | Word/character timing, Japanese lexical features |
| [Appleseed audiobook — `ds007870`](https://openneuro.org/datasets/ds007870) | MEG; 13 participants; approximately 44 GB | Audio envelope, word/phoneme timing, embeddings |
| [Chinese natural reading / TMNRED — `ds005383`](https://nemar.org/dataset/on005383) | EEG; 30 participants; approximately 19 GB | Word/character onset and linguistic variables |
| [Silent visual reading — `ds007058`](https://nemar.org/dataset/on007058) | EEG; 10 participants | Visual word onset, lexical variables, eye movements |
| [Brain Treebank](https://nemar.org/dataset/nm000253) | iEEG; approximately 276 GB | Movie-language events, word timing, linguistic features |

## Other structured experimental corpora

| Dataset | Modality and scale | Notes |
|---|---|---|
| [Forrest Gump MEG — `ds003633`](https://nemar.org/dataset/on003633) | MEG; 12 participants; approximately 166 GB | Naturalistic film and noise; movie rights must be handled separately. |
| [Reality-TV naturalistic MEG — `ds005346`](https://nemar.org/dataset/on005346) | MEG; 30 participants; approximately 121 GB | Rich audiovisual experiment; media-rights caveat. |
| [Cross-modal oddball — `ds004574`](https://openneuro.org/datasets/ds004574) | EEG; 146 participants | BIDS events and patient/control cohorts make event conversion straightforward. |
| [Audiovisual speech memory — `ds006334`](https://nemar.org/dataset/on006334) | MEG; 30 participants; approximately 185 GB | Audiovisual speech and memory-condition features. |
| [Essex EEG Movie Memory — `ds006142`](https://nemar.org/dataset/on006142) | EEG; 27 participants | Movie-memory paradigm; verify media availability. |
| [Naturalistic simultaneous EEG-fMRI — `nm000254`](https://nemar.org/dataset/nm000254) | EEG plus fMRI; 22 participants; approximately 275 GB | Verify the dataset license and included stimulus materials. |

## Massive clinical, sleep, and resting-state corpora

These contain enormous signal volumes but are weaker semantic matches for conventional stimulus-response CND. They should use a separately named **continuous-annotation CND profile** based on seizures, sleep stages, diagnoses, or conditions.

| Corpus | Scale and structure | Access status | Possible CND representation |
|---|---|---|---|
| [TUH EEG Corpus](https://isip.piconepress.com/projects/nedc/html/tuh_eeg/) | 26,846 clinical EDF recordings with physician reports | Registration and signed access form | Recording windows, montage, clinical annotations, normal/abnormal or seizure labels |
| [CHB-MIT Scalp EEG](https://physionet.org/content/chbmit/1.0.0/) | 42.6 GB; 182 annotated seizures | Open, ODC-By 1.0 | Seizure onset/offset, state, channel metadata |
| [EEG Motor Movement/Imagery](https://physionet.org/content/eegmmidb/1.0.0/) | 109 participants; 14 EDF runs each | Open | Motor cue, executed/imagined action, rest, run condition |
| [Siena Scalp EEG](https://physionet.org/content/siena-scalp-eeg/1.0.0/) | Clinical epilepsy EEG in EDF | Open | Seizure onset/offset and clinical condition |
| [Sleep Heart Health Study](https://sleepdata.org/datasets/shhs/pages/04-dataset-introduction.md) | Polysomnography from 5,804 shared participants | Account and DUA required | Sleep stage, arousal, apnea, respiratory and cardiac annotations |
| [Open MEG Archive / OMEGA](https://www.mcgill.ca/bic/neuroinformatics/omega) | 644 participants; approximately 1,800 BIDS resting-state recordings | Controlled access and ethics approval | Rest condition, clinical cohort, questionnaire variables |
| [CamCAN MEG](https://opendata.mrc-cbu.cam.ac.uk/projects/camcan/) | Approximately 647 BIDS MEG participants | Application and institutional storage restrictions | Rest, sensorimotor and sensory-task features |
| [Human Connectome Project MEG](https://megcore.nih.gov/index.php/OpenAccess_MEG) | Large structured task/rest MEG resource | Registration and data-use terms | Task events, rest, sensory and language features |

## Proposed feature plug-ins

### Continuous speech and music

- Waveform and onset strength
- Broadband and band-limited envelopes
- Spectrogram or cochleagram
- Phoneme, syllable, word, sentence, and speaker-change impulses
- Word frequency, surprisal, entropy, syntax, and embeddings
- Attended and unattended streams

### Reading

- Character, word, line, page, and chapter onsets
- Lexical frequency, length, part of speech, and surprisal
- Text-model embeddings
- Eye position, fixation, and saccade features when available

### Images and video

- Image/frame onset impulses
- Object concept, exemplar, category, and semantic dimensions
- Vision-model embeddings
- Scene cuts, object detections, optical flow, and audio features
- Eye tracking and behavioral responses

### ERP and BCI tasks

- Target/non-target impulses
- Cue and response onsets
- Class labels and feedback
- Accuracy and reaction time

### Clinical and sleep data

- Seizure and abnormal-event onset/offset
- Sleep stage and arousal annotations
- Clinical condition and recording context
- Physiological covariates

Resting-state recordings should not be given fabricated stimulus features. Either exclude them from stimulus-response CND or define an explicit annotation-only profile.

## Recommended implementation order

1. **Reference EEG conversion:** [selective-attention speech `ds006434`](https://github.com/OpenNeuroDatasets/ds006434) or [ChineseEEG `ds004952`](https://github.com/OpenNeuroDatasets/ds004952).
2. **Scale test:** [EEG-Speech Brain Decoding `ds007808`](https://nemar.org/dataset/on007808).
3. **Visual/event generalization:** [THINGS-EEG1/2](https://things-initiative.org/) and, after its license is confirmed, Alljoined-1.6M.
4. **Cross-study breadth:** all eleven Healthy Brain Network EEG releases.
5. **MEG extension:** [MEG-MASC](https://www.nature.com/articles/s41597-023-02752-5), then [MEG-SCANS](https://www.nemar.org/dataset/on006468) and [THINGS-MEG](https://things-initiative.org/).
6. **Separate profiles:** clinical/sleep annotation CND and iEEG CND.

## Dataset intake checklist

Before a dataset is accepted into a conversion run, record:

- [ ] Canonical dataset ID, DOI, version, and source URL
- [ ] Whether the source is original or a mirror
- [ ] Neural-data license
- [ ] Independent license/provenance for every stimulus asset
- [ ] Modality and acquisition system
- [ ] Participants, sessions, tasks, runs, and recording duration
- [ ] Raw versus derivative data selection
- [ ] Signal format, channel types, units, montage, and sampling rates
- [ ] Completeness of BIDS events and sidecars
- [ ] Availability of audio, video, images, text, and presentation logs
- [ ] Synchronization delays and corrected trigger timing
- [ ] Candidate CND trial-boundary policy
- [ ] Candidate stimulus features
- [ ] Storage and compute requirements
- [ ] Conversion and validation status

## Validation requirements

Every converted corpus should pass:

1. BIDS/source-file validation before conversion.
2. Channel count, type, unit, name, and sampling-rate checks.
3. Event count and timing comparison against the source.
4. Stimulus/neural duration and synchronization checks.
5. CND schema validation.
6. CND-to-MNE loading tests.
7. Numerical and metadata round-trip tests where possible.
8. A machine-readable conversion manifest containing source DOI/version and transformation parameters.

## Scope exclusions and overlap

Known datasets already distributed through the public CND catalogue are excluded from the new-source shortlist.

In particular, [Lalor Natural Speech / OpenNeuro `ds004408`](https://openneuro.org/datasets/ds004408) should be treated as an existing CND compatibility case, not a new BIDS-to-CND target. KUL auditory-attention datasets already represented in CND should be de-duplicated in the same way.

## Status

This repository currently contains the researched corpus directory, the first machine-readable registry, an example conversion recipe, provenance/storage conventions, and catalogue validation. It does **not** host or redistribute neural or stimulus data.

Dataset catalogues change frequently. Re-query the live source and verify the version, license, access status, included stimuli, and total storage requirement before downloading at scale.
