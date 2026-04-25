

DEFAULTS = {
    'N_tubes_y': 10,
    'N_tubes_z': 10,
    'N_tubes'
    'num_layers': 1,
    'velocity': 0,      ## cm/s
    'tube_radius': 2.0, ## cm,
    'no_tubes': False,
    'seed': 1,
    'batches': 100,
    'inactive': 99,
    'particles': 100000,
    'run_mode': 'eigenvalue',
    'square_grid': False,
    'thck_deplete': 3.0,
    'thck_fissile': 2.0,
    'thck_modrat': 20.0,
    'leu_enrich': 2.5,
    'dep_enrich': 0.1,
    'mat_fissile': 'fuel-rich',
    'mat_deplete': 'fuel-depleted',
    'mat_modrat': 'd2o',
    'mat_modrat_move': 'd2o-move',
    'pitch': 6
}

def resolve(config, model_default={}):
    if config is None:
        config = {}
    return {**DEFAULTS, **model_default, **config}

