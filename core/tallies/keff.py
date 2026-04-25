import openmc4d as mc
import numpy as np
import xarray as xr
from .registry import register_tally, StatePointTally

@register_tally("keff")
class Keff(StatePointTally):

    def _extract(self, statepoint):
        k = statepoint.keff

        return xr.Dataset(
            {"mean": xr.DataArray(k.nominal_value),
             "std_dev": xr.DataArray(k.std_dev)},
        )