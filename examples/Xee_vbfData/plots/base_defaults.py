from collections import OrderedDict
import numpy as np
import cmgrdf_cli.defaults

# The first matched pattern will be used
cmgrdf_cli.defaults.name_defaults = OrderedDict({
    "(.*)_p$": dict(
        bins=(40, 0, 500),
        label="($1) $|p|$ [GeV]",
        log="counts"
    ),
    "(.*)_(?:pt|invPt)(.*)": dict(
        bins=(40, 0, 80),
        label="($1) ($2) $p_{T}$ [GeV]",
    ),
    "(.*)_cosTheta(.*)": dict(
        bins=(30, -1.1, 1.1),
        label="($1) ($2) cos$(\theta)$",
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
        bins=(30, 2.6, 4.2),
        label="($1) ($2) m [GeV]",
    ),
    "(.*)_(normMass)(.*)": dict(
        bins=(30, 2.6, 4.2),
        label="($1) ($2) m [GeV]",
        density=True
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
        bins=(15, 0, 15),
        label="# ($1)",
        density=True,
        log="counts",
    ),
})
