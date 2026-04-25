import openmc4d as mc
import numpy as np
import pandas as pd
import yaml
from pathlib import Path
import xarray as xr

TALLIES_REGISTRY = {}
TALLY_SET_REGISTRY = {}

SAFE_GLOBALS = {
    "__builtins__": {},
    "np": np,
    "min": min,
    "max": max,
    "abs": abs,
    "int": int,
    "float": float,
}

class Tally:
    """
    Base class for all tally-like outputs.

    Subclasses may represent:
    - OpenMC tallies
    - statepoint values
    - derived quantities
    """

    default_config = {}
    type_name = None
    name = None
    labels = []

    def __init__(self, instance_name="", user_cfg=None):
        self.set_name(instance_name)
        self.merge_config(user_cfg)
        self.model = None

    def merge_config(self, user_cfg):
        cfg = dict(self.default_config)
        if user_cfg:
            cfg.update(user_cfg)

        self.cfg = cfg

    def should_apply(self, params):
        where = self.cfg.get("where", None)
        if where is None:
            return True

        for key, expected in where.items():

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

    def set_name(self, instance_name):
        if instance_name == "":
            self.name = self.type_name
        else:
            self.name = f"{self.type_name}:{instance_name}"

    def configure(self, params):
        """
        Optional configuration step using user parameters.
        Subclasses may override.
        """
        self.params = params

        self._raw_cfg = self.cfg

        self.cfg = self._evaluate_config(self.cfg, params)

        self._configure(params)

    def _configure(self, params):
        pass

    def attach(self, model):
        if not self.should_apply(self.params):
            return

        self.model = model
        self._attach(model)


    def _attach(self, model):
        """
        Subclasses override this instead of attach.
        """
        pass

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

    def export_mesh_metadata(self, params):
        """
        Optional hook for exporting mesh information.
        """
        return None

    def export(self, statepoint, output_dir):
        if not self.should_apply(self.params):
            return

        ds = self._extract(statepoint)

        if ds is None:
            return

        output_path = Path(output_dir) / f"{self.name}.nc"
        ds.to_netcdf(output_path)

        self._post_export(output_path, ds)


    def _extract(self, statepoint):
        raise NotImplementedError


    def _post_export(self, path, ds):
        pass
    
    def _to_xarray(self, tally):
        """
        Convert an OpenMC tally to an xarray Dataset.
        """

        if len(tally.scores) != 1:
            raise ValueError("Multiple scores not supported in base export")

        if len(tally.nuclides) != 1:
            raise ValueError("Multiple nuclides not supported in base export")

        mean = tally.mean[:, 0, 0]
        std = tally.std_dev[:, 0, 0]

        dims = []
        coords = {}
        shape = []

        for f in tally.filters:

            if isinstance(f, mc.EnergyFilter):

                dims.append("energy")
                shape.append(f.num_bins)

                edges = np.array(f.bins)
                coords["energy"] = 0.5 * (edges[:, 0] + edges[:, 1])

            elif isinstance(f, mc.MaterialFilter):

                dims.append("material")
                shape.append(f.num_bins)

                material_map = {
                    m.id: (m.name if m.name else f"material_{m.id}")
                    for m in self.model.materials
                }

                coords["material"] = np.array([
                    material_map.get(mat_id, f"material_{mat_id}")
                    for mat_id in f.bins
                ])


            elif isinstance(f, mc.MeshFilter):

                mesh = f.mesh
                nx, ny, nz = mesh.dimension

                dims.extend(["x", "y", "z"])
                shape.extend([nx, ny, nz])

                x_edges = np.linspace(
                    mesh.lower_left[0],
                    mesh.upper_right[0],
                    nx + 1
                )
                coords["x"] = 0.5 * (x_edges[:-1] + x_edges[1:])

                y_edges = np.linspace(
                    mesh.lower_left[1],
                    mesh.upper_right[1],
                    ny + 1
                )
                coords["y"] = 0.5 * (y_edges[:-1] + y_edges[1:])

                z_edges = np.linspace(
                    mesh.lower_left[2],
                    mesh.upper_right[2],
                    nz + 1
                )
                coords["z"] = 0.5 * (z_edges[:-1] + z_edges[1:])

            else:

                name = type(f).__name__.replace("Filter", "").lower()
                dims.append(name)
                shape.append(f.num_bins)
                coords[name] = np.array(f.bins)

        values = mean.reshape(shape)
        std_values = std.reshape(shape)

        ds = xr.Dataset(
            {
                "mean": (dims, values),
                "std_dev": (dims, std_values),
            },
            coords=coords,
        )

        return ds

class OpenMCTally(Tally):

    def build(self):
        raise NotImplementedError

    def _attach(self, model):

        if model.tallies is None:
            model.tallies = mc.Tallies()

        tally = self.build()
        model.tallies += tally

    def _extract(self, statepoint):
        tally = statepoint.get_tally(name=self.name)
        return self._to_xarray(tally)

class StatePointTally(Tally):

    def extract(self, statepoint):
        """
        Subclasses should implement extraction logic from the statepoint.
        """
        raise NotImplementedError


class DerivedTally(Tally):

    def extract(self, statepoint):
        """
        Subclasses implement calculation.
        """
        raise NotImplementedError


class MeshTally(OpenMCTally):
    """
    Base class for a mesh tally.
    """
    @property
    def mesh_metadata(self):
        return {}
    
    def export_mesh_metadata(self, path):
        with open(path, 'w') as file:
            yaml.safe_dump(self.mesh_metadata, file)
        

def register_tally(type_name):

    """
    Decorator used by tally to register themselves.
    """
    def decorator(cls):
        if type_name in TALLIES_REGISTRY:
            raise ValueError(f"Tally '{type_name}' already registered.")
        cls.name = type_name
        cls.type_name = type_name
        TALLIES_REGISTRY[type_name] = cls
        return cls
    return decorator

def register_tally_set(name, members):
    if name in TALLY_SET_REGISTRY:
        raise ValueError(f"Tally set '{name}' already registered")

    TALLY_SET_REGISTRY[name] = list(members)


def get_tally_blocks(entries):

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
                    k for k, v in nested.items() if isinstance(v, dict)
                ]

                config_entries = {
                    k: v for k, v in nested.items()
                    if not isinstance(v, dict)
                }
                if instance_names and config_entries:
                    raise ValueError(
                        "Mixed instance/config entry not allowed. "
                        "Observable must define either instances or config."
                    )
                if instance_names:
                    instance_cfgs = [
                        (name, nested[name]) for name in instance_names
                    ]
                else:
                    instance_cfgs = [("", nested)]
            else:
                raise TypeError(
                    f"Invalid tally config for '{type_name}'"
                )
        else:
            raise TypeError(f"Invalid tally entry: {entry}")

        # ----------------------------------
        # Expand tally sets
        # ----------------------------------

        if type_name in TALLY_SET_REGISTRY:

            expanded_names = TALLY_SET_REGISTRY[type_name]

            # Recurse using same logic so nested config is supported
            expanded_entries = []

            for name in expanded_names:
                if instance_cfgs == [("", None)]:
                    expanded_entries.append(name)
                else:
                    # If user tried to configure a set directly, forbid it
                    raise ValueError(
                        f"Tally set '{type_name}' cannot accept per-instance config."
                    )

            blocks.extend(get_tally_blocks(expanded_entries))
            continue


        # ----------------------------------
        # Instantiate atomic tally
        # ----------------------------------

        if type_name not in TALLIES_REGISTRY:
            available = ", ".join(TALLIES_REGISTRY)
            raise ValueError(
                f"Unknown tally '{type_name}'. Available: {available}"
            )

        tally_cls = TALLIES_REGISTRY[type_name]

        for instance_name, cfg in instance_cfgs:
            block = tally_cls()
            block.set_name(instance_name)
            if cfg:
                block.merge_config(cfg)
            blocks.append(block)
    return blocks