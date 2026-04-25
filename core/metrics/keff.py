from .registry import register_metric, Metric
from core.analysis import Scope

@register_metric("keff")
class Keff(Metric):
    arguments = {
        'nu-fission': 'nu-fission',
        'absorption': 'absorption'
    }

    scope = Scope.MEMBER
    def _compute(self, member):
        nufission = self.m("nu-fission", member).mean
        absorption = self.m("absorption", member).mean

        return nufission / absorption