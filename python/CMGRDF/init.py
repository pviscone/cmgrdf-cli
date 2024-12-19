import hashlib
import os.path
import sys
from typing import Any, Optional
import ROOT  # type: ignore

_codelines = []
_includepaths = set()
_dynpaths = set()
_dynlibs = []
_hasher = hashlib.sha256()


def _makePreprocessorGuard(code : str) -> str:
    if code.startswith("#ifndef"):
        return code
    hasher = hashlib.sha256()
    hasher.update(code.encode())
    symbol = f"_CMGRDF_auto_{hasher.hexdigest()}_"
    return f"#ifndef {symbol}\n#define {symbol}\n{code}\n#endif"


def ProcessLine(code : str) -> None:
    global _codelines, _hasher
    shortcode = code.strip()[:70]  # noqa: F841
    code = code if code[0] == "." else _makePreprocessorGuard(code)  # don't wrap CLING magic codes
    ROOT.gInterpreter.ProcessLine(code)
    _codelines.append(('ProcessLine', code))
    _hasher.update(('ProcessLine ' + code).encode())
    #print(f"Global hash is now {_hasher.hexdigest()} after processline {shortcode!r}")


def Declare(code : str) -> None:
    global _codelines, _hasher
    shortcode = code.strip()[:70]  # noqa: F841
    code = _makePreprocessorGuard(code)
    ROOT.gInterpreter.Declare(code)
    _codelines.append(('Declare', code))
    _hasher.update(('Declare ' + code).encode())
    #print(f"Global hash is now {_hasher.hexdigest()} after declaring {shortcode!r}")


def _hashFile(role : str, filename : str, filepath : str) -> None:
    global _hasher
    if filepath:
        filepath = os.path.expandvars(filepath)
        if not os.path.isfile(filepath + "/" + filename):
            raise RuntimeError(f"Error, could not find {role} {filename} in path {filepath}x)")
        with open(filepath + "/" + filename, "rb") as f:
            if hasattr(hashlib, 'file_digest'):
                hashlib.file_digest(f, lambda : _hasher)  # type: ignore
            else:
                size = os.stat(filepath + "/" + filename).st_size
                _hasher.update(f.read(size))


def AddHeader(header : str, includepath : str = "${CMGRDF}/include", extraIncludePaths : Optional[list[str]] = None) -> None:
    global _codelines, _includepaths, _hasher
    paths = ([includepath] if includepath else []) + (extraIncludePaths if extraIncludePaths else [])
    for p in paths:
        p = os.path.expandvars(p)
        ROOT.gInterpreter.AddIncludePath(p)
        _includepaths.add(p)
    ROOT.gInterpreter.Declare(f'#include "{header}"')
    _codelines.append(('Declare', f'#include "{header}"'))
    _hasher.update(('Include ' + header).encode())
    _hashFile('header', header, includepath)
    #print(f"Global hash is now {_hasher.hexdigest()} after loading {header}")


def LoadLibrary(library : str, filepath : str = "${CMGRDF}/lib", extraPaths : Optional[list[str]] = None) -> None:
    global _dynpaths, _dynlibs, _hasher
    paths = ([filepath] if filepath else []) + (extraPaths if extraPaths else [])
    for p in paths:
        p = os.path.expandvars(p)
        ROOT.gSystem.AddDynamicPath(p)  # type: ignore
        _dynpaths.add(p)
    ROOT.gSystem.Load(library)
    _dynlibs.append(library)
    _hasher.update(('Load ' + library).encode())
    _hashFile('Library', library, filepath)
    #print(f"Global hash is now {_hasher.hexdigest()} after loading {library}")


def HasherFromGlobalConfig() -> Any:
    global _hasher
    return _hasher.copy()


def GlobalConfigHash() -> str:
    global _hasher
    return _hasher.hexdigest()


_modules_and_inits = [
    ("correctionlib", "correctionlib.register_pyroot_binding()"),
    ("CMSJMECalculators", "CMSJMECalculators.loadJMESystematicsCalculators()")
]


def RunDistributedInitializer(daskClient : Any) -> None:
    global _modules_and_inits
    current_config = _hasher.hexdigest()
    #print(f"Requested hash is now {current_config}")
    #check if used modules are loaded
    import sys
    for attempt in "first", "second", "failed":
        for mod, initstr in _modules_and_inits:
            if mod in sys.modules:
                print(f"{mod} loaded here, will try to propagate to workers")
                maybe_corrlib = daskClient.run(eval, f'"{mod}" in sys.modules')
                no_corrlib_workers = [w for (w, s) in maybe_corrlib.items() if not s]
                daskClient.run(exec, f'import {mod}\n{initstr}', workers=no_corrlib_workers)
        #Check if CMGRDF was loaded
        maybe_cmgrdf = daskClient.run(eval, '"CMGRDF" in sys.modules')
        cmgrdf_workers = [w for (w, s) in maybe_cmgrdf.items() if s]
        nocmgrdf_workers = [w for (w, s) in maybe_cmgrdf.items() if not s]
        #print(f"Clients have CMGRDF loaded ? {maybe_cmgrdf}")
        if cmgrdf_workers:
            # Check hash
            cmgrdf_hash = daskClient.run(eval, 'sys.modules["CMGRDF"].init.GlobalConfigHash()', workers=cmgrdf_workers)
            #print(f"Hash of CMGRDF workers {cmgrdf_hash}")
            bad_workers = [w for (w, h) in cmgrdf_hash.items() if h != current_config]
            if bad_workers:
                raise RuntimeError(f"WARNING: Found {len(bad_workers)} workers with CMGRDF already loaded but an incompatible config hash.")
            print(f"INFO: Found {len([h for h in cmgrdf_hash.values() if h == current_config])} workers with CMGRDF already loaded with the proper init")
        if nocmgrdf_workers:
            hashes = daskClient.run(eval, 'sys._xoptions.get("_CMGRDF_global_hash", None)', workers=nocmgrdf_workers)
            #print(f"Worker hashes: {hashes}")
            all_workers = [w for w in hashes.keys() if w not in cmgrdf_workers]
            done_workers = [w for w in all_workers if hashes[w] == current_config]
            todo_workers = [w for w in all_workers if hashes[w] is None]
            other_workers = [w for w in all_workers if hashes[w] not in (current_config, None)]
            if other_workers:
                if attempt == "failed":
                    raise RuntimeError(f"DANGER: {len(other_workers)} workers in the Dask cluster were already initialized with different inits (includes, libs, declares, ...)")
                else:
                    print(f"DANGER: {len(other_workers)} workers in the Dask cluster were already initialized with different inits (includes, libs, declares, ...), {attempt} attempt to restart them.")
                    restart_result = daskClient.restart_workers(other_workers, timeout=300, raise_for_error=False)
                    print("Restart result:", restart_result)
                    continue
            if len(done_workers):
                print(f"INFO: {len(done_workers)} workers in the Dask cluster were already initialized with the right config.")
            if len(todo_workers):
                print(f"INFO: {len(todo_workers)} workers in the Dask cluster need to be initialized.")
                daskClient.run(exec, DistributedInitializerCode(), workers=todo_workers)
                #hashes = daskClient.run(eval, 'sys._xoptions.get("_CMGRDF_global_hash", None)')
                #print(f"Worker hashes: {hashes}")
        break


def DistributedInitializerCode() -> str:
    global _codelines, _includepaths, _dynpaths, _dynlibs, _modules_and_inits, _hasher
    current_config = _hasher.hexdigest()
    code = "import os, sys\n"
    for mod, initstr in _modules_and_inits:
        if mod in sys.modules:
            code += f'if "{mod}" not in sys.modules:\n'
            code += f'  import {mod}\n'
            code += f'  {initstr}\n'
    code += f"if (\"CMGRDF\" not in sys.modules) and (sys._xoptions.get(\"_CMGRDF_global_hash\", None) != \"{current_config}\"):\n"
    code += "  print('Initializing worker for config %s, existing was', sys._xoptions.get(\"_CMGRDF_global_hash\", None), flush=True)\n" % current_config
    code += "  import ROOT\n"
    code += "  ROOT.gROOT.SetBatch(True)\n"
    code += "  ROOT.PyConfig.IgnoreCommandLineOptions = True\n"
    code += "  ROOT.EnableThreadSafety()\n"
    code += '  os.environ["CMGRDF"] = %r\n' % os.environ["CMGRDF"]
    code += "".join(f"  ROOT.gInterpreter.AddIncludePath({p!r})\n" for p in _includepaths)
    code += "".join(f"  ROOT.gSystem.AddDynamicPath({p!r})\n" for p in _dynpaths)
    code += "".join(f"  ROOT.gSystem.Load({p!r}, \"\", True)\n" for p in _dynlibs)
    code += "".join(f"  ROOT.gInterpreter.{op}({line!r})\n" for (op, line) in _codelines)
    code += "  print('Initialization done for config %s', flush=True)\n" % current_config
    code += "  sys._xoptions['_CMGRDF_global_hash'] = %r\n" % current_config
    #code += "else:\n"
    #code += "  print('Not re-initializing worker, CMGRDF %s, hash %s' % (\"CMGRDF\" in sys.modules, sys._xoptions.get(\"_CMGRDF_global_hash\", None)))\n"
    return code
