from .registry import register_metric, Metric
from core.analysis import Scope
import numpy as np

@register_metric("value")
class STDevMetric(Metric):
    arguments = {
        "measurement": None
    }
    def set_name(self, instance_name):
        if instance_name == "":
            self.name = self.type_name
        else:
            self.name = instance_name
    

@register_metric("member-stdev")
class MemberValueMetric(STDevMetric):
    scope = Scope.MEMBER

    def _compute(self, member):
        return self.m("measurement", member).mean


@register_metric("case-value")
class CaseValueMetric(STDevMetric):
    scope = Scope.CASE

    def _compute(self, case):
        measurements = self.m("measurement", case)
        case_mean = np.std([m.std for m in measurements], axis=0)
        
        return case_mean


@register_metric("study-value")
class StudyValueMetric(STDevMetric):
    scope = Scope.STUDY

    def _compute(self, study):
        return self.m("measurement", study).mean