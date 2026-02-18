import openmc4d as mc
import os

# ---------------------------------------------------------
# run: execute simulation within case directory
# ---------------------------------------------------------
def run_simulation(case_dir):
    os.chdir(case_dir)
    mc.run(openmc_exec='openmc4d')