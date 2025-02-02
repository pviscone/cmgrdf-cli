from CMGRDF import Plot
import copy
import re

from plots.defaults import global_defaults, histo1d_defaults, histo2d_defaults, name_defaults

class BaseHist(Plot):
    def __init__(self, type_kwargs, pattern_kwargs, user_kwargs, name, expr, bins=None):
        union_kwargs = {**global_defaults, **type_kwargs, **pattern_kwargs, **user_kwargs}
        if bins is None:
            raise ValueError("Bins are not defined neither in the user arguments nor in the name_defaults")
        super().__init__(name, expr, bins, **union_kwargs)


class Hist(BaseHist):
    def __init__(self, name, expr, bins=None, **user_kwargs):
        if "typ" in user_kwargs:
            del user_kwargs["typ"]

        pattern_kwargs = {}
        for pattern in name_defaults:
            if re.search(pattern, name):
                pattern_kwargs = copy.deepcopy(name_defaults[pattern])
                label = pattern_kwargs.get("label", None)
                if label:
                    groups = re.match(pattern, name).groups()
                    for i, group in enumerate(groups):
                        label = label.replace(f"(${i+1})", group, 1)
                pattern_kwargs["xTitle"] = label
                pattern_kwargs["xlabel"] = label
                bins = pattern_kwargs.pop("bins", bins) if bins is None else bins
                break

        super().__init__(histo1d_defaults, pattern_kwargs, user_kwargs, name, expr, bins)


class Hist2D(BaseHist):
    def __init__(self, name, expr_x, expr_y, bins_x = None, bins_y = None, **user_kwargs):
        assert name.count(":") == 1, "Name must contain exactly one ':'"
        expr = f"{expr_y}:{expr_x}"
        user_kwargs["typ"] = "Histo2D"

        bins = [bins_x, bins_y]

        #The only arguments taken from name_defaults for th2 are bins and labels
        th2_dict = {}
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
                    if ax_idx == 0:
                        th2_dict["xTitle"] = label
                        th2_dict["xlabel"] = label
                    elif ax_idx == 1:
                        th2_dict["yTitle"] = label
                        th2_dict["ylabel"] = label
                    break

        assert all(bins), "Bins are not defined neither in the user arguments nor in the name_defaults"

        #Currently, cmgrdf not supports mixed definition of bins. In case, convert the tuple to a list
        if isinstance(bins[0], tuple) and isinstance(bins[1], tuple):
            bins = (*bins[0], *bins[1])
        else:
            for ax_idx in range(2):
                if isinstance(bins[ax_idx], tuple):
                    bins[ax_idx] = [bins[ax_idx][1]+bins[ax_idx][2]*i/bins[ax_idx][0] for i in range(bins[ax_idx][0]+1)]

        name = name.replace(":", "_vs_")
        super().__init__(histo2d_defaults, th2_dict, user_kwargs, name, expr, bins)


