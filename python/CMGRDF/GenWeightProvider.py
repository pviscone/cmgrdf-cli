import ROOT

class GenWeightProvider:
    def __init__(self):
        ROOT.gInterpreter.ProcessLine('#include "genWeightProvider.h"')
        self._cpp = ROOT.GenWeightProvider()
        self._strvec = ROOT.std.vector(ROOT.std.string)
        self._samples = []
    def bookEras(self, sample, eras):
        for era in eras:
            if sample.hasEra(era):
                self.book(sample, era)
    def book(self, sample, era, later=False):
        self._samples.append((sample,era))
        src = sample.source(era)
        files = self._strvec(len(src.files))
        for i,f in enumerate(src.files):
            files[i] = f
        name = f"{sample.name}:{era}" if era else sample.name
        if later:
            self._cpp.addSample(name, files, sample.genSumWeightName)
        else:
            self._cpp.addSampleAndRun(name, files, sample.genSumWeightName)
    def runAll(self,mode="Old"):
        assert(mode in ("Now", "Multi", "Old"))
        getattr(self._cpp, 'doAll'+mode)()
        for (sample,era) in self._samples:
            name = f"{sample.name}:{era}" if era else sample.name
            #src = sample.source(era)
            sum = self._cpp.weightSumByName(name)
            sample._genWeightSum[era] = sum
            #print("V2 GEN SUM: sample %s, era %r, source %s, file0 %s, sum %r" % (
            #        sample.name, era, src.longId(), src.files[0], sample._genWeightSum[era]))
    def nSamples(self):
        return self._cpp.nSamples()
    def provider(self):
        return self._cpp