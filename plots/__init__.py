from CMGRDF import Plot
import copy
import re
import numpy as np
from plots.defaults import global_defaults, histo1d_defaults, histo2d_defaults, histo3d_defaults, name_defaults

class BaseHist(Plot):
    def __init__(self, type_kwargs, pattern_kwargs, user_kwargs, name, expr, bins=None):
        union_kwargs = {**global_defaults, **type_kwargs, **pattern_kwargs, **user_kwargs}
        if bins is None:
            raise ValueError(f"For {name}:{expr}, bins are not defined neither in the user arguments nor in the name_defaults")
        super().__init__(name, expr, bins, **union_kwargs)


class Hist(BaseHist):
    def __init__(self, name, expr, bins=None, **user_kwargs):
        if "typ" in user_kwargs:
            del user_kwargs["typ"]

        pattern_kwargs = {}
        for pattern in name_defaults:
            if re.search(pattern, name):
                pattern_kwargs = copy.deepcopy(name_defaults[pattern])
                pattern_kwargs.setdefault("label", None)
                pattern_kwargs.setdefault("log", "")

                label = pattern_kwargs.get("label")
                if label:
                    groups = re.match(pattern, name).groups()
                    for i, group in enumerate(groups):
                        label = label.replace(f"(${i+1})", group, 1)
                    label = label.replace("  ", " ")
                pattern_kwargs["xTitle"] = label
                pattern_kwargs["xlabel"] = label
                bins = pattern_kwargs.pop("bins", bins) if bins is None else bins

                #log
                log = pattern_kwargs.pop("log", "")
                log_l = log.split(",")
                log = ""
                if "axis" in log_l:
                    log += "x"
                elif "counts" in log_l:
                    log += "y"
                pattern_kwargs["log"] = log

                break
        super().__init__(histo1d_defaults, pattern_kwargs, user_kwargs, name, expr, bins)


class Hist2D(BaseHist):
    def __init__(self, name, expr_x, expr_y, bins_x = None, bins_y = None, **user_kwargs):
        assert name.count(":") == 1, "Name must contain exactly one ':'"
        expr = f"{expr_y}:{expr_x}"
        user_kwargs["typ"] = "Histo2D"

        bins = [bins_x, bins_y]
        th2_dict = dict(log="")
        for ax_idx, ax_name in enumerate(name.split(":")):
            for pattern in name_defaults:
                if re.search(pattern, ax_name):
                    pattern_kwargs = copy.deepcopy(name_defaults[pattern])
                    bins[ax_idx] = pattern_kwargs.pop("bins", bins[ax_idx]) if bins[ax_idx] is None else bins[ax_idx]

                    label = pattern_kwargs.pop("label", None)
                    if label:
                        groups = re.match(pattern, ax_name).groups()
                        for i, group in enumerate(groups):
                            label = label.replace(f"(${i+1})", group, 1)
                        label = label.replace("  ", " ")
                    if ax_idx == 0:
                        th2_dict["xTitle"] = label
                        th2_dict["xlabel"] = label
                    elif ax_idx == 1:
                        th2_dict["yTitle"] = label
                        th2_dict["ylabel"] = label

                    #Log
                    #log on counts also if setted for one single axis
                    log = pattern_kwargs.pop("log", "")
                    log_l = log.split(",")
                    if "axis" in log_l:
                        th2_dict["log"] += "x" if ax_idx == 0 else "y"
                    elif "counts" in log_l:
                        th2_dict["log"] += "z"

                    #density true only if density is setted for both axis or in user_kwargs
                    if "density" in pattern_kwargs:
                        density = pattern_kwargs.pop("density", False)
                        if "density" in th2_dict:
                            th2_dict["density"] = th2_dict["density"] and density
                        else:
                            th2_dict["density"] = density


                    break
        assert all(bins), "Bins are not defined neither in the user arguments nor in the name_defaults"

        #Currently, cmgrdf not supports mixed definition of bins. In case, convert the tuple to a list
        if isinstance(bins[0], tuple) and isinstance(bins[1], tuple):
            bins = (*bins[0], *bins[1])
        else:
            for ax_idx in range(2):
                if isinstance(bins[ax_idx], tuple):
                    bins[ax_idx] = np.linspace(bins[ax_idx][1], bins[ax_idx][2], bins[ax_idx][0]+1).tolist()
        name = name.replace(":", "_vs_")
        super().__init__(histo2d_defaults, th2_dict, user_kwargs, name, expr, bins)


class Hist3D(BaseHist):
    def __init__(self, name, expr_x, expr_y, expr_z, bins_x = None, bins_y = None, bins_z = None, **user_kwargs):
        assert name.count(":") == 2, "Name must contain exactly two ':'"
        expr = f"{expr_y}:{expr_x}:{expr_z}"
        user_kwargs["typ"] = "Histo3D"

        bins = [bins_x, bins_y, bins_z]
        th3_dict = dict(log="")
        for ax_idx, ax_name in enumerate(name.split(":")):
            for pattern in name_defaults:
                if re.search(pattern, ax_name):
                    pattern_kwargs = copy.deepcopy(name_defaults[pattern])
                    bins[ax_idx] = pattern_kwargs.pop("bins", bins[ax_idx]) if bins[ax_idx] is None else bins[ax_idx]

                    pattern_kwargs.pop("log")
                    pattern_kwargs.pop("label")
                    pattern_kwargs.pop("density")
                    break
        assert all(bins), "Bins are not defined neither in the user arguments nor in the name_defaults"

        #Currently, cmgrdf not supports mixed definition of bins. In case, convert the tuple to a list
        if isinstance(bins[0], tuple) and isinstance(bins[1], tuple) and isinstance(bins[2], tuple):
            bins = (*bins[0], *bins[1], *bins[2])
        else:
            for ax_idx in range(3):
                if isinstance(bins[ax_idx], tuple):
                    bins[ax_idx] = [bins[ax_idx][1]+bins[ax_idx][2]*i/bins[ax_idx][0] for i in range(bins[ax_idx][0]+1)]

        name = name.replace(":", "_vs_")
        super().__init__(histo3d_defaults, th3_dict, user_kwargs, name, expr, bins)
