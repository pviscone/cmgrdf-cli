# pyright: reportImportCycles=false
import copy
from typing import Any, Literal, Optional, TypeVar, Union, TYPE_CHECKING, overload
from collections.abc import Iterable, Mapping, Sequence
import ROOT  # type: ignore
import os
import os.path
import glob
import XRootD.client.glob_funcs as xrdglob
from CMGRDF.utils import recursiveHash, safeName, NormUncertainty, eosToUrl
if TYPE_CHECKING:
    from CMGRDF.flow import Hook

ROOT.gInterpreter.ProcessLine('#include <progressBarManager.h>')
ProgressBar = ROOT.ProgressBarManager()


class Source:
    """Base class that wraps a list of files from which an RDF can be created"""

    useDefinePerSample = True

    def __init__(self,
                 name : str,
                 files : Union[str, list[str]],
                 era : Optional[str] = None,
                 friends : Optional[Sequence[Union[str, tuple[str, str]]]] = None):
        if isinstance(files, str):
            if files.startswith("root://"):
                files = xrdglob.glob(files) if '*' in files else [files]
            else:
                files = glob.glob(files) if '*' in files else [files]
        else:
            assert (len(files) >= 1)
            assert (not any(("*" in f) for f in files))
        self.name = name if name else Source._autoName(files)
        self.files = files
        self.era = era
        self.friends = friends
        self._bigHash = None
        self._bigHashNoFriendsNoMeta = None
        self._filesForHash = None
        self._friendsForHash = None
        self._metas = []

    def _getEntriesFromSample(self, rsample : Any, cache : Any = None) -> int:
        if cache and cache.hasSum(self, "_N_EVENTS_"):
            return cache.getSum(self, "_N_EVENTS_")
        nevents = 0
        for fil, tree in zip(rsample.GetFileNameGlobs(), rsample.GetTreeNames()):
            tf = ROOT.TFile.Open(str(fil))
            nevents += tf.Get(str(tree)).GetEntries()
            tf.Close()
        if cache:
            cache.writeSum(self, "_N_EVENTS_", nevents)
        return nevents

    def _createRSample(self, treeName : str = "Events") -> Any:
        metaInfo = ROOT.RDF.Experimental.RMetaData()
        for meta in self._metas:
            metaInfo.Add(meta[0], meta[1])
        files = self.files
        if len(files) == 1 and os.path.isdir(files[0]):
            if treeName == "Events":
                raise RuntimeError("Cannot support friend trees when provinding a directory as input")
            files = list(glob.glob(files[0] + '/*.root'))
        files = [eosToUrl(f) for f in files]
        return ROOT.RDF.Experimental.RSample(self.name, treeName, files, metaInfo)

    def _addGlobalFriends(self, spec : Any) -> None:
        if self.friends is not None:
            for f in self.friends:
                if isinstance(f, tuple):
                    spec.WithGlobalFriends(f[0], f[1])
                elif isinstance(f, str):
                    spec.WithGlobalFriends("Friends", f)
                else:
                    raise RuntimeError("Unsupported friend %r for %s" % (f, self))

    @staticmethod
    def _addDefinesFromMetas(rdf : Any, metas : list[tuple[str, Union[str, int, float]]]) -> Any:
        for meta in metas:
            src = rdf
            if isinstance(meta[1], str):
                rdf = rdf.Define(meta[0], meta[1])
            else:
                rdf = rdf.DefinePerSample(meta[0], f'rdfsampleinfo_.GetD("{meta[0]}")')  # could implement other types
            rdf._from = src
        return rdf

    def createRDF(self, treeName : str = "Events", distributed : bool = False, cache : Any = None, **kwargs : Any) -> Any:
        """
        Create a ROOT RDataFrame or a custom DataFrame from a given tree name.

        Args:
            treeName (str): The name of the tree to create the DataFrame from. Defaults to "Events".
            distributed (bool): True for distributed execution.
            cache (Any): Optional cache to use for retrieving entries.
            **kwargs (Any): Additional keyword arguments to pass to the DataFrameClass.

        Returns:
            Any: The created DataFrame.

        Notes:
            - If `treeName` is "Events", global friends are added to the dataset specification.
            - If distributed is true and "npartitions" is not in kwargs, the number of partitions is calculated based on the number of events.
            - If distributed is true and  and `Source.useDefinePerSample` is True, it is set to False with a warning message.
            - If `Source.useDefinePerSample` is True, defines from metas are added to the DataFrame.
        """
        sample = self._createRSample(treeName)
        spec = ROOT.RDF.Experimental.RDatasetSpec()
        spec.AddSample(sample)
        if treeName == "Events":
            self._addGlobalFriends(spec)
        if distributed and ("npartitions" not in kwargs):
            kwargs = dict(**kwargs)
            nevents = self._getEntriesFromSample(sample, cache=cache)
            kwargs['npartitions'] = min(max(2, int((nevents / 1e4)**0.5)), 16)
            print(f"Will use {kwargs['npartitions']} partitions for {self.name}, era {self.era}, events {nevents}")
        ret = ROOT.RDataFrame(spec, **kwargs)
        if not (distributed) and ProgressBar.Enabled():
            nevents = self._getEntriesFromSample(sample, cache=cache)
            ProgressBar.AddDataFrame(ret, nevents)
        if distributed and Source.useDefinePerSample:
            print("Will not use DefinePerSample to handle xsec and gen weights as it's not yet supported in DistRDF")
            Source.useDefinePerSample = False
        if Source.useDefinePerSample:
            ret = Source._addDefinesFromMetas(ret, self._metas)
        return ret

    def __eq__(self, o : Any) -> bool:
        if o.__class__ == Source:
            return o.name == self.name and o.files == self.files and o.era == self.era and o.friends == self.friends and self._metas == o._metas
        else:
            return id(self) == id(o)

    def addMeta(self, field : str, value : Union[str, int, float]) -> None:
        for mykey, myval in self._metas:
            if mykey == field:
                if myval != value:
                    raise RuntimeError(f"Error, changing meta {field} from {myval!r} to {value!r} on source {self}")
                return  # already there, don't re-add and don't invalidate hash
        self._metas.append((field, value))
        # invalidate hash
        self._bigHash = None

    def hasMeta(self, key : str) -> bool:
        """
        Check if a metadata key exists.

        Args:
            key (str): The metadata key to check.

        Returns:
            bool: True if the key exists in the metadata, False otherwise.
        """
        return any(m[0] == key for m in self._metas)

    def hasCompatibleMeta(self, otherSource : "Source") -> bool:
        """
        Check if the metadata of this source is compatible with another source.

        Args:
            otherSource (Source): The other source to compare metadata with.

        Returns:
            bool: True if the metadata of both sources are compatible, False otherwise.
        """
        if len(otherSource._metas) != len(self._metas):
            return False
        for m1, m2 in zip(self._metas, otherSource._metas):
            if m1[0] != m2[0]:
                return False
            if isinstance(m1[1], str) and m1[1] != m2[1]:
                return False
        return True

    def bigHash(self, friendsAndMeta : bool = True) -> str:
        if not self._bigHash:
            self._makeBigHash()
        return self._bigHash if friendsAndMeta else self._bigHashNoFriendsNoMeta  # type: ignore

    def _makeFilesHash(self) -> None:
        if os.path.exists(self.files[0]):  # files may not exist if e.g. they're globs or root URLs
            self._filesForHash = [(f, os.path.getmtime(f)) for f in self.files]
            tsfriends = []
            if self.friends:
                for f in self.friends:
                    if isinstance(f, tuple):
                        if len(self.files) == 1:
                            tsfriends.append((f[0], f[1], os.path.getmtime(f[1])))
                        else:
                            for fi in f[1]:
                                tsfriends.append((f[0], fi, os.path.getmtime(fi)))
                    else:
                        if len(self.files) == 1:
                            tsfriends.append((f, os.path.getmtime(f)))
                        else:
                            for fi in f:
                                tsfriends.append((fi, os.path.getmtime(fi)))
            self._friendsForHash = tsfriends
        else:
            self._filesForHash = self.files[:]
            self._friendsForHash = self.friends[:] if self.friends else None

    def _makeBigHash(self) -> None:
        if not self._filesForHash:
            self._makeFilesHash()
        self._bigHash = recursiveHash(self.name, self.era, self._metas, self._filesForHash, self._friendsForHash)
        self._bigHashNoFriendsNoMeta = recursiveHash(self.name, self.era, self._filesForHash)

    def __hash__(self) -> int:
        return hash(self.bigHash())

    def longId(self) -> str:
        return "%s-%s-%s" % (safeName(self), self.era if self.era else "", self.bigHash())

    def idForSumCache(self, cacheName : str) -> str:
        return "%s-%s-%s-%s" % (safeName(self), self.era if self.era else "", self.bigHash(False), cacheName)

    def __str__(self) -> str:
        return "Source(%s%s, %d files[%s%s]%s, id %s)" % (
            self.name, (", era %s" % self.era) if self.era else "",
            len(self.files), self.files[0], ", ..." if len(self.files) > 1 else "",
            (", %d friends[%s, ...]" % (len(self.friends), self.friends[0])) if self.friends else "",
            self.bigHash()
        )

    @staticmethod
    def _autoName(files: list[str]) -> str:
        """
        Generate a name based on the provided list of file paths.

        Args:
            files (list[str]): A list of file paths.

        Returns:
            str: A generated name based on the file paths.

        Raises:
            AssertionError: If the list of files is empty.

        Notes:
            - If the list contains more than one file or the first file ends with "/*.root",
              the name will be the basename of the directory containing the first file.
            - Otherwise, the name will be the basename of the first file with "*" and ".root" removed.
        """
        assert (len(files) != 0)
        if len(files) > 1 or files[0].endswith("/*.root"):
            return os.path.basename(os.path.dirname(files[0]))
        else:
            return os.path.basename(files[0]).replace("*", "").replace(".root", "")


class MergedSource(Source):
    """Multiple sources merged into a single one, but with possibly different metadata"""

    def __init__(self, name : str, sources : Sequence[Source], era : Optional[str]):
        self.name = name
        self.sources = list(sources[:])
        self.era = era
        self._bigHash = None
        self._bigHashNoFriends = None

    def createRDF(self, treeName : str = "Events", distributed : bool = False, cache : Any = None, **kwargs : Any) -> Any:
        if distributed:
            raise RuntimeError("MergedSource only supported in plain non-distributed RDataFrame for now")
        spec = ROOT.RDF.Experimental.RDatasetSpec()
        for src in self.sources:
            sample = src._createRSample(treeName)
            spec.AddSample(sample)
        if treeName == "Events":
            for src in self.sources:
                src._addGlobalFriends(spec)
        ret = ROOT.RDataFrame(spec, **kwargs)
        if len(self.sources) > 1 and not any(self.sources[0].hasCompatibleMeta(s2) for s2 in self.sources[1:]):
            metadumps = "\n".join((s.name + ':' + ', '.join(m[0] + "=" + repr(m[1]) for m in s._metas)) for s in self.sources)
            raise RuntimeError(f"Incompatible metadata in components of merged source {self}: {metadumps}")
        ret = Source._addDefinesFromMetas(ret, self.sources[0]._metas)
        return ret

    def __eq__(self, o : object) -> bool:
        if isinstance(o, MergedSource):
            return o.name == self.name and o.sources == self.sources and o.era == self.era
        else:
            return id(self) == id(o)

    def addMeta(self, field : str, value : Union[str, int, float]) -> None:
        raise RuntimeError(f"Error: you can't add a metadata {field}, {value} to a merged source {self}")

    def __hash__(self) -> int:
        return hash(self.bigHash())

    def bigHash(self, friendsAndMeta : bool = True) -> str:
        return recursiveHash(self.name, [s.bigHash(friendsAndMeta) for s in self.sources])

    def __str__(self) -> str:
        return "MergedSource(%s%s, %d sources[%s%s], id %s)" % (
            self.name, (", era %s" % self.era) if self.era else "",
            len(self.sources), self.sources[0], ", ..." if len(self.sources) > 1 else "",
            self.bigHash()
        )


TSample = TypeVar("TSample", bound="Sample")


class Sample:
    """A set of files, possibly era-dependent, to be processed homogeneously.
       This is just a base class, users should normally use the subclasses MCSample, DataSample or DataDrivenSample

       It can have hooks that modify the processing flow, and normalization uncertainties.
    """

    #Signature for samples without eras
    @overload
    def __init__(self,
                 name : str,
                 source : Union[Source, str, list[str]],
                 eras : None = None,
                 hooks : Optional[Iterable['Hook']] = None,
                 subera : Optional[Union[str, int]] = None,
                 friends : Optional[list[str]] = None,
                 normUncertainty : Union[None,
                                         list[NormUncertainty],
                                         float,
                                         tuple[float, float],
                                         dict[str, Union[float, tuple[float, float]]]] = None,
                 suffix : str = "",
                 weight : Union[float, str] = 1,
                 **kwargs : Any):
        ...

    #Signature for samples with eras
    @overload
    def __init__(self,
                 name : str,
                 source : Union[Mapping[str, Source], str, Mapping[str, str], Mapping[str, list[str]]],
                 eras : list[str],
                 hooks : Optional[Iterable['Hook']] = None,
                 subera : Optional[Union[str, int]] = None,
                 friends : Optional[list[str]] = None,
                 normUncertainty : Union[None,
                                         list[NormUncertainty],
                                         float,
                                         tuple[float, float],
                                         dict[str, Union[float, tuple[float, float]]]] = None,
                 suffix : str = "",
                 weight : Union[float, str] = 1,
                 **kwargs : Any):
        ...

    #Implementation
    def __init__(self,
                 name : str,
                 source : Union[Source, Mapping[str, Source], str, list[str], Mapping[str, str], Mapping[str, list[str]]],
                 eras : Optional[list[str]] = None,
                 hooks : Optional[Iterable['Hook']] = None,
                 subera : Optional[Union[str, int]] = None,
                 friends : Optional[list[str]] = None,
                 normUncertainty : Union[None,
                                         list[NormUncertainty],
                                         float,
                                         tuple[float, float],
                                         dict[str, Union[float, tuple[float, float]]]] = None,
                 suffix : str = "",
                 weight : Union[float, str] = 1,
                 **kwargs : Any):
        """For samples without eras, source can be any of the following:
             - a source object
             - a string, being a file name or directory name or glob string, which may include {name} inside
             - a list of strings of filenames
           For samples with eras, source can be any of the following:
             - a string, being a file name or directory name or glob string, which may include {name} and should include {era} inside
             - a dict (era -> Source)
             - a dict (era -> string), or (era -> list[string])

           normUncertainty can be any of the following:
             - None
             - a list of NormUncertainty objects
             - a float (logNormal kappa)
             - a tuple (kappaLow, kappaHigh)
             - a dict with keys being the nuisance names, and values being kappas or kappa tuples
           suffix is a suffix to the name, that is NOT used to identify the source. This is useful (and only used there) for the creation  of snapshots
        """
        self.name = name
        self._hooks = list(hooks) if hooks else []
        self.eras = eras
        self.subera = subera
        self.suffix = suffix
        self.weight = weight

        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.eras:
            if isinstance(source, str):
                friendFiles = dict((era, [f.format(name=name, era=era) for f in friends] if friends else None) for era in self.eras)
                self._sources = dict((era, Source('', source.format(name=name, era=era), era=era, friends=friendFiles[era])) for era in self.eras)
            else:
                assert isinstance(source, dict)
                friendFiles = dict((era, [f.format(name=name, era=era) for f in friends] if friends else None) for era in self.eras)
                firstsource = source[self.eras[0]]
                if isinstance(firstsource, str):
                    assert all(isinstance(source[era], str) for era in self.eras)
                    self._sources = dict((era, Source('', source[era].format(name=name, era=era), era=era, friends=friendFiles[era])) for era in self.eras)  # type: ignore
                elif isinstance(firstsource, list):
                    assert isinstance(firstsource[0], str)
                    assert all(isinstance(source[era], list) for era in self.eras)
                    self._sources = dict((era, Source('', source[era], era=era, friends=friendFiles[era])) for era in self.eras)  # type: ignore
                else:
                    assert all(isinstance(source[era], Source) for era in self.eras)
                    self._sources = dict((era, source[era]) for era in self.eras)
        elif isinstance(source, Source):
            assert (friends is None)  # should have been put in the Source object
            self._source = source
        elif isinstance(source, list) and isinstance(source[0], str):
            assert (friends is None)  # not supported for the moment, could be added but it's tricky (just use Source instead)
            self._source = Source('', source, friends=None)
        else:
            assert (isinstance(source, str))
            friendFiles = [f.format(name=name) for f in friends] if friends else None
            self._source = Source('', source.format(name=name), friends=friendFiles)
        self.isMC = False
        self.isDataDriven = False
        self.isData = False
        self.normUncertainties = NormUncertainty.parse(normUncertainty, "norm_" + name)

    def source(self, era : Optional[str] = None) -> Source:
        if era is not None:
            assert (self.eras is not None)
            return self._sources.get(era, None)  # type: ignore
        else:
            assert (self.eras is None)
            return self._source

    def hasEra(self, era : Optional[str]) -> bool:
        if era is not None:
            assert (self.eras is not None)
            return era in self._sources
        else:
            assert (self.eras is None)
            return True

    def customizeFlow(self, flow : Any, era : Optional[str]) -> Any:
        """
        Customizes the given flow by applying a series of hooks and filtering steps based on the sample and era.

        Args:
            flow (Any): The initial flow object to be customized.
            era (Optional[str]): The era to be considered for customization. Can be None.

        Returns:
            Any: The customized flow object after applying hooks and filtering steps.
        """
        for h in self._hooks:
            flow = h.customizeFlow(flow, era=era)
        return flow.filterSteps(lambda s : s.appliesTo(self, era))

    def _sourcesAsString(self) -> str:
        if self.eras:
            return ", ".join([f"\n    {e} = {s}" for (e, s) in self._sources.items()])
        else:
            return str(self._source)

    def clone(self : TSample,

              hooks : Optional[Iterable['Hook']] = None,
              postfix : Optional[str] = None) -> TSample:
        """
        Create a copy of the current sample instance with optional modifications.

        Args:
            hooks (Optional[Iterable['Hook']]): An optional iterable of Hook objects to be added to the cloned instance's hooks.
            postfix (Optional[str]): An optional string to be appended to the cloned instance's name.

        """
        cloned = copy.deepcopy(self)
        if hooks:
            cloned._hooks += hooks
        if postfix:
            cloned.name += "_" + postfix
        return cloned


class MCSample(Sample):
    """A MC sample.

       By default, events are normalized by multiplying them by the specified genWeight,
       divided by the sum of those weights across the whole sample,
       multiplied by the specified cross section (in picobarns),
       and by the luminosity specified in the processing.

       For samples that area already weighted, specify genWeightName = None, xsec = None, weight = ... """

    #Signature for samples without eras, and with gen weights to be normalized via sum of weights
    @overload
    def __init__(self,
                 name : str,
                 source : Union[Source, str, list[str]],
                 eras : None = None,
                 genWeightName : str = "genWeight",
                 genWeightSum : Optional[float] = None,
                 genSumWeightName : str = "_auto_",
                 xsec : Union[float, str] = 1.0,
                 **kwargs : Any):
        """For samples without eras, and with gen weights to be normalized via sum of weights"""
        ...

    #Signature for samples without eras, and pre-computed weights (no sum-of-gen-weights normalization). You must also specify a weight!"""
    @overload
    def __init__(self,
                 name : str,
                 source : Union[Source, Mapping[str, Source], str, list[str], Mapping[str, str], Mapping[str, list[str]]],
                 eras : None = None,
                 genWeightName : None = None,
                 genWeightSum : None = None,
                 genSumWeightName : Literal["_auto_"] = "_auto_",  # unused in this case
                 xsec : None = None,
                 **kwargs : Any):
        """For samples without eras, and pre-computed weights (no sum-of-gen-weights normalization). You must also specify a weight!"""
        ...

    #Signature for samples with eras, and with gen weights to be normalized via sum of weights"""
    @overload
    def __init__(self,
                 name : str,
                 source : Union[Mapping[str, Source], str, Mapping[str, str], Mapping[str, list[str]]],
                 eras : list[str],
                 genWeightName : str = "genWeight",
                 genWeightSum : Optional[float] = None,
                 genSumWeightName : str = "_auto_",
                 xsec : Union[float, str] = 1.0,
                 **kwargs : Any):
        """For samples with eras, and with gen weights to be normalized via sum of weights"""
        ...

    #Signature for samples with eras, and pre-computed weights (no sum-of-gen-weights normalization)"""
    @overload
    def __init__(self,
                 name : str,
                 source : Union[Mapping[str, Source], str, Mapping[str, str], Mapping[str, list[str]]],
                 eras : list[str],
                 genWeightName : None = None,
                 genWeightSum : None = None,
                 genSumWeightName : Literal["_auto_"] = "_auto_",  # unused in this case
                 xsec : None = None,
                 **kwargs : Any):
        """For samples with eras, and pre-computed weights (no sum-of-gen-weights normalization)"""
        ...

    #actual implementation of all 4
    def __init__(self,
                 name : str,
                 source : Union[Source, Mapping[str, Source], str, list[str], Mapping[str, str], Mapping[str, list[str]]],
                 eras : Optional[list[str]] = None,
                 genWeightName : Optional[str] = "genWeight",
                 genWeightSum : Optional[float] = None,
                 genSumWeightName : str = "_auto_",
                 xsec : Union[float, str, None] = 1.0,
                 **kwargs : Any):
        if eras is not None:
            assert isinstance(source, str) or isinstance(source, dict)
            super().__init__(name, source, eras=eras, **kwargs)
        else:
            assert not isinstance(source, dict)
            super().__init__(name, source, **kwargs)

        assert ((xsec is None) == (genWeightName is None))
        assert ((genWeightName is not None) or ('weight' in kwargs))
        self.genWeightName = genWeightName
        if self.eras:
            if genWeightSum:
                self._genWeightSum = genWeightSum
            else:
                self._genWeightSum = dict((e, None) for e in self.eras)
        else:
            self._genWeightSum = {None: genWeightSum}
        self.genSumWeightName = genSumWeightName
        self.xsec = xsec
        #self.xsec = xsec if xsec is not None else 1.0
        self.isMC = True
        if self.xsec:
            if self.eras is None:
                self.source().addMeta("_xsec", self.xsec)
            else:
                for era in self.eras:
                    self.source(era).addMeta("_xsec", self.xsec)

    def customizeFlowMC(self, flow : Any, luminosity : float, era : Optional[str] = None) -> Any:
        flow2 = super().customizeFlow(flow, era=era)
        from CMGRDF.flow import AddWeight
        if self.genWeightName:
            if Source.useDefinePerSample:
                return flow2.prepend(
                    AddWeight("mcSampleWeight", f"{self.genWeightName}*_xsec*{luminosity * 1000}*({self.weight})/genWeightSum"))
            else:
                return flow2.prepend(
                    AddWeight("mcSampleWeight", f"{self.genWeightName}*({self.xsec})*({luminosity * 1000 / self._genWeightSum[era]})*({self.weight})"))  # type: ignore
        else:
            assert (self.weight is not None)
            return flow2.prepend(AddWeight("weight", str(self.weight)))

    def genWeightSum(self, era : Optional[str] = None) -> float:
        assert ((self.eras is None) == (era is None))
        return self._genWeightSum[era]  # type: ignore

    def bookSumWeight(self, eras : Iterable[Optional[str]], cache : Any = None) -> int:
        """Compute the sum of weights for this sample, and return the number of computations actually done"""
        ret = 0
        for era in eras:
            src = self.source(era)
            if src is None or src.hasMeta("genWeightSum"):
                continue
            if cache and cache.hasSum(src, self.genSumWeightName):
                sumw = cache.getSum(src, self.genSumWeightName)
                self._genWeightSum[era] = sumw  # type: ignore
                src.addMeta("genWeightSum", sumw)
                continue
            genSumWeightName = self.genSumWeightName
            if genSumWeightName == "_nevents_":
                self.genWeightName = "1."
                chain = ROOT.TChain("Events")
                for f in src.files:
                    chain.Add(f)
                sumw = float(chain.GetEntries())
            else:
                chain = ROOT.TChain("Runs")
                for f in src.files:
                    chain.Add(f)
                if genSumWeightName == "_auto_":
                    if chain.GetBranch("genEventSumw"):
                        genSumWeightName = "genEventSumw"
                    elif chain.GetBranch("genEventSumw_"):
                        genSumWeightName = "genEventSumw_"
                    else:
                        raise RuntimeError("ERROR: can't find gen sum name in sample " + self.name)
                chain.Draw("0.5 >> htemp(1,0,1)", genSumWeightName, "GOFF")
                hist = ROOT.gROOT.FindObject("htemp")
                sumw = hist.GetBinContent(1)
            self._genWeightSum[era] = sumw  # type: ignore
            src.addMeta("genWeightSum", sumw)
            if cache:
                cache.writeSum(src, self.genSumWeightName, sumw)
            ret += 1
        return ret

    def __str__(self):
        xsec_string = f", xsec = {self.xsec}" if self.xsec else ""
        return f"MCSample({self.name}{xsec_string}, {self._sourcesAsString()})"


def _mergeEras(samples : Iterable[Sample]) -> Optional[list[str]]:
    if all((s.eras is None) for s in samples):
        return None
    else:
        # use set to make unique
        assert all((s.eras is not None) for s in samples)
        return list(sorted(set([e for s in samples for e in s.eras])))  # type: ignore


def _mergeErasAndSources(name : str, samples : Iterable[Sample]) -> Union[tuple[None, MergedSource], tuple[list[str], dict[str, MergedSource]]]:
    eras = _mergeEras(samples)
    eralist = eras if eras is not None else [None]
    sourcemap = dict()
    for e in eralist:
        sourcesThisEra = []
        for s in samples:
            src = s.source(e)
            if src is None:
                continue
            sourcesThisEra.append(src)
        sourcemap[e] = MergedSource(name, sourcesThisEra, era=e)
    if eras is None:
        return (eras, sourcemap[None])
    else:
        return (eras, sourcemap)


class MCGroup(Sample):
    """A group of MC samples that are processed together unformly except for the normalization
       from the genWeights, that is to be computed separately for each sample.
       Useful e.g. for samples binned at gen level and that can be used all together.
       This allows the framework to build a single RDF graph, and saves some overheads."""

    def __init__(self,
                 name : str,
                 samples : list[MCSample],
                 moreHooks : Optional[Iterable['Hook']] = None,
                 extraWeight : Optional[Union[str, float]] = None):
        eras, source = _mergeErasAndSources(name, samples)
        if eras is None:
            assert isinstance(source, MergedSource)
            super().__init__(name, source)
        else:
            assert isinstance(source, dict)
            super().__init__(name, source, eras=eras)
        self.samples = samples
        self.moreHooks = list(moreHooks) if moreHooks else []
        self.extraWeight = extraWeight
        self._hooks = samples[0]._hooks[:]
        for s in samples[1:]:
            assert (s._hooks == self._hooks)
        self._hooks += self.moreHooks
        if samples[0].genSumWeightName=="_nevents_":
            self.genWeightName = "1."
            assert all((s.genSumWeightName == "_nevents_") for s in samples[1:])
        else:
            self.genWeightName = samples[0].genWeightName
            assert all((s.genWeightName == self.genWeightName) for s in samples[1:])
        self.weight = samples[0].weight
        assert all((s.weight == self.weight) for s in samples[1:])
        if any(isinstance(s.xsec, str) for s in samples):
            assert (all((s.xsec == samples[0].xsec) for s in samples))
        if extraWeight:
            self.weight = "(%s)*(%s)" % (self.weight, extraWeight)
        self.isMC = True

    def customizeFlowMC(self, flow : Any, luminosity : float, era : Optional[str] = None) -> Any:
        flow2 = super().customizeFlow(flow, era=era)
        from CMGRDF.flow import AddWeight
        if self.genWeightName:
            return flow2.prepend(
                AddWeight("mcSampleWeight", f"{self.genWeightName}*_xsec*{luminosity * 1000}*({self.weight})/genWeightSum"))
        else:
            return flow2.prepend(AddWeight("weight", str(self.weight)))

    def bookSumWeight(self, eras : Iterable[Optional[str]], **kwargs : Any) -> int:
        """Compute the sum of weights for these samples, and return the number of computations actually done"""
        return sum(s.bookSumWeight(eras, **kwargs) for s in self.samples)

    def split(self) -> list[MCSample]:
        """Split back into individual samples, potentially adding the extra weight and hooks"""
        if self.extraWeight is None and len(self.moreHooks) == 0:
            return self.samples[:]
        ret = []
        import copy
        for sample in self.samples:
            scopy = copy.copy(sample)
            scopy.name = sample.name + f"_for{self.name}"
            if self.moreHooks:
                scopy._hooks = sample._hooks + self.moreHooks
            if self.extraWeight:
                scopy.weight = ("(%s)*(%s)" % (sample.weight, self.extraWeight)) if sample.weight != 1 else self.extraWeight
            ret.append(scopy)
        return ret


class DataDrivenSample(Sample):
    """A sample for a data driven background estimate, and so not scaled by luminosity."""

    def __init__(self,
                 name : str,
                 source : Union[Source, Mapping[str, Source], str, list[str], Mapping[str, str], Mapping[str, list[str]]],
                 weight : Union[str, float] = 1,
                 **options):
        super().__init__(name, source, **options)
        self.weight = weight
        self.isMC = False
        self.isDataDriven = True
        self.isData = False

    def customizeFlow(self, flow : Any, era : Optional[str]) -> Any:
        flow2 = super().customizeFlow(flow, era=era)
        if self.weight not in ("1", 1):
            from CMGRDF.flow import AddWeight
            return flow2.append(
                AddWeight("weight", self.weight))
        else:
            return flow2

    def __str__(self) -> str:
        weight_string = f", weight = {self.weight}" if self.weight != "1" else ""
        return f"DataDrivenSample({self.name}{weight_string}, {self._sourcesAsString()})"


class DataSample(DataDrivenSample):
    """The data sample"""

    def __init__(self,
                 name : str,
                 source : Union[Source, Mapping[str, Source], str, list[str], Mapping[str, str], Mapping[str, list[str]]],
                 **options : Any):
        super().__init__(name, source, **options)
        self.isData = True

    def __str__(self) -> str:
        return f"DataSample({self.name}, {self._sourcesAsString()})"


class Process:
    """A group of one or more samples that are added up together as a single entry in plots or datacards.
       You can specify a more pretty label for it (by default it uses the computer-friendly name of it)
       It can have addional nomalization uncertainties, specified as in the Sample class."""

    def __init__(self, name : str, samples : "Union[Sample, list[Sample]]", signal=False, label=None, normUncertainty=None, **options):
        self.name = name
        if isinstance(samples, Sample):
            self.samples = [samples]
        else:
            self.samples = list(samples)
        for k, v in options.items():
            setattr(self, k, v)
        self.label = label if label is not None else self.name
        self.isData = False
        self.isSignal = signal
        self.normUncertainties = NormUncertainty.parse(normUncertainty, "norm_" + name)

    def getOpt(self, name, default=None):
        return getattr(self, name, default)


class Data(Process):
    """The data process, containing all the data samples"""

    def __init__(self, samples, label="Data", **options):
        super().__init__("data", samples, label=label, **options)
        self.isData = True
