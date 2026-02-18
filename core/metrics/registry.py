
METRICS_REGISTRY = {}

class Metric:
    default_config = {}

    type_name = None
    def merge_config(self, user_cfg):
        cfg = dict(self.default_config)

        if user_cfg:
            cfg.update(user_cfg)

        setattr(self, 'cfg', cfg)

    def set_name(self, instance_name):
        if instance_name == '':
            setattr(self, 'name', self.type_name)
        else:
            setattr(self, 'name', f'{self.type_name}:{instance_name}')

    def compute(self):
        raise NotImplementedError
    

def register_metric(name):
    """
    Decorator used by metrics to register themselves.
    """
    def decorator(cls):
        if name in METRICS_REGISTRY:
            raise ValueError(f"Metric '{name}' already registered.")
        
        METRICS_REGISTRY[name] = cls()
        return cls
    return decorator

def get_metric_blocks(names):

    builders = []
    for n in names:
        if n not in METRICS_REGISTRY:
            available = ", ".join(METRICS_REGISTRY)
            raise ValueError(f"Unknown metric '{n}'. Available: {available}")
    
        builders.append(METRICS_REGISTRY[n])
    return builders

def get_observable_blocks(entries):

    blocks = []
    for entry in entries:
        # ----------------------------------
        # Case 1: string
        # ----------------------------------
        if isinstance(entry, str):

            type_name = entry
            instance_cfgs = [("", None)]

        # ----------------------------------
        # Case 2: dict
        # ----------------------------------
        elif isinstance(entry, dict):

            if len(entry) != 1:
                raise ValueError(
                    f"Observable entry must have single key: {entry}"
                )

            type_name, nested = next(iter(entry.items()))

            if nested is None:
                instance_cfgs = [("", None)]

            elif isinstance(nested, list):
                instance_cfgs = [(name, None) for name in nested]

            elif isinstance(nested, dict):
                instance_names = [
                    k for k, v in nested.items() if isinstance(v, dict)
                ]

                config_entries = {
                    k: v for k, v in nested.items()
                    if not isinstance(v, dict)
                }
                if instance_names and config_entries:
                    raise ValueError(
                        "Mixed instance/config entry not allowed. "
                        "Observable must define either instances or config."
                    )
                if instance_names:
                    instance_cfgs = [
                        (name, nested[name]) for name in instance_names
                    ]
                else:
                    instance_cfgs = [("", nested)]
            else:
                raise TypeError(
                    f"Invalid observable config for '{type_name}'"
                )
        else:
            raise TypeError(f"Invalid observable entry: {entry}")

        # ----------------------------------
        # Instantiate blocks
        # ----------------------------------
        if type_name not in METRICS_REGISTRY:
            available = ", ".join(METRICS_REGISTRY)
            raise ValueError(
                f"Unknown observable '{type_name}'. Available: {available}"
            )

        observable_cls = METRICS_REGISTRY[type_name]

        for instance_name, cfg in instance_cfgs:
            block = observable_cls()
            block.set_name(instance_name)
            if cfg:
                block.merge_config(cfg)
            blocks.append(block)
    return blocks