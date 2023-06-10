from typing import Union
import ROOT
import os
import os.path
import glob
from CMGRDF.utils import recursiveHash, safeName, NormUncertainty


class Source(object):
    """Base class that wraps a list of files from which an RDF can be created"""

    def __init__(self, name : str, files, era=None, friends=None):
        if isinstance(files, str):
            if "*" in files:
                files = glob.glob(files)
            else:
                files = [files]
        else:
            assert (len(files) >= 1)
            assert (not any(("*" in f) for f in files))
        self.name = name if name else Source._autoName(files)
        self.files = files
        self.era = era
        self.friends = friends
        self._bigHash = None
        self._bigHashNoFriends = None

    def createRDF(self, treeName="Events"):
        if len(self.files) == 1:
            if os.path.isdir(self.files[0]):
                if treeName == "Events":
                    assert (self.friends is None)  # not supported
                ret = ROOT.RDataFrame(treeName, self.files[0] + "/*.root")
            else:
                if treeName == "Events" and self.friends is not None:
                    tfile = ROOT.TFile.Open(self.files[0])
                    tree = tfile.Get(treeName)
                    for f in self.friends:
                        if isinstance(f, tuple):
                            tree.AddFriend(f[0], f[1])
                        elif isinstance(f, str):
                            tree.AddFriend("Friends", f)
                        else:
                            raise RuntimeError("Unsupported friend %r for %s" % (f, self))
                    ret = ROOT.RDataFrame(tree)
                    ret._tree = tree
                    ret._tfile = tfile
                else:
                    ret = ROOT.RDataFrame(treeName, self.files[0])
        else:
            chain = ROOT.TChain(treeName)
            for f in self.files:
                chain.Add(f)
            friendChains = []
            if treeName == "Events":
                if self.friends is not None:
                    #print("Creating friends for %s %s" % (treeName, self.longId()))
                    for i, files in enumerate(self.friends):
                        #print(" -> creating chain for friend %d: %s" % (i+1,files[:2]))
                        ftname = "Friends"
                        if isinstance(files, tuple):
                            ftname = files[0]
                            files = files[1]
                        fchain = ROOT.TChain(ftname)  # "iFriends%d" % (i+1))
                        for f in files:
                            fchain.Add(f)  # f"{f}?#{ftname}")
                        chain.AddFriend(fchain)
                        friendChains.append(fchain)
            ret = ROOT.RDataFrame(chain)
            ret._chain = chain
            ret._friendChains = friendChains
            #print("RDF for %s %s: chain %s, friends %s" % (treeName, self.longId(), chain, friendChains))
        #print("RDF for %s %s: FO branches %s" % (treeName, self.longId(), [s for s in ret.GetColumnNames() if "FO" in str(s)]))
        return ret

    def __eq__(self, o : object) -> bool:
        if o.__class__ == Source:
            return o.name == self.name and o.files == self.files and o.era == self.era and o.friends == self.friends
        else:
            return id(self) == id(o)

    def bigHash(self, friends=True):
        if not self._bigHash:
            self._makeBigHash()
        return self._bigHash if friends else self._bigHashNoFriends

    def _makeBigHash(self):
        if os.path.exists(self.files[0]):  # files may not exist if e.g. they're globs or root URLs
            tsfiles = [(f, os.path.getmtime(f)) for f in self.files]
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
            self._bigHash = recursiveHash(self.name, self.era, tsfiles, tsfriends)
            if self.friends:
                self._bigHashNoFriends = recursiveHash(self.name, self.era, tsfiles)
            else:
                self._bigHashNoFriends = self._bigHash
        else:
            self._bigHash = recursiveHash(self.name, self.era, self.files, self.friends)
            if self.friends:
                self._bigHashNoFriends = recursiveHash(self.name, self.era, self.files)
            else:
                self._bigHashNoFriends = self._bigHash

    def __hash__(self):
        return hash(self.bigHash())

    def longId(self):
        return "%s-%s-%s" % (safeName(self), self.era if self.era else "", self.bigHash())

    def __str__(self):
        return "Source(%s%s, %d files[%s%s]%s, id %s)" % (
            self.name, (", era %s" % self.era) if self.era else "",
            len(self.files), self.files[0], ", ..." if len(self.files) > 1 else "",
            (", %d friends[%s, ...]" % (len(self.friends), self.friends[0])) if self.friends else "",
            self.bigHash()
        )

    @staticmethod
    def _autoName(files: "list[str]") -> str:
        assert (len(files) != 0)
        if len(files) > 1 or files[0].endswith("/*.root"):
            return os.path.basename(os.path.dirname(files[0]))
        else:
            return os.path.basename(files[0]).replace("*", "").replace(".root", "")


class Sample(object):
    """A set of files, possibly era-dependent, to be processed homogeneously.
       This is just a base class, users should normally use the subclasses MCSample, DataSample or DataDrivenSample

       It can have hooks that modify the processing flow, and normalization uncertainties.
    """

    def __init__(self, name : str, source, hooks=[], eras=None, friends=None, normUncertainty=None, **kwargs):
        """source can be any 4 of the following:
             - a source object, if this sample doesn't have a list of eras
             - a dict (era -> Source) if this sample has a list of eras.
             - a string, being a file name or directory name or glob string, which may include {name} and/or {era} inside
             - a dict (era -> String) if this sample has a list of eras
           normUncertainty can be any of the following:
             - None
             - a list of NormUncertainty objects
             - a float (logNormal kappa)
             - a tuple (kappaLow, kappaHigh)
             - a dict with keys being the nuisance names, and values being kappas or kappa tuples
        """
        self.name = name
        self._hooks = hooks[:]
        self.eras = eras
        for k, v in kwargs.items():
            setattr(self, k, v)
        if self.eras:
            if isinstance(source, str):
                friendFiles = dict((era, [f.format(name=name, era=era) for f in friends] if friends else None) for era in self.eras)
                self._sources = dict((era, Source('', source.format(name=name, era=era), era=era, friends=friendFiles[era])) for era in self.eras)
            else:
                friendFiles = dict((era, [f.format(name=name, era=era) for f in friends] if friends else None) for era in self.eras)
                if isinstance(source[self.eras[0]], str):
                    self._sources = dict((era, Source('', source[era].format(name=name, era=era), era=era, friends=friendFiles[era])) for era in self.eras)
                else:
                    self._sources = dict((era, source[era]) for era in self.eras)
        elif isinstance(source, Source):
            assert (friends is None)  # should have been put in the Source object
            self._source = source
        else:
            friendFiles = [f.format(name=name) for f in friends] if friends else None
            self._source = Source('', source.format(name=name), friends=friendFiles)
        self.isMC = False
        self.isDataDriven = False
        self.isData = False
        self.normUncertainties = NormUncertainty.parse(normUncertainty, "norm_" + name)

    def source(self, era=None) -> Source:
        if era is not None:
            assert (self.eras is not None)
            return self._sources[era] if era in self._sources else None
        else:
            assert (self.eras is None)
            return self._source

    def hasEra(self, era):
        if era is not None:
            assert (self.eras is not None)
            return era in self._sources
        else:
            assert (self.eras is None)
            return True

    def customizeFlow(self, flow, era=None):
        for h in self._hooks:
            flow2 = h.customizeFlow(flow, era=era)
            if flow2 != flow:
                flow2._from = flow
                flow = flow2
        return flow.filterSteps(lambda s : s.appliesTo(self, era))

    def _sourcesAsString(self) -> str:
        if self.eras:
            return ", ".join([f"\n    {e} = {s}" for (e, s) in self._sources.items()])
        else:
            return str(self._source)


class MCSample(Sample):
    """A MC sample.

       By default, events are normalized by multiplying them by the specified genWeight,
       divided by the sum of those weights across the whole sample,
       multiplied by the specified cross section (in picobarns),
       and by the luminosity specified in the processing.

       For samples that area already weighted, specify genWeightName = None, xsec = None, weight = ... """

    def __init__(self, name : str, source, genWeightName="genWeight", genWeightSum=None, genSumWeightName="_auto_", xsec="1.0", **kwargs):
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
        self.isMC = True

    def customizeFlow(self, flow, luminosity, sumWeightProvider, era=None):
        flow2 = super().customizeFlow(flow, era=era)
        from CMGRDF.flow import DefinePerSample, AddWeight
        if self.genWeightName:
            return flow2.prepend(
                DefinePerSample("genWeightSum", sumWeightProvider),
                AddWeight("mcSampleWeight", "{0}*{1}*{2}*({3})/genWeightSum".format(self.genWeightName, self.xsec, luminosity * 1000, getattr(self, "weight", 1))))
        else:
            return flow2.prepend(AddWeight("weight", self.weight))

    def genWeightSum(self, era=None):
        assert ((self.eras is None) == (era is None))
        return self._genWeightSum[era]

    def bookSumWeight(self, sumWeightProvider, eras):
        sumWeightProvider.bookEras(self, eras)

    def __str__(self):
        xsec_string = f", xsec = {self.xsec}" if self.xsec else ""
        return f"MCSample({self.name}{xsec_string}, {self._sourcesAsString()})"


def _mergeEras(samples):
    if all((s.eras is None) for s in samples):
        return None
    else:
        return list(sorted(set([e for s in samples for e in s.eras])))  # use set to make unique


def _mergeSources(name, samples):
    eras = _mergeEras(samples)
    if eras is None:
        eras = [None]
    sources = dict()
    for e in eras:
        files, friends = [], None
        for s in samples:
            src = s.source(e)
            if src is None:
                continue
            files += src.files
            if src.friends:
                assert (len(src.files) == 1)  # this is not implemented for N(files)>1
                assert (all(s2.source(e).friends for s2 in samples))
                if friends is None:
                    friends = [[f] for f in src.friends]
                else:
                    for i, f in enumerate(src.friends):
                        friends[i].append(f)
        sources[e] = Source(name, files, era=e, friends=friends)
    return sources if eras != [None] else sources[None]


class MCGroup(Sample):
    """A group of MC samples that are processed together unformly except for the normalization
       from the genWeights, that is to be computed separately for each sample.
       Useful e.g. for samples binned at gen level and that can be used all together.
       This allows the framework to build a single RDF graph, and saves some overheads."""

    def __init__(self, name : str, samples : "list[MCSample]", moreHooks=[], extraWeight=None):
        super().__init__(name, _mergeSources(name, samples), eras=_mergeEras(samples))
        self.samples = samples
        self._hooks = samples[0]._hooks[:]
        for s in samples[1:]:
            assert (s._hooks == self._hooks)
        self._hooks += moreHooks[:]
        self.xsec = samples[0].xsec
        for s in samples[1:]:
            assert (s.xsec == self.xsec)
        self.genWeightName = samples[0].genWeightName
        for s in samples[1:]:
            assert (s.genWeightName == self.genWeightName)
        self.weight = getattr(samples[0], 'weight', 1)
        for s in samples[1:]:
            assert (getattr(s, 'weight', 1) == self.weight)
        if extraWeight:
            self.weight = "(%s)*(%s)" % (self.weight, extraWeight)
        self.isMC = True

    def customizeFlow(self, flow, luminosity, sumWeightProvider, era=None):
        flow2 = super().customizeFlow(flow, era=era)
        from CMGRDF.flow import DefinePerSample, AddWeight
        return flow2.prepend(
            DefinePerSample("genWeightSum", sumWeightProvider),
            AddWeight("mcSampleWeight", "{0}*{1}*{2}*({3})/genWeightSum".format(self.genWeightName, self.xsec, luminosity * 1000, getattr(self, "weight", 1))))

    def bookSumWeight(self, sumWeightProvider, eras):
        for s in self.samples:
            sumWeightProvider.bookEras(s, eras)


class DataDrivenSample(Sample):
    """A sample for a data driven background estimate, and so not scaled by luminosity."""

    def __init__(self, name, source, weight="1", **options):
        super().__init__(name, source, **options)
        self.weight = weight
        self.isMC = False
        self.isDataDriven = True
        self.isData = False

    def customizeFlow(self, flow, era):
        flow2 = super().customizeFlow(flow, era=era)
        if self.weight not in ("1", 1):
            from CMGRDF.flow import AddWeight
            return flow2.prepend(
                AddWeight("weight", str(getattr(self, "weight", "1"))))
        else:
            return flow2

    def __str__(self):
        weight_string = f", weight = {self.weight}" if self.weight != "1" else ""
        return f"DataDrivenSample({self.name}{weight_string}, {self._sourcesAsString()})"


class DataSample(DataDrivenSample):
    """The data sample"""

    def __init__(self, name, samples, **options):
        super().__init__(name, samples, **options)
        self.isData = True

    def __str__(self):
        return f"DataSample({self.name}, {self._sourcesAsString()})"


class Process(object):
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
        super(Data, self).__init__("data", samples, label=label, **options)
        self.isData = True
