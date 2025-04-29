from collections import OrderedDict
import importlib
import os
import inspect

def load_defaults(module_relative_path):
    frame = inspect.currentframe()
    filename = frame.f_back.f_code.co_filename
    del frame
    abs_path = os.path.abspath(filename)
    abs_path = os.path.dirname(abs_path)
    spec = importlib.util.spec_from_file_location("defaults", os.path.join(abs_path, f"{module_relative_path}.py"))
    foo = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(foo)

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
