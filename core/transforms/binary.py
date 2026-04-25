from .registry import register_transform


@register_transform("multiply")
def multiply(block, member, index=None):

    m1 = block.m("m1", member, index).mean
    m2 = block.m("m2", member, index).mean

    return m1 * m2

@register_transform("divide")
def divide(block, member, index=None):

    d1 = block.m("d1", member, index).mean
    d2 = block.m("d2", member, index).mean

    return d1 / d2

@register_transform("add")
def add(block, member, index=None):

    a1 = block.m("a1", member, index).mean
    a2 = block.m("a2", member, index).mean

    return a1 + a2

@register_transform("subtract")
def subtract(block, member, index=None):

    s1 = block.m("a1", member, index).mean
    s2 = block.m("a2", member, index).mean

    return s1 - s2