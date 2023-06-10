import ROOT


class GenWeightProvider:
    def __init__(self, cache=None, mode="Old", lazy=False):
        ROOT.gInterpreter.ProcessLine('#include "genWeightProvider.h"')
        self._cpp = ROOT.GenWeightProvider()
        self._strvec = ROOT.std.vector(ROOT.std.string)
        self._samples = []
        self._cache = cache
        self._mode = mode
        self._lazy = lazy

    def bookEras(self, sample, eras):
        for era in eras:
            if sample.hasEra(era):
                self._book(sample, era)

    def _book(self, sample, era):
        self._samples.append((sample, era))
        src = sample.source(era)
        files = self._strvec(len(src.files))
        for i, f in enumerate(src.files):
            files[i] = f
        name = f"{sample.name}:{era}" if era else sample.name
        if sample._genWeightSum[era] is not None:
            self._cpp.addSampleWithSum(name, files, sample._genWeightSum[era])
        elif self._cache and self._cache.hasSum(src):
            sample._genWeightSum[era] = self._cache.getSum(src)
            #print("Got sum for %s from cache: %r" % (name,sample._genWeightSum[era]))
            self._cpp.addSampleWithSum(name, files, sample._genWeightSum[era])
        elif self._lazy:
            self._cpp.addSample(name, files, sample.genSumWeightName)
        else:
            self._cpp.addSampleAndRun(name, files, sample.genSumWeightName)

    def runAll(self, mode="Default"):
        if mode == "Default":
            mode = self._mode
        assert (mode in ("Now", "Multi", "Old"))
        getattr(self._cpp, 'doAll' + mode)()
        for (sample, era) in self._samples:
            name = f"{sample.name}:{era}" if era else sample.name
            wsum = self._cpp.weightSumByName(name)
            sample._genWeightSum[era] = wsum
            if self._cache:
                self._cache.writeSum(sample.source(era), wsum)
            #src = sample.source(era)
            #print("V2 GEN SUM: sample %s, era %r, source %s, file0 %s, sum %r" % (
            #        sample.name, era, src.longId(), src.files[0], sample._genWeightSum[era]))
        if self._cache:
            self._cache.commitSums()

    def nSamples(self):
        return self._cpp.nSamples()

    def provider(self):
        return self._cpp
