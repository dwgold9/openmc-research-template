import openmc4d as mc
import numpy as np
from .registry import register_tally, MeshTally
from core.utils.energy_bins import resolve_energy_bins


@register_tally("flux-distribution-1d")
class FluxDistribution1D(MeshTally):
    name = 'flux-distribution-1d'
    default_config = {
        'lower_left': [-100, -100, -100],
        'upper_right': [100, 100, 100],
        'num_points' : 50,
        'direction': 'x',
        'energy_bins': [0, 20e6]
    }

    @property
    def mesh_metadata(self):
        cfg = self.cfg
        dir = cfg['direction']
        nx = cfg['num_points'] if dir == 'x' else 1
        ny = cfg['num_points'] if dir == 'y' else 1
        nz = cfg['num_points'] if dir == 'z' else 1
        dimensions = [nx, ny, nz]
        metadata = {
            'lower_left': self.cfg['lower_left'],
            'upper_right': self.cfg['upper_right'],
            'dimensions': dimensions
        }
        return metadata

    def build(self):
        cfg = self.cfg
        ## read config
        energy_bins = resolve_energy_bins(
            cfg['energy_bins'])
    
        dir = cfg['direction']
        lower_left = cfg['lower_left']
        upper_rght = cfg['upper_right']
        nx = cfg['num_points'] if dir == 'x' else 1
        ny = cfg['num_points'] if dir == 'y' else 1
        nz = cfg['num_points'] if dir == 'z' else 1

        mesh = mc.RectilinearMesh()   
        mesh.x_grid = np.linspace(lower_left[0],
                                    upper_rght[0], 
                                    nx+1)
        mesh.y_grid = np.linspace(lower_left[1],
                                    upper_rght[1], 
                                    ny+1)
        mesh.z_grid = np.linspace(lower_left[2],
                                    upper_rght[2], 
                                    nz+1)
        meshfilter = mc.MeshFilter(mesh=mesh)

        energyfilter = mc.EnergyFilter(energy_bins)

        t = mc.Tally(name=self.name)
        t.filters = [meshfilter, energyfilter]
        t.scores = ['flux']
        return [t]
    

@register_tally("score-distribution-1d")
class ScoreDistribution1D(MeshTally):
    name = 'score-distribution-1d'
    default_config = {
        'score': 'flux',
        'lower_left': [-100, -100, -100],
        'upper_right': [100, 100, 100],
        'num_points' : 50,
        'direction': 'x',
        'energy_bins': [0, 20e6],
        'materials': None
    }

    @property
    def mesh_metadata(self):
        cfg = self.cfg
        dir = cfg['direction']
        nx = cfg['num_points'] if dir == 'x' else 1
        ny = cfg['num_points'] if dir == 'y' else 1
        nz = cfg['num_points'] if dir == 'z' else 1
        dimensions = [nx, ny, nz]
        metadata = {
            'lower_left': self.cfg['lower_left'],
            'upper_right': self.cfg['upper_right'],
            'dimensions': dimensions
        }
        return metadata

    def build(self):
        cfg = self.cfg
        ## read config
        score = cfg['score']
        energy_bins = resolve_energy_bins(
            cfg['energy_bins'])
        dir = cfg['direction']
        lower_left = cfg['lower_left']
        upper_rght = cfg['upper_right']
        nx = cfg['num_points'] if dir == 'x' else 1
        ny = cfg['num_points'] if dir == 'y' else 1
        nz = cfg['num_points'] if dir == 'z' else 1
        material_inputs = cfg['materials']

        filters = []

        if material_inputs is not None:

            if not isinstance(material_inputs, list):
                material_inputs = [material_inputs]

            materials = list(self.model.materials)

            id_map = {m.id: m for m in materials}
            name_map = {m.name: m for m in materials}

            selected_materials = []

            for m in material_inputs:

                # -------------------------
                # Resolve model parameter
                # -------------------------

                if isinstance(m, str) and m in self.model.parameters:
                    m = self.model.parameters[m]

                # -------------------------
                # Resolve material id
                # -------------------------

                if isinstance(m, int):

                    if m not in id_map:
                        raise ValueError(
                            f"Material id {m} not found. "
                            f"Available ids: {list(id_map.keys())}"
                        )

                    selected_materials.append(id_map[m])
                    continue

                # -------------------------
                # Resolve material name
                # -------------------------

                if isinstance(m, str):

                    if m not in name_map:
                        raise ValueError(
                            f"Material '{m}' not found. "
                            f"Available names: {list(name_map.keys())}"
                        )

                    selected_materials.append(name_map[m])
                    continue

                raise TypeError(
                    f"Material specifier must resolve to name or id, got {type(m)}"
                )

            filters.append(mc.MaterialFilter(selected_materials))


        mesh = mc.RectilinearMesh()   
        mesh.x_grid = np.linspace(lower_left[0],
                                    upper_rght[0], 
                                    nx+1)
        mesh.y_grid = np.linspace(lower_left[1],
                                    upper_rght[1], 
                                    ny+1)
        mesh.z_grid = np.linspace(lower_left[2],
                                    upper_rght[2], 
                                    nz+1)
        meshfilter = mc.MeshFilter(mesh=mesh)
        filters.append(meshfilter)
        energyfilter = mc.EnergyFilter(energy_bins)
        filters.append(energyfilter)

        t = mc.Tally(name=self.name)
        t.filters = filters
        t.scores = [score]
        return [t]