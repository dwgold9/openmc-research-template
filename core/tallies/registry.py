import openmc4d as mc

TALLIES_REGISTRY = {}

class Tally:
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

    def build(self):
        raise NotImplementedError
    
    def extract(self, statepoint):
        raise NotImplementedError
    
    def attach(self, model):
        if model.tallies is None:
            model.tallies = mc.Tallies()

        model.tallies += self.build()

def register_tally(type_name):

    """
    Decorator used by tally to register themselves.
    """
    def decorator(cls):
        if type_name in TALLIES_REGISTRY:
            raise ValueError(f"Tally '{type_name}' already registered.")
        cls.type_name = type_name
        TALLIES_REGISTRY[type_name] = cls
        return cls
    return decorator


def get_tally_blocks(entries):

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
                    f"Invalid tally config for '{type_name}'"
                )
        else:
            raise TypeError(f"Invalid tally entry: {entry}")

        # ----------------------------------
        # Instantiate blocks
        # ----------------------------------
        if type_name not in TALLIES_REGISTRY:
            available = ", ".join(TALLIES_REGISTRY)
            raise ValueError(
                f"Unknown tally '{type_name}'. Available: {available}"
            )

        tally_cls = TALLIES_REGISTRY[type_name]

        for instance_name, cfg in instance_cfgs:
            block = tally_cls()
            block.set_name(instance_name)
            if cfg:
                block.merge_config(cfg)
            blocks.append(block)
    return blocks