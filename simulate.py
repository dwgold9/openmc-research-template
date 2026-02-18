import argparse
import itertools
import os
from pathlib import Path
import shutil
import yaml
import json

# model registration
from core import models
from core.models.registry import MODEL_REGISTRY, get_model_block

# observables registration
from core import tallies
from core.tallies.registry import TALLIES_REGISTRY, get_tally_blocks

# pipeline stages
from core import pipeline
from core.pipeline.attach import attach_tallies
from core.pipeline.assemble import assemble_xml
from core.pipeline.run import run_simulation
from core.pipeline.plot import plot_slice
from core.pipeline.scrape import scrape_results


# ---------------------------------------------------------
# utility: cartesian expansion of parameter sweeps
# ---------------------------------------------------------

def expand_parameters(param_dict):
    """
    Converts a dict of parameters into a list of concrete configs.
    Scalars become length-1 lists.
    """
    if not param_dict:
        return [{}]

    keys = list(param_dict.keys())
    values = []

    for k in keys:
        v = param_dict[k]
        if isinstance(v, (list, tuple)):
            values.append(v)
        else:
            values.append([v])

    combos = []
    for prod in itertools.product(*values):
        combos.append(dict(zip(keys, prod)))

    return combos


# ---------------------------------------------------------
# utility: stable case naming
# ---------------------------------------------------------

def case_name(index):
    return f"case_{index:04d}"


# ---------------------------------------------------------
# main orchestration
# ---------------------------------------------------------

def main(cli_args):

    ## read command-line arguments
    cli_study_name = cli_args.study
    plot_only = cli_args.plot

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
    model_name = cfg["model"]

    # -----------------------
    # optional fields
    # -----------------------
    tally_entries = cfg.get("tallies", [])
    params = cfg.get("params", {})

    # normalize plots
    plot_entries = cfg.get("plot", {})
    if isinstance(plot_entries, list):
        plots = plot_entries
    elif isinstance(plot_entries, dict):
        plots = [{'plot': plot_entries}]
    else:
        raise TypeError("plot must be a dict or list")

    # -----------------------
    # read blocks
    # -----------------------
    model_block = get_model_block(model_name)
    tally_blocks = get_tally_blocks(tally_entries)
    # ------------------------
    # prepare result directory
    # ------------------------
    runs_root = Path("runs") / study_name
    cases_root = runs_root / "cases"

    cases_root.mkdir(parents=True, exist_ok=True)

    # freeze config for reproducibility
    shutil.copy(config_path, runs_root / "study_frozen.yaml")

    # ------------------------
    # expand parameter sweep
    # ------------------------
    cases = expand_parameters(params)

    print(f"Study: {study_name}")
    print(f"Model: {model_name}")
    print(f"Total cases: {len(cases)}")

    # ------------------------
    # loop over cases
    # ------------------------
    for i, params in enumerate(cases):

        name = case_name(i+1)
        case_dir = cases_root / name
        case_dir.mkdir(exist_ok=True)

        # save parameter realization
        with open(case_dir / "params.json", "w") as f:
            json.dump(params, f, indent=2)

        # ------------------------
        # attach tallies
        # ------------------------
        model = model_block(params)
        print(params)
        for block in tally_blocks:
            block.attach(model)

        # ------------------------
        # build model + xml
        # ------------------------
        assemble_xml(model, case_dir)

        # ------------------------
        # plot geometry
        # ------------------------
        for p in plots:
            name, plot_cfg = next(iter(p.items()))
            plot_slice(model, case_dir,
                       name, **plot_cfg)
        if plot_only:
            continue

        # ------------------------
        # run simulation
        # ------------------------
        run_simulation(
            case_dir=case_dir,
        )

    print("Run complete.")


# ---------------------------------------------------------
# CLI
# ---------------------------------------------------------

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("study", help="Name of study")
    parser.add_argument("-p", "--plot",
                        action="store_true",
                        help="Plot geometry only (no simulation)")

    args = parser.parse_args()
    main(args)