from enum import Enum, auto
from core.analysis import *
from core.analysis.base import AnalysisBlock
import yaml
import numpy as np
import xarray as xr


# -----------------------------------------------------------------------------
# Global Metric Registry
# -----------------------------------------------------------------------------
METRICS_REGISTRY = {}


class Metric(AnalysisBlock):

    # Metrics historically used `args`
    # but we unify with AnalysisBlock
    arguments = {}

    def compute(self, context):

        # ----------------------------------------
        # Check cache
        # ----------------------------------------
        if hasattr(context, "_metric_cache") and self.name in context._metric_cache:
            return context._metric_cache[self.name]

        # ----------------------------------------
        # Resolve arguments
        # ----------------------------------------
        eval_context = dict(context.params)
        eval_context["context"] = context

        self._resolved_args = {
            k: self._evaluate_config(v, eval_context)
            for k, v in self._argument_keys.items()
        }

        # ----------------------------------------
        # Compute
        # ----------------------------------------
        result = self._compute(context)
        normalized = self._normalize_result(result)

        # ----------------------------------------
        # Store in context cache
        # ----------------------------------------
        if hasattr(context, "_metric_cache"):
            context._metric_cache[self.name] = normalized

        return normalized

    # ------------------------------------------------------------------
    # Required override
    # ------------------------------------------------------------------

    def _compute(self, context):
        raise NotImplementedError

    # ------------------------------------------------------------------
    # Result normalization
    # ------------------------------------------------------------------

    def _normalize_result(self, result):

        if isinstance(result, (int, str, list)):
            return result
        
        if isinstance(result, float):
            return float(result)

        if isinstance(result, np.ndarray):
            return result.tolist()

        if isinstance(result, xr.DataArray):
            if result.ndim == 0:
                return float(result.values)
            return result.values.tolist()

        if isinstance(result, dict):
            return result

        raise TypeError(
            f"Unsupported metric return type: {type(result)}"
        )

    # ------------------------------------------------------------------
    # Execution
    # ------------------------------------------------------------------

    def _execute(self, context):

        result = self._compute(context)
        normalized = self._normalize_result(result)

        metric_file = context.path / "metric.yaml"

        if metric_file.exists():
            with open(metric_file, "r") as f:
                data = yaml.safe_load(f) or {}
        else:
            data = {}

        data[self.name] = normalized

        with open(metric_file, "w") as f:
            yaml.safe_dump(data, f)

        return result


# -----------------------------------------------------------------------------
# Registration Decorator
# -----------------------------------------------------------------------------
def register_metric(type_name):

    def decorator(cls):

        if type_name in METRICS_REGISTRY:
            raise ValueError(
                f"Metric '{type_name}' already registered."
            )

        cls.type_name = type_name
        METRICS_REGISTRY[type_name] = cls
        return cls

    return decorator


# -----------------------------------------------------------------------------
# YAML Block Instantiation
# -----------------------------------------------------------------------------
def get_metric_blocks(entries):

    blocks = []

    for entry in entries:

        # ----------------------------------
        # Case 1: simple string
        # ----------------------------------
        if isinstance(entry, str):

            type_name = entry
            instance_cfgs = [("", None)]

        # ----------------------------------
        # Case 2: dictionary form
        # ----------------------------------
        elif isinstance(entry, dict):

            if len(entry) != 1:
                raise ValueError(
                    f"Metric entry must have single key: {entry}"
                )

            type_name, nested = next(iter(entry.items()))

            if nested is None:
                instance_cfgs = [("", None)]

            elif isinstance(nested, list):
                instance_cfgs = [(name, None) for name in nested]

            elif isinstance(nested, dict):

                instance_names = [
                    k for k, v in nested.items()
                    if isinstance(v, dict)
                ]

                config_entries = {
                    k: v for k, v in nested.items()
                    if not isinstance(v, dict)
                }

                if instance_names and config_entries:
                    raise ValueError(
                        "Mixed instance/config entry not allowed. "
                        "Metric must define either instances or config."
                    )

                if instance_names:
                    instance_cfgs = [
                        (name, nested[name])
                        for name in instance_names
                    ]
                else:
                    instance_cfgs = [("", nested)]

            else:
                raise TypeError(
                    f"Invalid metric config for '{type_name}'"
                )

        else:
            raise TypeError(f"Invalid metric entry: {entry}")

        # ----------------------------------
        # Instantiate blocks
        # ----------------------------------
        if type_name not in METRICS_REGISTRY:
            available = ", ".join(METRICS_REGISTRY)
            raise ValueError(
                f"Unknown metric '{type_name}'. "
                f"Available: {available}"
            )

        metric_cls = METRICS_REGISTRY[type_name]

        for instance_name, cfg in instance_cfgs:
            block = metric_cls()
            block.set_name(instance_name)
            block.merge_config(cfg)
            blocks.append(block)

    return blocks