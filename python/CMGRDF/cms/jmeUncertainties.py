import ROOT

from CMGRDF.flow import Define, Cut
from CMSJMECalculators import loadJMESystematicsCalculators
loadJMESystematicsCalculators()
from CMSJMECalculators import config as calcConfigs
from CMGRDF.CorrectionlibFactory import CorrectionlibFactory

jecTags = {
    '2016': 'Summer19UL16_V7_MC',
    '2016APV': 'Summer19UL16APV_V7_MC',
    '2017': 'Summer19UL17_V5_MC',
    '2018': 'Summer19UL18_V5_MC',
    '2022': 'Summer22_22Sep2023_V2_MC',
    '2022EE': 'Summer22EE_22Sep2023_V2_MC',
}

jecTagsDATA = {
    "2022C": "Summer22_22Sep2023_RunCD_V2_DATA",
    "2022D": "Summer22_22Sep2023_RunCD_V2_DATA",
    "2022EEE": "Summer22EE_22Sep2023_RunE_V2_DATA",
    "2022EEF": "Summer22EE_22Sep2023_RunF_V2_DATA",
    "2022EEG": "Summer22EE_22Sep2023_RunG_V2_DATA",
    '2016APVB': 'Summer19UL16APV_RunBCD_V7_DATA',
    '2016APVC': 'Summer19UL16APV_RunBCD_V7_DATA',
    '2016APVD': 'Summer19UL16APV_RunBCD_V7_DATA',
    '2016APVE': 'Summer19UL16APV_RunEF_V7_DATA',
    '2016APVF': 'Summer19UL16APV_RunEF_V7_DATA',
    '2016F': 'Summer19UL16_RunFGH_V7_DATA',
    '2016G': 'Summer19UL16_RunFGH_V7_DATA',
    '2016H': 'Summer19UL16_RunFGH_V7_DATA',
    '2017B': 'Summer19UL17_RunB_V5_DATA',
    '2017C': 'Summer19UL17_RunC_V5_DATA',
    '2017D': 'Summer19UL17_RunD_V5_DATA',
    '2017E': 'Summer19UL17_RunE_V5_DATA',
    '2017F': 'Summer19UL17_RunF_V5_DATA',
    '2018A': 'Summer19UL18_RunA_V5_DATA',
    '2018B': 'Summer19UL18_RunB_V5_DATA',
    '2018C': 'Summer19UL18_RunC_V5_DATA',
    '2018D': 'Summer19UL18_RunD_V5_DATA',
}


jerTags = {
    '2016APV'  : 'Summer20UL16APV_JRV3_MC',
    '2016'     : 'Summer20UL16_JRV3_MC',
    '2017'     : 'Summer19UL17_JRV2_MC',
    '2018'     : 'Summer19UL18_JRV2_MC',
    '2022'     : 'Summer22_22Sep2023_JRV1_MC',
    '2022EE'   : 'Summer22EE_22Sep2023_JRV1_MC'
}

jsonMap = {
    "2022EE" : "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/2022_Summer22EE/",
    "2022"   : "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/2022_Summer22/",
    "2018"   : "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/2018_UL/",
    "2017"   : "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/2017_UL/",
    "2016"   : "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/2016postVFP_UL/",
    "2016APV": "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/2016preVFP_UL/"

}


jetVetoTags = {
    "2022"   : "Summer22_23Sep2023_RunCD_V1",
    "2022EE" : "Summer22EE_23Sep2023_RunEFG_V1",
}


class JMEFactory(object):
    _ids = dict()

    @classmethod
    def loadJME(cls, doMET, era, subera, jetAlgo, isData, splitJER, uncSources, suffix):
        configCls = calcConfigs.METVariations if doMET else calcConfigs.JetVariations
        config = configCls(jsonMap[era] + "/jet_jerc.json.gz", jetAlgo)
        config.jecTag = jecTagsDATA[era + subera] if isData else jecTags[era]
        config.jecLevel = "L1L2L3Res"
        config.splitJER = splitJER

        if not isData:
            config.jesUncertainties = uncSources
            config.jerTag = jerTags[era]
            config.jsonFileSmearingTool = "/cvmfs/cms.cern.ch/rsync/cms-nanoAOD/jsonpog-integration/POG/JME/jer_smear.json.gz"
            if doMET:
                config.isT1SmearedMET = True

        declareexpr = f"{config.calcClass} cmgJMECalc{suffix} = {config.cppConstruct};"
        if f'cmgJMECalc{suffix}' in cls._ids:
            if cls._ids[f'cmgJMECalc{suffix}'] != declareexpr:
                raise RuntimeError(f"You have tried to declare two different objects with same cmgJMECalc{suffix}. You have to change the code logic")
        else:
            ROOT.gInterpreter.Declare(declareexpr)
            cls._ids[f'cmgJMECalc{suffix}'] = declareexpr


class JMEUncertaintiesDefine(Define):
    def __init__(self, splitJER=False, uncSources=["Total"], doMET=True,
                 jetAlgo="AK4PFPuppi", metcollection="PuppiMET", doSyst=False, suffix="", **options):

        if len(options['eras']) != 1:
            raise RuntimeError("You cannot only call JMEUncertaintiesDefine for one era")
        self.era = options['eras'][0]

        if 'suberas' not in options:
            self.subera = ""
        elif len(options['suberas']) != 1:
            raise RuntimeError("You cannot call JMEUncertaintiesDefine for more than one subera")
        else:
            self.subera = options['suberas'][0]

        if options['onMC'] and options['onData']:
            raise RuntimeError("JMEUncertaintiesDefine cannot be called both in MC and data mode")

        if doMET:
            super().__init__(f"{metcollection}_T1",
                             f'''cmgJMECalc{suffix}_MET.produce(Jet_pt, Jet_eta, Jet_phi, Jet_mass,
                             Jet_rawFactor, Jet_area,Jet_muonSubtrFactor,
                             Jet_neEmEF,Jet_chEmEF, Jet_jetId,
                             Rho_fixedGridRhoFastjetAll,
                             Jet_genJetIdx,
                             Jet_partonFlavour,
                             42,
                             GenJet_pt, GenJet_eta, GenJet_phi,GenJet_mass,
                             Raw{metcollection}_phi, Raw{metcollection}_pt,
                             CorrT1METJet_rawPt, CorrT1METJet_eta, CorrT1METJet_phi, CorrT1METJet_area,
                             CorrT1METJet_muonSubtrFactor, CorrT1METJet_neEmEF, CorrT1METJet_chEmEF,
                             {metcollection}_MetUnclustEnUpDeltaX,
                             {metcollection}_MetUnclustEnUpDeltaY)''',
                             **options)
        else:
            super().__init__("ak4JetVars",
                             f'''cmgJMECalc{suffix}.produce(Jet_pt, Jet_eta, Jet_phi, Jet_mass,
                             Jet_rawFactor, Jet_area,
                             Jet_jetId, Rho_fixedGridRhoFastjetAll,
                             Jet_genJetIdx,
                             Jet_partonFlavour,
                             42,
                             GenJet_pt, GenJet_eta, GenJet_phi,GenJet_mass)''',
                             **options)

        self._init = False
        self.splitJER = splitJER
        self.uncSources = uncSources
        self.doMET = doMET
        self.jetAlgo = jetAlgo
        self.suffix = suffix + ("_MET" if self.doMET else "")
        self.doSyst = doSyst
        self.metcollection = metcollection

    def init(self):

        JMEFactory.loadJME(self.doMET, self.era, self.subera, self.jetAlgo, self.onData, self.splitJER, self.uncSources, self.suffix)
        self._init = True

    def _attach(self, rdf) :
        if not self._init:
            self.init()

        try:
            rdf = rdf.Define(self.name, self.expr)
            if self.doMET:
                rdf = rdf.Redefine(f"{self.metcollection}_pt", f"{self.metcollection}_T1.pt(0)")
                rdf = rdf.Redefine(f"{self.metcollection}_phi", f"{self.metcollection}_T1.phi(0)")

                if self.doSyst:
                    for obs in ["pt", "phi"]:
                        njer = 1 if not self.splitJER else 6
                        for ijer in range(njer):
                            rdf = rdf.Vary(f"{self.metcollection}_{obs}", f"ROOT::RVecD({{ {self.metcollection}_T1.{obs}(%d), {self.metcollection}_T1.{obs}(%d)}})" % (2 * ijer + 1, 2 * ijer + 2),
                                           variationTags=["up", "down"], variationName="CMS_res_j_%s_%s" % (ijer, self.era))
                        for isource, source in enumerate(self.uncSources):
                            rdf = rdf.Vary(f"{self.metcollection}_{obs}", f"ROOT::RVecD({{ {self.metcollection}_T1.{obs}(%d), {self.metcollection}_T1.{obs}(%d)}})" % (2 * isource + 2 * njer + 1, 2 * isource + 2 * njer + 2),
                                           variationTags=["up", "down"], variationName="CMS_scale_j_%s" % source)
                        rdf = rdf.Vary(f"{self.metcollection}_{obs}", f"ROOT::RVecD({{ {self.metcollection}_T1.{obs}(%d), {self.metcollection}_T1.{obs}(%d)}})" % (1 + 2 * njer + 2 * len(self.uncSources), 2 + 2 * njer + 2 * len(self.uncSources)),
                                       variationTags=["up", "down"], variationName="Uncl")
            else:
                rdf = rdf.Redefine("Jet_pt", "ak4JetVars.pt(0)")
                if self.doSyst:
                    njer = 1 if not self.splitJER else 6
                    for ijer in range(njer):
                        rdf = rdf.Vary("Jet_pt", "ROOT::VecOps::RVec<ROOT::VecOps::RVec<float>>({ ak4JetVars.pt(%d), ak4JetVars.pt(%d)})" % (2 * ijer + 1, 2 * ijer + 2),
                                       variationTags=["up", "down"], variationName="CMS_res_j_%s_%s" % (ijer, self.era))
                    for isource, source in enumerate(self.uncSources):
                        rdf = rdf.Vary("Jet_pt", "ROOT::VecOps::RVec<ROOT::VecOps::RVec<float>>({ ak4JetVars.pt(%d), ak4JetVars.pt(%d)})" % (2 * isource + 2 * njer + 1, 2 * isource + 2 * njer + 2),
                                       variationTags=["up", "down"], variationName="CMS_scale_j_%s" % source)
            return rdf

        except BaseException:
            print(f"ERROR attaching Define({self.name}, {self.expr}")
            raise


class JetVetoMapCut(Cut):
    def __init__(self, cutName, **options):
        if len(options['eras']) != 1:
            raise RuntimeError("You can only call JetVetoMapCut for one era")
        self.era = options['eras'][0]

        super().__init__(cutName, f"passesJetVetoMap_{self.era}( Jet_pt, Jet_eta, Jet_phi, Jet_jetId, Jet_neEmEF, Jet_neHEF, Muon_eta, Muon_phi, Muon_isPFcand)", **options)

        self._fname = jsonMap[self.era] + '/jetvetomaps.json.gz'
        self._corrName = jetVetoTags[self.era]
        self._init = False

    def init(self):
        vetoMapId = CorrectionlibFactory.loadCorrector(self._fname, self._corrName, check=True)[0]
        ROOT.gInterpreter.Declare('''bool passesJetVetoMap_<era>( const ROOT::RVec<float> & Jet_pt, const ROOT::RVec<float> & Jet_eta,
                                                                  const ROOT::RVec<float> & Jet_phi, const ROOT::RVec<int> & Jet_jetId,
                                                                  const ROOT::RVec<float> & Jet_neEmEF, const ROOT::RVec<float> & Jet_neHEF,
                                                                  const ROOT::RVec<float> & Muon_eta, const ROOT::RVec<float> & Muon_phi, const ROOT::RVec<int> & Muon_isPFcand){
        bool ret=true;
        for (int ijet=0; ijet<Jet_pt.size(); ++ijet){
             if (<correctionname>->evaluate({"jetvetomap", TMath::Max( -5.0f, TMath::Min(5.0f, Jet_eta.at(ijet))), TMath::Max( -3.14f, TMath::Min(3.14f, Jet_phi.at(ijet)))}) == 0) continue;
             if (Jet_pt.at(ijet) < 15.) continue;
             if (Jet_jetId.at(ijet) < 2) continue;
             if (Jet_neEmEF.at(ijet)+Jet_neHEF.at(ijet) > 0.9) continue;
             bool overlaps=false;
             for (int imuo=0; imuo<Muon_eta.size(); ++imuo){ // see if it overlaps with a PF muon
                 if ( deltaR2(Muon_eta.at(imuo), Muon_phi.at(imuo), Jet_eta.at(ijet), Jet_phi.at(ijet)) > 0.04) continue;
                 if ( !Muon_isPFcand.at(imuo) ) continue;
                 overlaps=true;
                 break;
             }
             if (!overlaps) ret=false;
             if (!ret) break;
        }
        return ret;
}'''.replace("<era>", self.era).replace("<correctionname>", vetoMapId))
        self._init = True

    def _attach(self, rdf):
        if not self._init:
            self.init()
        return super()._attach(rdf)


class JetPuIDSF(Define):
    def __init__(self, WP="L", jetCol="Jet", doSyst=True, onData=False, onDataDriven=False, **options):

        if len(options['eras']) != 1:
            raise RuntimeError("You can only call JetPuIDSF for one era")
        self.era = options['eras'][0]

        super().__init__('weight_jetPUId',
                         f'weight_jetPUId_{self.era}({jetCol}_pt, {jetCol}_eta, {jetCol}_genJetIdx, "{WP}")',
                         onData=onData, onDataDriven=onDataDriven, **options)

        self._fname = jsonMap[self.era] + '/jmar.json.gz'
        self._corrName = "PUJetID_eff"
        self._init = False
        self.doSyst = doSyst

    def init(self):
        corrId = CorrectionlibFactory.loadCorrector(self._fname, self._corrName, check=True)[0]
        ROOT.gInterpreter.Declare('''
        double weight_jetPUId_<ERA>(const ROOT::RVec<float> & pt, const ROOT::RVec<float> & eta, const ROOT::RVec<int> & idx, const std::string & wp, const std::string & choice = "nom") {
        double ret=1.;
        for (unsigned int i = 0, n = pt.size(); i < n; ++i) {
            if ( (idx.at(i) < 0) || (pt.at(i) > 50)) continue;
            ret *= <CORRID>->evaluate({eta.at(i), pt.at(i), choice, wp});
        }
        return ret;
     }'''.replace("<CORRID>", corrId).replace("<ERA>", self.era))
        self._init = True

    def _attach(self, rdf):
        if not self._init:
            self.init()

        try:
            rdf = rdf.Define(self.name, self.expr)
            if self.doSyst:
                up_expr = self.expr.replace(')', ', "up")')
                dn_expr = self.expr.replace(')', ', "down")')
                rdf = rdf.Vary(self.name, f"ROOT::RVecD( {{{up_expr}, {dn_expr}}})",
                               variationTags=["up", "down"], variationName=f"CMS_eff_j_PUJET_id_{self.era}")
            return rdf
        except BaseException:
            print(f"ERROR attaching Define({self.name}, {self.expr}")
            raise
