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
    ".*_(pt|invPt).*": dict(
        bins=(50, 0, 50),
    ),
    ".*_eta.*": dict(
        bins=(30, -2, 2),
    ),
    ".*_(mass|invMass).*": dict(
        bins=(40, 0, 6),
    ),
    ".*_dR.*": dict(
        bins=(40, 0, 1.5),
    ),
    ".*_type": dict(
        bins=(3, 1, 4),
    ),
    "n.*": dict(
        bins=(10, 0, 10),
    ),
}

# TODO Think of a smart way to define defaults for TH2
name2d_defaults = {
    ".*_(pt|invPt).*": dict(
        bins=(50, 0, 50),
    ),
    ".*_eta.*": dict(
        bins=(30, -2, 2),
    ),
    ".*_(mass|invMass).*": dict(
        bins=(40, 0, 6),
    ),}
