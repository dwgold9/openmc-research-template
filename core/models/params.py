

DEFAULTS = {
    'N_tubes_y': 10,
    'N_tubes_z': 10,
    'num_layers': 1,
    'velocity': 0,      ## cm/s
    'tube_radius': 2.0, ## cm,
    'no_tubes': False,
    'seed': 1,
    'batches': 100,
    'inactive': 99,
    'particles': 100000

}

def resolve(config):
    if config is None:
        config = {}
    return {**DEFAULTS, **config}

