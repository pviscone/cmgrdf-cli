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

        self.corrector = CorrectionlibFactory.loadCorrector(corrections_map[era], "Smearing", check=True)[0]

        cpp_sf = """
            ROOT::RVec<float> electronSmearingSF_<era> (ROOT::RVec<float> &pt, const ROOT::RVec<float> &eta, const ROOT::RVec<float> &r9){
                int n = eta.size();
                for (int i = 0; i < n; i++) {
                    float rho = <corrector>->evaluate({"rho", eta[i], r9[i]});
                    pt[i] *= generator.Gaus(1., rho);
                }
                return pt;
            }
        """.replace("<era>", era).replace("<corrector>", self.corrector)

        cpp_up = """
            ROOT::RVec<float> electronSmearing_up_<era> (ROOT::RVec<float> &pt, const ROOT::RVec<float> &eta, const ROOT::RVec<float> &r9){
                int n = eta.size();
                for (int i = 0; i < n; i++) {
                    float rho = <corrector>->evaluate({"rho", eta[i], r9[i]}) + <corrector>->evaluate({"err_rho", eta[i], r9[i]});
                    pt[i] *= generator.Gaus(1., rho);
                }
                return pt;
            }
        """.replace("<era>", era).replace("<corrector>", self.corrector)

        cpp_down = """
            ROOT::RVec<float> electronSmearing_down_<era> (ROOT::RVec<float> &pt, const ROOT::RVec<float> &eta, const ROOT::RVec<float> &r9){
                int n = eta.size();
                for (int i = 0; i < n; i++) {
                    float rho = <corrector>->evaluate({"rho", eta[i], r9[i]}) - <corrector>->evaluate({"err_rho", eta[i], r9[i]});
                    pt[i] *= generator.Gaus(1., rho);
                }
                return pt;
            }
        """.replace("<era>", era).replace("<corrector>", self.corrector)

        ROOT.gInterpreter.Declare(cpp_sf)
        ROOT.gInterpreter.Declare(cpp_up)
        ROOT.gInterpreter.Declare(cpp_down)

        branch_name = self.pt if not bool(self.defineNew) else self.defineNew
        return BranchCorrection(
            branch_name,
            f'electronSmearingSF_{era}({self.pt}, {self.eta}, {self.r9})',
            f'electronSmearing_up_{era}(_OLD_{self.pt}_, {self.eta}, {self.r9})',
            f'electronSmearing_down_{era}(_OLD_{self.pt}_, {self.eta}, {self.r9})',
            preserve=[self.pt],
            onData=False,
            onDataDriven=False,
            redefine=not bool(self.defineNew),
        )


class electronScale(BaseCorrection):
    def __init__(self, doSyst=True, **kwargs):
        pass

    def init(self):
        pass
