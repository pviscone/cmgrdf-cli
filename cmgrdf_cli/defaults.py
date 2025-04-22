from collections import OrderedDict

# Priority: global_defaults < histo1d_defaults < branch_defaults < user defined
global_defaults = OrderedDict()

histo1d_defaults = OrderedDict(
    includeOverflows=False,
    includeUnderflows=False,
)

histo2d_defaults = OrderedDict()

histo3d_defaults = OrderedDict()

# The first matched pattern will be used
name_defaults = OrderedDict({})
