import glob
import os
import sys
from functools import wraps

import matplotlib.pyplot as plt
from mpl_toolkits.axes_grid1 import make_axes_locatable
import mplhep as hep
import numpy as np
from cycler import cycler
from hist import Hist, intervals
from hist import rebin as Rebin
from matplotlib import colors
from rich import print as pprint

# cms palette list (10 colors version)
petroff10 = [
    "#3f90da",
    "#ffa90e",
    "#bd1f01",
    "#94a4a2",
    "#832db6",
    "#a96b59",
    "#e76300",
    "#b9ac70",
    "#92dadd",
    "#717581",
]

acab_palette = (
    "#1f77b4",
    "#ff7f0e",
    "#2ca02c",
    "#d62728",
    "#9467bd",
    "#8c564b",
    "#e377c2",
    "#7f7f7f",
    "#bcbd22",
    "#17becf",
)

ggplot_palette=('#348ABD','#E24A33', '#988ED5', '#777777', '#FBC15E', '#8EBA42', '#FFB5B8')

hep.styles.cms.CMS["patch.linewidth"] = 2
hep.styles.cms.CMS["lines.linewidth"] = 2
hep.styles.cms.CMS["axes.prop_cycle"] = cycler("color", ggplot_palette)
hep.styles.cms.CMS["legend.frameon"] = True
hep.styles.cms.CMS["figure.autolayout"] = True
hep.style.use(hep.style.CMS)

def merge_kwargs(**decorator_kwargs):
    def decorator(method):
        @wraps(method)
        def wrapper(self, *args, **kwargs):
            kwargs = {**self.kwargs, **kwargs}
            for key, value in decorator_kwargs.items():
                kwargs.setdefault(key, value)
            return method(self, *args, **kwargs)

        return wrapper

    return decorator


def filepath_loader(path_list):
    files_list = []
    for path in path_list:
        if ".root" in path:
            files_list.append(path)
        else:
            files_list.extend(glob.glob(os.path.join(path, "*.root")))
    yield from files_list

def convert_to_hist(*hists):
    if len(hists)>1:
        res=[]
        for h in hists:
            if not isinstance(h, Hist):
                res.append(h.to_hist())
            else:
                return res.append(h)
        return res
    if not isinstance(hists[0], Hist):
        return hists[0].to_hist()
    return hists[0]

def set_palette(palette):
    hep.styles.cms.CMS["axes.prop_cycle"] = cycler("color", palette)
    hep.style.use(hep.style.CMS)

def set_style(key, value):
    hep.styles.cms.CMS[key] = value
    hep.style.use(hep.style.CMS)

class BasePlotter:
    def __init__(
        self,
        name="",
        fig=None,
        ax=None,
        xlim=None,
        ylim=None,
        zlim=None,
        log="",
        grid=True,
        xlabel="",
        ylabel="",
        lumitext="",
        cmstext="",
        cmstextsize=None,
        lumitextsize=None,
        legend_kwargs={},
        cmsloc=0,
        rebin=1,
        **kwargs,
    ):
        if (fig is None and ax is not None) or (fig is not None and ax is None):
            raise ValueError("If fig is provided, ax must be provided as well, and vice versa.")

        if fig is None and ax is None:
            fig, ax = plt.subplots()
        self.fig = fig
        self.ax = ax
        self.name = name
        self.lumitext = lumitext
        self.cmstext = cmstext

        hep.cms.text(self.cmstext, ax=self.ax, loc=cmsloc, fontsize=cmstextsize)
        hep.cms.lumitext(self.lumitext, ax=self.ax, fontsize=lumitextsize)
        self.lazy_args = []

        self.ax.set_xlabel(xlabel)
        self.ax.set_ylabel(ylabel)

        self.ax.grid(grid)
        if xlim is not None:
            self.ax.set_xlim(xlim)
            self.ax.autoscale_view(scalex=True, scaley=True)
        if ylim is not None:
            self.ax.set_ylim(ylim)
            self.ax.autoscale_view(scalex=True, scaley=True)

        if "y" in log.lower():
            self.ax.set_yscale("log")
        if "x" in log.lower():
            self.ax.set_xscale("log")
        if "z" in log.lower():
            self.zlog = True
        else:
            self.zlog = False
        if zlim is None:
            self.zlim = (None, None)

        self.kwargs = kwargs

        self.markers = ["v", "^", "X", "P", "d", "*", "p", "o"]
        self.markers_copy = self.markers.copy()
        if isinstance(rebin, int):
            self.rebin = Rebin(rebin)
        else:
            self.rebin = [Rebin(r) for r in rebin]

        self.legend_kwargs = legend_kwargs

    def add_text(self, *args, **kwargs):
        self.ax.text(*args, **kwargs)

    def add_line(self, x=None, y=None, **kwargs):
        if x is not None and y is None:
            self.ax.axvline(x, **kwargs)
        elif y is not None and x is None:
            self.ax.axhline(y, **kwargs)
        else:
            self.ax.plot(x, y, **kwargs)
        sys.stderr = open(os.devnull, "w")
        self.ax.legend(**self.legend_kwargs)
        sys.stderr = sys.__stderr__

    def save(self, filename, *args, **kwargs):
        pprint(f"Saving {filename}")
        self.fig.savefig(filename, *args, **kwargs)
        plt.close(self.fig)

    def lazy_add(self, to_file, mode="normal", *args, **kwargs):
        self.lazy_args.append((to_file, mode, args, kwargs))

    def lazy_execute(self, file):
        for to_file, mode, args, kwargs in self.lazy_args:
            hists_list = [file[var] for var in to_file]
            if mode == "normal":
                self.add(*hists_list, *args, **kwargs)
            elif mode == "rate_vs_pt_score":
                score_cuts = hists_list[0].axes[1].edges[:-1]
                for idx, cut in enumerate(score_cuts):
                    if "cuts" in kwargs:
                        if cut not in kwargs["cuts"]:
                            continue
                    label = kwargs.get("label")
                    if label is not None:
                        label = label.replace("%cut%", cut)
                        kwargs.pop("label")
                    self.add(hists_list[0][:, idx], *args, label=label, **kwargs)
            else:
                raise ValueError(f"mode '{mode}' is not implemented")


class TH1(BasePlotter):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    @merge_kwargs()
    def add(self, hist, **kwargs):
        hist=convert_to_hist(hist)
        hist = hist[self.rebin]
        hep.histplot(hist, ax=self.ax, clip_on=True, **kwargs)
        sys.stderr = open(os.devnull, "w")
        self.ax.legend(**self.legend_kwargs)
        sys.stderr = sys.__stderr__

        if kwargs.get("histtype") == "fill":
            self.ax.set_axisbelow(True)


class TH2(BasePlotter):
    def __init__(self, *args, rebin=[1,1], **kwargs):
        super().__init__(*args, rebin=rebin, **kwargs)

    @merge_kwargs(cmap = plt.cm.viridis, cmin=1)
    def add(self, hist, **kwargs):
        hist=convert_to_hist(hist)
        hist = hist[*self.rebin]
        if self.zlog:
            kwargs["norm"] = colors.LogNorm(vmin=self.zlim[0], vmax=self.zlim[1])

        if "cmap" in kwargs:
            kwargs["cmap"].set_under('w',1)
        if kwargs.get("density", False):
            kwargs.pop("density")
            hep.hist2dplot(hist, ax=self.ax, **kwargs)
        else:
            kwargs.pop("density")
            kwargs.pop("cmin")
            data = hist.density().T
            data[data == 0] = np.nan
            im = self.ax.imshow(data, origin = "lower", aspect = "auto", interpolation='none', extent=[hist.axes[0].edges[0],hist.axes[0].edges[-1],hist.axes[1].edges[0],hist.axes[1].edges[-1]], **kwargs)
            divider = make_axes_locatable(self.ax)
            cax = divider.append_axes('right', size='5%', pad=0.05)
            self.fig.colorbar(im, cax=cax, orientation='vertical')



class TEfficiency(BasePlotter):
    def __init__(self, yerr=True, xerr=False, ylabel="Efficiency", step=True, fillerr=False, avxalpha=0.15, *args, **kwargs):
        super().__init__(*args, ylabel=ylabel, **kwargs)
        self.yerr = yerr
        self.xerr = xerr
        self.step = step
        self.fillerr = fillerr
        self.avxalpha = avxalpha

    @merge_kwargs(linewidth=3, markeredgecolor="Black", markersize=0, errcapsize=3, errlinewidth=2, errzorder=-99, fillalpha=0.3)
    def add(self, num, den, **kwargs):
        keys=list(kwargs.keys())
        err_kwargs = {key.split("err")[1]:kwargs.pop(key) for key in keys if key.startswith("err")}
        fill_kwargs = {key.split("fill")[1]:kwargs.pop(key) for key in keys if key.startswith("fill")}
        num = convert_to_hist(num)[self.rebin]
        den = convert_to_hist(den)[self.rebin]
        num = num.to_numpy()
        edges = num[1]
        num = num[0]
        den = den.to_numpy()[0]
        centers = (edges[:-1] + edges[1:]) / 2
        eff = np.nan_to_num(num / den, 0)
        if "marker" not in kwargs:
            kwargs["marker"] = self.markers_copy.pop(0)
            if len(self.markers_copy) == 0:
                self.markers_copy = self.markers.copy()
        if self.step:
            self.ax.step(centers, eff, where="mid", **kwargs)
        else:
            self.ax.plot(centers, eff, **kwargs)

        if self.yerr:
            err = np.nan_to_num(intervals.ratio_uncertainty(num, den, "efficiency"), 0)
            if self.fillerr:
                self.ax.fill_between(centers, eff-err[0], eff+err[1], color=self.ax.lines[-1].get_color(),**fill_kwargs)
            else:
                xerr = np.diff(edges) / 2 if (not self.step and self.xerr) else None
                self.ax.errorbar(centers, eff, yerr=err, xerr=xerr, fmt="none", color=self.ax.lines[-1].get_color(), **err_kwargs)

        sys.stderr = open(os.devnull, "w")
        self.ax.legend(**self.legend_kwargs)
        sys.stderr = sys.__stderr__