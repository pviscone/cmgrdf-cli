from CMGRDF.CorrectionlibFactory import CorrectionlibFactory
from flows.SFs import BaseCorrection, BranchCorrection

import ROOT

#!TODO There is no smearings for 2023, I am using 2022 for now FIX
corrections_map = {
    "2023": "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/EGM/2022_Summer22/electronSS.json.gz",
    "2022EE": "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/EGM/2022_Summer22EE/electronSS.json.gz",
}


class electronSmearing(BaseCorrection):
    def __init__(self, name, pt, eta, r9, defineNew=False, **kwargs):
        self.pt = pt
        self.eta = eta
        self.r9 = r9
        self.defineNew = defineNew
        super().__init__(name, **kwargs)

    def init(self, era=None):
        if era is None:
            raise ValueError("Must be defined with one and only one era")
        self.era = era
        self.eras = [era]

        self.corrector = CorrectionlibFactory.loadCorrector(corrections_map[self.era], "Smearing", check=True)[0]
        cpp_sf = """
            ROOT::RVec<float> electronSmearingSF_<era> (const std::string &syst_type, const ROOT::RVec<float> &pt, const ROOT::RVec<float> &eta, const ROOT::RVec<float> &r9){
                int n = eta.size();
                auto generator = TRandom();
                ROOT::RVec<float> sf(n);
                for (int i = 0; i < n; i++) {
                    float rho = <corrector>->evaluate({"rho", eta[i], r9[i]});
                    if (syst_type == "up"){
                        rho += <corrector>->evaluate({"err_rho", eta[i], r9[i]});
                    } else if (syst_type == "down"){
                        rho -= <corrector>->evaluate({"err_rho", eta[i], r9[i]});
                    } else if (syst_type != "nominal"){
                        throw std::invalid_argument("Unknown syst_type: " + syst_type);
                    }
                    sf[i] = generator.Gaus(1., rho);
                }
                return sf*pt;
            }
        """.replace("<era>", self.era).replace("<corrector>", self.corrector)

        ROOT.gInterpreter.Declare(cpp_sf)

        branch_name = self.pt if not bool(self.defineNew) else self.defineNew
        return BranchCorrection(
            branch_name,
            f'electronSmearingSF_{self.era}("nominal", {self.pt}, {self.eta}, {self.r9})',
            f'electronSmearingSF_{self.era}("up", _OLD_{self.pt}_, {self.eta}, {self.r9})',
            f'electronSmearingSF_{self.era}("down", _OLD_{self.pt}_, {self.eta}, {self.r9})',
            preserve=[self.pt],
            onData=False,
            onDataDriven=False,
            era=self.era,
            doSyst=self.doSyst,
            nuisName=self.nuisName,
            redefine=not bool(self.defineNew),
        )


class electronScale(BaseCorrection):
    def __init__(self, doSyst=True, **kwargs):
        pass

    def init(self):
        pass
