import openmc4d as mc

def load_statepoint(model, run_dir):
    batches = model.settings.batches
    sp_path = run_dir / f"statepoint.{batches}.h5"
    return mc.StatePoint(sp_path)
