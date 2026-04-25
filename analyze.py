from pathlib import Path
import argparse
import yaml

# Ensure registries populate
import core.metrics
from core.metrics.registry import (
    METRICS_REGISTRY, get_metric_blocks, Scope
)

import core.artifacts
from core.artifacts.registry import (
    ARTIFACTS_REGISTRY, get_artifact_blocks
)

import core.analysis
from core.analysis import *


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

def analyze(cli_args):

    ## read command-line arguments
    cli_study_name = cli_args.study
    
    studies_root = Path("studies")
    # ------------------------
    # load config
    # ------------------------
    config_path = studies_root / cli_study_name / "study.yaml"
    with open(config_path, "r") as f:
        cfg = yaml.safe_load(f)


    # -----------------------
    # required fields
    # -----------------------
    study_name = cfg["name"]

    # direct to study/ and runs/
    study_root = studies_root / study_name
    runs_root = Path("runs") / study_name
    
    context = build_context(runs_root)
    # -----------------------
    # optional fields
    # -----------------------
    metric_entries = cfg.get("metrics", [])
    artifact_entries = cfg.get("artifacts", {})

    results_store = {}

    # Optional: tallies list if you keep it in YAML
    available_tallies = set(
        cfg.get("available_tallies", [])
    )

    # ------------------------------
    # METRICS
    # ------------------------------
    metric_blocks = get_metric_blocks(metric_entries)

    for block in metric_blocks:
        if block.scope == Scope.MEMBER:
            for case in context.cases:
                for member in case.members:
                    block.execute(member)

        elif block.scope == Scope.CASE:
            for case in context.cases:
                block.execute(case)

        elif block.scope == Scope.STUDY:
            block.execute(context)

    print(f"Wrote metrics.yaml")

    # ------------------------------
    # ARTIFACTS
    # ------------------------------
    artifact_blocks = get_artifact_blocks(artifact_entries)

    for block in artifact_blocks:
        if block.scope == Scope.MEMBER:
            for case in context.cases:
                for member in case.members:
                    block.execute(member)

        elif block.scope == Scope.CASE:
            for case in context.cases:
                block.execute(case)

        elif block.scope == Scope.STUDY:
            block.execute(context)

    print("Analysis complete.")


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("study", help="results/<study>/")
    cli_args = parser.parse_args()

    analyze(cli_args)


if __name__ == "__main__":
    main()