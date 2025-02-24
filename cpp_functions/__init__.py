import ROOT

import glob
import os

thisdir = os.path.dirname(__file__)
cfile_ext = ("cpp", "cxx", "cc", "c++", "c", "C", "CPP", "h", "hxx", "hpp", "hh", "H")


def load(*files, exclude=[]):
    if files and exclude:
        raise ValueError("Both 'files' and 'exclude' cannot be specified at the same time.")

    if files:
        for file in files:
            file_path = os.path.join(thisdir, file)
            print(f"Including {file_path.rsplit('/', 2)[-1]}")
            ROOT.gInterpreter.Declare(f'#include "{file_path}"')
    else:
        for ext in cfile_ext:
            for file_path in glob.glob(os.path.join(thisdir, f"*.{ext}")):
                if file_path.rsplit("/", 1)[-1] in exclude:
                    continue
                print(f"Including {file_path.rsplit('/', 2)[-1]}")
                ROOT.gInterpreter.Declare(f'#include "{file_path}"')
