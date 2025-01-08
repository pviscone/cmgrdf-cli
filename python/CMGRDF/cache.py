import contextlib
import os
import time
import json
import pickle
import sys
import shutil
from typing import Any, Union
import ROOT  # type: ignore

from CMGRDF.data import Source


class SumCache:
    def __init__(self, jsonFileName : str):
        self._fileName = jsonFileName
        self._cache = self._maybeRead()

    def has(self, source : Source, genSumName : str) -> bool:
        return source.idForSumCache(genSumName) in self._cache

    def get(self, source : Source, genSumName : str) -> Union[float, int]:
        return self._cache[source.idForSumCache(genSumName)][0]

    def write(self, source : Source, genSumName : str, wsum : Union[float, int]) -> None:
        self._cache[source.idForSumCache(genSumName)] = (wsum, time.time())

    def commitToDisk(self) -> None:
        if not os.path.isdir(os.path.dirname(self._fileName)):
            os.makedirs(os.path.dirname(self._fileName))
        existing = self._maybeRead()
        for k, v in existing.items():
            if (k not in self._cache) or (v[1] > self._cache[k][1]):
                self._cache[k] = v
        #print("Writing to %r: %s" % (self._fileName, self._cache))
        json.dump(self._cache, open(self._fileName, 'w'))

    def flush(self) -> None:
        self._cache.clear()

    def _maybeRead(self) -> dict[str, tuple[Union[float, int], float]]:
        if os.path.isfile(self._fileName):
            with contextlib.suppress(BaseException):
                return json.load(open(self._fileName))
        return dict()


class CacheLayer:
    def __init__(self, root, ttl=None, touch=True, verbose=False) -> None:
        self._root = root
        self._ttl = ttl
        self._now = time.time()
        self._touch = touch
        self._verbose = verbose

    def _upToDate(self, fullpath : str) -> bool:
        if self._ttl:
            return os.path.getmtime(fullpath) > self._now - self._ttl
        return True

    def has(self, path : str) -> bool:
        fullpath = os.path.join(self._root, path)
        return os.path.isfile(fullpath) and self._upToDate(fullpath)

    def get(self, path : str) -> Any:
        fullpath = os.path.join(self._root, path)
        if self._touch:
            os.system("touch " + fullpath)
        ret = pickle.load(open(fullpath, 'rb'))
        if self._verbose:
            print("retrieving %s from cache file %s" % (path, fullpath))
        return ret

    def getRDF(self, path : str, treeName="Events"):
        fullpath = os.path.join(self._root, path)
        if self._touch:
            os.system("touch " + fullpath)
        ret = ROOT.RDataFrame(treeName, fullpath)
        if self._verbose:
            print("retrieving %s from cache file %s" % (path, fullpath))
        return ret

    def write(self, path : str, obj : Any) -> None:
        fullpath = os.path.join(self._root, path)
        pathdir = os.path.dirname(fullpath)
        if not os.path.isdir(pathdir):
            os.makedirs(pathdir)
        pickle.dump(obj, open(fullpath, 'wb'))

    def flush(self) -> None:
        if os.path.isdir(self._root):
            for f in os.listdir(self._root):
                shutil.rmtree(os.path.join(self._root, f))


class SimpleCache:
    def __init__(self,
                 root : str = "__auto__",
                 cacheSums : bool = True,
                 cachePlots : bool = True,
                 cacheDatasets : bool = False,
                 flush : Union[int, bool] = False,
                 **kwargs: Any):
        if root == "__auto__":
            root = sys.argv[0].rsplit(".py", 1)[0] + "_cache.dir"
        print("Using cache dir %s%s" % (root, ", and flushing it" if flush else ""))
        self._sums = SumCache(os.path.join(root, "sums.json")) if cacheSums else None
        self._data = CacheLayer(os.path.join(root, "data"), **kwargs) if cacheDatasets else None
        self._plots = CacheLayer(os.path.join(root, "plots"), **kwargs) if cachePlots else None
        if flush:
            if not isinstance(flush, bool):
                self.flush(alsoSums=(flush > 1))
            else:
                self.flush()

    def hasSum(self, source : Source, genSumName : str) -> bool:
        return self._sums.has(source, genSumName) if self._sums else False

    def getSum(self, source : Source, genSumName : str) -> Union[float, int]:
        assert self._sums
        return self._sums.get(source, genSumName)

    def writeSum(self, source : Source, genSumName : str, wsum : Union[float, int]) -> None:
        if self._sums:
            self._sums.write(source, genSumName, wsum)

    def hasPlot(self, k3 : tuple[str, str, str]) -> bool:
        """Check with key beign a tuple(sourceid, flowid, targetid)"""
        key = os.path.join(*k3)
        return self._plots.has(key) if self._plots else False

    def getPlot(self, k3 : tuple[str, str, str]) -> Any:
        """Check with key beign a tuple(sourceid, flowid, targetid), return (plot, variations map)"""
        key = os.path.join(*k3)
        assert (self._plots is not None)
        return self._plots.get(key)

    def writePlot(self, k3 : tuple[str, str, str], plot, plotvars) -> None:
        key = os.path.join(*k3)
        assert (self._plots is not None)
        self._plots.write(key, (plot, plotvars))

    def flush(self, alsoSums=True) -> None:
        if alsoSums and self._sums is not None:
            self._sums.flush()
        for c in (self._data, self._plots):
            if c is not None:
                c.flush()

    def commitSums(self) -> None:
        if self._sums:
            self._sums.commitToDisk()
