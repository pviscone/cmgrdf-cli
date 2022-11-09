import os
import ROOT

from CMGRDF.flow import Define
from CMGRDF.CorrectionlibFactory import CorrectionlibFactory
from CMGRDF.cms.eras import run2eras

muonSFPath = os.environ["MUON_SF_PATH"] if "MUON_SF_PATH" in os.environ else "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/MUO"
muonPOGEras = {"2016pre": "2016preVFP_UL", "2016post": "2016postVFP_UL", "2017": "2017_UL", "2018": "2018_UL"}


class MuonIDSFDefine(Define):
    def __init__(self, idName, era, onData=False, onDataDriven=False, den="genTracks", nuisName="CMS_eff_m", ptRange=(15, 249.999), **options):
        super().__init__(f'Muon_SF_{idName}Id',
                         f'muonIDSF_{idName}_{era}(Muon_pt, {ptRange[0]}, {ptRange[1]}, Muon_eta)',
                         onData=onData, onDataDriven=onDataDriven, **options)
        self.era = era
        self.idName = idName
        self.nuisName = nuisName
        self.exprUp = self.expr.replace('"sf"', '"systup"')
        self.exprDown = self.expr.replace('"sf"', '"systdown"')
        self._fname = muonSFPath + "/" + muonPOGEras[era] + "/muon_Z.json.gz"
        self._corrName = f"NUM_{idName}ID_DEN_{den}"
        self._init = False

    def init(self):
        corrId = CorrectionlibFactory.loadCorrector(self._fname, self._corrName, fileHint=f"muonSF_{self.era}", corrHint=self.idName, check=True)[0]
        ROOT.gInterpreter.Declare('''
        ROOT::RVec<float> muonIDSF_<ID>_<ERA>(const ROOT::RVec<float> & pt, float ptMin, float ptMax, const ROOT::RVec<float> & eta, const std::string & choice = "sf") {
            ROOT::RVec<float> sf(pt.size(), 1.0);
            for (unsigned int i = 0, n = pt.size(); i < n; ++i) {
                double eta_i = std::min<double>(std::abs(eta[i]),2.3999);
                double pt_i = std::min(std::max(ptMin, pt[i]), ptMax);
                sf[i] = <CORRID>->evaluate({"<POGERA>", eta_i, pt_i, choice});
            }
            return sf;
        }
        ROOT::RVec<ROOT::RVec<float>> muonIDSF_<ID>_<ERA>_syst(const ROOT::RVec<float> & pt, float ptMin, float ptMax, const ROOT::RVec<float> & eta) {
            ROOT::RVec<ROOT::RVec<float>> sf(2);
            sf[0].resize(pt.size(), 1.0);
            sf[1].resize(pt.size(), 1.0);
            const std::string up = "systup", down = "systdown";
            for (unsigned int i = 0, n = pt.size(); i < n; ++i) {
                double eta_i = std::min<double>(std::abs(eta[i]),2.3999);
                double pt_i = std::min(std::max(ptMin, pt[i]), ptMax);
                sf[0][i] = <CORRID>->evaluate({"<POGERA>", eta_i, pt_i, down});
                sf[0][i] = <CORRID>->evaluate({"<POGERA>", eta_i, pt_i, up});
            }
            return sf;
        }
        '''.replace("<ID>", self.idName).replace("<ERA>", self.era).replace("<CORRID>", corrId).replace("<POGERA>", muonPOGEras[self.era]))
        self._init = True

    def _attach(self, rdf):
        if not self._init:
            self.init()
        try:
            rdf = rdf.Define(self.name, self.expr)
            if self.nuisName:
                rdf = rdf.Vary(self.name, self.expr.replace('(', '_syst('), variationTags=["down", "up"], variationName=self.nuisName)
            return rdf
        except BaseException:
            print(f"ERROR attaching Define({self.name}, {self.expr}")
            raise


class MuonIDIsoSFDefine(Define):
    def __init__(self, idName, isoName, era, onData=False, onDataDriven=False, den="genTracks", nuisName="CMS_eff_m", ptRange=(15, 249.999), **options):
        super().__init__(f'Muon_SF_{idName}Id_{isoName}Iso',
                         f'muonIDIsoSF_{idName}_{isoName}_{era}(Muon_pt, {ptRange[0]}, {ptRange[1]}, Muon_eta)',
                         onData=onData, onDataDriven=onDataDriven, **options)
        self.era = era
        self.idName = idName
        self.isoName = isoName
        self.nuisName = nuisName
        isoKind = "RelIso"  # to be changed for the HighPtID
        self._fname = muonSFPath + "/" + muonPOGEras[era] + "/muon_Z.json.gz"
        self._idCorrName = f"NUM_{idName}ID_DEN_{den}"
        self._isoCorrName = f"NUM_{isoName}{isoKind}_DEN_{idName}ID"
        self._init = False

    def init(self):
        corrId = CorrectionlibFactory.loadCorrector(self._fname, self._idCorrName, fileHint=f"muonSF_{self.era}", corrHint=self.idName, check=True)[0]
        corrIso = CorrectionlibFactory.loadCorrector(self._fname, self._isoCorrName, fileHint=f"muonSF_{self.era}", corrHint=self.isoName, check=True)[0]
        ROOT.gInterpreter.Declare('''
        ROOT::RVec<float> muonIDIsoSF_<ID>_<ISO>_<ERA>(const ROOT::RVec<float> & pt, float ptMin, float ptMax, const ROOT::RVec<float> & eta, const std::string & choice = "sf") {
            ROOT::RVec<float> sf(pt.size(), 1.0);
            for (unsigned int i = 0, n = pt.size(); i < n; ++i) {
                double eta_i = std::min<double>(std::abs(eta[i]),2.3999);
                double pt_i = std::min(std::max(ptMin, pt[i]), ptMax);
                sf[i] = <CORRID>->evaluate({"<POGERA>", eta_i, pt_i, choice}) * <CORRISO>->evaluate({"<POGERA>", eta_i, pt_i, choice});
            }
            return sf;
        }
        ROOT::RVec<ROOT::RVec<float>> muonIDIsoSF_<ID>_<ISO>_<ERA>_syst(const ROOT::RVec<float> & pt, float ptMin, float ptMax, const ROOT::RVec<float> & eta) {
            ROOT::RVec<ROOT::RVec<float>> sf(2);
            sf[0].resize(pt.size(), 1.0);
            sf[1].resize(pt.size(), 1.0);
            const std::string up = "systup", down = "systdown";
            for (unsigned int i = 0, n = pt.size(); i < n; ++i) {
                double eta_i = std::min<double>(std::abs(eta[i]),2.3999);
                double pt_i = std::min(std::max(ptMin, pt[i]), ptMax);
                sf[0][i] = <CORRID>->evaluate({"<POGERA>", eta_i, pt_i, down}) * <CORRISO>->evaluate({"<POGERA>", eta_i, pt_i, down});
                sf[1][i] = <CORRID>->evaluate({"<POGERA>", eta_i, pt_i, up}) * <CORRISO>->evaluate({"<POGERA>", eta_i, pt_i, up});
            }
            return sf;
        }
        '''.replace("<ID>", self.idName).replace("<ISO>", self.isoName).replace("<ERA>", self.era).replace("<CORRID>", corrId).replace("<CORRISO>", corrIso).replace("<POGERA>", muonPOGEras[self.era]))
        self._init = True

    def _attach(self, rdf):
        if not self._init:
            self.init()
        try:
            rdf = rdf.Define(self.name, self.expr)
            if self.nuisName:
                rdf = rdf.Vary(self.name, self.expr.replace('(', '_syst('), variationTags=["down", "up"], variationName=self.nuisName)
            return rdf
        except BaseException:
            print(f"ERROR attaching Define({self.name}, {self.expr}")
            raise


MuonSFs = dict()
for id in "Loose", "Medium", "MediumPrompt":
    for era in run2eras:
        MuonSFs[(f"{id}Id", era)] = MuonIDSFDefine(id, era)
    MuonSFs[f"{id}Id"] = [MuonIDSFDefine(id, era, eras=[era]) for era in run2eras]
    for iso in ("Loose", "Tight"):
        if iso == "Tight" and id == "Loose":
            continue
        for era in run2eras:
            MuonSFs[(f"{id}Id_{iso}Iso", era)] = MuonIDIsoSFDefine(id, iso, era)
        MuonSFs[f"{id}Id_{iso}Iso"] = [MuonIDIsoSFDefine(id, iso, era, eras=[era]) for era in run2eras]
