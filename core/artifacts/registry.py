from pathlib import Path
from core.analysis import Scope
from core.analysis.base import AnalysisBlock


ARTIFACTS_REGISTRY = {}


class Artifact(AnalysisBlock):

    """
    Base class for all artifacts.

    Artifacts consume measurements and produce files
    (plots, NetCDF outputs, reports, etc.).

    They do NOT write to metric.yaml.
    """

    def _generate(self, context):
        """
        Subclasses must implement this.

        Should produce files inside context.path.
        """
        raise NotImplementedError

    def _execute(self, context):
        """
        Unified execution entrypoint.
        """
        return self._generate(context)


def register_artifact(type_name):
    """
    Decorator used by artifacts to register themselves.
    """

    def decorator(cls):
        if type_name in ARTIFACTS_REGISTRY:
            raise ValueError(
                f"Artifact '{type_name}' already registered."
            )

        cls.type_name = type_name
        ARTIFACTS_REGISTRY[type_name] = cls
        return cls

    return decorator


def get_artifact_blocks(entries):

    blocks = []

    for entry in entries:

        # ----------------------------------
        # Case 1: string
        # ----------------------------------
        if isinstance(entry, str):

            type_name = entry
            instance_cfgs = [("", None)]

        # ----------------------------------
        # Case 2: dict
        # ----------------------------------
        elif isinstance(entry, dict):

            if len(entry) != 1:
                raise ValueError(
                    f"Observable entry must have single key: {entry}"
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
                        "Artifact must define either instances or config."
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
                    f"Invalid artifact config for '{type_name}'"
                )

        else:
            raise TypeError(
                f"Invalid artifact entry: {entry}"
            )

        # ----------------------------------
        # Instantiate blocks
        # ----------------------------------
        if type_name not in ARTIFACTS_REGISTRY:
            available = ", ".join(ARTIFACTS_REGISTRY)
            raise ValueError(
                f"Unknown artifact '{type_name}'. "
                f"Available: {available}"
            )

        artifact_cls = ARTIFACTS_REGISTRY[type_name]

        for instance_name, cfg in instance_cfgs:
            block = artifact_cls()
            block.set_name(instance_name)
            block.merge_config(cfg)
            blocks.append(block)

    return blocks