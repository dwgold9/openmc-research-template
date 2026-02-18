import openmc4d as mc

# ---------------------------------------------------------
# attach: add tallies to the model
# ---------------------------------------------------------
def attach_tallies(model, observable_builders):
    tallies = mc.Tallies()
    for b in observable_builders:
        t = b.build()
        tallies += t

    model.tallies = tallies