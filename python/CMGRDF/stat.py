# flake8: noqa: A005
# don't complain it's shadowing the builtin stat module
import os
import os.path

import ROOT  # type: ignore
from CMGRDF.histoWithNuisances import listAllNuisances, mergePlots
from CMGRDF.utils import MultiKey, Options, MultiReport


class DatacardWriter(object):
    @staticmethod
    def defaultOptions() -> Options:
        opts = Options()
        opts.declare("asimov", None,
                     help=("Use an Asimov dataset of the specified kind: including signal ('signal','s','sig','s+b') or background-only ('background','bkg','b','b-only')"))
        opts.declare("autoMCStats", True, bool, help="use autoMCStats")
        opts.declare("autoMCStatsThreshold", 10, int, help="threshold to put on autoMCStats")
        opts.declare("threshold", 0.0, float, help="Minimum event yield to consider processes")
        opts.declare("regularize", False, bool, help="Regularize templates")
        return opts

    def __init__(self, **options):
        self._options = DatacardWriter.defaultOptions().update(**options)

    def makeCards(self, plots : MultiReport, plotKey : MultiKey, outname : str, **options) -> None:
        assert isinstance(plots, MultiReport)
        assert isinstance(plotKey, MultiKey)
        opts = self._options.cloneAndUpdate(**options)
        if os.path.dirname(outname) and not os.path.exists(os.path.dirname(outname)):
            os.makedirs(os.path.dirname(outname))
        for key, plot in plots:
            if not plotKey.isSuperSet(key):
                continue
            txtname = outname.format(**key)
            if txtname.endswith(".txt"):
                binname = os.path.basename(txtname.replace(".txt", ""))
                rootname = txtname.replace(".txt", ".input.root")
            else:
                binname = os.path.basename(txtname)
                rootname = txtname + ".input.root"
                txtname += ".txt"
            if binname[0] in "1234567890":
                raise RuntimeError("Bins should start with a letter.")
            signals, backgrounds, data_obs, byname = [], [], [], {}
            for p, h in plot.histos:
                h.cropNegativeBins()
                h.cropBinErrorTo100Percent()
                if p.isData:
                    data_obs.append((p, h))
                elif p.isSignal:
                    if h.Integral() > opts.threshold:
                        signals.append((p, h))
                else:
                    if h.Integral() > opts.threshold:
                        backgrounds.append((p, h))
                if p.name in byname:
                    raise RuntimeError("Duplicate process name %s" % p.name)
                byname[p.name] = h
            if len(signals) + len(backgrounds) == 0:
                print("Nothing to plot for %s" % key)
                continue
            if opts.asimov:
                if "s" in opts.asimov:
                    data_obs = mergePlots("data_obs", [h for (p, h) in signals + backgrounds])
                else:
                    data_obs = mergePlots("data_obs", [h for (p, h) in backgrounds])
            else:
                if len(data_obs) != 1:
                    raise RuntimeError("Can't choose process for data_obs among %s" % ([p.name for (p, h) in data_obs]))
                data_obs = data_obs[0][1].Clone("data_obs")
            nuisances = sorted(listAllNuisances(plot.histos))
            allyields = dict([(p.name, h.Integral()) for p, h in plot.histos])
            procs = []
            iproc = {}
            for i, (s, h) in enumerate(signals):
                procs.append(s.name)
                iproc[s.name] = i - len(signals) + 1
            for i, (b, h) in enumerate(backgrounds):
                procs.append(b.name)
                iproc[b.name] = i + 1
            systs = {}
            for name in nuisances:
                effshape = {}
                isShape = False
                for p in procs:
                    h = byname[p]
                    n0 = h.Integral()
                    if h.hasVariation(name):
                        if isShape or h.isShapeVariation(name):
                            if name.endswith("_lnU"):
                                raise RuntimeError("Nuisance %s should be lnU but has shape effect on %s" % (name, p))
                            isShape = True
                        variants = list(h.getVariation(name))
                        for hv, d in zip(variants, ('up', 'down')):
                            k = hv.Integral() / n0
                            if k == 0:
                                print("Warning: underflow template for %s %s %s %s. Will take the nominal scaled down by a factor 2" % (binname, p, name, d))
                                hv.Add(h.raw())
                                hv.Scale(0.5)
                            elif k < 0.2 or k > 5:
                                print("Warning: big shift in template for %s %s %s %s: kappa = %g " % (binname, p, name, d, k))
                        effshape[p] = variants
                if isShape:
                    if opts.regularize:
                        for p in procs:
                            byname[p].regularizeVariation(name, binname=binname)
                    systs[name] = ("shape", dict((p, "1" if p in effshape else "-") for p in procs), effshape)
                else:
                    effyield = dict((p, "-") for p in procs)
                    isNorm = False
                    for p, (hup, hdn) in effshape.items():
                        i0 = allyields[p]
                        kup, kdn = hup.Integral() / i0, hdn.Integral() / i0
                        if abs(kup * kdn - 1) < 1e-5:
                            if abs(kup - 1) > 2e-4:
                                effyield[p] = "%.3f" % kup
                                isNorm = True
                        else:
                            effyield[p] = "%.3f/%.3f" % (kdn, kup)  # type: ignore
                            isNorm = True
                    if isNorm:
                        if name.endswith("_lnU"):
                            systs[name] = ("lnU", effyield, {})
                        else:
                            systs[name] = ("lnN", effyield, {})
            # make a new list with only the ones that have an effect
            nuisances = sorted(systs.keys())
            datacard = open(txtname, "w")
            datacard.write("## Datacard for %s\n" % key)
            datacard.write("shapes *        * %s $PROCESS $PROCESS_$SYSTEMATIC\n" % os.path.basename(rootname))
            datacard.write('##----------------------------------\n')
            datacard.write('bin         %s\n' % binname)
            datacard.write('observation %s\n' % data_obs.Integral())
            datacard.write('##----------------------------------\n')
            klen = max([7, len(binname)] + [len(p) for p in procs])
            kpatt = " %%%ds " % klen
            fpatt = " %%%d.%df " % (klen, 3)
            npatt = "%%-%ds " % max(len('process'), max(map(len, nuisances)) if nuisances else 0)
            datacard.write('##----------------------------------\n')
            datacard.write((npatt % 'bin    ') + (" " * 6) + (" ".join([kpatt % binname for p in procs])) + "\n")
            datacard.write((npatt % 'process') + (" " * 6) + (" ".join([kpatt % p for p in procs])) + "\n")
            datacard.write((npatt % 'process') + (" " * 6) + (" ".join([kpatt % iproc[p] for p in procs])) + "\n")
            datacard.write((npatt % 'rate   ') + (" " * 6) + (" ".join([fpatt % allyields[p] for p in procs])) + "\n")
            datacard.write('##----------------------------------\n')
            towrite = [byname[p].raw() for p in procs] + [data_obs.raw()]
            for name in nuisances:
                (kind, effmap, effshape) = systs[name]
                datacard.write(('%s %5s' % (npatt % name, kind)) + " ".join([kpatt % effmap[p] for p in procs]) + "\n")
                for p, (hup, hdn) in effshape.items():
                    towrite.append(hup.Clone("%s_%sUp" % (p, name)))
                    towrite.append(hdn.Clone("%s_%sDown" % (p, name)))
            if opts.autoMCStats:
                datacard.write('* autoMCStats %d\n' % opts.autoMCStatsThreshold)

            workspace = ROOT.TFile.Open(rootname, "RECREATE")
            for h in towrite:
                workspace.WriteTObject(h, h.GetName())
            workspace.Close()

            print("Datacard for %s wrote to %s and %s" % (key, txtname, rootname))
