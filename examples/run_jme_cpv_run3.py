from CMGRDF import *
from CMGRDF.collectionUtils import *
from CMGRDF.cms.jmeUncertainties import JMEUncertaintiesDefine, JetVetoMapCut
from CMGRDF.cms.eras import run3eras, suberas_perera, lumis, lumiUncertainties
from CMGRDF.stat import DatacardWriter

P = "root://eoscms.cern.ch//eos/cms/store/cmst3/group/tthlep/sesanche/NanoTrees_forCMGRDF_100524_summerstudent/{era}/{name}.root"

jet_run3 = "AK4PFPuppi"
met_run3 = "PuppiMET"

# first we hardcode some variable to zero (as done in nanoaodtools, until these inputs are added to nano)
jme_sequences = [Define(f'CorrT1METJet_{var}', '0.0*CorrT1METJet_rawPt') for var in ['neEmEF', 'chEmEF']]

# then, data needs dummy variables to prevent the thing from crashing
jme_sequences.extend([Define(f"GenJet_{var}", "0*Jet_pt-99.", onMC=False) for var in ['pt', 'eta', 'phi', 'mass']])
jme_sequences.extend([Define(f"Jet_{var}", "0*Jet_pt -99.", onMC=False) for var in ['partonFlavour', 'genJetIdx']])

# run3 samples have uncl variations stored differently :)
jme_sequences.append(Define(f"{met_run3}_MetUnclustEnUpDeltaX", f"{met_run3}_ptUnclusteredUp*TMath::Cos({met_run3}_phiUnclusteredUp)-{met_run3}_pt*TMath::Cos({met_run3}_phi)", eras=run3eras))
jme_sequences.append(Define(f"{met_run3}_MetUnclustEnUpDeltaY", f"{met_run3}_ptUnclusteredUp*TMath::Sin({met_run3}_phiUnclusteredUp)-{met_run3}_pt*TMath::Sin({met_run3}_phi)", eras=run3eras))

# now we go into the meat
for era in run3eras:
    for subera in suberas_perera[era]:
        # adding a sequence per era,subera for data. first met and then jets
        jme_sequences.append(JMEUncertaintiesDefine(doMET=True, jetAlgo=jet_run3 , suffix="data_%s_%s" % (era, subera)     , eras=[era], suberas=[subera], onMC=False, onData=True, onDataDriven=True, metcollection=met_run3))
        jme_sequences.append(JMEUncertaintiesDefine(doMET=False, jetAlgo=jet_run3, suffix="data_jets_%s_%s" % (era, subera), eras=[era], suberas=[subera], onMC=False, onData=True, onDataDriven=True, metcollection=met_run3))

    # adding a sequence per era for MC. first met and then jets
    uncSources = ["Total"]
    jme_sequences.append(JMEUncertaintiesDefine(doMET=True , jetAlgo=jet_run3, suffix="mc_" + era     , doSyst=True, onMC=True, onData=False, onDataDriven=False, eras=[era], metcollection=met_run3, splitJER=True, uncSources=uncSources))
    jme_sequences.append(JMEUncertaintiesDefine(doMET=False, jetAlgo=jet_run3, suffix="mc_jets_" + era, doSyst=True, onMC=True, onData=False, onDataDriven=False, eras=[era], metcollection=met_run3, splitJER=True, uncSources=uncSources))

    # now we add jet veto maps for run3. no PU ID SF for run 3
    jme_sequences.append(JetVetoMapCut("jetVetoMapCut", eras=[era]))

eras = ['2022', '2022EE']

processes_MC = [
    Process("ttZ"  , MCSample("TTLL_MLL_50" , P, xsec="xsec", eras=eras, hooks=[Append(AddWeightUncertainty("ttZ_ps_isr", "PSWeight[0]", "PSWeight[2]"))]), fillColor=ROOT.kSpring + 1, normUncertainty=[NormUncertainty("ttZ_norm", 1.1)] + lumiUncertainties),
    Process("tZq"  , MCSample("TZQB" , P, xsec="xsec", eras=eras, hooks=[Append(AddWeightUncertainty("tZq_ps_isr", "PSWeight[0]", "PSWeight[2]"))]), fillColor=ROOT.kSpring + 2, normUncertainty=[NormUncertainty("tZq_norm", 1.1)] + lumiUncertainties)
]
processes_Data = [
    Data(DataSample(f"{PD}_Run2022{subera}", P, eras=[era], subera=subera) for era in run3eras for subera in suberas_perera[era] for PD in ("MuonEG", "EGamma", "Muon"))
]

cuts = Flow("3l_3j_2b",
            AddWeight("prescaleFromSkim", "prescaleFromSkim", onData=True, onDataDriven=True),
            # Leptons
            Define("LepGood_isTight", "LepGood_pt > 15 && LepGood_miniPFRelIso_all < 0.1 && LepGood_sip3d < 4 && LepGood_mvaTTH_run3 > 0.8"),
            Cut("3l", "Sum(LepGood_isTight) >= 3"),
            DefineSkimmedCollection("LepTight", "LepGood", mask="LepGood_isTight",
                                    members=("pt", "eta", "phi", "mass", "charge", "pdgId", "dxy", "dz", "sip3d", "miniPFRelIso_all", "jetIdx", "mvaTTH_run3")),
            Cut("3l", "nLepTight >= 3"),
            DefineP4("LepTight"),
            DefineMinMass("minMllTight", "LepTight"),
            Cut("minMll12", "minMllTight > 12"),
            Define("lepZ", "bestPairByMass(pairsSFOS(LepTight_pdgId),LepTight_p4)"),
            Cut("hasZ", "lepZ.first != lepZ.second"),  # if no Z is found, findZll returns {0,0} and the code below would fail
            Define("mZll", "(LepTight_p4[lepZ.first]+LepTight_p4[lepZ.second]).M()"),
            Cut("Zpeak", "mZll > 60 && mZll < 120"),
            # Jets
            jme_sequences,
            Define("LepTight_forJetCleaning", "LepTight_pt > 15"),
            Define("Jet_noLep", "cleanByIndex(nJet,LepTight_forJetCleaning,LepTight_jetIdx)"),
            DefineSkimmedCollection("JetGood", "Jet", ("pt", "eta", "phi", "mass", "btagDeepFlavB"), cut="Jet_pt > 25 && abs(Jet_eta) < 2.4 && Jet_jetId > 1 && Jet_noLep"),
            Define("nJet30", "Sum(JetGood_pt > 30)"),
            Cut("3jets", "nJet30 >= 3"),
            Define("nBJetMedium30", "Sum(JetGood_pt > 30 && JetGood_btagDeepFlavB >= 0.31)"),  # FIXME
            Cut("1b", "nBJetMedium30 >= 2"),
            )
plots = [
    Plot("minMll", "minMllTight", (20, 0, 120), xTitle="min m(ll)", legend="TL"),
    Plot("mZll", "mZll", (40, 60, 120), xTitle="m(ll)", legend="TL"),
    Plot("met", f"{met_run3}_pt", (20, 0, 240), xTitle="p_{T}^{miss} (GeV)"),
    Plot("nBMedium", "nBJetMedium30", (4, 0.5, 4.5), xTitle="Number of medium b-jets (p_{T} > 30)", logy=True, moreY=10),
    Plot("nJet", "nJet30", (5, 2.5, 7.5), xTitle="Number of jets (p_{T} > 30)", logy=True, moreY=10),
]

if __name__ == "__main__":
    from CMGRDF.utils import processorFromCommandLineArgs
    maker = processorFromCommandLineArgs()
    printer = PlotSetPrinter(topRightText="L = %(lumi).1f fb^{-1} (13.6 TeV)", showRatio=True, maxRatioRange=(0, 2.49))
    maker.book(processes_MC + processes_Data, lumis, cuts, plots, eras=eras, withUncertainties=True)
    result_plots = maker.runPlots()
    printer.printSet(result_plots, "plots/jme_run3/{flow}")

    cardMaker = DatacardWriter(regularize=True, autoMCStats=False)
    cardMaker.makeCards(result_plots, MultiKey(name="minMll"), "plots/jme_run3/datacards/run3_{era}")
