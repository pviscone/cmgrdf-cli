from flows.SFs import BaseCorrection, Declare
from CMGRDF import AddWeightUncertainty, AddWeight
from CMGRDF.CorrectionlibFactory import CorrectionlibFactory

P = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/EGM/"

corrections_map = {
    "2022": P + "2022_Summer22/electron.json.gz",
    "2022EE": P + "2022_Summer22EE/electron.json.gz",
    "2023": P + "2023_Summer23/electron.json.gz",
    "2023BPix": P + "2023_Summer23BPix/electron.json.gz",
}

era_map = {
    "2022": "2022Re-recoBCD",
    "2022EE": "2022Re-recoE+PromptFG",
    "2023": "2023PromptC",
    "2023BPix": "2023PromptD",
}


class electronID(BaseCorrection):
    def __init__(self, name, wp, eta, pt, phi, era=None, **kwargs):
        """
        wp: Loose, Medium, Reco20to75, RecoAbove75, RecoBelow20, Tight, Veto, wp80iso, wp80noiso, wp90iso, wp90noiso
        """
        self.pt = pt
        self.eta = eta
        self.phi = phi
        self.wp = wp
        self.name = name

        super().__init__(self.name, **kwargs)

    def init(self, era=None):
        if era is None:
            raise ValueError("Must be defined with one and only one era")
        self.era = era
        self.eras = [era]

        self.corrector = CorrectionlibFactory.loadCorrector(corrections_map[self.era], "Electron-ID-SF", check=True)[0]

        cpp_sf = (
            """
            double electronIDSF_<era>_<wp> (const std::string &sf_type, const ROOT::RVec<float> &eta, const ROOT::RVec<float> &pt, const ROOT::RVec<float> &phi){
                int n = pt.size();
                double weight = 1.;
                for (int i = 0; i < n; i++) {
                    if (pt[i] < 10.) continue;
                    weight *= <corrector>->evaluate({"<year_string>", sf_type, "<wp>", eta[i], pt[i], phi[i]});
                }
                return weight;
            }
        """.replace("<era>", self.era)
            .replace("<corrector>", self.corrector)
            .replace("<wp>", self.wp)
            .replace("<year_string>", era_map[self.era])
        )

        Declare(cpp_sf)

        if self.doSyst:
            return AddWeightUncertainty(
                self.name,
                f'electronIDSF_{self.era}_{self.wp}("sfup", {self.eta}, {self.pt}, {self.phi})',
                f'electronIDSF_{self.era}_{self.wp}("sfdown", {self.eta}, {self.pt}, {self.phi})',
                nominal=f'electronIDSF_{self.era}_{self.wp}("sf", {self.eta}, {self.pt}, {self.phi})',
                onData=False,
                onDataDriven=False,
            )
        else:
            return AddWeight(
                self.name,
                f'electronIDSF_{self.era}_{self.wp}("sf", {self.eta}, {self.pt}, {self.phi})',
                onData=False,
                onDataDriven=False,
            )
