from .registry import register_metric

@register_metric("example_metric")
class Metric:
    def compute():
        pass