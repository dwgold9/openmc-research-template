from .registry import register_metric, Metric
from core.analysis import Scope
import numpy as np

@register_metric("aggregate")
class AggregateMetric(Metric):
    arguments = {
        "measurement": None,
        "parameters": []
    }

    def set_name(self, instance_name):
        if instance_name == "":
            self.name = self.type_name
        else:
            self.name = instance_name
    

@register_metric("member-aggregate")
class MemberAggregateMetric(AggregateMetric):
    scope = Scope.MEMBER

    def _compute(self, member):
        return self.m("measurement", member).mean


@register_metric("case-aggregate")
class CaseAggregateMetric(AggregateMetric):
    scope = Scope.CASE

    def _compute(self, case):
        measurements = self.m("measurement", case)
        case_mean = [m for m in measurements]
        return case_mean


@register_metric("study-aggregate")
class StudyAggregateMetric(AggregateMetric):
    scope = Scope.STUDY

    def _compute(self, study):
        data = {}
        selected = set(self.a("parameters"))

        for case in study:
            case_key = case.case_id

            case_params = {
                k: v for k, v in case.params.items()
                if k in selected
            }

            members = list(case)

            # Single-member case
            if len(members) == 1:
                member = members[0]

                result = self.m("measurement", member).mean
                value = self._normalize_result(result)

                entry = {
                    "parameters": case_params,
                    "value": value,
                }

                data[case_key] = entry
                continue

            # Multi-member case
            case_data = {"parameters": case_params}

            for member in members:
                member_key = member.member_id

                result = self.m("measurement", member).mean
                value = self._normalize_result(result)

                member_params = {
                    k: v for k, v in member.params.items()
                    if k in selected and k not in case_params.keys()
                }

                case_data[member_key] = {
                    "parameters": member_params,
                    "value": value,
                }

            data[case_key] = case_data

        return data
    


