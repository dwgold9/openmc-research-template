from .registry import register_artifact, Artifact
from core.analysis import Scope
from core.transforms import *
import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1.inset_locator import inset_axes
import matplotlib.image as mpimg
import numpy as np
import xarray as xr


@register_artifact("distribution-plot")
class DistributionPlot(Artifact):

    arguments = {
        "distribution": None,          # flux-distribution, score-distribution
        "ylabel": "",
        "materials": False,            # split curves by material
        "compare_members": False,      # case-level comparison
        "density": True,               # normalize by dx
        "normalize": False,
        "xlim": "",
        "ylim": "",
        "energy": "collapse",     # collapse | index | range | all
        "energy_index": 0,
        "energy_range": 'None',     # e.g. [0, 10]
        "boundaries": [],
        "keff": "keff",
        "outfile": "distribution",
        'title': ''
    }

    scope = Scope.MEMBER

    # ------------------------------------------------
    # Utilities
    # ------------------------------------------------

    def _get_distribution(self, member, index=None):

        # try raw measurement
        try:
            m = self.m("distribution", member, index)
            ds = m.mean
            da = ds.squeeze()

        except Exception:
            # fallback to derived transform
            ds = self.d("distribution", member, index)
            da = ds.squeeze()

        # ------------------------------------------------
        # Energy handling
        # ------------------------------------------------

        if "energy" in da.dims:

            mode = self.a("energy")

            if mode == "collapse":
                da = da.sum(dim="energy")

            elif mode == "index":
                idx = self.a("energy_index")
                da = da.isel(energy=idx)

            elif mode == "range":
                erange = self.a("energy_range")

                if erange is None or len(erange) != 2:
                    raise ValueError("energy_range must be [gmin, gmax]")

                gmin, gmax = erange
                da = da.isel(energy=slice(gmin, gmax)).sum(dim="energy")

            elif mode == "all":
                # leave as-is for plotting with hue
                pass

            else:
                raise ValueError(f"Unknown energy mode: {mode}")

        # ------------------------------------------------
        # Density normalization
        # ------------------------------------------------

        if self.a("density"):
            dx = np.gradient(da["x"])[0]
            da = da / dx

        # ------------------------------------------------
        # Integral normalization
        # ------------------------------------------------

        if self.a("normalize"):
            dx = np.gradient(da["x"])[0]

            # handle multi-dim safely
            integral = (da * dx).sum(dim="x")

            # avoid divide-by-zero
            da = da / integral.where(integral != 0)

        return da


    def _plot_regions(self, ax):

        boundaries = self.a("boundaries")

        colors = ['#d9e8ff', '#e8f5d9', '#ffe4d4', '#f3e5ff', '#fff4cc']

        for i in range(len(boundaries) - 1):

            ax.axvspan(
                boundaries[i],
                boundaries[i + 1],
                color=colors[i % len(colors)],
                alpha=0.3,
                zorder=0
            )

        for b in boundaries:
            ax.axvline(x=b, color="black", linestyle="--", linewidth=1.2)

        ymax = ax.get_ylim()[1]

        for i in range(len(boundaries) - 1):

            x_mid = (boundaries[i] + boundaries[i + 1]) / 2

            ax.text(x_mid, ymax * 0.5, f"Region {i+1}", ha="center")

    def _style_axes(self, ax):

        ax.set_xlabel("x (cm)")
        ax.set_ylabel(self.a("ylabel"))

        if self.a("xlim"):
            ax.set_xlim(self.a("xlim"))

        if self.a("ylim"):
            ax.set_ylim(self.a("ylim"))

        ax.grid(True)

    def _annotate(self, ax, member):

        keff = self.m("keff", member).mean_value()
        velocity = member.params["velocity"] / 100

        textstr = f"$k_{{eff}}$ = {keff:.5f}\nVelocity = {velocity:.3f} m/s"

        ax.text(
            0.02,
            0.95,
            textstr,
            transform=ax.transAxes,
            fontsize=12,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

    # ------------------------------------------------
    # Plotters
    # ------------------------------------------------

    def _plot_member(self, member, ax):

        a_distribution = self.a("distribution")

        def plot_distribution(index=None):

            da = self._get_distribution(member, index)

            if self.a("materials") and "material" in da.coords:

                for mat in da.material.values:
                    
                    da.sel(material=mat).plot.line(
                        ax=ax,
                        marker="o",
                        markersize=2,
                        lw=2,
                        label=str(mat),
                    )

            else:

                da.plot.line(
                    ax=ax,
                    marker="o",
                    markersize=2,
                    lw=2,
                )

        if isinstance(a_distribution, list):

            for i in range(len(a_distribution)):
                plot_distribution(i)

        else:

            plot_distribution()

    def _plot_case(self, case, ax):

        colors = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7"]

        for i, member in enumerate(case):

            velocity = member.params["velocity"] / 100

            if velocity not in [0, 100, -100]:
                continue

            da = self._get_distribution(member, i)

            keff = self.m("keff", member).mean_value()

            da.plot.line(
                ax=ax,
                color=colors[i % len(colors)],
                marker="o",
                markersize=3,
                lw=2,
                label=f"{velocity:>8.3f}   {keff:>7.5f}",
            )

        ax.legend(
            title="        v (m/s)     $k_{eff}$",
            prop={"family": "monospace"},
        )

    # ------------------------------------------------
    # Main
    # ------------------------------------------------

    def _generate(self, obj):

        fig, ax = plt.subplots(figsize=(9, 6))

        if self.a("compare_members"):

            self._plot_case(obj, ax)

        else:

            self._plot_member(obj, ax)

            self._annotate(ax, obj)

            if self.a("materials"):
                ax.legend(title="Material")

        self._style_axes(ax)

        self._plot_regions(ax)

        plt.title(self.a('title'))
        plt.tight_layout()
        plt.savefig(obj.path / self.a("outfile"), dpi=300)


@register_artifact("case-distribution-plot")
class CaseDistributionPlot(Artifact):

    arguments = {
        "distribution": None,          # flux-distribution, score-distribution
        "ylabel": "",
        "materials": False,            # split curves by material
        "compare_members": False,      # case-level comparison
        "density": True,               # normalize by dx
        "xlim": "",
        "ylim": "",
        "boundaries": [],
        "keff": "keff",
        "outfile": "distribution",
        'title': ''
    }

    scope = Scope.CASE

    # ------------------------------------------------
    # Utilities
    # ------------------------------------------------

    def _get_distribution(self, case, index=None):

        # try raw measurement
        try:
            m = self.m("distribution", case, index)

            ds = m.mean
            da = ds.squeeze()

        except Exception:

            # fallback to derived transform
            ds = self.d("distribution", case, index)
            da = ds.squeeze()

        if self.a("density"):
            dx = np.gradient(da["x"])
            da = da / dx
        
        if self.a("normalize"):
            dx = np.gradient(da["x"])
            integral = (da.values * dx).sum()

            if integral != 0:
                da = da / integral

        return da


    def _plot_regions(self, ax):

        boundaries = self.a("boundaries")

        colors = ['#d9e8ff', '#e8f5d9', '#ffe4d4', '#f3e5ff', '#fff4cc']

        for i in range(len(boundaries) - 1):

            ax.axvspan(
                boundaries[i],
                boundaries[i + 1],
                color=colors[i % len(colors)],
                alpha=0.3,
                zorder=0
            )

        for b in boundaries:
            ax.axvline(x=b, color="black", linestyle="--", linewidth=1.2)

        ymax = ax.get_ylim()[1]

        for i in range(len(boundaries) - 1):

            x_mid = (boundaries[i] + boundaries[i + 1]) / 2

            ax.text(x_mid, ymax * 0.5, f"Region {i+1}", ha="center")

    def _style_axes(self, ax):

        ax.set_xlabel("x (cm)")
        ax.set_ylabel(self.a("ylabel"))

        if self.a("xlim"):
            ax.set_xlim(self.a("xlim"))

        if self.a("ylim"):
            ax.set_ylim(self.a("ylim"))

        ax.grid(True)

    def _annotate(self, ax, case):

        velocity = case.params["velocity"] / 100

        textstr = f"Velocity = {velocity:.3f} m/s"

        ax.text(
            0.02,
            0.95,
            textstr,
            transform=ax.transAxes,
            fontsize=12,
            verticalalignment="top",
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8),
        )

    # ------------------------------------------------
    # Plotters
    # ------------------------------------------------

    def _plot_case(self, case, ax):

        a_distribution = self.a("distribution")

        def plot_distribution(index=None):

            da = self._get_distribution(case, index)

            if self.a("materials") and "material" in da.coords:

                for mat in da.material.values:

                    da.sel(material=mat).plot.line(
                        ax=ax,
                        marker="o",
                        markersize=2,
                        lw=2,
                        label=str(mat),
                    )

            else:

                da.plot.line(
                    ax=ax,
                    marker="o",
                    markersize=2,
                    lw=2,
                )

        if isinstance(a_distribution, list):

            for i in range(len(a_distribution)):
                plot_distribution(i)

        else:

            plot_distribution()

    # ------------------------------------------------
    # Main
    # ------------------------------------------------

    def _generate(self, obj):

        fig, ax = plt.subplots(figsize=(9, 6))

        self._plot_case(obj, ax)

        self._annotate(ax, obj)

        if self.a("materials"):
            ax.legend(title="Material")

        self._style_axes(ax)

        self._plot_regions(ax)

        plt.title(self.a('title'))
        plt.tight_layout()
        plt.savefig(obj.path / self.a("outfile"), dpi=300)


@register_artifact("flux-materials-distribution-plot")
class FluxMaterialsDistributionPlot(Artifact):
    arguments = {
        'flux-distribution': 'flux-distribution-1D',
        'xlim': '',
        'ylim': '',
        'keff': 'keff',
        'boundaries': [],
        'outfile': 'flux-distribution',
    }

    scope = Scope.MEMBER

    def _generate(self, member):
        a_flux_distribution = self.a('flux-distribution')
        keff = self.m('keff', member).mean_value()
        velocity = member.params['velocity'] / 100  # m/s

        def plot_distribution(index=None):

            m = self.m("flux-distribution", member, index)
            ds = m.mean
            da = ds.squeeze()

            dx = np.gradient(ds["x"])
            da = da / dx

            for mat in da.material.values:

                da.sel(material=mat).plot.line(
                    ax=ax,
                    marker='o',
                    markersize=2,
                    lw=2,
                    label=str(mat)
                )

        fig, ax = plt.subplots(figsize=(9, 6))
        fig.suptitle('Flux Distribution')

        if isinstance(a_flux_distribution, list):

            for i in range(len(a_flux_distribution)):
                plot_distribution(i)

        else:
            plot_distribution()

        ax.set_xlabel("x (cm)")
        ax.set_ylabel("Normalized Neutron Flux")

        if self.a('xlim') != '':
            ax.set_xlim(self.a('xlim'))

        if self.a('ylim') != '':
            ax.set_ylim(self.a('ylim'))

        ax.grid(True)

        boundaries = self.a('boundaries')

        # soft color palette (cycles automatically)
        colors = ['#d9e8ff', '#e8f5d9', '#ffe4d4', '#f3e5ff', '#fff4cc']

        # --- Shade regions ---
        for i in range(len(boundaries) - 1):
            ax.axvspan(
                boundaries[i],
                boundaries[i+1],
                color=colors[i % len(colors)],
                alpha=0.3,
                zorder=0
            )

        # --- Draw boundary lines ---
        for b in boundaries:
            ax.axvline(
                x=b,
                color='black',
                linestyle='--',
                linewidth=1.2
            )

        # --- Label regions ---
        ymax = ax.get_ylim()[1]

        for i in range(len(boundaries) - 1):
            x_mid = (boundaries[i] + boundaries[i+1]) / 2
            ax.text(
                x_mid,
                ymax * 0.5,
                f"Region {i+1}",
                ha='center'
            )
        # --- Add keff and velocity annotation ---
        textstr = f"$k_{{eff}}$ = {keff:.5f}\nVelocity = {velocity:.3f} m/s"

        ax.text(
            0.02, 0.95,
            textstr,
            transform=ax.transAxes,
            fontsize=12,
            verticalalignment='top',
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
        )


        ax.legend(title="Material")
        plt.tight_layout()
        plt.savefig(member.path / self.a('outfile'), dpi=300)



@register_artifact("score-materials-distribution-plot")
class ScoreMaterialsDistributionPlot(Artifact):
    arguments = {
        'score-distribution': None,
        'xlim': '',
        'ylim': '',
        'keff': 'keff',
        'boundaries': [],
        'outfile': 'score-distribution',
    }

    scope = Scope.MEMBER

    def _generate(self, member):
        a_score_distribution = self.a('score-distribution')
        keff = self.m('keff', member).mean_value()
        velocity = member.params['velocity'] / 100  # m/s

        def plot_distribution(index=None):

            m = self.m("score-distribution", member, index)
            ds = m.mean
            da = ds.squeeze()

            dx = np.gradient(ds["x"])
            da = da / dx

            for mat in da.material.values:

                da.sel(material=mat).plot.line(
                    ax=ax,
                    marker='o',
                    markersize=2,
                    lw=2,
                    label=str(mat)
                )

        fig, ax = plt.subplots(figsize=(9, 6))
        fig.suptitle('Score Distribution')

        if isinstance(a_score_distribution, list):

            for i in range(len(a_score_distribution)):
                plot_distribution(i)

        else:
            plot_distribution()

        ax.set_xlabel("x (cm)")
        ax.set_ylabel("Normalized Neutron Score")

        if self.a('xlim') != '':
            ax.set_xlim(self.a('xlim'))

        if self.a('ylim') != '':
            ax.set_ylim(self.a('ylim'))

        ax.grid(True)

        boundaries = self.a('boundaries')

        # soft color palette (cycles automatically)
        colors = ['#d9e8ff', '#e8f5d9', '#ffe4d4', '#f3e5ff', '#fff4cc']

        # --- Shade regions ---
        for i in range(len(boundaries) - 1):
            ax.axvspan(
                boundaries[i],
                boundaries[i+1],
                color=colors[i % len(colors)],
                alpha=0.3,
                zorder=0
            )

        # --- Draw boundary lines ---
        for b in boundaries:
            ax.axvline(
                x=b,
                color='black',
                linestyle='--',
                linewidth=1.2
            )

        # --- Label regions ---
        ymax = ax.get_ylim()[1]

        for i in range(len(boundaries) - 1):
            x_mid = (boundaries[i] + boundaries[i+1]) / 2
            ax.text(
                x_mid,
                ymax * 0.5,
                f"Region {i+1}",
                ha='center'
            )
        # --- Add keff and velocity annotation ---
        textstr = f"$k_{{eff}}$ = {keff:.5f}\nVelocity = {velocity:.3f} m/s"

        ax.text(
            0.02, 0.95,
            textstr,
            transform=ax.transAxes,
            fontsize=12,
            verticalalignment='top',
            bbox=dict(boxstyle="round", facecolor="white", alpha=0.8)
        )


        ax.legend(title="Material")
        plt.tight_layout()
        plt.savefig(member.path / self.a('outfile'), dpi=300)


@register_artifact("comparison-flux-distribution-plot")
class ComparisonFluxDistributionPlot(Artifact):
    arguments = {
        'flux-distribution': 'flux-distribution-1D',
        'xlim': '',
        'ylim': '',
        'keff': 'keff',
        'boundaries': [],
        'outfile': 'comparison-flux-distribution',
    }

    scope = Scope.CASE

    def _generate(self, case):
        plt.style.use("seaborn-v0_8-paper")
        plt.rcParams.update({
            "font.size": 12,
            "axes.labelsize": 13,
            "axes.titlesize": 14,
            "legend.fontsize": 11,
            "lines.linewidth": 2,
        })
        colors = ["#0072B2", "#E69F00", "#009E73", "#D55E00", "#CC79A7"]

        fig, ax = plt.subplots(figsize=(9, 6))
        fig.suptitle('Flux Distribution')

        for i, member in enumerate(case):
            keff = self.m('keff', member).mean_value()
            velocity = member.params['velocity'] / 100  # m/s

            if velocity not in [0, 100, -100]:
                continue

            m = self.m("flux-distribution", member)

            ds = m.mean
            da = ds.squeeze()

            dx = np.gradient(ds["x"])
            da /= dx

            da.plot.line(
                ax=ax,
                color=colors[i % len(colors)],
                marker="o",
                markersize=3,
                lw=2,
                label = f"{velocity:>8.3f}   {keff:>7.5f}"
            )
            
        ax.set_title('')
        ax.set_xlabel("x (cm)")
        ax.set_ylabel("Normalized Neutron Flux")

        if self.a('xlim') != '':
            ax.set_xlim(self.a('xlim'))

        if self.a('ylim') != '':
            ax.set_ylim(self.a('ylim'))

        ax.grid(True, linestyle="--", linewidth=0.5, alpha=0.6)

        boundaries = self.a('boundaries')

        # soft color palette (cycles automatically)
        colors = ['#d9e8ff', '#e8f5d9', '#ffe4d4', '#f3e5ff', '#fff4cc']

        # --- Shade regions ---
        for i in range(len(boundaries) - 1):
            ax.axvspan(
                boundaries[i],
                boundaries[i+1],
                color=colors[i % len(colors)],
                alpha=0.3,
                zorder=0
            )

        # --- Draw boundary lines ---
        for b in boundaries:
            ax.axvline(
                x=b,
                color='black',
                linestyle='--',
                linewidth=1.2
            )

        # --- Label regions ---
        ymax = ax.get_ylim()[1]

        for i in range(len(boundaries) - 1):
            x_mid = (boundaries[i] + boundaries[i+1]) / 2
            ax.text(
                x_mid,
                ymax * 0.5,
                f"Region {i+1}",
                ha='center'
            )
        # --- Add keff and velocity annotation ---

        ax.legend(
            title="        v (m/s)     $k_{eff}$",
            prop={"family": "monospace"}
        )

        plt.tight_layout()
        plt.savefig(case.path / self.a('outfile'), dpi=300)