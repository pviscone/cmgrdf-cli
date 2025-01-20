# Priority: global_defaults < histo1d_defaults < branch_defaults < user defined
global_defaults = dict()

histo1d_defaults = dict(
    includeOverflows=False,
    includeUnderflows=False,
)

histo2d_defaults = {}


# The first matched pattern will be used
# TODO xTitle like a regex pattern?
name1d_defaults = {
    ".*_pt.*": dict(
        bins=(50, 0, 50),
    ),
    ".*_mass.*": dict(
        bins=(30, 2.7, 3.3),
    ),
}

# TODO Think of a smart way to define defaults for TH2
name2d_defaults = {}
