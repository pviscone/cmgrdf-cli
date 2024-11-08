from CMGRDF.CorrectionlibFactory import CorrectionlibFactory
from flows.SFs import BaseCorrection

import ROOT

#!TODO There is no smearings for 2023, I am using 2022 for now FIX
era_map = {
    "2023": "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/EGM/2022_Summer22/electronSS.json.gz",
    "2022EE": "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/EGM/2022_Summer22EE/electronSS.json.gz",
}


class electronSmearing(BaseCorrection):
    def __init__(self, pt, eta, r9, doSyst=True, era=None, name="Electron_smearing", defineNew=False, **kwargs):
        self.doSyst = doSyst
        kwargs.setdefault("onData", False)
        kwargs.setdefault("onDataDriven", False)

        self.pt = pt
        self.eta = eta
        self.r9 = r9
        self.name = name
        self.defineNew = defineNew

        super().__init__(self.name, **kwargs)
        self._init = False
        self.era = era
        if self.era is not None:
            self.init(era=self.era)

    def init(self, era=None):
        if era is None:
            raise ValueError("Must be defined with one and only one era")
        self.era = era
        self.eras = [era]

        self.corrector = CorrectionlibFactory.loadCorrector(era_map[self.era], "Smearing", check=True)[0]
        cpp_sf = """
            ROOT::RVec<float> electronSmearingSF_corr_<era> (const ROOT::RVec<float> &pt, const ROOT::RVec<float> &eta, const ROOT::RVec<float> &r9){
                int n = eta.size();
                auto generator = TRandom();
                ROOT::RVec<float> sf(n);
                for (int i = 0; i < n; i++) {
                    sf[i] = generator.Gaus(1., <corrector>->evaluate({"rho", eta[i], r9[i]}));
                }
                return sf*pt;
            }
        """.replace("<era>", self.era).replace("<corrector>", self.corrector)

        cpp_unc = """
            ROOT::RVec<ROOT::RVec<float>> electronSmearingSF_syst_<era> (const ROOT::RVec<float> &pt, const ROOT::RVec<float> &eta, const ROOT::RVec<float> &r9){
                int n = eta.size();
                auto generator = TRandom();
                ROOT::RVec<float> sf_up(n);
                ROOT::RVec<float> sf_down(n);
                for (int i = 0; i < n; i++) {
                    float rho = generator.Gaus(1., <corrector>->evaluate({"rho", eta[i], r9[i]}));
                    sf_up[i] = generator.Gaus(1., rho + <corrector>->evaluate({"err_rho", eta[i], r9[i]}));
                    sf_down[i] = generator.Gaus(1., rho - <corrector>->evaluate({"err_rho", eta[i], r9[i]}));
                }
                return {sf_up*pt, sf_down*pt};
            }
        """.replace("<era>", self.era).replace("<corrector>", self.corrector)

        ROOT.gInterpreter.Declare(cpp_sf)
        if self.doSyst:
            ROOT.gInterpreter.Declare(cpp_unc)

        self._init = True
        return self

    def _attach(self, rdf):
        if self.defineNew is False:
            rdf = rdf.Define(
                f"_Old_{self.pt}_", self.pt
            )  # Save the old pt. This is needed for the syst variation. I cannot vary before redefining, this invalidate the pointer to the old pt that Vary uses
            rdf = rdf.Redefine(self.pt, f"electronSmearingSF_corr_{self.era}({self.pt}, {self.eta}, {self.r9})")
        else:
            rdf = rdf.Define(self.defineNew, f"electronSmearingSF_corr_{self.era}({self.pt}, {self.eta}, {self.r9})")

        if self.doSyst:
            original_pt = f"_Old_{self.pt}_" if self.defineNew is False else self.pt
            rdf = rdf.Vary(
                self.pt if self.defineNew is False else self.defineNew,
                f"electronSmearingSF_syst_{self.era}({original_pt}, {self.eta}, {self.r9})",
                variationTags=["up", "down"],
                variationName=self.name,
            )
        return rdf


class electronScale(BaseCorrection):
    def __init__(self, doSyst=True, **kwargs):
        pass

    def _attach(self):
        pass
