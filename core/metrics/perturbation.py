from .registry import register_metric, Metric
from core.analysis import Scope
from core.quantities.perturbation import compute_rr_perturbation, compute_mc_perturbation
import xarray as xr
import numpy as np

@register_metric("perturbation")
class Perturbation(Metric):

    arguments = {
        'flux': None,
        'total': None,
        'total-move': None,
        'nu-fission': None,
        'keff': 'keff'
    }

    scope = Scope.CASE

    def _compute(self, case):
        u = 100.e2
        ## prefactor (empirical not derived yet)
        pf = 1

        results = {}
        try:
            drho_ana = compute_rr_perturbation(self, case, u)
            results['drho_ana'] = pf * drho_ana
        except:
            pass

        try:
            drho_mc = compute_mc_perturbation(self, case, u)
            results['drho_mc'] = drho_mc.n
        except:
            pass

        return results
    
@register_metric("perturbation2")
class Perturbation2(Perturbation):
    pass

@register_metric("perturbation3")
class Perturbation3(Perturbation):
    pass