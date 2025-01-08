#pyright: reportUninitializedInstanceVariable=false
import contextlib
from typing import Any, Optional, Union
from CMGRDF.data import DataSample, MCSample, Source
from CMGRDF.skimFilters import JsonFilter
from CMGRDF.modifiers import Prepend
from CMGRDF.utils import recursiveHash
import json
import os
import subprocess


class DASEngine:
    """Main class responsible for executing and interpreting a DAS query"""

    def __init__(self,
                 lfn2pfn : str = "root://eoscms.cern.ch//eos/cms{lfn}",
                 redirector : str = "root://xrootd-cms.infn.it/{lfn}",
                 cacheDir : str = ".dascache",
                 dasgoclient : str = "/cvmfs/cms.cern.ch/common/dasgoclient"):
        self.dasgoclient = dasgoclient
        self._lfn2pfn = lfn2pfn
        self._redirector = redirector
        self._cacheDir = cacheDir

    def query(self, dataset : str, checkEOS=True) -> Any:
        fname = dataset.strip("/").replace("/", ".") + ".json"
        data = None
        if os.path.exists(self._cacheDir + "/" + fname):
            with contextlib.suppress(BaseException):  # if the cache is not readable or corrupted we just ignore it
                data = json.load(open(self._cacheDir + "/" + fname))
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

    def listLfns(self, query) -> list[Any]:
        return list(sorted(row['file'][0]['name'] for row in query))

    def listPfns(self, query) -> list[Any]:
        pfns = []
        for row in query:
            lfn = row['file'][0]['name']
            pfn = self._lfn2pfn.format(lfn=lfn)
            if ('remote' in row['file'][0]) and row['file'][0]['remote']:
                pfn = self._redirector.format(lfn=lfn)
            pfns.append(pfn)
        return pfns

    def fileIDsForHash(self, query) -> list[tuple[str, Any, Any]]:
        return list(sorted((row['file'][0]['name'], row['file'][0]['creation_date'], row['file'][0]['check_sum']) for row in query))

    def numEvents(self, query) -> int:
        return sum(row['file'][0]['nevents'] for row in query)

    def totSize(self, query) -> int:
        return sum(row['file'][0]['size'] for row in query)


class DASSource(Source):
    def __init__(self,
                 name : str,
                 dataset : str,
                 era : Optional[str] = None,
                 engine : Optional[DASEngine] = None,
                 maxFiles : Optional[int] = None):
        Source.__init__(self, name, dataset, era=era)
        self.dataset = dataset
        self._engine = engine if engine else DASEngine()
        dasData = self._engine.query(dataset)
        if maxFiles:
            dasData = dasData[:maxFiles]
        self._initData(dasData)

    def _initData(self, data) -> None:
        self._dasData = data
        self.lfns = self._engine.listLfns(data)
        self.pfns = self._engine.listPfns(data)
        self.files = list(self.pfns)  # make a copy
        self.events = self._engine.numEvents(data)
        self.size = self._engine.totSize(data)
        self._bigHash = recursiveHash((self.name, self.era, self.dataset, self._engine.fileIDsForHash(data)))
        self._bigHashNoFriends = self._bigHash

    def __str__(self) -> str:
        return "Source(%s%s, %s, %d files[%s%s], %d events, id %s)" % (
            self.name, (", era %s" % self.era) if self.era else "",
            self.dataset,
            len(self.lfns), self.lfns[0], ", ..." if len(self.lfns) > 1 else "",
            self.events,
            self.bigHash()
        )

    def cropFiles(self, maxFiles : int) -> None:
        if len(self._dasData) > maxFiles:
            ## pick the files with the larger number of events
            self._dasData.sort(key=lambda r : -r['file'][0]['nevents'])
            self._initData(self._dasData[:maxFiles])

    def cropEvents(self, maxEvents : float) -> None:
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
    def _makeSource(name : str,
                    dataset : Union[str, dict[str, str]],
                    era : Optional[str] = None,
                    eras : Optional[list[str]] = None,
                    engine : Optional[DASEngine] = None,
                    maxFiles : Optional[int] = None) -> Union[dict[str, DASSource], DASSource]:
        if eras is not None:
            assert era is None
            if len(eras) == 1 and isinstance(dataset, str):
                dataset = {eras[0]: dataset}
            assert isinstance(dataset, dict)
            return dict((e, DASSource(name + "_" + e, d, era=e, engine=engine, maxFiles=maxFiles)) for (e, d) in dataset.items())
        elif era is not None:
            assert isinstance(dataset, str)
            return {era: DASSource(name, dataset, era=era, engine=engine, maxFiles=maxFiles)}
        else:
            assert isinstance(dataset, str)
            return DASSource(name, dataset, engine=engine, maxFiles=maxFiles)

    def totEvents(self, era=None) -> int:
        if (era is None) and getattr(self, 'eras', None):
            return sum(self.totEvents(e) for e in self.eras)  # type: ignore
        src = self._source if era is None else self._sources[era]  # type: ignore
        return src.events

    def cropFiles(self, maxFiles : int) -> None:
        if self.eras:  # type: ignore
            for e, s in self._sources.items():  # type: ignore
                s.cropFiles(maxFiles)
        else:
            self._source.cropFiles(maxFiles)  # type: ignore


class DASMCSample(MCSample, _DASMixin):
    def __init__(self,
                 name : str,
                 dataset : Union[str, dict[str, str]],
                 era : Optional[str] = None,
                 eras : Optional[list[str]] = None,
                 engine : Optional[DASEngine] = None,
                 xsec : float = 1.0,
                 maxFiles=None,
                 **kwargs):
        src = _DASMixin._makeSource(name, dataset, era=era, eras=eras, engine=engine, maxFiles=maxFiles)
        super().__init__(name, src, xsec=xsec, **kwargs)

    def equivLumi(self, era : Optional[str] = None) -> float:
        if (era is None) and self.eras:
            return sum(self.equivLumi(e) for e in self.eras)
        src = self._source if era is None else self._sources[era]
        assert isinstance(self.xsec, float)
        assert isinstance(src, DASSource)
        return src.events / (self.xsec * 1000)

    def cropToLumi(self, lumi : Union[float, dict[str, float]], scale : float = 1.0) -> None:
        assert isinstance(self.xsec, float)
        if self.eras:
            if isinstance(lumi, float):
                for (e, s) in self._sources.items():
                    assert isinstance(s, DASSource)
                    s.cropEvents(lumi * self.xsec * 1000 * scale)
            else:
                assert isinstance(lumi, dict)
                for (e, l) in lumi.items():
                    if e in self.eras:
                        src = self._sources[e]
                        assert isinstance(src, DASSource)
                        src.cropEvents(l * self.xsec * 1000 * scale)
        else:
            assert isinstance(lumi, float)
            assert isinstance(self._source, DASSource)
            self._source.cropEvents(lumi * self.xsec * 1000 * scale)


class DASDataSample(DataSample, _DASMixin):
    def __init__(self,
                 name : str,
                 dataset : Union[str, dict[str, str]],
                 era : Optional[str] = None,
                 eras : Optional[list[str]] = None,
                 engine : Optional[DASEngine] = None,
                 maxFiles : Optional[int] = None,
                 json : Optional[str] = None,
                 **kwargs):
        src = _DASMixin._makeSource(name, dataset, era=era, eras=eras, engine=engine, maxFiles=maxFiles)
        super().__init__(name, src, **kwargs)
        if json:
            self._hooks.insert(0, Prepend(JsonFilter(json)))


if __name__ == "__main__":
    engine = DASEngine()
    data = engine.query("/Zto2Q-4Jets_HT-400to600_TuneCP5_13p6TeV_madgraphMLM-pythia8/Run3Summer22EENanoAODv11-126X_mcRun3_2022_realistic_postEE_v1-v1/NANOAODSIM")
    src = DASSource("Zqq_HT400", "/Zto2Q-4Jets_HT-400to600_TuneCP5_13p6TeV_madgraphMLM-pythia8/Run3Summer22EENanoAODv11-126X_mcRun3_2022_realistic_postEE_v1-v1/NANOAODSIM", era="2022EE")
    print(str(src))
