from .registry import register_metric, Metric
from core.analysis import Scope
import numpy as np

@register_metric("value")
class ValueMetric(Metric):
    arguments = {
        "measurement": None
    }
    def set_name(self, instance_name):
        if instance_name == "":
            self.name = self.type_name
        else:
            self.name = instance_name
    

@register_metric("member-value")
class MemberValueMetric(ValueMetric):
    scope = Scope.MEMBER

    def _compute(self, member):
        return self.m("measurement", member).mean


@register_metric("case-value")
class CaseValueMetric(ValueMetric):
    scope = Scope.CASE

    def _compute(self, case):

        measurements = self.m("measurement", case)
        case_mean = measurements.mean()
        
        return case_mean


@register_metric("study-value")
class StudyValueMetric(ValueMetric):
    scope = Scope.STUDY

    def _compute(self, study):

        measurements = self.m("measurement", study)
        study_mean = np.mean([m.mean() for m in measurements], axis=0)

        return study_mean
    


