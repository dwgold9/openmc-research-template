import openmc.mgxs as mgxs
import numpy as np

def resolve_energy_bins(value):

    if value is None:
        return None

    if isinstance(value, str):

        # try OpenMC first
        if value in mgxs.GROUP_STRUCTURES:
            return np.array(mgxs.GROUP_STRUCTURES[value])

        raise ValueError(f"Unknown energy group '{value}'")

    return np.asarray(value)