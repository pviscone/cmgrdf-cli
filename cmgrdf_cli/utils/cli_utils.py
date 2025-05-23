import importlib
import os
import re
import types
import shutil
import sys

from CMGRDF import Flow, Cut
from CMGRDF.flow import SimpleExprFlowStep

from cmgrdf_cli.flows import Tree

def center_header(text, s="-", padding=0, max_width=150):
    text=f" {text} "
    term_width = os.get_terminal_size().columns
    if max_width is not None:
        term_width = min(term_width, max_width)
    max_padding = term_width // 2
    adjusted_padding = min(padding, max_padding)
    available_width = term_width - 2 * adjusted_padding
    truncated_text = text[:available_width] if len(text) > available_width else text
    if available_width > 0:
        line_part = f"{truncated_text:{s}^{available_width}}"
    else:
        line_part = ''
    return ' ' * adjusted_padding + line_part + ' ' * adjusted_padding

def load_module(filepath):
    if filepath is not None:
        if filepath.count(":") == 0:
            module_name = filepath.split(".py")[0].replace("/", ".")
            kwargs = {}
        elif filepath.count(":") == 1:
            filepath, args = filepath.split(":")
            module_name = filepath.split(".py")[0].replace("/", ".")
            filepath = os.path.join(os.getcwd(), filepath)
            kwargs = eval(f"dict({args})")
        else:
            raise ValueError("The filepath should contain at most one ':' to specify the function arguments")
        filepath = os.path.join(os.getcwd(), filepath)
        spec = importlib.util.spec_from_file_location(module_name, filepath)
        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)
        return module, kwargs
    return None, {}


def parse_function(module, name, typ, kwargs={}):
    if module is None:
        if typ is Flow:
            return Flow("alwaysTrue", [Cut("alwaysTrue", "1")])
        elif typ is None:
            return None
        else:
            return typ()

    if typ is Flow:
        obj = getattr(
            module, name, Flow("alwaysTrue", [Cut("alwaysTrue", "1")])
        )  # typ or function that returns typ
    elif typ is None:
        obj = getattr(
            module, name, None
        )
    else:
        obj = getattr(
            module, name, typ()
        )  # typ or function that returns typ

    if not isinstance(obj, typ | types.FunctionType):
        raise ValueError(f"Expected a {typ} or a function but got {type(obj)}")

    if isinstance(obj, types.FunctionType):
        obj = obj(**kwargs)
        if not ((obj is None and typ is None) or isinstance(obj, typ)):
            raise ValueError(f"The function should return an object of type {typ} but got {type(obj)}")

    if isinstance(obj, Flow):
        if not isinstance(obj[0], SimpleExprFlowStep) or obj[0].expr != "1":
            obj.prepend(Cut("nEvents", "1"))

    if isinstance(obj, Tree):
        for segment in obj.segments:
            if obj.segments[segment].isHead:
                obj.segments[segment].obj.insert(0, Cut("nEvents", "1"))

    return obj

def copy_file_to_subdirectories(src_file, target_folder, ignore=[]):
    shutil.copy(src_file, target_folder)
    for root, dirs, _ in os.walk(target_folder):
        for directory in dirs:
            target_dir = os.path.abspath(os.path.join(root, directory))
            skip = False
            for i in ignore:
                if i in target_dir:
                    skip = True
            if skip:
                continue
            shutil.copy(src_file, target_dir)

def is_in_command(pattern):
    return bool(re.match(pattern, os.environ["cmgrdf_cli_command"]))

def is_in_extra(pattern):
    extras = os.environ["cmgrdf_cli_extra"].split(",")
    for extra in extras:
        if re.match(pattern, extra):
            return True
    return False
