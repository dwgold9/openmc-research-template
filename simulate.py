import argparse
from pathlib import Path
import yaml
import json

# model registration
from core import models
from core.models.registry import MODEL_REGISTRY, get_model_block

# tally registration
from core import tallies
from core.tallies.registry import TALLIES_REGISTRY, get_tally_blocks

from core import metrics
from core.metrics.registry import METRICS_REGISTRY, get_metric_blocks

# pipeline stages
from core import pipeline
from core.pipeline.case import expand_ensemble
from core.pipeline.meta import StudyMeta

## drivers
from core.drivers import run_parametric, run_optimization

## utils
from core.utils import *


def normalize_config(cfg):

    cfg = dict(cfg)

    # already new-style
    if "study" in cfg or "parametric" in cfg:
        return cfg

    parameters = cfg.get("parameters", {})

    study = {}
    variables = {}

    for k, v in parameters.items():

        if isinstance(v, (list, tuple)) and len(v) > 1:
            variables[k] = v
        else:
            study[k] = v

    cfg["study"] = study

    if variables:
        cfg["parametric"] = {
            "mode": "outer",
            "variables": variables,
        }
    
    else:
        cfg["parametric"] = {
            "mode": "outer",
            "variables": {},
        }

    # remove legacy
    cfg.pop("parameters", None)

    return cfg

# ---------------------------------------------------------
# main
# ---------------------------------------------------------

def main(cli_args):

    cli_study_name = cli_args.study
    plot_only = cli_args.plot
    isrun = not cli_args.tally

    studies_root = Path("studies")

    study_yaml_path = studies_root / cli_study_name / "study.yaml"

    with open(study_yaml_path, "r") as f:
        cfg = yaml.safe_load(f)

    cfg = normalize_config(cfg)

    study_name = cfg["name"]
    model_name = cfg["model"]

    tally_entries = cfg.get("tallies", [])
    study_params = cfg.get("study", {})
    parametric = cfg.get("parametric", {})
    optimization = cfg.get("optimization", None)
    ensemble = cfg.get("ensemble", {})

    plot_entries = cfg.get("plot", {})
    if isinstance(plot_entries, list):
        plots = plot_entries
    elif isinstance(plot_entries, dict):
        plots = [{'plot': plot_entries}]
    else:
        raise TypeError("plot must be a dict or list")

    model_block = get_model_block(model_name)
    tally_blocks = get_tally_blocks(tally_entries)
    metric_blocks = get_metric_blocks(cfg.get("metrics", []))

    runs_root = Path("runs") / study_name
    guard_runs_root(runs_root, cli_args.force, cli_args.resume)

    if cli_args.resume:
        handle_resume_with_revisioning(study_yaml_path, runs_root)
    else:
        freeze_study_yaml(study_yaml_path, runs_root)

    members = expand_ensemble(ensemble)

    study_meta = StudyMeta(runs_root)

    # ------------------ OPTIMIZATION ------------------

    if optimization:

        run_optimization(
            study_params,
            optimization,
            study_meta,
            model_block,
            tally_blocks,
            metric_blocks,
            plots,
            members,
            runs_root,
            plot_only,
            isrun,
        )

        print("Execution complete.")
        return

    # ------------------ PARAMETRIC ------------------

    run_parametric(
        study_params,
        parametric,
        study_meta,
        model_block,
        tally_blocks,
        metric_blocks,
        plots,
        members,
        runs_root,
        plot_only,
        isrun,
    )

    print("Execution complete.")


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

def parse_cli():
    parser = argparse.ArgumentParser()
    parser.add_argument("study", help="Name of study")
    parser.add_argument("-p", "--plot", action="store_true")
    parser.add_argument("-t", "--tally", action="store_true")

    parser.add_argument("--force", action="store_true")
    parser.add_argument("--resume", action="store_true")

    return parser.parse_args()


if __name__ == "__main__":
    cli_args = parse_cli()
    main(cli_args)