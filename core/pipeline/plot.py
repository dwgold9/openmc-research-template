import openmc4d as mc
import seaborn as sns
import matplotlib.pyplot as plt

def aesthetic_openmc_palette():
    base = sns.color_palette('pastel')

    return {
        m-1: tuple(int(255*x) for x in color)
        for m, color in enumerate(base)
    }

default = {
    'outline': False,
    'colors': aesthetic_openmc_palette()
}


def plot_slice(mc_obj, case_dir, name, **plot_kwargs):
    plot_kwargs = {**plot_kwargs, **default}
    plt.figure(figsize=(6.4*2, 4.8*2))
    axs = mc_obj.plot(openmc_exec='openmc4d', 
                      **plot_kwargs)
    axs.plot()
    plt.tight_layout()
    plt.savefig(f'{case_dir}/{name}', dpi=300)

