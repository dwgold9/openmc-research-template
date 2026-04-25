import numpy as np
import h5py
import xarray as xr
from uncertainties import ufloat

def _calculate_chi(run_dir, material, temperature):
    def _resolve_material_name(f, material):
        keys = list(f.keys())

        if material in keys:
            return material

        alt = material.replace("-", "_")
        if alt in keys:
            return alt

        alt = material.replace("_", "-")
        if alt in keys:
            return alt

        raise KeyError(f"Material '{material}' not found. Available: {keys}")

    mgxs_path = run_dir / "mgxs.h5"

    with h5py.File(mgxs_path, "r") as f:

        lib_name = _resolve_material_name(f, material)
        lib = f[lib_name]

        if temperature not in lib:
            temps = [k for k in lib.keys() if k.endswith("K")]
            raise KeyError(
                f"Temperature '{temperature}' not found. Available: {temps}"
            )

        T_group = lib[temperature]

        if "chi" not in T_group:
            raise KeyError(f"No chi in {material}/{temperature}")

        chi = T_group["chi"][()]

    # reverse: fast→thermal → thermal→fast
    chi = chi[::-1]

    # normalize
    chi = chi / chi.sum()

    return chi


def _load_xs(xs_name, run_dir, material, temperature):
    def _resolve_material_name(f, material):
        keys = list(f.keys())

        if material in keys:
            return material

        alt = material.replace("-", "_")
        if alt in keys:
            return alt

        alt = material.replace("_", "-")
        if alt in keys:
            return alt

        raise KeyError(f"Material '{material}' not found. Available: {keys}")

    mgxs_path = run_dir / "mgxs.h5"

    with h5py.File(mgxs_path, "r") as f:

        lib_name = _resolve_material_name(f, material)
        lib = f[lib_name]

        if temperature not in lib:
            temps = [k for k in lib.keys() if k.endswith("K")]
            raise KeyError(
                f"Temperature '{temperature}' not found. Available: {temps}"
            )

        T_group = lib[temperature]

        if xs_name not in T_group:
            raise KeyError(f"No {xs_name} in {material}/{temperature}")

        xs = T_group[xs_name][()]

    # reverse: fast→thermal → thermal→fast
    xs = xs[::-1]

    return xs


def compute_rr_perturbation(block, context, u):
    u = 100e2

    params = context.params

    member = context.get_member({
        "solver": "random_ray",
        "adjoint": False,
        "rr_groups": 'CASMO-70'
    })

    chi = _calculate_chi(
        member.run_dir,
        params["mat_fissile"],
        "294K",
    )

    inv_vel = _load_xs(
        "inverse-velocity",
        member.run_dir,
        params["mat_fissile"],
        "294K"
    )

    total = block.m("total", context).select(
        adjoint=False, velocity=0, solver="random_ray"
    ).mean().squeeze()


    total_move = block.m("total-move", context).select(
        adjoint=False, velocity=0, solver="random_ray"
    ).mean().squeeze()

    beta = total_move / total

    forward_flux = block.m("flux", context).select(
        adjoint=False, velocity=0, solver="random_ray"
    ).mean().squeeze()

    adjoint_flux = block.m("flux", context).select(
        adjoint=True, velocity=0, solver="random_ray"
    ).mean().squeeze()

    nu_fission = block.m("nu-fission", context).select(
        adjoint=False, velocity=0, solver="random_ray"
    ).mean().squeeze()

    # --- spatial normalization ---
    dx = np.gradient(forward_flux["x"])[0]

    forward_flux /= dx
    adjoint_flux /= dx
    nu_fission /= dx

    # --- energy structure ---
    chi = xr.DataArray(
        chi,
        dims="energy",
        coords={"energy": forward_flux.energy},
    )

    inv_vel = xr.DataArray(
        inv_vel,
        dims="energy",
        coords={"energy": forward_flux.energy},
    )

    Fflux = nu_fission.sum("energy") * chi
    fflux_beta = forward_flux * beta

    # --- gradient ---
    grad_aflux = (
        adjoint_flux.roll(x=-1) - adjoint_flux.roll(x=1)
    ) / (2 * dx)

    # --- perturbation ---
    num = (inv_vel * (fflux_beta * grad_aflux).sum("x")).sum("energy")
    den = (Fflux * adjoint_flux).sum("x").sum("energy")

    return u * float(num / den)


def compute_rr_perturbation_new(block, context, u):
    u = 100e2

    params = context.params

    ## volumetric fraction of moving d2o
    vfrac = 1 - np.pi / (4 * params['pitch_to_diameter']**2)


    material = xr.XArray()

    member = context.get_member({
        "solver": "random_ray",
        "adjoint": False,
    })

    chi = _calculate_chi(
        member.run_dir,
        params["mat_fissile"],
        "294K",
    )

    inv_vel = _load_xs(
        "inverse-velocity",
        member.run_dir,
        params["mat_fissile"],
        "294K"
    )

    nu_fission = _load_xs(
        "nu-fission",
        member.run_dir,
        params["mat_fissile"],
        "294K"
    )

    total_fissile = _load_xs(
        "total",
        member.run_dir,
        params["mat_fissile"],
        "294K"
    )

    total_deplete = _load_xs(
        "total",
        member.run_dir,
        params["mat_deplete"],
        "294K"
    )

    total_modrat = _load_xs(
        "total",
        member.run_dir,
        params["mat_modrat"],
        "294K"
    )

    total_move = _load_xs(
        "total",
        member.run_dir,
        "d2o-move",
        "294K"
    )
   
    beta = []
    for total in (total_fissile, total_deplete, total_modrat):

        betai = (1 - vfrac) * total_move  \
            / (vfrac * total + (1 - vfrac) * total_move)
        
        beta.append(betai)

    forward_flux = block.m("flux", context).select(
        adjoint=False, velocity=0, solver="random_ray"
    ).mean().squeeze()

    adjoint_flux = block.m("flux", context).select(
        adjoint=True, velocity=0, solver="random_ray"
    ).mean().squeeze()

    nu_fission = forward_flux * nu_fission

    # --- spatial normalization ---
    dx = np.gradient(forward_flux["x"])[0]

    forward_flux /= dx
    adjoint_flux /= dx
    nu_fission /= dx

    # --- energy structure ---
    chi = xr.DataArray(
        chi,
        dims="energy",
        coords={"energy": forward_flux.energy},
    )

    inv_vel = xr.DataArray(
        inv_vel,
        dims="energy",
        coords={"energy": forward_flux.energy},
    )

    Fflux = nu_fission.sum("energy") * chi
    fflux_beta = forward_flux * beta

    # --- gradient ---
    grad_aflux = (
        adjoint_flux.roll(x=-1) - adjoint_flux.roll(x=1)
    ) / (2 * dx)

    # --- perturbation ---
    num = (inv_vel * (fflux_beta * grad_aflux).sum("x")).sum("energy")
    den = (Fflux * adjoint_flux).sum("x").sum("energy")

    return u * float(num / den)


def compute_mc_perturbation(block, context, u):
    solver = "monte_carlo"

    k0_m = block.m("keff", context).select(
        velocity=0, solver=solver
    ).flatten()[0]

    k1_m = block.m("keff", context).select(
        velocity=u, solver=solver
    ).flatten()[0]

    k0 = ufloat(
        float(k0_m.mean.values),
        float(k0_m.std.values),
    )

    k1 = ufloat(
        float(k1_m.mean.values),
        float(k1_m.std.values),
    )

    rho0 = (k0 - 1) / k0
    rho1 = (k1 - 1) / k1

    return rho1 - rho0