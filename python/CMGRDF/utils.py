from collections import defaultdict
from collections.abc import Collection, ItemsView, Iterator, KeysView
from typing import Any, Optional, Union
import struct
import copy
import hashlib
import sys
import os.path
import re
import fnmatch


class OptionDecl(object):
    def __init__(self, name : str, default=None, opttype : Any = str, cmdline=None, **kwargs):
        self.name = name
        self.default = default
        self.type = opttype
        self.cmdline = cmdline
        self.kwargs = kwargs


class Options(object):
    def __init__(self, *optionDeclarations : OptionDecl):
        self._values: dict[str, Any] = dict()
        self._declarations = []
        for opt in optionDeclarations:
            self.declare(opt.name, default=opt.default, opttype=opt.type, cmdline=opt.cmdline, **opt.kwargs)

    def declare(self, name : str, default : Any = None, opttype : Any = str, cmdline=None, **kwargs) -> "Options":
        self._declarations.append((name, default, opttype, cmdline, kwargs))
        if name in self._values:
            if default is not None:
                raise RuntimeError("Duplicate definition of " + name)
        else:
            self._values[name] = default
        return self

    def addToParser(self, parser) -> None:
        for (name, default, opttype, cmdline, kwargs) in self._declarations:
            if opttype == bool:
                if not cmdline:
                    cmdline = ["--no" + name] if default else ["--" + name]
                action = "store_false" if default else "store_true"
                parser.add_argument(*cmdline, dest=name, action=action, **kwargs)
            else:
                if not cmdline:
                    cmdline = ["--" + name]
                parser.add_argument(*cmdline, dest=name, type=opttype, default=self._values[name], **kwargs)

    def __getattr__(self, name : str) -> Any:
        return self._values[name]

    def __getitem__(self, name : str) -> Any:
        return self._values[name]

    def __hasattr__(self, name : str) -> bool:
        return name in self._values

    def __contains__(self, name : str) -> bool:
        return name in self._values

    def __setattr__(self, name : str, value) -> None:
        if name[0] == "_" or name not in self._values:
            object.__setattr__(self, name, value)
        else:
            self._values[name] = value

    def __setitem__(self, name : str, value) -> None:
        self._values[name] = value

    def __len__(self) -> int:
        return len(self._values)

    def update(self, **kwargs) -> "Options":
        self._values.update(kwargs)
        return self

    def items(self) -> ItemsView[str, Any]:
        return self._values.items()

    def keys(self) -> KeysView[str]:
        return self._values.keys()

    def cloneAndUpdate(self, **kwargs) -> "Options":
        ret = Options()
        ret._values = dict(self._values.items())
        ret._values.update(**kwargs)
        return ret

    def cloneAndExtend(self, *optionDeclarations : OptionDecl) -> "Options":
        ret = Options()
        ret._values = copy.copy(self._values)
        ret._declarations = copy.copy(self._declarations)
        for opt in optionDeclarations:
            self.declare(opt.name, default=opt.default, type=opt.type, cmdline=opt.cmdline, **opt.kwargs)
        return ret


class MultiKey(object):
    """A multi-field key to identify results, e.g. a histogram by its selection flow, variable name, and sample used"""

    def __init__(self, **kwargs : Any):
        self._keys = sorted(kwargs.keys())
        self._values = dict(kwargs.items())

    def idTuple(self) -> tuple[int, ...]:
        return tuple([id(self._values[k]) for k in self._keys])

    def keys(self) -> list[str]:
        return self._keys

    def items(self) -> ItemsView[str, Any]:
        return self._values.items()

    def __len__(self) -> int:
        return len(self._keys)

    def __getattr__(self, name : str) -> Any:
        return self._values[name]

    def __getitem__(self, name : str) -> Any:
        return self._values[name]

    def __hasattr__(self, name : str) -> bool:
        return name in self._values

    def __contains__(self, name : str) -> bool:
        return name in self._values

    def isSuperSet(self, other : "MultiKey") -> bool:
        """Returns true if our key is a superset of `other`, i.e. if all our fields match those of `other`,
        (but `other` may have more fields that we don't have)"""
        return all((other._values[k] == v) for k, v in self._values.items())

    def removeKeys(self, *keysToRemove : str) -> "MultiKey":
        """Produces a new multi-key removing the specified fields"""
        assert (all((k in self._keys) for k in keysToRemove))
        filtered = dict((k, v) for (k, v) in self.items() if k not in keysToRemove)
        return MultiKey(**filtered)

    def selectKeys(self, *keys : str) -> "MultiKey":
        """Produces a new multi-key selecting only the specified fields"""
        assert (all((k in self._keys) for k in keys))
        filtered = dict((k, v) for (k, v) in self.items() if k in keys)
        return MultiKey(**filtered)

    def addKeys(self, **kwargs : Any) -> "MultiKey":
        """Produces a new multi-key adding the specified fields"""
        extended = copy.copy(self._values)
        for (k, v) in kwargs.items():
            assert (k not in extended)
            extended[k] = v
        return MultiKey(**extended)

    def __hash__(self) -> int:
        return hash(tuple((k, self._values[k]) for k in self._keys))

    def __eq__(self, other) -> bool:
        if other.__class__ == MultiKey:
            if self._keys != other._keys:
                return False
            return all(self[k] == other[k] for k in self._keys)
        return id(self) == id(other)

    def __str__(self) -> str:
        return "(%s)" % (",".join("%s=%s" % (k, self._values[k]) for k in self._keys))

    def __repr__(self) -> str:
        return "MultiKey(%s)" % (",".join("%s=%r" % (k, self._values[k]) for k in self._keys))


class MultiReport(object):
    """A list of pairs (multi-key, object) with some convenience methods for extracting them."""

    def __init__(self, *items : tuple[MultiKey, Any]):
        self._items = list(items)
        for item in items:
            assert (isinstance(item, tuple) and isinstance(items[0], MultiKey))

    def append(self, key : MultiKey, value : Any) -> None:
        self._items.append((key, value))

    def __len__(self) -> int:
        return len(self._items)

    def __iter__(self) -> Iterator[tuple[MultiKey, Any]]:
        return iter(self._items)

    def groupRemoving(self, *keys : str) -> ItemsView[MultiKey, list[Any]]:
        """Return a list of groups of items removing some fields of the key"""
        mergeMap = defaultdict(list)
        for k, v in self._items:
            gk = k.removeKeys(*keys)
            mergeMap[gk].append(v)
        return mergeMap.items()

    def allMatchingKey(self, key : MultiKey) -> list[tuple[MultiKey, Any]]:
        """Get the subset of (key,value) pairs whose key matches all the fields in this key"""
        return [(k, p) for (k, p) in self._items if key.isSuperSet(k)]

    def getByKey(self, key : MultiKey) -> Any:
        alls = self.allMatchingKey(key)
        assert (len(alls) == 1)
        return alls[0][1]

    def sort(self, *args, **kwargs) -> None:
        self._items.sort(*args, **kwargs)


def _recursiveAddToHash(obj : Any, hasher) -> None:
    if obj is None:
        hasher.update(b"<None>")
        return
    hasher.update(str(type(obj)).encode())
    if isinstance(obj, str):
        hasher.update(obj.encode())
    elif isinstance(obj, bool):
        hasher.update(b"1" if obj else b"0")
    elif isinstance(obj, int):
        hasher.update(obj.to_bytes(8, sys.byteorder))
    elif isinstance(obj, float):
        hasher.update(struct.pack("d", obj))
    elif isinstance(obj, (list, tuple)):
        _recursiveAddToHash(len(obj), hasher)
        for e in obj:
            _recursiveAddToHash(e, hasher)
    elif isinstance(obj, set):
        _recursiveAddToHash(len(obj), hasher)
        for e in sorted(obj):
            _recursiveAddToHash(e, hasher)
    elif isinstance(obj, dict):
        _recursiveAddToHash(len(obj), hasher)
        for k, v in sorted(obj.items()):
            _recursiveAddToHash(k, hasher)
            _recursiveAddToHash(v, hasher)
    else:
        raise RuntimeError("Don't know how to hash %r of type %s" % (obj, type(obj)))


def safeName(obj : Any) -> str:
    return re.sub("[^A-Za-z0-9_]", "", obj.name)


def recursiveHash(*objs : Any) -> str:
    hasher = hashlib.sha256()
    for obj in objs:
        _recursiveAddToHash(obj, hasher)
    return hasher.hexdigest()


def eosToUrl(path : str) -> str:
    if path.startswith("/eos/cms"):
        return "root://eoscms.cern.ch/" + path
    elif path.startswith("/eos/user"):
        return "root://eosuser.cern.ch/" + path
    else:
        return path


def localOrEOS(path : str, localroot : str, eosroot : str) -> str:
    localPath = os.path.join(localroot, path)
    if os.path.isdir(localPath):
        return localPath
    return eosToUrl(os.path.join(eosroot, path))


def _getDefinedColumnNames(rdf) -> set[str]:
    if "DistRDF" in rdf.__module__:
        ret: set[str] = set()
        node = rdf
        while node is not None:
            if node.operation is not None and (node.operation.name.startswith("Define") or node.operation.name == "Alias"):
                ret.add(node.operation.args[0])
            node = node.parent
        return ret
    else:
        return set(map(str, rdf.GetDefinedColumnNames()))


def selectColumns(rdf, columnSel : Collection[str], columnVeto : Collection[str]) -> Any:
    import ROOT  # type: ignore
    import re
    cols = list(map(str, rdf.GetColumnNames()))
    newcols = _getDefinedColumnNames(rdf)
    oldcols = list(set(cols).difference(newcols))
    sel = set(cols) if columnSel == [] else set()  # type: set[str]
    for pat in columnSel:
        if pat == "#new":
            sel.update(newcols)
        elif pat == "#old":
            sel.update(oldcols)
        else:
            pat = re.compile(pat + "$")
            for c in cols:
                if re.match(pat, c):
                    sel.add(c)
    for pat in columnVeto:
        if pat == "#new":
            sel.difference_update(newcols)
        elif pat == "#old":
            sel.difference_update(oldcols)
        else:
            pat = re.compile(pat + "$")
            for c in cols:
                if re.match(pat, c):
                    sel.discard(c)
    ret = ROOT.std.vector(ROOT.std.string)()
    ret.reserve(len(sel))
    for c in cols:
        if c in sel:
            ret.push_back(c)
    return ret


class NormUncertainty(object):
    def __init__(self, name : str, value : "Union[float, tuple[float, float]]", eras=None):
        self.name = name
        self.value = value
        if isinstance(value, float):
            self.kappaUp = value
            self.kappaDown = 1. / value
        elif isinstance(value, tuple) and len(value) == 2 and isinstance(value[0], float):
            self.kappaDown = value[0]
            self.kappaUp = value[1]
        else:
            raise RuntimeError("Unsupported value %r (type %s) for norm uncertainty %s" % (value, type(value), name))
        self.eras = eras

    @staticmethod
    def parse(optionValue : Union[None,
                                  float,
                                  tuple[float, float],
                                  dict[str, Union[float, tuple[float, float]]],
                                  list["NormUncertainty"]],
              defaultName : str) -> "list[NormUncertainty]":
        if optionValue is None:
            return []
        elif isinstance(optionValue, float) or (isinstance(optionValue, tuple) and isinstance(optionValue[0], float)):
            return [NormUncertainty(defaultName, optionValue)]
        elif isinstance(optionValue, list):
            assert all(isinstance(o, NormUncertainty) for o in optionValue)
            return optionValue[:]
        else:
            assert isinstance(optionValue, dict)
            return [NormUncertainty(k, v) for (k, v) in optionValue.items()]


class FilteringList(list):
    def __init__(self, *args : Any, **kwargs):
        super().__init__(*args, **kwargs)

    def byNames(self, *args : str, match="glob") -> "FilteringList":
        ret = FilteringList()
        if match == "glob":
            for item in self:
                if any(fnmatch.fnmatch(item.name, a) for a in args):
                    ret.append(item)
        elif match == "re":
            for item in self:
                if any(re.match(a + "$", item.name) for a in args):
                    ret.append(item)
        elif match == "exact":
            for item in self:
                if item.name in args:
                    ret.append(item)
        else:
            raise RuntimeError(f"Unsupported match {match}, only 'exact', 're', and 'glob' are supported")
        return ret

    def byName(self, arg : str) -> Any:
        matchingitems = [i for i in self if i.name == arg]
        if len(matchingitems) == 1:
            raise RuntimeError(f"Error, looking for name {arg} found {len(matchingitems)} matches: " + ", ".join([m.name for m in matchingitems]))
        return matchingitems[0]

    def by(self, **kwargs : Any) -> "FilteringList":
        ret = FilteringList()
        for item in self:
            if all((getattr(item, p[0]) == p[1]) for p in kwargs.items()):
                ret.append(item)
        return ret

    def __iadd__(self, other) -> "FilteringList":
        return super().__iadd__(other)

    def __add__(self, other) -> "FilteringList":
        ret = FilteringList(self)
        ret += other
        return ret


def processorFromCommandLineArgs(parser=None):
    import argparse
    import ROOT  # type: ignore
    from CMGRDF.cache import SimpleCache
    from CMGRDF.processor import Processor
    parser = parser if parser is not None else argparse.ArgumentParser()
    parser.add_argument("--mode", help="how to run", default="local", choices=("local", "dask"))
    parser.add_argument("--dask", help="shortcut for --mode dask", dest="mode", action="store_const", const="dask")
    parser.add_argument("-u", "--with-systematics", "--syst", help="enable systematics by default", dest="withSystematics", action="store_const", const=True, default=None)
    parser.add_argument("--stat", "--without-systematics,", help="disable systematics by default", dest="withSystematics", action="store_const", const=False, default=None)
    parser.add_argument("-f", "--flush-cache", dest="flushCache", help="flush the cache at the start of the job. Use it once to flush just the plot cache, twice (-ff) to fush also the sums cache", action='count', default=0)
    parser.add_argument("-n", "--nocache", help="skip cache", action="store_true")
    parser.add_argument("-c", "--cluster", help="cluster url / connection (needed if dask is specified)")
    parser.add_argument("-j", "--njobs", type=int, help="number of threads or processes")
    parser.add_argument("-v", "--verbose", action='count', default=0)
    parser.add_argument("-b", "--batch", help="batch mode (don't show progress bars)", default=False, action="store_true")
    args = parser.parse_args()
    executor : Optional[tuple[str, Any]] = None
    if args.mode == "local":
        if args.njobs:
            ROOT.EnableImplicitMT(args.njobs if args.njobs > 0 else 0)
    elif args.mode == "dask":
        from CMGRDF.data import Source
        Source.useDefinePerSample = False
        from dask.distributed import Client
        if args.cluster:
            client = Client(args.cluster)
        else:
            print(f"Spawning local cluster with {args.njobs if args.njobs else 'default number'} nodes")
            from dask.distributed import LocalCluster
            cluster = LocalCluster(n_workers=args.njobs, threads_per_worker=1, processes=True)
            client = Client(cluster)
        faulthandler = "import faulthandler\nfaulthandler.enable()"
        client.run(exec, faulthandler)
        client.run_on_scheduler(exec, faulthandler)
        if args.cluster and args.njobs:
            client.run(exec, f"import  ROOT\nROOT.EnableImplicitMT({args.njobs})")
        executor = (args.mode, client)
    cache = None if args.nocache else SimpleCache(flush=args.flushCache)
    maker = Processor(cache=cache, executor=executor, withUncertainties=args.withSystematics)
    maker.commandlineArgs = args  # type: ignore # in case they're used downstream
    if args.verbose:
        level = [ROOT.Experimental.ELogLevel.kInfo, ROOT.Experimental.ELogLevel.kDebug, ROOT.Experimental.ELogLevel.kDebug + 20][min(args.verbose, 2)]
        maker._rdfVerbosity = ROOT.Experimental.RLogScopedVerbosity(ROOT.Detail.RDF.RDFLogChannel(), level)  # type: ignore
    if args.batch:
        from CMGRDF.data import ProgressBar
        ProgressBar.Disable()
    return maker
