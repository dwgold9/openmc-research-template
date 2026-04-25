import openmc4d as mc
import openmc4d.model


def perform_criticality_search(
    base_params,
    crit_cfg,
    model_block,
):

    var = crit_cfg["variable"]
    bracket = crit_cfg.get("bracket", None)
    tol = crit_cfg.get("tol", 1e-3)
    method = crit_cfg.get("method", "bisection")

    # ------------------------------------------
    # Build OpenMC-compatible model function
    # ------------------------------------------

    def build_model(x):

        params = dict(base_params)
        params[var] = x
        params['particles'] = int(params['particles'] / 10)

        model = model_block(params)

        return model

    # ------------------------------------------
    # Run search
    # ------------------------------------------
    try:
        crit_val, _, _= mc.search_for_keff(
                build_model,
                bracket=bracket,
                tol=tol,
                print_iterations=True,
                run_args={
                    'openmc_exec': 'openmc4d'}
        )

    except ValueError:

        bracket = [bracket[0]*0.5, 
                   bracket[1]*1.5]
        
        crit_val, _, _ = mc.search_for_keff(
                build_model,
                bracket=bracket,
                tol=tol,
                print_iterations=True,
                run_args={
                    'openmc_exec': 'openmc4d'}
        )

    

    return crit_val