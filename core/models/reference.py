import openmc4d as mc
from .defaults import *
from .registry import register_model
from .materials import MATERIALS, materials, generate_materials


@register_model("reference")
def build_model(config):
    p = resolve(config)

    mc.reset_auto_ids()
    model = mc.Model()
    model.parameters = p

    # - materials
    # ============================================================
    generate_materials(p)
    model.materials = materials()

    # - geometry
    # ============================================================
    # ------------------------------------------------------------
    # GEOMETRY PARAMETERS
    # ------------------------------------------------------------
    thck_fissile = p['thck_fissile'] # fissile layer thickness (cm)
    thck_deplete = p['thck_deplete'] # absorber (Cd) layer thickness (cm)
    thck_modrat = p['thck_modrat'] # moderator layer thickness (cm)

    Lx = thck_fissile + thck_deplete + thck_modrat  # total width in x (cm)
    Ly = 130.0  # total height in y (cm)
    Lz = 130.0
    x_split_fissile = thck_fissile  # vertical plane separating left/right regions
    x_split_deplete = x_split_fissile + thck_deplete

    no_tubes = p['no_tubes']
    if p['square_grid']:
        N_tubes_y = N_tubes_z = p['N_tubes']
    else:
        N_tubes_y = p['N_tubes_y']  # number of tubes (cylinders)
        N_tubes_z = p['N_tubes_z']  # number of tubes (cylinders)
    tube_radius = p['tube_radius']

    pitch_y = Ly / N_tubes_y
    pitch_z = Lz / N_tubes_z

    velocity = p['velocity'] # moderator velocity (cm/s)

    # boundary in y
    y_min = mc.YPlane(y0=-Ly / 2, boundary_type='reflective')
    y_max = mc.YPlane(y0=+Ly / 2, boundary_type='reflective')

    # boundary in z
    z_min = mc.ZPlane(z0=-Lz / 2, boundary_type='reflective')
    z_max = mc.ZPlane(z0=+Lz / 2, boundary_type='reflective')

    # instantiate cells
    cells = []

    # boundary in x
    x_min = mc.XPlane(x0=0, boundary_type='periodic')
    x_max = mc.XPlane(x0=Lx, boundary_type='periodic')
    x_min.periodic_surface = x_max

    # Vertical splitting plane (not periodic)
    x_fissile = mc.XPlane(x0=x_split_fissile)
    x_deplete = mc.XPlane(x0=x_split_deplete)

    # ------------------------------------------------------------
    # BUILD HORIZONTAL RECTANGULAR TUBES
    # ------------------------------------------------------------

    tube_regions = []  # regions to be subtracted from left/right
    tube_cells = []  # cells actually filled with tube material

    # Starting vertical position of the first tube
    y0 = -Ly / 2 + pitch_y / 2
    z0 = -Lz / 2 + pitch_z / 2

    for ky in range(N_tubes_y):
        for kz in range(N_tubes_z):
            # Bottom and top surfaces of the tube
            cyl = mc.XCylinder(r=tube_radius, 
                            y0=y0 + ky*pitch_y, 
                            z0=z0 + kz*pitch_z)

            # Tube region only in center...
            reg_tube = +x_min & -x_max & -cyl
            tube_regions.append(reg_tube)

            # Tube cell itself
            tube_cell = mc.Cell(region=reg_tube, fill=MATERIALS[p['mat_modrat_move']])
            tube_cell.material_velocity = [velocity, 0, 0]

            tube_cells.append(tube_cell)

    # Union of all tubes (for subtraction)
    if len(tube_regions) > 1:
        forbidden = mc.Union(tube_regions)
    else:
        forbidden = tube_regions[0]

    # ------------------------------------------------------------
    # LEFT AND RIGHT REGIONS
    # ------------------------------------------------------------

    if no_tubes:
        # Left region = left half minus all tubes
        region_fissile = (
            +x_min & -x_fissile & +y_min & -y_max & +z_min & -z_max
        )
        cell_fissile = mc.Cell(region=region_fissile, fill=MATERIALS[p['mat_fissile']])

        region_deplete = (
            +x_fissile & -x_deplete & +y_min & -y_max & +z_min & -z_max
        )
        cell_deplete= mc.Cell(region=region_deplete, fill=MATERIALS[p['mat_deplete']])

        region_modrat = (
            +x_deplete & -x_max & +y_min & -y_max & +z_min & -z_max
        )
        cell_modrat = mc.Cell(region=region_modrat, fill=MATERIALS[p['mat_modrat']])

        cells += [cell_fissile, cell_deplete, cell_modrat]
    else:
        # Left region = left half minus all tubes
        region_fissile = (
            +x_min & -x_fissile & +y_min & -y_max & +z_min & -z_max
        ) & ~forbidden
        cell_fissile = mc.Cell(region=region_fissile, fill=MATERIALS[p['mat_fissile']])

        region_deplete = (
            +x_fissile & -x_deplete & +y_min & -y_max & +z_min & -z_max
        ) & ~forbidden
        cell_deplete = mc.Cell(region=region_deplete, fill=MATERIALS[p['mat_deplete']])

        region_modrat = (
            +x_deplete & -x_max & +y_min & -y_max & +z_min & -z_max
        ) & ~forbidden
        cell_modrat = mc.Cell(region=region_modrat, fill=MATERIALS[p['mat_modrat']])

        cells += [cell_fissile, cell_deplete, cell_modrat] + tube_cells


    root_universe = mc.Universe(
        cells=cells
    )

    model.geometry = mc.Geometry(root=root_universe)
    model.geometry.merge_surfaces = True

    # - settings
    # ===============================================================
    src_init = mc.IndependentSource()
    src_init.space = mc.stats.Point([0+1e-6, 0, 0])
    src_init.energy = mc.stats.delta_function(1e6)
    src_init.angle = mc.stats.Monodirectional()
    src_init.time = mc.stats.delta_function(0.0)

    settings = mc.Settings()
    settings.particles = p['particles']
    settings.batches = p['batches']
    settings.inactive = p['inactive']
    settings.seed = p['seed']
    settings.run_mode = p['run_mode']
    settings.create_fission_neutrons = True
    settings.source = [src_init]
    settings.verbosity = 7
    model.settings = settings

    return model