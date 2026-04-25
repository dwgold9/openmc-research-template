import openmc4d as mc


MATERIALS = {
    'None': None
}

def materials():
    return [value for value in MATERIALS.values() if value != None]

def register_material(material):
    key = material.name
    MATERIALS[key] = material

# - materials
# ===============================================================
def generate_materials(params):
    p = params
    d2o = mc.Material(name='d2o')
    d2o.set_density('g/cc', 1.0)
    d2o.add_nuclide('H2', 2.0)
    d2o.add_nuclide('O16', 1.0)
    register_material(d2o)

    d2o_move = mc.Material(name='d2o-move')
    d2o_move.set_density('g/cc', 1.0)
    d2o_move.add_nuclide('H2', 2.0)
    d2o_move.add_nuclide('O16', 1.0)
    register_material(d2o_move)

    beo = mc.Material(name='beo')
    beo.set_density('g/cc', 3.02)
    beo.add_nuclide('Be9', 1.0)
    beo.add_nuclide('O16', 1.0)
    register_material(beo)

    lead = mc.Material(name='lead')
    lead.set_density('g/cc', 10.0)
    lead.add_element('Pb', 1.0)
    register_material(lead)

    zirc = mc.Material(name='zirc')
    zirc.set_density('g/cc', 6.55)
    zirc.add_element('Zr', 1.0)
    register_material(zirc)

    fuel_depleted = mc.Material(name='fuel-depleted')
    fuel_depleted.set_density('g/cc', 10.2)
    fuel_depleted.add_element('U', 1.0, enrichment=p['dep_enrich'])
    fuel_depleted.add_nuclide('O16', 2.0)
    register_material(fuel_depleted)

    americium = mc.Material(name='americium')
    americium.set_density('g/cc', 13.6)
    americium.add_nuclide('Am241', 1.0)
    register_material(americium)

    cadmium = mc.Material(name='cadmium')
    cadmium.set_density('g/cc', 8.65)
    cadmium.add_element('Cd', 1.0)
    register_material(cadmium)

    fuel_rich = mc.Material(name='fuel-rich')
    fuel_rich.set_density('g/cc', 10.2)
    fuel_rich.add_element('U', 1.0, enrichment=p['leu_enrich'])
    fuel_rich.add_nuclide('O16', 2.0)
    register_material(fuel_rich)

    fuel_d2o_mix = mc.Material().mix_materials(
        [fuel_rich, d2o], [0.0001, 0.9999]
    )
    fuel_d2o_mix.name = 'fuel-d2o-mix'
    register_material(fuel_d2o_mix)


    fuel_mox = mc.Material(name='fuel-mox')
    fuel_mox.set_density('g/cc', 10.0)
    fuel_mox.add_nuclide('U238', 0.57)
    fuel_mox.add_nuclide('Pu239', 0.43)
    register_material(fuel_mox)

    lithium = mc.Material(name='lithium')
    lithium.set_density('g/cc', 0.5)
    lithium.add_element('Li', 1.0)
    register_material(lithium)
