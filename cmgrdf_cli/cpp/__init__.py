import ROOT
from cmgrdf_cli.utils.log_utils import accessed_files
import glob
import os

cfile_ext = ("cpp", "cxx", "cc", "c++", "c", "C", "CPP", "h", "hxx", "hpp", "hh", "H")

def add_include_path(path):
    #if p is a subpath of any of the paths in accessed_files, do not add it
    if not any([p in os.path.abspath(path) for p in accessed_files]):
        accessed_files.append(os.path.abspath(path))
    ROOT.gInterpreter.AddIncludePath(path)

def include(path):
    #if p is a subpath of any of the paths in accessed_files, do not add it
    if not any([p in os.path.abspath(path) for p in accessed_files]):
        accessed_files.append(os.path.abspath(path))
    ROOT.gInterpreter.Declare(f'#include "{path}"')
    print(f"Including {path.rsplit('/', 2)[-1]}")

def declare(cpp_string):
    ROOT.gInterpreter.Declare(cpp_string)

def load(folder, *files, exclude=[]):
    ROOT.gInterpreter.AddIncludePath(folder)
    if files and exclude:
        raise ValueError("Both 'files' and 'exclude' cannot be specified at the same time.")

    if files:
        for file in files:
            file_path = os.path.join(folder, file)
            print(f"Including {file_path.rsplit('/', 2)[-1]}")
            ROOT.gInterpreter.Declare(f'#include "{file_path}"')
    else:
        for ext in cfile_ext:
            for file_path in glob.glob(os.path.join(folder, f"*.{ext}")):
                if file_path.rsplit("/", 1)[-1] in exclude:
                    continue
                print(f"Including {file_path.rsplit('/', 2)[-1]}")
                ROOT.gInterpreter.Declare(f'#include "{file_path}"')
                accessed_files.append(os.path.abspath(file_path))
