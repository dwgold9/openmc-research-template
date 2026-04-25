# OpenMC Research Template

A modular, reproducible OpenMC workflow template for scientific neutronics research.

This repository provides a structured foundation for computational nuclear engineering projects. It enforces a strict separation between model definition, simulation execution, artifact construction, and metric evaluation, enabling scalable, reproducible research without script duplication.

The goal is to provide a durable research workflow that can serve as the starting point for future OpenMC-based projects.

---

## Design Philosophy

This template is built around several principles:

1. **Separation of concerns**
   - Model construction
   - Tally registration
   - Simulation execution
   - Artifact generation
   - Metric reduction
   are all independent layers.

2. **Simulation–analysis decoupling**
   - `simulate.py` runs transport.
   - `analyze.py` processes results.
   - Neither performs the other’s responsibility.

3. **YAML-driven studies**
   Each study is defined by a `study.yaml` file describing:
   - model selection
   - parameters
   - tallies
   - metrics

4. **Reproducibility**
   Each study lives in its own directory.
   Outputs are generated, not version-controlled.

5. **Extensibility**
   New physics models, artifacts, or metrics can be added without modifying the execution engine.

---

## Repository Structure

```
openmc-research-template/
│
├── core/
│   ├── models/
│       ├── registry.py
│       └── model_example.py
│   ├── tallies/
│       ├── registry.py
│       └── tally_example.py
│   ├── artifacts/
│       ├── registry.py
│       └── artifact_example.py
│   ├── metrics/
│       ├── registry.py
│       └── metric_example.py
│   ├── simulate.py
│   └── analyze.py
|
├── runs/
│   └── example_run/
│       ├── cases/
│       └── study_frozen.yaml
│
├── studies/
│   └── example_study/
│       ├── study.yaml
│       └── output/
│
├── environment.yml
├── pyproject.toml
└── README.md
```

---

## Workflow

### 1. Define a Study

Create a directory under `studies/`:

```
studies/my_study/
    study.yaml
```

Example:

```yaml
name: base_case

model: example_model

params:
  slab_width: 2.0

tallies:
  - flux_spectrum
```

---

### 2. Run Simulation

```
python -m research.cli.simulate --study my_study
```

Optional geometry plot only:

```
python -m research.cli.simulate --study my_study -p
```

This will:
- Build the model
- Register tallies
- Export XML
- Run OpenMC
- Store statepoint files in `studies/my_study/output/`

---

### 3. Analyze Results

```
python -m research.cli.analyze --study my_study
```

This will:
- Load statepoint
- Build artifacts
- Compute metrics
- Save `metrics.json`
- Generate figures

---

## Core Concepts

### Models
Define geometry, materials, and settings.
Return an `openmc.Model` object.
No analysis logic allowed.

### Tallies
Declarative tally definitions.
Attached during simulation runtime.

### Artifacts
Structured physical quantities derived from statepoints.
Examples:
- Flux maps
- Reaction rate densities
- Energy spectra

Artifacts are not scalars.

### Metrics
Reduced scalar quantities derived from artifacts.
Examples:
- keff
- spectral index
- gain factors

Metrics are suitable for study comparison.

---

## What This Template Is Not

This is not:
- A single experiment repository
- A collection of ad-hoc scripts
- A notebook-based workflow

It is a structured computational research runtime.

---

## Recommended Usage

For a new project:

1. Fork this repository.
2. Rename the package under `src/`.
3. Replace the contents of:
   - `models/`
   - `tallies/`
   - `artifacts/`
   - `metrics/`
4. Keep `core/` intact unless architectural improvements are required.

---

## Environment

Create the environment:

```
conda env create -f environment.yml
conda activate openmc-research
```

---

## Version Control Guidelines

Add to `.gitignore`:

```
*.h5
output/
```

Do not commit:
- Statepoint files
- Large data outputs
- Derived artifacts

Commit:
- Study definitions
- Model definitions
- Metric logic

---

## Intended Audience

This template is designed for:

- Nuclear engineering graduate research
- OpenMC-based reactor physics studies
- Reproducible parametric investigations
- Structured neutronics development workflows

---

## License

Add an appropriate open-source license if publishing publicly.

---

## Citation

If this template is used in academic work, cite the associated publication or repository as appropriate.

