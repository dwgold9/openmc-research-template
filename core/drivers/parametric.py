import yaml
import json

from core.pipeline.case import expand_parametric, set_case_name, evaluate_case
from core.pipeline.search import perform_criticality_search

def load_completed_parametric_cases(runs_root, param_names):

    completed = set()

    for case_dir in runs_root.iterdir():

        params_file = case_dir / "case_params.json"
        meta_file = case_dir / "case_meta.yaml"

        if not (params_file.exists() and meta_file.exists()):
            continue

        with open(meta_file) as f:
            meta = yaml.safe_load(f)

        if meta.get("status") != "complete":
            continue

        with open(params_file) as f:
            params = json.load(f)

        key = tuple(round(float(params[p]), 8) for p in param_names)

        completed.add(key)

    return completed


def run_parametric(
    study_params,
    parametric_cfg,
    study_meta,
    model_block,
    tally_blocks,
    metric_blocks,
    plots,
    members,
    runs_root,
    plot_only,
    isrun,
):

    cases = expand_parametric(parametric_cfg)

    param_names = list(parametric_cfg.get("variables", {}).keys())

    completed = load_completed_parametric_cases(runs_root, param_names)

    case_dirs = []

    for i, case_vars in enumerate(cases):

        case_name = set_case_name(i + 1)

        case_params = {
            **study_params,
            **case_vars,
        }

        print(f"\n=== Parametric case {case_name} ===")
        print(case_vars)

        # ----------------------------------------
        # CACHE CHECK (BEFORE CRITICALITY)
        # ----------------------------------------

        x_key = tuple(round(float(case_vars[p]), 8) for p in param_names 
                      if not isinstance(case_vars[p], str))

        if x_key in completed:
            print("[resume] skipping completed case")
            continue

        # ----------------------------------------
        # Criticality solve
        # ----------------------------------------
        if "criticality" in parametric_cfg:

            crit_cfg = parametric_cfg["criticality"]

            crit_value = perform_criticality_search(
                case_params,
                crit_cfg,
                model_block,
            )

            case_params[crit_cfg["variable"]] = crit_value

            print(f"Critical {crit_cfg['variable']} = {crit_value}")

        # ----------------------------------------
        # Run simulation
        # ----------------------------------------
        case_context = evaluate_case(
            case_params=case_params,
            members=members,
            model_block=model_block,
            tally_blocks=tally_blocks,
            metric_blocks=metric_blocks,
            plots=plots,
            runs_root=runs_root,
            case_name=case_name,
            plot_only=plot_only,
            isrun=isrun,
        )

        case_dirs.append(case_context.path)

    study_meta.update_from_cases(case_dirs)