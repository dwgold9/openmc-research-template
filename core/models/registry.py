


MODEL_REGISTRY = {}

def register_model(name):
    """
    Decorator used by model files to register themselves.
    """
    def decorator(func):
        if name in MODEL_REGISTRY:
            raise ValueError(f"Model '{name}' already registered.")
        MODEL_REGISTRY[name] = func
        return func
    return decorator

def get_model_block(name):

    if name not in MODEL_REGISTRY:
        available = ", ".join(MODEL_REGISTRY)
        raise ValueError(f"Unknown model '{name}'. Available: {available}")
    
    return MODEL_REGISTRY[name]