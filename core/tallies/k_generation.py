import openmc4d as mc
import numpy as np
import xarray as xr
from .registry import register_tally, register_tally_set, StatePointTally

@register_tally("k-generation")
class KGeneration(StatePointTally):

    def _extract(self, statepoint):
        k = np.asarray(statepoint.k_generation)

        return xr.Dataset(
            {"mean": (("generation",), k)},
            coords={"generation": np.arange(len(k))}
        )