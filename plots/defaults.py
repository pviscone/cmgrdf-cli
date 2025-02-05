from collections import OrderedDict

# Priority: global_defaults < histo1d_defaults < branch_defaults < user defined
global_defaults = OrderedDict()

histo1d_defaults = OrderedDict(
    includeOverflows=False,
    includeUnderflows=False,
)

histo2d_defaults = OrderedDict()

# The first matched pattern will be used
name_defaults = OrderedDict({
    "(.*)_(?:pt|invPt)(.*)": dict(
        bins=(50, 0, 50),
        label="($1) ($2) $p_{T}$ [GeV]",
    ),
    "(.*)_eta(.*)": dict(
        bins=(30, -2, 2),
        label="($1) ($2) $\eta$",
    ),
    "(.*)_abseta(.*)": dict(
        bins=(30, 0, 2),
        label="($1) ($2) $|\eta|$",
    ),
    "(.*)_phi(.*)": dict(
        bins=(30, -3.14, 3.14),
        label="($1) ($2) $\phi$",
    ),
    "(.*)_(mass|invMass)(.*)": dict(
        bins=(40, 0, 6),
        label="($1) ($2) m [GeV]",
    ),
    "(.*)_dR(.*)": dict(
        bins=(40, 0, 1.5),
        label="($1) ($2) $\Delta$R",
    ),
    "(.*)_type(.*)": dict(
        bins=(3, 1, 4),
        label="($1) ($2) type",
    ),
    "n(.*)": dict(
        bins=(10, 0, 10),
        label="# ($1)",
    ),
})
