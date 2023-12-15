from typing import Any, Mapping, Union
from CMGRDF.data import DataSample, MCSample, Source
from CMGRDF.skimFilters import JsonFilter
from CMGRDF.modifiers import Prepend
from CMGRDF.utils import recursiveHash
import json
import os
import subprocess


class DASEngine(object):
    """Main class responsible for executing and interpreting a DAS query"""

    def __init__(self, lfn2pfn="root://eoscms.cern.ch//eos/cms{lfn}", redirector="root://xrootd-cms.infn.it/{lfn}", cacheDir=".dascache", dasgoclient="/cvmfs/cms.cern.ch/common/dasgoclient"):
        self.dasgoclient = dasgoclient
        self._lfn2pfn = lfn2pfn
        self._redirector = redirector
        self._cacheDir = cacheDir

    def query(self, dataset : str, checkEOS=True):
        fname = dataset.strip("/").replace("/", ".") + ".json"
        data = None
        if os.path.exists(self._cacheDir + "/" + fname):
            try:
                data = json.load(open(self._cacheDir + "/" + fname))
            except BaseException:
                pass
        if not data:
            ret = subprocess.run([self.dasgoclient, "-json", "-query", f"file dataset={dataset}"], stdout=subprocess.PIPE)
            data = json.loads(ret.stdout)
            if checkEOS and os.path.isdir("/eos/cms"):
                for row in data:
                    row['file'][0]['remote'] = not os.path.exists("/eos/cms" + row['file'][0]['name'])
            if self._cacheDir:
                if not os.path.isdir(self._cacheDir):
                    os.makedirs(self._cacheDir)
                json.dump(data, open(self._cacheDir + "/" + fname, "w"))
        return data

    def listLfns(self, query):
        return list(sorted(row['file'][0]['name'] for row in query))

    def listPfns(self, query):
        pfns = []
        for row in query:
            lfn = row['file'][0]['name']
            pfn = self._lfn2pfn.format(lfn=lfn)
            if ('remote' in row['file'][0]) and row['file'][0]['remote']:
                pfn = self._redirector.format(lfn=lfn)
            pfns.append(pfn)
        return pfns

    def fileIDsForHash(self, query):
        return list(sorted((row['file'][0]['name'], row['file'][0]['creation_date'], row['file'][0]['check_sum']) for row in query))

    def numEvents(self, query):
        return sum(row['file'][0]['nevents'] for row in query)

    def totSize(self, query):
        return sum(row['file'][0]['size'] for row in query)


class DASSource(Source):
    def __init__(self, name : str, dataset : str, era=None, engine : DASEngine = DASEngine(), maxFiles=None):
        Source.__init__(self, name, dataset, era=era)
        self.dataset = dataset
        self._engine = engine
        dasData = engine.query(dataset)
        if maxFiles:
            dasData = dasData[:maxFiles]
        self._initData(dasData)

    def _initData(self, data):
        self._dasData = data
        self.lfns = self._engine.listLfns(data)
        self.pfns = self._engine.listPfns(data)
        self.files = list(self.pfns)  # make a copy
        self.events = self._engine.numEvents(data)
        self.size = self._engine.totSize(data)
        self._bigHash = recursiveHash((self.name, self.era, self.dataset, self._engine.fileIDsForHash(data)))
        self._bigHashNoFriends = self._bigHash

    def __str__(self):
        return "Source(%s%s, %s, %d files[%s%s], %d events, id %s)" % (
            self.name, (", era %s" % self.era) if self.era else "",
            self.dataset,
            len(self.lfns), self.lfns[0], ", ..." if len(self.lfns) > 1 else "",
            self.events,
            self.bigHash()
        )

    def cropFiles(self, maxFiles):
        if len(self._dasData) > maxFiles:
            ## pick the files with the larger number of events
            self._dasData.sort(key=lambda r : -r['file'][0]['nevents'])
            self._initData(self._dasData[:maxFiles])

    def cropEvents(self, maxEvents):
        if self.events > maxEvents:
            self._dasData.sort(key=lambda r : -r['file'][0]['nevents'])
            newData = []
            tot = 0
            for row in self._dasData:
                newData.append(row)
                tot += row['file'][0]['nevents']
                if tot > maxEvents:
                    break
            self._initData(newData)


class _DASMixin:
    @staticmethod
    def _makeSource(name, dataset, kwargs, engine : DASEngine = DASEngine(), maxFiles=None):
        if "eras" in kwargs:
            assert ("era" not in kwargs)
            if len(kwargs['eras']) == 1 and isinstance(dataset, str):
                dataset = {kwargs['eras'][0]: dataset}
            return dict((e, DASSource(name + "_" + e, d, era=e, engine=engine, maxFiles=maxFiles)) for (e, d) in dataset.items())
        elif "era" in kwargs:
            era = kwargs["era"]
            del kwargs["era"]
            kwargs["eras"] = [era]
            return {era: DASSource(name, dataset, era=era, engine=engine, maxFiles=maxFiles)}
        else:
            return DASSource(name, dataset, engine=engine, maxFiles=maxFiles)

    def totEvents(self, era=None):
        if (era is None) and self.eras:
            return sum(self.totEvents(e) for e in self.eras)
        src = self._source if era is None else self._sources[era]
        return src.events

    def cropFiles(self, maxFiles):
        if self.eras:
            for e, s in self._sources.items():
                s.cropFiles(maxFiles)
        else:
            self._source.cropFiles(maxFiles)


class DASMCSample(MCSample, _DASMixin):
    def __init__(self, name : str, dataset, engine : DASEngine = DASEngine(), maxFiles=None, **kwargs):
        src = _DASMixin._makeSource(name, dataset, kwargs, engine=engine, maxFiles=maxFiles)
        super().__init__(name, src, **kwargs)

    def equivLumi(self, era=None):
        if (era is None) and self.eras:
            return sum(self.equivLumi(e) for e in self.eras)
        src = self._source if era is None else self._sources[era]
        return src.events / (self.xsec * 1000)

    def cropToLumi(self, lumi : Union[float, Mapping[Any, float]], scale=1.0):
        if self.eras:
            if isinstance(lumi, float):
                for (e, s) in self._sources.items():
                    s.cropEvents(lumi * self.xsec * 1000 * scale)
            else:
                for (e, l) in lumi.items():
                    if e in self.eras:
                        self._sources[e].cropEvents(l * self.xsec * 1000 * scale)
        else:
            self._source.cropEvents(lumi * self.xsec * 1000 * scale)


class DASDataSample(DataSample, _DASMixin):
    def __init__(self, name : str, dataset, engine : DASEngine = DASEngine(), maxFiles=None, json=None, **kwargs):
        src = _DASMixin._makeSource(name, dataset, kwargs, engine=engine, maxFiles=maxFiles)
        super().__init__(name, src, **kwargs)
        if json:
            self._hooks.insert(0, Prepend(JsonFilter(json)))


if __name__ == "__main__":
    engine = DASEngine()
    data = engine.query("/Zto2Q-4Jets_HT-400to600_TuneCP5_13p6TeV_madgraphMLM-pythia8/Run3Summer22EENanoAODv11-126X_mcRun3_2022_realistic_postEE_v1-v1/NANOAODSIM")
    src = DASSource("Zqq_HT400", "/Zto2Q-4Jets_HT-400to600_TuneCP5_13p6TeV_madgraphMLM-pythia8/Run3Summer22EENanoAODv11-126X_mcRun3_2022_realistic_postEE_v1-v1/NANOAODSIM", era="2022EE")
    print(str(src))
