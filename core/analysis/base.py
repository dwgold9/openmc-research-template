from .scope import Scope
from core.transforms.registry import get_transform
import numpy as np

SAFE_GLOBALS = {
    "__builtins__": {},
    "np": np,
    "min": min,
    "max": max,
    "abs": abs,
    "int": int,
    "float": float,
}

class AnalysisBlock:

    default_config = {}
    scope: Scope
    arguments = {}
    type_name = None

    def _bind_arguments(self):

        bound = {}

        for param, default in self.arguments.items():

            if param in self.cfg:
                key = self.cfg[param]
            elif default is not None:
                key = default
            else:
                raise ValueError(
                    f"{self.type_name} requires argument '{param}'"
                )

            bound[param] = key

        for param, value in self.cfg.items():

            if param not in bound:
                bound[param] = value

        self._argument_keys = bound

    def merge_config(self, user_cfg):
        cfg = dict(self.default_config)

        if user_cfg:
            cfg.update(user_cfg)

        self.cfg = cfg
        self._bind_arguments()

        self.where = self.cfg.get("where", None)

    def _evaluate_config(self, value, context):

        if isinstance(value, dict):

            # explicit expression
            if "expr" in value:
                return eval(value["expr"], SAFE_GLOBALS, context)

            return {
                k: self._evaluate_config(v, context)
                for k, v in value.items()
            }

        elif isinstance(value, list):
            return [self._evaluate_config(v, context) for v in value]

        elif isinstance(value, str):
            # optional: treat strings as expressions if valid
            try:
                return eval(value, SAFE_GLOBALS, context)
            except Exception:
                return value

        else:
            return value

    # -------------------------------------------------
    # Predicate
    # -------------------------------------------------

    def should_apply(self, params):

        if self.where is None:
            return True

        for key, expected in self.where.items():

            if key not in params:
                return False

            actual = params[key]

            if isinstance(expected, (list, tuple)):
                if actual not in expected:
                    return False
            else:
                if actual != expected:
                    return False

        return True

    def m(self, param, context, index=None):
        key = self.a(param)
        if index != None:
            if not isinstance(key, list):
                raise ValueError(
                    f'An indexed argument must be list')
            return context.get_measurement(key[index])
        else:
            return context.get_measurement(key)
        
    def d(self, param, context, index=None):
        key = self.a(param)
        if index != None:
            if not isinstance(key, list):
                raise ValueError(
                    f'An indexed argument must be list')
            key = key[index]

        transform = get_transform(key)

        if not transform:
            raise ValueError(f"Unknown transform '{key}'")

        return transform(self, context, index)
    
    def a(self, param):
        if hasattr(self, "_resolved_args"):
            return self._resolved_args[param]
        return self._argument_keys[param]

    def set_name(self, instance_name):
        if instance_name == "":
            self.name = self.type_name
        else:
            self.name = f"{self.type_name}:{instance_name}"


    def execute(self, context):

        if not self.should_apply(context.params):
            return None

        # build evaluation context
        eval_context = dict(context.params)
        eval_context["context"] = context

        # resolve arguments
        self._resolved_args = {
            k: self._evaluate_config(v, eval_context)
            for k, v in self._argument_keys.items()
        }

        return self._execute(context)

    def _execute(self, context):
        raise NotImplementedError