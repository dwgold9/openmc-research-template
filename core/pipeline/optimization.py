from core.analysis.scope import CaseContext

def evaluate_objective(context, metric_blocks, objective_cfg):

    name = objective_cfg["metric"]
    key = objective_cfg.get("value")

    for m in metric_blocks:

        if m.name == name:

            result = m.execute(context)

            if isinstance(result, dict):
                if key is None:
                    raise ValueError(
                        f"Metric '{name}' returned dict but no 'value' specified"
                    )
                return result[key]

            return result

    raise ValueError(f"Metric '{name}' not found")