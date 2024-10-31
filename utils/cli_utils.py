import importlib
import types
import typing

from CMGRDF import Flow, Cut


def load_module(filepath):
    if filepath is not None:
        return importlib.import_module(filepath.split(".py")[0].replace("/", "."))
    return None


def parse_args(args, func):
    kwargs = {}
    hints = typing.get_type_hints(func)
    for arg in args:
        key, value = arg.split("=")
        typ = hints[key]
        kwargs[key] = typ(value)
    return kwargs


def parse_function(module, name, typ, args=[]):
    if module is None:
        return typ() if typ is not Flow else Flow("alwaysTrue", [Cut("alwaysTrue", "1")])

    if typ is not Flow:
        obj = getattr(module, name, typ())
    else:
        obj = getattr(module, name, Flow("alwaysTrue", [Cut("alwaysTrue", "1")]))

    if isinstance(obj, typ):
        return obj
    elif isinstance(obj, types.FunctionType):
        kwargs = parse_args(args, obj)
        res = obj(**kwargs)
        if isinstance(res, typ):
            return res
        else:
            raise ValueError(f"The function should return an object of type {typ} but got {type(res)}")
    else:
        raise ValueError(f"Expected a {typ} or a function but got {type(obj)}")
