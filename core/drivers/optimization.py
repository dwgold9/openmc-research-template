import json
from scipy.optimize import minimize
import copy
import yaml

from core.pipeline.case import evaluate_case
from core.pipeline.optimization import evaluate_objective
from core.pipeline.search import perform_criticality_search


def load_completed_cases(runs_root, param_names, objective_cfg):

    completed = {}

    for case_dir in runs_root.iterdir():

        params_file = case_dir / "case_params.json"
        meta_file = case_dir / "case_meta.yaml"
        metric_file = case_dir / "metric.yaml"

        if not (params_file.exists() and meta_file.exists() and metric_file.exists()):
            continue

        # ------------------------
        # Check status
        # ------------------------
        with open(meta_file) as f:
            meta = yaml.safe_load(f)

        if meta.get("status") != "complete":
            continue

        # ------------------------
        # Load params
        # ------------------------
        with open(params_file) as f:
            params = json.load(f)

        x_key = tuple(round(params[p], 8) for p in param_names)

        # ------------------------
        # Load metric
        # ------------------------
        with open(metric_file) as f:
            metrics = yaml.safe_load(f)

        metric_name = objective_cfg["metric"]
        value_key = objective_cfg["value"]

        value = metrics[metric_name][value_key]

        completed[x_key] = value

    return completed


# ---------------------------------------------------------
# optimization driver
# ---------------------------------------------------------

def run_optimization(
    study_params,
    opt_cfg,
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

    param_names = list(opt_cfg["parameters"].keys())

    x0 = []
    bounds = []

    for p in param_names:
        spec = opt_cfg["parameters"][p]
        x0.append(spec["initial"])
        bounds.append(tuple(spec["bounds"]))

    objective_cfg = opt_cfg["objective"]
    maximize = opt_cfg["objective"].get("goal", "maximize") == "maximize"
    sign = -1 if maximize else 1

    iteration = {"i": 1}
    case_dirs = []
    history = []

    completed = load_completed_cases(runs_root, param_names, objective_cfg)

    def evaluate(x):

        opt_params = dict(zip(param_names, x))

        params = {
            **study_params,
            **opt_params,
        }

        case_name = f"opt{iteration['i']:03d}"
        iteration["i"] += 1

        print(f"\n=== Optimization iteration {case_name} ===")
        print(params)


        # ----------------------------------------
        # CACHE CHECK (RIGHT PLACE)
        # ----------------------------------------

        x_key = tuple(round(float(v), 8) for v in x)


        if x_key in completed:
            print(f"[resume] using cached result")

            value = completed[x_key]

            history.append({
                "iteration": iteration["i"],
                "params": params,
                "metric": value,
                "cached": True,
            })

            return sign * value

        # ----------------------------------------
        # Criticality solve
        # ----------------------------------------
        if "criticality" in opt_cfg:

            crit_cfg = opt_cfg["criticality"]

            crit_value = perform_criticality_search(
                    params,
                    crit_cfg,
                    model_block,
                )

            params[crit_cfg["variable"]] = crit_value

            print(f"Critical {crit_cfg['variable']} = {crit_value}")


            # ----------------------------------------
            # Run simulation
            # ----------------------------------------
            try:
                case_context = evaluate_case(
                    case_params=params,
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

                local_metrics = [copy.deepcopy(m) for m in metric_blocks]

                value = evaluate_objective(case_context, local_metrics, objective_cfg)

            except Exception as e:
                print(f"[error] Evaluation failed: {e}")
                value = float("inf")

            case_dirs.append(case_context.path)

            history.append({
                "iteration": iteration["i"],
                "params": params,
                "metric": value,
                "cached": False,
            })

            print(f"Objective: {value}")

            return sign * value

    result = minimize(
        evaluate,
        x0,
        bounds=bounds,
        method=opt_cfg.get("algorithm", "nelder-mead"),
        options=opt_cfg.get("options", {}),
    )

    with open(runs_root / "optimizer_history.json", "w") as f:
        json.dump(history, f, indent=2)

    study_meta.update_from_cases(case_dirs)

    print("\nOptimization complete.")
    print(result)
