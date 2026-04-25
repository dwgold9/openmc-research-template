from pathlib import Path
import yaml
import json
import copy
import itertools

# pipeline stages
from core import pipeline
from core.pipeline.meta import CaseMeta, execute_member
from archive.core.pipeline.assemble import assemble_xml
from archive.core.pipeline.run import run_simulation
from archive.core.pipeline.plot import plot_slice
from core.pipeline.scrape import load_statepoint
from core.analysis.scope import MemberContext, CaseContext

## utils
from core.utils import *

# ---------------------------------------------------------
# utility: cartesian expansion of parameter sweeps
# ---------------------------------------------------------

def expand_parameters(param_dict):
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

def expand_parametric(parametric_cfg):

    if not parametric_cfg:
        return [{}]

    mode = parametric_cfg.get("mode", "outer")
    variables = parametric_cfg.get("variables", {})

    if not variables:
        return [{}]

    keys = list(variables.keys())
    values = list(variables.values())

    if mode == "outer":
        return [
            dict(zip(keys, combo))
            for combo in itertools.product(*values)
        ]

    elif mode == "inner":
        return [
            dict(zip(keys, combo))
            for combo in zip(*values)
        ]

    else:
        raise ValueError(f"Unknown parametric mode: {mode}")


def expand_ensemble(ensemble_cfg):
    if not ensemble_cfg:
        return [{}]

    members = []
    grouped = all(isinstance(v, dict) for v in ensemble_cfg.values())

    if grouped:
        for group_name, group_params in ensemble_cfg.items():
            combos = expand_parameters(group_params)
            for combo in combos:
                members.append({"_group": group_name, **combo})
    else:
        combos = expand_parameters(ensemble_cfg)
        for combo in combos:
            members.append(combo)

    return members


# ---------------------------------------------------------
# naming
# ---------------------------------------------------------

def set_case_name(index):
    return f"case{index:03d}"

def set_member_name(index):
    return f"member{index:03d}"



# ---------------------------------------------------------
# CORE: evaluate a case (reusable)
# ---------------------------------------------------------
def evaluate_case(
    case_params,
    members,
    model_block,
    tally_blocks,
    metric_blocks,
    plots,
    runs_root,
    case_name,
    plot_only,
    isrun,
):

    case_dir = runs_root / case_name
    case_dir.mkdir(exist_ok=True)

    case_meta = CaseMeta(case_dir)

    # ----------------------------------------
    # Save case params
    # ----------------------------------------
    with open(case_dir / "case_params.json", "w") as f:
        json.dump(case_params, f, indent=2)

    member_dirs = []
    member_contexts = []

    # ----------------------------------------
    # MEMBER LOOP
    # ----------------------------------------
    for j, member_params in enumerate(members):

        member_name = set_member_name(j + 1)
        member_dir = case_dir / member_name
        member_dir.mkdir(exist_ok=True)

        member_dirs.append(member_dir)

        run_dir = member_dir / "run"
        run_dir.mkdir(exist_ok=True)

        msment_dir = member_dir / "measurements"
        msment_dir.mkdir(exist_ok=True)

        # merge params
        params = {**case_params, **member_params}

        # path to executable
        openmc_exec = params.get("openmc_exec", "openmc4d")

        # save resolved params
        with open(member_dir / "resolved_params.json", "w") as f:
            json.dump(params, f, indent=2)

        # build model
        model = model_block(params)

        # isolate tally state
        local_tallies = [copy.deepcopy(t) for t in tally_blocks]

        for tally in local_tallies:
            tally.configure(params)
            if not tally.should_apply(params):
                continue
            tally.attach(model)

        # optional model preparation
        prepare = getattr(model, "prepare", None)
        if prepare is not None and not plot_only:
            prepare(run_dir)

        assemble_xml(model, run_dir)

        # ----------------------------------------
        # MEMBER EXECUTION
        # ----------------------------------------
        def plot_member():
            for p in plots:
                plot_name, plot_cfg = next(iter(p.items()))
                plot_slice(model, member_dir, plot_name, **plot_cfg)

            if plot_only:
                return

        def run_member():

            plot_member()

            if plot_only:
                return

            if isrun:
                sp = run_simulation(model=model, 
                                    run_dir=run_dir,
                                    openmc_exec=openmc_exec)
            else:
                sp = load_statepoint(model, run_dir)

            for t in local_tallies:
                t.export(sp, msment_dir)

        if not plot_only:
            execute_member(member_dir, params, run_member)
        else:
            plot_member()

        # ----------------------------------------
        # Build MemberContext (USE EXISTING CLASS)
        # ----------------------------------------
        member_contexts.append(
            MemberContext(
                member_id=member_name,
                path=member_dir,
            )
        )

    # ----------------------------------------
    # Update metadata
    # ----------------------------------------
    case_meta.update_from_members(member_dirs)

    # ----------------------------------------
    # Build CaseContext
    # ----------------------------------------
    case_context = CaseContext(
        case_id=case_name,
        path=case_dir,
        members=member_contexts,
    )

    return case_context