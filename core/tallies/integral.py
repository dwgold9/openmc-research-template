import openmc4d as mc
from .registry import register_tally, register_tally_set, OpenMCTally

# ---------------------------------------------------------
# utility: extract 1d tally
# ---------------------------------------------------------
def extract_1d(statepoint, name):
    tally = statepoint.get_tally(name=name)
    return tally.get_pandas_dataframe()
    

@register_tally("absorption")
class Absorption(OpenMCTally):
    def build(self):
        t = mc.Tally(name=self.name)
        t.scores = ['absorption']
        return [t]
    
@register_tally("fission")
class Fission(OpenMCTally):
    def build(self):
        t = mc.Tally(name=self.name)
        t.scores = ['fission']
        return [t]
    
@register_tally("nu-fission")
class NuFission(OpenMCTally):
    def build(self):
        t = mc.Tally(name=self.name)
        t.scores = ['nu-fission']
        return [t]
    
@register_tally("flux")
class NuFission(OpenMCTally):
    def build(self):
        t = mc.Tally(name=self.name)
        t.scores = ['flux']
        return [t]

register_tally_set(
    "integral-set", 
    ["absorption", "fission", "nu-fission", "flux"])