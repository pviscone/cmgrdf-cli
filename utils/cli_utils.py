import importlib
import types

from CMGRDF import Flow, Cut
from CMGRDF.flow import SimpleExprFlowStep

from flows import Tree

def load_module(filepath):
    if filepath is not None:
        if filepath.count(":") == 0:
            return importlib.import_module(filepath.split(".py")[0].replace("/", ".")), {}
        elif filepath.count(":") == 1:
            filepath, args = filepath.split(":")
            kwargs = eval(f"dict({args})")
            return importlib.import_module(filepath.split(".py")[0].replace("/", ".")), kwargs
        else:
            raise ValueError("The filepath should contain at most one ':' to specify the function arguments")
    return None, {}


def parse_function(module, name, typ, kwargs={}):
    if module is None:
        return typ() if typ is not Flow else Flow("alwaysTrue", [Cut("alwaysTrue", "1")])

    obj = getattr(
        module, name, typ() if typ is not Flow else Flow("alwaysTrue", [Cut("alwaysTrue", "1")])
    )  # typ or function that returns typ

    if not isinstance(obj, typ | types.FunctionType):
        raise ValueError(f"Expected a {typ} or a function but got {type(obj)}")

    if isinstance(obj, types.FunctionType):
        obj = obj(**kwargs)
        if not isinstance(obj, typ):
            raise ValueError(f"The function should return an object of type {typ} but got {type(obj)}")

    if isinstance(obj, Flow):
        if not isinstance(obj[0], SimpleExprFlowStep) or obj[0].expr != "1":
            obj.prepend(Cut("nEvents", "1"))

    if isinstance(obj, Tree):
        for segment in obj.segments:
            if obj.segments[segment].isHead:
                obj.segments[segment].obj.insert(0, Cut("nEvents", "1"))

    return obj
