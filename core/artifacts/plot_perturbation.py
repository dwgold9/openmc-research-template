from .registry import register_artifact, Artifact
from core.analysis import Scope
from core.quantities.perturbation import compute_rr_perturbation, compute_mc_perturbation
import xarray as xr
import numpy as np
import matplotlib.pyplot as plt
from uncertainties import ufloat

@register_artifact("perturbation-error-plot")
class PlotPerturbationError(Artifact):

    arguments = {
        'flux': None,
        'total': None,
        'total-move': None,
        'nu-fission': None,
        'divide': False,
        'keff': 'keff',
        "xlim": "",
        "ylim": "",
    }

    scope = Scope.STUDY

    def _generate(self, study):

        v0 = 2200.0e2
        u = 100.e2

        keys = set()
        for case in study:
            keys.update(case.params.keys())

        varied_param = None

        for key in keys:
            values = [case.params.get(key) for case in study]

            if len(set(values)) > 1 and key != 'leu_enrich':
                if varied_param is not None:
                    raise RuntimeError(
                        "Multiple parameters vary across cases."
                    )
                
                varied_param = key

        if varied_param is None:
            raise RuntimeError("No varying parameter detected.")

        xvals = []
        drho_mc_list = []
        drho_mc_std_list = []
        drho_ana_list = []

        for case in study:

            xvals.append(case.params[varied_param])
            # --------------------------------------------------
            # Monte Carlo perturbation

            drho_ana = compute_rr_perturbation(self, case, u)
            drho_mc = compute_mc_perturbation(self, case, u)

            if self.a('divide'):
                drho_mc /= drho_ana


            # --------------------------------------------------
            # Store results
            # --------------------------------------------------
            drho_mc_list.append(drho_mc.n)
            drho_mc_std_list.append(drho_mc.s)
            drho_ana_list.append(drho_ana)

        # --------------------------------------------------
        # Plot comparison
        # --------------------------------------------------

        xvals = np.array(xvals)

        order = np.argsort(xvals)

        xvals = xvals[order]
        drho_mc_list = np.array(drho_mc_list)[order]
        drho_mc_std_list = np.array(drho_mc_std_list)[order]
        drho_ana_list = np.array(drho_ana_list)[order]

        fig, ax = plt.subplots(figsize=(7,4))

        if self.a('divide'):
            ax.errorbar(
                xvals,
                drho_mc_list,
                yerr=drho_mc_std_list,
                fmt="o",
                label="Monte Carlo"
            )

            ax.set_ylabel(r"$\Delta\rho_{mc} / $\Delta\rho_{ana}$")
        else:
            ax.errorbar(
                xvals,
                drho_mc_list,
                yerr=drho_mc_std_list,
                fmt="o",
                label="Monte Carlo"
            )

            ax.scatter(
                xvals,
                drho_ana_list * 1,
                marker="s",
                label="Analytic",
                color='C2'
            )

            ax.set_ylabel(r"$\Delta\rho$")

        ax.set_xlabel(varied_param)
        ax.legend()

        if self.a("xlim"):
            ax.set_xlim(self.a("xlim"))

        if self.a("ylim"):
            ax.set_ylim(self.a("ylim"))

        fig.tight_layout()
        plt.savefig(study.path / "perturbation_error.png", dpi=300)