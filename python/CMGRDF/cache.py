import os
import time
import json
import pickle
import sys
import ROOT

from CMGRDF.data import Source


class SumCache(object):
    def __init__(self, jsonFileName):
        self._fileName = jsonFileName
        self._cache = self._maybeRead()

    def has(self, source : Source):
        return source.longId() in self._cache

    def get(self, source : Source):
        return self._cache[source.longId()][0]

    def write(self, source : Source, sum : float):
        self._cache[source.longId()] = (sum, time.time())

    def commitToDisk(self):
        if not os.path.isdir(os.path.dirname(self._fileName)):
            os.makedirs(os.path.dirname(self._fileName))
        existing = self._maybeRead()
        for k, v in existing.items():
            if (k not in self._cache) or (v[1] > self._cache[k][1]):
                self._cache[k] = v
        #print("Writing to %r: %s" % (self._fileName, self._cache))
        json.dump(self._cache, open(self._fileName, 'w'))

    def _maybeRead(self):
        if os.path.isfile(self._fileName):
            try:
                return json.load(open(self._fileName))
            except BaseException:
                pass
        return dict()


class CacheLayer(object):
    def __init__(self, root, ttl=None, touch=True, verbose=False):
        self._root = root
        self._ttl = ttl
        self._now = time.time()
        self._touch = touch
        self._verbose = verbose

    def _upToDate(self, fullpath):
        if self._ttl:
            return os.path.getmtime(fullpath) > self._now - self._ttl
        return True

    def has(self, path):
        fullpath = os.path.join(self._root, path)
        return os.path.isfile(fullpath) and self._upToDate(fullpath)

    def get(self, path):
        fullpath = os.path.join(self._root, path)
        if self._touch:
            os.system("touch " + fullpath)
        ret = pickle.load(open(fullpath, 'rb'))
        if self._verbose:
            print("retrieving %s from cache file %s" % (path, fullpath))
        return ret

    def getRDF(self, path, treeName="Events"):
        fullpath = os.path.join(self._root, path)
        if self._touch:
            os.system("touch " + fullpath)
        ret = ROOT.RDataFrame(treeName, fullpath)
        if self._verbose:
            print("retrieving %s from cache file %s" % (path, fullpath))
        return ret

    def write(self, path, obj):
        fullpath = os.path.join(self._root, path)
        dir = os.path.dirname(fullpath)
        if not os.path.isdir(dir):
            os.makedirs(dir)
        pickle.dump(obj, open(fullpath, 'wb'))


class SimpleCache(object):
    def __init__(self, root="__auto__", cacheSums=True, cachePlots=True, cacheDatasets=False, **kwargs):
        if root == "__auto__":
            root = sys.argv[0].rsplit(".py", 1)[0] + "_cache.dir"
            print("Using cache dir %s" % root)
        self._sums = SumCache(os.path.join(root, "sums.json")) if cacheSums else None
        self._data = CacheLayer(os.path.join(root, "data"), **kwargs) if cacheDatasets else None
        self._plots = CacheLayer(os.path.join(root, "plots"), **kwargs) if cachePlots else None

    def hasSum(self, source : Source):
        return self._sums.has(source) if self._sums else False

    def getSum(self, source : Source):
        assert self._sums
        return self._sums.get(source)

    def writeSum(self, source : Source, sum : float):
        if self._sums:
            self._sums.write(source, sum)

    def hasPlot(self, k3):
        """Check with key beign a tuple(sourceid, flowid, targetid)"""
        key = os.path.join(*k3)
        return self._plots.has(key) if self._plots else False

    def getPlot(self, k3):
        """Check with key beign a tuple(sourceid, flowid, targetid), return (plot, variations map)"""
        key = os.path.join(*k3)
        return self._plots.get(key)

    def writePlot(self, k3, plot, vars):
        key = os.path.join(*k3)
        self._plots.write(key, (plot, vars))

    def commitSums(self):
        if self._sums:
            self._sums.commitToDisk()
