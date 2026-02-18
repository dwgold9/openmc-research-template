import openmc4d as mc
from .params import *
from .registry import register_model


@register_model("example_model")
def build_model(config):
    p = resolve(config)
    model = mc.Model()
    return model