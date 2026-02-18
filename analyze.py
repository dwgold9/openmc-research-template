from pathlib import Path
import argparse
import yaml

# Ensure registries populate
import core.metrics
from core.metrics.registry import (
    METRICS_REGISTRY,
)

import core.artifacts
from core.artifacts.registry import (
    ARTIFACTS_REGISTRY,
)


# ---------------------------------------------------------
# Utilities
# ---------------------------------------------------------

def load_yaml(path):
    with open(path, "r") as f:
        return yaml.safe_load(f)


def write_yaml(path, data):
    with open(path, "w") as f:
        yaml.safe_dump(data, f, sort_keys=False)


# ---------------------------------------------------------
# Context Builder
# ---------------------------------------------------------

def build_context(study_results_dir):

    study_results_dir = Path(study_results_dir)

    runs_dir = study_results_dir / "runs"

    cases = []

    if runs_dir.exists():
        for case_dir in sorted(runs_dir.iterdir()):
            if case_dir.is_dir():
                cases.append({
                    "case_dir": case_dir,
                    "statepoint": case_dir / "statepoint.h5",
                    "params": case_dir / "params.json",
                })

    context = {
        "study_dir": study_results_dir,
        "runs_dir": runs_dir,
        "cases": cases,
    }

    return context


# ---------------------------------------------------------
# Requirement Checking
# ---------------------------------------------------------

def check_metric_requirements(func, available_observables):

    req = getattr(func, "requires_observables", [])

    missing = [r for r in req if r not in available_observables]

    if missing:
        raise RuntimeError(
            f"Result '{func.__name__}' missing observables: {missing}"
        )


def check_artifact_requirements(func, results_store):

    req = getattr(func, "requires_results", [])

    missing = [r for r in req if r not in results_store]

    if missing:
        raise RuntimeError(
            f"Deliverable '{func.__name__}' missing results: {missing}"
        )


# ---------------------------------------------------------
# Processing Pipeline
# ---------------------------------------------------------

def process(study_name):
    studies_root = Path("studies")
    # load analysis
    study_root = studies_root / study_name
    analysis_path = study_root / 'analysis.yaml'
    analysis = load_yaml(analysis_path)

    context = build_context(study_root)

    results_store = {}

    # Optional: observables list if you keep it in YAML
    available_observables = set(
        analysis.get("available_observables", [])
    )

    # ------------------------------
    # METRICS
    # ------------------------------
    for entry in analysis.get("metrics", []):

        if isinstance(entry, dict):
            name = entry["name"]
            cfg = entry
        else:
            name = entry
            cfg = {}

        if name not in METRICS_REGISTRY:
            raise RuntimeError(f"Unknown result '{name}'")

        func = METRICS_REGISTRY[name]

        check_metric_requirements(func, available_observables)

        print(f"[METRIC] {name}")

        output = func(context, cfg)

        results_store[name] = output

    # Write results.yaml at study root
    metrics_yaml_path = Path(study_results_dir) / "metrics.yaml"
    write_yaml(metrics_yaml_path, results_store)

    print(f"Wrote metrics.yaml → {metrics_yaml_path}")

    # ------------------------------
    # DELIVERABLES
    # ------------------------------
    for entry in analysis.get("artifacts", []):

        if isinstance(entry, dict):
            name = entry["name"]
            cfg = entry
        else:
            name = entry
            cfg = {}

        if name not in ARTIFACTS_REGISTRY:
            raise RuntimeError(f"Unknown deliverable '{name}'")

        func = ARTIFACTS_REGISTRY[name]

        check_artifact_requirements(func, results_store)

        print(f"[ARIFACT] {name}")

        func(context, cfg, results_store)


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

def main():

    parser = argparse.ArgumentParser()
    parser.add_argument("study_results_dir", help="results/<study>/")

    args = parser.parse_args()

    process(args.study_results_dir)


if __name__ == "__main__":
    main()