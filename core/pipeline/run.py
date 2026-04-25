import openmc4d as mc
import os

# ---------------------------------------------------------
# run: execute simulation within case directory
# ---------------------------------------------------------
def run_simulation(model, run_dir, openmc_exec) -> mc.StatePoint:
    path = model.run(openmc_exec=openmc_exec,
                     cwd=run_dir)
    statepoint = mc.StatePoint(path)
    return statepoint