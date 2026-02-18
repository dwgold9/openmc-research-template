ARTIFACTS_REGISTRY = {}


def register_artifact(name):
    """
    Decorator used by artifacts to register themselves.
    """
    def decorator(cls):
        if name in ARTIFACTS_REGISTRY:
            raise ValueError(f"Artifact '{name}' already registered.")
        
        ARTIFACTS_REGISTRY[name] = cls()
        return cls
    return decorator

def get_artifact_blocks(names):

    builders = []
    for n in names:
        if n not in ARTIFACTS_REGISTRY:
            available = ", ".join(ARTIFACTS_REGISTRY)
            raise ValueError(f"Unknown artifact '{n}'. Available: {available}")
    
        builders.append(ARTIFACTS_REGISTRY[n])
    return builders