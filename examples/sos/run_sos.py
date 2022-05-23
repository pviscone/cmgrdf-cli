import os, ROOT
from CMGRDF import *
from CMGRDF.data import Source # stuff beyond the basics

os.environ["SOS_DATA_DIR"] = "/afs/cern.ch/work/g/gpetrucc/ttHH/CMSSW_10_6_30/src/CMGTools/TTHAnalysis/data/susySosSF"

ROOT.gInterpreter.ProcessLine('#include "functionsSOS.cc"')
ROOT.gInterpreter.ProcessLine('#include "functionsSF.cc"')

P0=localOrEOS("NanoTrees_SOS_070220_v6_skim_2lep_met125","/scratch/gpetrucc","/eos/cms/store/cmst3/group/tthlep/peruzzi/")
P=P0+"/{era}/{name}.root"
PF=[P0+"/{era}/recleaner/{name}_Friend.root"]
PFMC=PF+[P0+"/{era}/jetmetUncertainties/{name}_Friend.root",P0+"/{era}/bTagWeights/{name}_Friend.root"]

recleanerDefines = [
    ReDefine("nLepGood", "nLepFO_Recl"),
    Define("nLepTight", "nLepFO_Recl"),
    ReDefine("nLepGood","nLepFO_Recl"),
    ReDefine("nLepTight", "nLepTight_Recl"),
    Define("nTauFO", "nTauSel_Recl"),
    Define("nTauTight", "Sum(TauSel_Recl_idMVAoldDMdR032017v2>=4)"),
    Define("nJet25", "nJet25_Recl"),
    Define("htJet25j", "htJet25j_Recl"),
    Define("mhtJet25", "mhtJet25_Recl"),
    Define("nJet40", "nJet40_Recl"),
    Define("htJet40j", "htJet40j_Recl"),
    Define("mhtJet40", "mhtJet40_Recl"),
    Define("nFwdJet", "nFwdJet_Recl"),
    Define("nBJetLoose25", "nBJetLoose25_Recl"),
    Define("nBJetMedium25", "nBJetMedium25_Recl"),
    #Define("nBJetTight25", "nBJetTight25_Recl"),
    Define("nBJetLoose40", "nBJetLoose40_Recl"),
    Define("nBJetMedium40", "nBJetMedium40_Recl"),
    #Define("nBJetTight40", "nBJetTight40_Recl"),
    ReDefine("mZ1", "mZ1_Recl"),
    ReDefine("minMllAFAS", "minMllAFAS_Recl"),
    ReDefine("minMllAFOS", "minMllAFOS_Recl"),
    #ReDefine("minMllAFSS", "minMllAFSS_Recl"),
    ReDefine("minMllSFOS", "minMllSFOS_Recl"),
]
for i in range(3):
   recleanerDefines += [ Define("LepGood%d_isLepTight" % (i+1), "LepGood_isLepTight_Recl[iLepFO_Recl[%d]]"%i) ]
   for var in "pt","eta","phi","mass","pdgId":
       recleanerDefines += [ Define("LepGood%d_%s" % (i+1,var), "LepGood_%s[iLepFO_Recl[%d]]"%(var,i)) ]
for i in range(1):
    for var in "jetId",:
        recleanerDefines += [ Define("JetSel%d_%s" % (i+1,var), "JetSel_Recl_%s[%d]"%(var,i)) ]

branchDefaults = [
    DefineDefault("Flag_ecalBadCalibFilterV2","1"),
    DefineDefault("HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ","0"),
    DefineDefault("HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ","0"),
    DefineDefault("HLT_DoubleMu3_PFMET50","0"),
    DefineDefault("HLT_PFMETNoMu120_PFMHTNoMu120_IDTight","0"),
    DefineDefault("HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8","0"),
    DefineDefault("HLT_DoubleMu3_DZ_PFMET50_PFMHT60","0"),
    DefineDefault("HLT_PFMETNoMu120_PFMHTNoMu120_IDTight_PFHT60","0"),
    DefineDefault("HLT_PFMETNoMu120_PFMHTNoMu120_IDTight","0"),
    DefineDefault("L1PreFiringWeight_Nom","1"),
]
eventFilterDefines = [
    Define("EventFilters", "Flag_goodVertices>=1 && Flag_globalSuperTightHalo2016Filter>=1 && Flag_HBHENoiseFilter>=1 && Flag_HBHENoiseIsoFilter>=1 && Flag_EcalDeadCellTriggerPrimitiveFilter>=1 && Flag_BadPFMuonFilter>=1 && Flag_ecalBadCalibFilterV2>=1"),
    Define("HLT_MuMu16", "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ || HLT_Mu17_TrkIsoVVL_TkMu8_TrkIsoVVL_DZ"),
    Define("HLT_MuMuMET16", "HLT_DoubleMu3_PFMET50"),
    Define("HLT_HighMET16", "HLT_PFMETNoMu120_PFMHTNoMu120_IDTight"),
    Define("HLT_MuMu", "HLT_Mu17_TrkIsoVVL_Mu8_TrkIsoVVL_DZ_Mass3p8"),
    Define("HLT_MuMuMET", "HLT_DoubleMu3_DZ_PFMET50_PFMHT60"),
    Define("HLT_HighMET", "HLT_PFMETNoMu120_PFMHTNoMu120_IDTight_PFHT60 || HLT_PFMETNoMu120_PFMHTNoMu120_IDTight"),
    Define("PrefireWeight","L1PreFiringWeight_Nom"),
]

### MET in MC
metFixes = [
    ReDefine("MET_pt_jesTotalUp","METFixEE2017_pt_jesTotalUp ",eras=[2017], onData=False, onDataDriven=False),
    ReDefine("MET_pt_jesTotalDown","METFixEE2017_pt_jesTotalDown ",eras=[2017], onData=False, onDataDriven=False),
    ReDefine("MET_phi_jesTotalUp","METFixEE2017_phi_jesTotalUp ",eras=[2017], onData=False, onDataDriven=False),
    ReDefine("MET_phi_jesTotalDown","METFixEE2017_phi_jesTotalDown ",eras=[2017], onData=False, onDataDriven=False),
    ReDefine("MET_pt_jerUp","METFixEE2017_pt_jerUp ",eras=[2017], onData=False, onDataDriven=False),
    ReDefine("MET_pt_jerDown","METFixEE2017_pt_jerDown ",eras=[2017], onData=False, onDataDriven=False),
    ReDefine("MET_phi_jerUp","METFixEE2017_phi_jerUp ",eras=[2017], onData=False, onDataDriven=False),
    ReDefine("MET_phi_jerDown","METFixEE2017_phi_jerDown ",eras=[2017], onData=False, onDataDriven=False),
    ReDefine("MET_pt","MET_pt_jer ",eras=[2016], onData=False, onDataDriven=False),
    ReDefine("MET_pt","METFixEE2017_pt_jer ",eras=[2017], onData=False, onDataDriven=False),
    ReDefine("MET_pt","MET_pt_jer ",eras=[2018], onData=False, onDataDriven=False),
    ReDefine("MET_phi","MET_phi_jer ",eras=[2016], onData=False, onDataDriven=False),
    ReDefine("MET_phi","METFixEE2017_phi_jer ",eras=[2017], onData=False, onDataDriven=False),
    ReDefine("MET_phi","MET_phi_jer ",eras=[2018], onData=False, onDataDriven=False),
    ReDefine("MET_pt","METFixEE2017_pt ",eras=[2017], onMC=False),
    ReDefine("MET_phi","METFixEE2017_phi ",eras=[2017], onMC=False),
]

preSelection = [ 
    Cut("eventFilters", "EventFilters", onMC=False),
    AddWeight("puWeight","puWeight"),
    AddWeight("eventBTagSF","eventBTagSF"),
    Cut("dilep", "nLepGood == 2"),
    Cut("sublepPt", "(abs(LepGood2_pdgId)==13 && LepGood2_pt > 3.5) || (abs(LepGood2_pdgId)==11 && LepGood2_pt > 5)"),
    Define("mll","mass_2(LepGood1_pt, LepGood1_eta, LepGood1_phi, LepGood1_mass, LepGood2_pt, LepGood2_eta, LepGood2_phi, LepGood2_mass)"),
    Define("ptll","pt_2(LepGood1_pt, LepGood1_phi, LepGood2_pt, LepGood2_phi)"),
    Define("metmm12", "metmm_pt(LepGood1_pdgId, LepGood1_pt, LepGood1_phi, LepGood2_pdgId, LepGood2_pt, LepGood2_phi, MET_pt, MET_phi)"),
    Define("mT1", "mt_2(LepGood1_pt, LepGood1_phi, MET_pt, MET_phi)"),
    Define("mT2", "mt_2(LepGood2_pt, LepGood2_phi, MET_pt, MET_phi)"),
    Define("mtautau12", "mass_tautau(MET_pt,MET_phi,LepGood1_pt,LepGood1_eta,LepGood1_phi,LepGood2_pt,LepGood2_eta,LepGood2_phi)"),
    Cut("upsilonVeto", "mll < 9 || mll > 10.5"),
    Cut("dilepPt", "ptll > 3 "),
    Cut("ISRjet", "JetSel1_jetId >= 4"),
    Cut("METoverHT", "(MET_pt/htJet25j)>(2./3.) && (MET_pt/htJet25j) < 1.4"),
    Cut("minHT", "htJet25j > 100")
 ] #)

metCutsMap = dict([(c.name,c) for c in [
    ##### Triggers and Binning
    ### Low MET
    Cut("metlow", "MET_pt > 125 && metmm12 > 125  && metmm12 < 200"),
    Cut("metlow_trig", "(year==2016 && HLT_MuMuMET16) || ( (year==2017 || year==2018) && HLT_MuMuMET )"),
    ####### Med MET	
    Cut("metmed", "metmm12 > 200 && metmm12 < 240"),
    Cut("metmed_CR", "metmm12 > 200"),
    Cut("metmed_AR", "$DATA{metmm12 > 200 && metmm12 < 240} $MC{EWK_MCMetBoundMed}"),
    Cut("metmed_col", "metmm12 > 200 && metmm12 < 290"),
    Cut("metmed_trig", "(year==2016 && HLT_HighMET16) || ( (year==2017 || year==2018) && HLT_HighMET )"),
    ### High MET
    Cut("methigh", "metmm12 > 240 && metmm12 < 290"),
    Cut("methigh_AR", "$DATA{metmm12 > 240 && metmm12 < 290} $MC{EWK_MCMetBoundHigh}"),
    Cut("methigh_col", "metmm12 > 290 && metmm12 < 340"),
    Cut("methigh_trig", "(year==2016 && HLT_HighMET16) || ( (year==2017 || year==2018) && HLT_HighMET )"),
    ### Ultra MET
    Cut("metultra", "metmm12 > 290"),
    Cut("metultra_AR", "$DATA{metmm12 > 290} $MC{EWK_MCMetBoundUltra}"),
    Cut("metultra_col", "metmm12 > 340"),
    Cut("metultra_trig", "(year==2016 && HLT_HighMET16) || ( (year==2017 || year==2018) && HLT_HighMET )"),
    ###Inclusive in MET
    Cut("inclMET_2l", "(MET_pt > 125 && metmm12 > 125 && metmm12 < 200 && ((year==2016 && HLT_MuMuMET16) || ( (year==2017 || year==2018) && HLT_MuMuMET )) && (abs(LepGood1_pdgId)==13 && abs(LepGood2_pdgId)==13)) || (metmm12 > 200 && ((year==2016 && HLT_HighMET16) || ( (year==2017 || year==2018) && HLT_HighMET )))"),
]])

srCuts = [
    AddWeight("triggerSF12", "triggerSF(muDleg_SF(year,LepGood1_pt,LepGood1_eta,LepGood2_pt,LepGood2_eta), MET_pt, metmm12, year)"),
    AddWeight("lepSF12", "lepSF(LepGood1_pt,LepGood1_eta,LepGood1_pdgId,year)*lepSF(LepGood2_pt,LepGood2_eta,LepGood2_pdgId,year)"),
    Cut("OS", "LepGood1_pdgId*LepGood2_pdgId<0"),
    Cut("twoTight", "LepGood1_isLepTight && LepGood2_isLepTight"),
    Cut("bveto", "nBJetMedium25 == 0"),
    Cut("mtautau", "0.0 > mtautau12 || mtautau12 > 160.0"),
    Cut("mT", "mT1 < 70. && mT2 < 70.0"),
    Cut("SF", "abs(LepGood1_pdgId*LepGood2_pdgId)==169 || abs(LepGood1_pdgId*LepGood2_pdgId)==121"),
    Cut("mll_low", "mll > 1 && mll < 50"),
    Cut("JPsiVeto", "mll < 3 || mll > 3.2"),
    Cut("ledlepPt3p5", "((abs(LepGood1_pdgId)==13 && LepGood1_pt > 3.5) || (abs(LepGood1_pdgId)==11 && LepGood1_pt > 5))  && LepGood1_pt < 30.0"),
    Cut("mindR", "deltaR(LepGood1_eta, LepGood1_phi, LepGood2_eta,LepGood2_phi)>0.3"),
]

controlRegions = dict(
    cr_dy=dict(disable=["ledlepPt"], invert=["mtautau"], add=[
                Cut("CRDYledlepPt", "5.0 < LepGood1_pt")]),
    cr_tt=dict(disable=["ledlepPt","bveto","mT"], invert=[], add=[     
                Cut("CRTTledlepPt", "5.0 < LepGood1_pt"),
                Cut("btag", "nBJetMedium25 > 0")]),
    cr_vv=dict(disable=["ledlepPt","mT"], invert=[], add=[     
                Cut("CRVVledlepPt", "30.0 < LepGood1_pt"),
                Cut("CRVVbveto", "nBJetLoose25 == 0"),
                Cut("CRVVmT", "mT1 > 90. || mT2 > 90.0")]),
    cr_ss0=dict(disable=["pt5sublep","mT"],invert=["OS"], add=[
                Cut("1LNT", "LepGood1_isLepTight+LepGood2_isLepTight==0")]),
    cr_ss1=dict(disable=["pt5sublep","mT"],invert=["OS"], add=[
                Cut("2LNT", "LepGood1_isLepTight+LepGood2_isLepTight==1")]),

)


others = [ 
    Cut("mllcut", "mll > 4 && mll < 50"), 
    Cut("ledlepPt", "5.0 < LepGood1_pt && LepGood1_pt < 30.0"),
    Cut("CRDYledlepPt_low", "((abs(LepGood1_pdgId)==13 && LepGood1_pt > 3.5) || (abs(LepGood1_pdgId)==11 && LepGood1_pt > 5))"),
    Cut("CRTTledlepPt_low", "((abs(LepGood1_pdgId)==13 && LepGood1_pt > 3.5) || (abs(LepGood1_pdgId)==11 && LepGood1_pt > 5))"),
    Cut("mm", "abs(LepGood1_pdgId)==13 && abs(LepGood2_pdgId)==13"),
    Cut("pt5sublep", "(fabs(LepGood2_pdgId)==13 && LepGood2_pt > 5) || (fabs(LepGood2_pdgId)==11 && LepGood2_pt > 5)"),
]


commonSteps = recleanerDefines + branchDefaults + eventFilterDefines + metFixes
flow_SR = dict( (met,Flow(f"SR{met}", commonSteps + preSelection + [metCutsMap[f"met{met}"],metCutsMap[f"met{met}_trig"]] + srCuts)) for met in ("med","high",) )

TruthMatchedLeptons = Insert(Cut("mcTrue","LepGood_mcMatchId[iLepFO_Recl[0]] != 0 && LepGood_mcMatchId[iLepFO_Recl[1]] != 0"), after="dilep")
FakeMatchedLeptons = Insert(Cut("mcTrue","||".join(f"(LepGood_mcMatchId[iLepFO_Recl[{i}]] == 0 && LepGood_mcPromptGamma[iLepFO_Recl[{i}]] == 0)" for i in (0,1))), after="dilep")

def makeMCs(names,hooks,eras=[2016,2017,2018]):
    ret = []
    if type(names) == str:
        names = [ str ]
    for name in names:
        if type(name) == tuple: # name & eras
            ret += makeMCs([name[0]], hooks, eras=[*name[1:]])
        elif type(name) == list: 
            ret += makeMCs(name, hooks, eras=eras)
        else:
            ret.append( MCSample(name, P, friends=PFMC, xsec="xsec", eras=eras, hooks=hooks) )
    return ret
def makePrompt(names,eras=[2016,2017,2018]):
    return makeMCs(names,[TruthMatchedLeptons],eras=eras)
def makeFakes(names,eras=[2016,2017,2018]):
    return makeMCs(names,[FakeMatchedLeptons],eras=eras)

def makeBins(edges,to="to"):
    return ["%sto%s" % (edges[i-1],edges[i]) for i in range(1,len(edges))]
def makeWJ(hooks=[FakeMatchedLeptons], years=[2016,2017,2018]):
    WJbins = makeBins([100,200,400,600,800,1200,2500,"Inf"])
    return [MCSample("WJetsToLNu_HT%s" % s, P, friends=PFMC, xsec="xsec", eras=years, hooks=hooks) for s in WJbins]
def makeDYs(hooks,years=[2016,2017,2018]):
    ret = []
    for year in years:
        lowM = 4 if year != 2016 else 5
        DYlow  = makeBins([70,100,200,400,600,"Inf"])
        DYmid  = makeBins([70,100,200,400,600,"Inf"])[(0 if year == 2018 else 1):]
        DYhigh = makeBins([70,100,200,400,600,800,1200,2500,"Inf"])[(0 if year == 2016 else 1):]
        bins  = [f"M1to{lowM}_HT{ht}" for ht in DYlow]
        bins += [f"M{lowM}to50_HT{ht}" for ht in DYmid]
        bins += [f"M50_HT{ht}" for ht in DYhigh]
        for b in bins:
            name = "DYJetsToLL_"+b
            ret.append(MCSample(name, P, friends=PFMC, xsec="xsec", eras=[year], hooks=hooks))
    return ret

TT2l = ["TTJets_DiLepton"]
TT1l = ["TTJets_SingleLeptonFromT","TTJets_SingleLeptonFromTbar"]
TW = ["T_tWch_noFullyHad","TBar_tWch_noFullyHad"]
T = ["T_sch_lep","T_tch","TBar_tch"]
WZ = ["WZTo3LNu_mllmin01"]
VVp = [ "ZZTo2L2Q", "ZZTo2L2Q", "ZZTo4L_M1toInf", "VVTo2L2Nu_M1toInf", "WpWpJJ", ("WWDoubleTo2L",2016), ("WW_DPS",2017,2018) ]
VVf = [ "WWToLNuQQ", ("WZTo1L1Nu2Q",2016,2017) ]
TTW = [ ("TTWToLNu_fxfx",2018),("TTWToLNu",2016) ]
TTZ = [ ("TTZToLLNuNu_amc",2017,2018),("TTZToLLNuNu",2016),"TTZToLLNuNu_m1to10"]
Rares  = [ "TZQToLL","tWll","WWW_ll","WWZ","WZZ","ZZZ"]

def makeData(pds,processing,years=[2016,2017,2018]):
    eras = {2016:"BCDEFGH",2017:"BCDEF",2018:"ABCD"}
    return [DataSample(f"{pd}_Run{y}{l}_{processing}", P, friends=PF, eras=[y]) for pd in pds for y in years for l in eras[y]]
def makeGData(pds,processing,years=[2016,2017,2018]):
    eras = {2016:"BCDEFGH",2017:"BCDEF",2018:"ABCD"}
    sources = dict()
    for y in years:
        files = [ P.format(name=f"{pd}_Run{y}{l}_{processing}", era=y) for pd in pds for l in eras[y] ]
        friends = [ [ F.format(name=f"{pd}_Run{y}{l}_{processing}", era=y) for pd in pds for l in eras[y] ] for F in PF ]
        name = "Data_Run%d%s_%s"%(y,eras[y],processing)
        sources[y] = Source(name, files, era=y, friends=friends)
    return [DataSample("Data_"+processing, sources, eras=years)]

data = dict(
    prompt = [
        Process("TT", makePrompt(TT2l), label="t#bar{t} (2l)", fillColor=ROOT.kBlue-7),
        Process("DY", MCGroup("DY",makeDYs([TruthMatchedLeptons])), label="DY", fillColor=ROOT.kCyan),
        Process("WZ", makePrompt(WZ), label="WZ", fillColor=ROOT.kGreen+1),
        Process("VV", makePrompt(VVp), label="VV", fillColor=ROOT.kViolet-4),
        Process("Rares", [MCGroup("Rares",makePrompt(TW+TTW+TTZ+Rares)),
                          *makePrompt(TT1l)], label="Rares", fillColor=ROOT.kViolet-4),
    ],
    mcfakes = [
        Process("Fakes_dy", MCGroup("DY",makeDYs([FakeMatchedLeptons])), label="DY(fakes)", fillColor=ROOT.kBlack),
        Process("Fakes_Wj", MCGroup("WJ",makeWJ()), label="Wj(fakes)", fillColor=ROOT.kGray),
        Process("Fakes_tt", makeFakes(TT2l+TT1l), label="t#bar{t}(fakes)", fillColor=ROOT.kGray+1),
        Process("Fakes_t",  makeFakes(TW+T), label="t(fakes)", fillColor=ROOT.kGray+2),
        Process("Fakes_vv", makeFakes(VVf), label="VV(fakes)", fillColor=ROOT.kGray+3),
    ],
    ddfakes = [
    ],
    data = [
        Data(makeGData(("DoubleMuon", "MET"),"25Oct2019"))
             #[DataSample(f"{pd}_Run2016{l}_25Oct2019", P, friends=PF, eras=[2016]) for pd in ("DoubleMuon", "MET") for l in "BCDEFGH"] +
             #[DataSample(f"{pd}_Run2017{l}_25Oct2019", P, friends=PF, eras=[2017]) for pd in ("DoubleMuon", "MET") for l in "BCDEF"] +
             #[DataSample(f"{pd}_Run2018{l}_25Oct2019", P, friends=PF, eras=[2018]) for pd in ("DoubleMuon", "MET") for l in "ABCD"])
    ]
)


plots = [ 
    Plot("yields", "1", (1,-0.5,0.5), xTitle="Total Event Yields"),
    Plot("SR_2l_ewk", "mll", [1,4,10,20,30,50], xTitle="#it{M(ll)} [GeV]", yTitle="Number of Events", legend='TL', legendCutoff=1e-3, moreY=1.8),
]

lumi = {2017:41.5, 2018:59.7}

ROOT.EnableImplicitMT(16)
maker = PlotMaker()
#verbosity = ROOT.Experimental.RLogScopedVerbosity(ROOT.Detail.RDF.RDFLogChannel(), ROOT.Experimental.ELogLevel.kInfo)
maker.book(data["prompt"]+data["mcfakes"]+data["data"],lumi,flow_SR["med"],plots,eras=[2018],taskName="mcFakes")
result_plots = maker.runAll()
printer = PlotSetPrinter(topRightText="L = %.0f fb^{-1} (13 TeV)"%lumi[2018], showRatio=True, showErrors=True)
printer.printSet(result_plots, "../plots/003/sos/cmgrdf/{era}/{flow}_{taskName}")