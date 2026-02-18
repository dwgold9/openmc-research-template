import openmc4d as mc
from .registry import register_tally, Tally

# ---------------------------------------------------------
# utility: extract 1d tally
# ---------------------------------------------------------
def extract_1d(statepoint, name):
    t = statepoint.get_tally(name=name)
    return t.mean
    

@register_tally("absorption")
class Absorption(Tally):
    name = 'absorption'
    def build(self):
        t = mc.Tally(name=self.name)
        t.scores = ['absorption']
        return [t]
    
    def extract(self, statepoint):
        return extract_1d(statepoint, self.name)
    
@register_tally("fission")
class Fission(Tally):
    name = 'fission'
    def build(self):
        t = mc.Tally(name=self.name)
        t.scores = ['fission']
        return [t]
    
    def extract(self, statepoint):
        return extract_1d(statepoint, self.name)
    
@register_tally("nu-fission")
class NuFission(Tally):
    name = 'nu-fission'
    def build(self):
        t = mc.Tally(name=self.name)
        t.scores = ['nu-fission']
        return [t]

    def extract(self, statepoint):
        return extract_1d(statepoint, self.name)

@register_tally("integral-set")
class Integral(Tally):
    tallies = [Absorption, Fission, NuFission]
    def build(self):
        t = []
        for tally in self.tallies:
            t += tally().build()
        return t
    
    def extract(self, statepoint):
        t = []
        for tally in self.tallies:
            t.append(tally().extract(statepoint))
        return t