from CMGRDF import Plot
import copy
import re

from plots.defaults import global_defaults, histo1d_defaults, histo2d_defaults, name1d_defaults, name2d_defaults


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
        for pattern in name1d_defaults:
            if re.search(pattern, name):
                pattern_kwargs = copy.deepcopy(name1d_defaults[pattern])
                if "bins" in name1d_defaults[pattern]:
                    bins = pattern_kwargs["bins"]
                    del pattern_kwargs["bins"]
                break

        super().__init__(histo1d_defaults, pattern_kwargs, user_kwargs, name, expr, bins)


class Hist2D(BaseHist):
    def __init__(self, name, expr, bins=None, **user_kwargs):
        user_kwargs["typ"] = "Histo2D"
        # TODO Implement pattern matching for 2D histograms
        pattern_kwargs = {}
        super().__init__(histo2d_defaults, pattern_kwargs, user_kwargs, name, expr, bins)
