import openmc4d as mc
import numpy as np
import xarray as xr
from .registry import register_tally, OpenMCTally


@register_tally("openmc-tally")
class ConfigurableOpenMCTally(OpenMCTally):

    name = "openmc-tally"

    default_config = {
        "score": "flux",
        "filters": []
    }

    def build(self):

        cfg = self.cfg

        score = cfg["score"]
        filter_configs = cfg.get("filters", [])

        filters = []

        for f in filter_configs:

            ftype = f["type"]

            if ftype == "energy":
                bins = f["bins"]
                filters.append(mc.EnergyFilter(bins))

            elif ftype == "cell":
                filters.append(mc.CellFilter(f["bins"]))

            elif ftype == "material":
                filters.append(mc.MaterialFilter(f["bins"]))

            elif ftype == "particle":
                filters.append(mc.ParticleFilter(f["bins"]))

            elif ftype == "mesh":

                mesh_cfg = f

                mesh = mc.RectilinearMesh()
                mesh.x_grid = np.linspace(
                    mesh_cfg["lower_left"][0],
                    mesh_cfg["upper_right"][0],
                    mesh_cfg["dimension"][0] + 1,
                )

                mesh.y_grid = np.linspace(
                    mesh_cfg["lower_left"][1],
                    mesh_cfg["upper_right"][1],
                    mesh_cfg["dimension"][1] + 1,
                )

                mesh.z_grid = np.linspace(
                    mesh_cfg["lower_left"][2],
                    mesh_cfg["upper_right"][2],
                    mesh_cfg["dimension"][2] + 1,
                )

                filters.append(mc.MeshFilter(mesh))

            else:
                raise ValueError(f"Unsupported filter type: {ftype}")

        tally = mc.Tally(name=self.name)
        tally.scores = [score]
        tally.filters = filters

        return [tally]


    def _extract(self, statepoint):

        tally = statepoint.get_tally(name=self.name)
        ds = self._to_xarray(tally)
        return ds


    def _to_xarray(self, tally):

        if len(tally.scores) != 1:
            raise ValueError("Multiple scores not supported")

        if len(tally.nuclides) != 1:
            raise ValueError("Multiple nuclides not supported")

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

            elif isinstance(f, mc.MeshFilter):

                mesh = f.mesh
                nx, ny, nz = mesh.dimension

                dims.extend(["x", "y", "z"])
                shape.extend([nx, ny, nz])

                x_edges = np.linspace(mesh.lower_left[0], mesh.upper_right[0], nx + 1)
                coords["x"] = 0.5 * (x_edges[:-1] + x_edges[1:])

                y_edges = np.linspace(mesh.lower_left[1], mesh.upper_right[1], ny + 1)
                coords["y"] = 0.5 * (y_edges[:-1] + y_edges[1:])

                z_edges = np.linspace(mesh.lower_left[2], mesh.upper_right[2], nz + 1)
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