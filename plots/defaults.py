from collections import OrderedDict
import numpy as np

# Priority: global_defaults < histo1d_defaults < branch_defaults < user defined
global_defaults = OrderedDict()

histo1d_defaults = OrderedDict(
    includeOverflows=False,
    includeUnderflows=False,
)

histo2d_defaults = OrderedDict()

histo3d_defaults = OrderedDict()

# The first matched pattern will be used
name_defaults = OrderedDict({
    "(.*)_(?:pt|invPt)(.*)": dict(
        bins=(40, 0, 80),
        label="($1) ($2) $p_{T}$ [GeV]",
    ),
    "(.*)_deta(.*)": dict(
        bins=(30, 0, 6),
        label="($1) ($2) $|\Delta \eta|$",
    ),
    "(.*)_eta(.*)": dict(
        bins=(20, -4, 4),
        label="($1) ($2) $\eta$",
    ),
    "(.*)_abseta(.*)": dict(
        bins=(20, 0, 4),
        label="($1) ($2) $|\eta|$",
    ),
    "(.*)_phi(.*)": dict(
        bins=(20, -3.14, 3.14),
        label="($1) ($2) $\phi$",
    ),
    "(.*)_(mass|invMass)(.*)": dict(
        bins=(30, 0, 15),
        label="($1) ($2) m [GeV]",
    ),
    "(.*)_dR(.*)": dict(
        bins=list(np.logspace(-2, np.log(5), 30)),
        label="($1) ($2) $\Delta$R",
        log="axis",
    ),
    "(.*)_type(.*)": dict(
        bins=(3, 1, 4),
        label="($1) ($2) type",
        density=True,
        log="counts",
    ),
    "n(.*)": dict(
        bins=(10, 0, 10),
        label="# ($1)",
        density=True,
        log="counts",
    ),
})
