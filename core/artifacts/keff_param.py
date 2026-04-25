from .registry import register_artifact, Artifact
from core.analysis import Scope
import matplotlib.pyplot as plt
import numpy as np


# ============================================================
# Base: single-case param plot
# ============================================================

@register_artifact("keff-param")
class KeffParamPlot(Artifact):
    arguments = {
        "keff": "keff",
        "parameter": None,
        "scale": 1,
        "xlabel": None,
        "ylabel": "k-effective",
        "xscale": "linear",    # "linear" or "log"
        "yscale": "linear",
    }

    scope = Scope.CASE

    def _generate(self, case):
        param = self.a("parameter")
        if param is None:
            raise ValueError("Must supply 'parameter'")

        agg = self.m("keff", case)
        ds = agg.to_xarray(param)

        x = ds[param]
        if self.a("scale"):
            x = x * self.a("scale")

        fig, ax = plt.subplots(figsize=(9, 6))

        sc = ax.scatter(x, ds["mean"], s=50)
        color = sc.get_facecolor()[0]

        ax.errorbar(
            x,
            ds["mean"],
            yerr=ds["std_dev"],
            fmt='none',
            ecolor=color,
            capsize=4
        )

        ax.set_xlabel(self.a("xlabel") or param)
        ax.set_ylabel(self.a("ylabel"))

        if self.a("xscale"):
            ax.set_xscale(self.a("xscale"))

        if self.a("yscale"):
            ax.set_yscale(self.a("yscale"))

        ax.grid(True)

        plt.tight_layout()
        plt.savefig(case.path / f"keff-{param}", dpi=300)


# ============================================================
# Base: study comparison (multiple cases)
# ============================================================

@register_artifact("keff-param-compare")
class KeffParamComparePlot(Artifact):
    arguments = {
        "keff": "keff",
        "parameter": None,
        "scale": 1,
        "labels": None,
        "xlabel": None,
        "ylabel": "k-effective",   # already present or add if missing
        "xscale": "linear",    # "linear" or "log"
        "yscale": "linear",
    }

    scope = Scope.STUDY

    def _generate(self, study):
        param = self.a("parameter")
        if param is None:
            raise ValueError("Must supply 'parameter'")

        labels_list = self.a("labels") or []

        fig, ax = plt.subplots(figsize=(9, 6))

        for i, case in enumerate(study):
            agg = self.m("keff", case)
            ds = agg.to_xarray(param)

            x = ds[param]
            if self.a("scale"):
                x = x * self.a("scale")

            label = (
                labels_list[i] if i < len(labels_list) else None
            ) or case.params.get("revision") or case.case_id

            sc = ax.scatter(x, ds["mean"], s=50, label=label)
            color = sc.get_facecolor()[0]

            ax.errorbar(
                x,
                ds["mean"],
                yerr=ds["std_dev"],
                fmt='none',
                ecolor=color,
                capsize=4
            )

        ax.set_xlabel(self.a("xlabel") or param)
        ax.set_ylabel(self.a("ylabel"))

        if self.a("xscale"):
            ax.set_xscale(self.a("xscale"))

        if self.a("yscale"):
            ax.set_yscale(self.a("yscale"))

        ax.legend()
        ax.grid(True)

        plt.tight_layout()
        plt.savefig(study.path / f"keff-{param}-compare", dpi=300)


# ============================================================
# Base: difference between two cases
# ============================================================

@register_artifact("keff-param-difference")
class KeffParamDifferencePlot(Artifact):
    arguments = {
        "keff": "keff",
        "parameter": None,
        "scale": 1,
        "labels": None,
        "case_order": None,
        "xlabel": None,
        "ylabel": "Δk-effective",   # already present or add if missing
        "xscale": "linear",    # "linear" or "log"
        "yscale": "linear",
    }

    scope = Scope.STUDY

    def _generate(self, study):
        param = self.a("parameter")
        if param is None:
            raise ValueError("Must supply 'parameter'")

        cases = list(study)
        if len(cases) != 2:
            raise ValueError("Difference plot requires exactly two cases")

        case_order = self.a("case_order")
        labels = self.a("labels") or []

        # --- resolve ordering ---
        if case_order:
            case_map = {c.case_id: c for c in cases}
            try:
                c0 = case_map[case_order[0]]
                c1 = case_map[case_order[1]]
            except KeyError as e:
                raise ValueError(f"Invalid case_id in case_order: {e}")
        else:
            c0, c1 = cases

        ds0 = self.m("keff", c0).to_xarray(param)
        ds1 = self.m("keff", c1).to_xarray(param)

        if not np.allclose(ds0[param], ds1[param]):
            raise ValueError(f"{param} grids do not match between cases")

        x = ds0[param]
        if self.a("scale"):
            x = x * self.a("scale")

        mean_diff = ds0["mean"] - ds1["mean"]
        std_diff = np.sqrt(ds0["std_dev"]**2 + ds1["std_dev"]**2)

        label0 = labels[0] if len(labels) > 0 else c0.case_id
        label1 = labels[1] if len(labels) > 1 else c1.case_id

        fig, ax = plt.subplots(figsize=(9, 6))

        sc = ax.scatter(x, mean_diff, s=50, label=f"{label0} - {label1}")
        color = sc.get_facecolor()[0]

        ax.errorbar(
            x,
            mean_diff,
            yerr=std_diff,
            fmt='none',
            ecolor=color,
            capsize=4
        )

        ax.axhline(0.0, linestyle="--", linewidth=1)

        ax.set_xlabel(self.a("xlabel") or param)
        ax.set_ylabel(self.a("ylabel"))

        if self.a("xscale"):
            ax.set_xscale(self.a("xscale"))

        if self.a("yscale"):
            ax.set_yscale(self.a("yscale"))

        ax.legend()
        ax.grid(True)

        plt.tight_layout()
        plt.savefig(study.path / f"keff-{param}-difference", dpi=300)


# ============================================================
# Legacy wrappers (zero logic duplication)
# ============================================================

@register_artifact("keff-velocity")
class KeffVelocityPlot(KeffParamPlot):
    arguments = {
        **KeffParamPlot.arguments,
        "parameter": "velocity",
        "scale": 0.01,
        "xlabel": "Velocity of D2O in m/s",
    }


@register_artifact("keff-velocity-compare")
class KeffVelocityComparePlot(KeffParamComparePlot):
    arguments = {
        **KeffParamComparePlot.arguments,
        "parameter": "velocity",
        "scale": 0.01,
    }


@register_artifact("keff-velocity-difference")
class KeffVelocityDifferencePlot(KeffParamDifferencePlot):
    arguments = {
        **KeffParamDifferencePlot.arguments,
        "parameter": "velocity",
        "scale": 0.01,
    }