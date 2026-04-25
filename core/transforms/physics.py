from .registry import register_transform


@register_transform("power")
def power(block, member, index=None):

    flux = block.dist(member, "flux-distribution", index)
    heating = block.dist(member, "heating-distribution", index)

    return flux * heating


@register_transform("normalized-flux")
def normalized_flux(block, member, index=None):

    flux = block.dist(member, "flux-distribution", index)

    return flux / flux.max()


@register_transform("fuel-flux")
def fuel_flux(block, member, index=None):

    flux = block.dist(member, "flux-distribution", index)

    return flux.sel(material="fuel")