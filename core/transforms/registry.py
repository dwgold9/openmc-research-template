TRANSFORMS_REGISTRY = {}


def register_transform(name):
    """
    Register a transform function.

    Transform signature:
        func(artifact, member, index=None) -> xr.DataArray
    """

    def wrapper(func):
        TRANSFORMS_REGISTRY[name] = func
        return func

    return wrapper


def get_transform(name):
    return TRANSFORMS_REGISTRY.get(name)