import os

from CMGRDF.flow import Define, ReDefine, Vary
from CMGRDF.cms.eras import run2eras

roccorPath = os.path.expandvars("${CMGRDF}/externals/RoccoR")
if not os.path.exists(roccorPath):
    raise RuntimeError(f"RoccoR external package is not installed under {roccorPath}")

import ROOT
ROOT.gInterpreter.AddIncludePath(roccorPath)
ROOT.gInterpreter.ProcessLine('#include <MuRoccoR.h>')
ROOT.gInterpreter.ProcessLine('#include <RoccoR.h>')

#for _ERA in "2016 2017 2018 2016aUL 2016bUL 2017UL 2018UL".split():
for _era in "2016aUL 2016bUL 2017UL 2018UL".split():
    ROOT.gInterpreter.Declare("""
        const RoccoR & muRoccoR_<ERA>() {
           static RoccoR rc("<PATH>/RoccoR<ERA>.txt");
           return rc;
        }
    """.replace("<PATH>",roccorPath).replace("<ERA>",_era))

def _corrPt(RocEra, eras=None):
    return [ Define("Muon_pt_uncorr", 
                        "Muon_pt",
                        eras = eras),
             ReDefine("Muon_pt",
                        f"MuRoccoR_pT_MC(muRoccoR_{RocEra}(),Muon_pt,Muon_eta,Muon_phi,Muon_charge,Muon_genPartIdx,GenPart_pt)",
                        onMC=True,
                        onData=False, 
                        onDataDriven=False,
                        eras = eras),
             ReDefine("Muon_pt",
                        f"MuRoccoR_pT_data(muRoccoR_{RocEra}(),Muon_pt,Muon_eta,Muon_phi,Muon_charge)",
                        onMC=False,
                        onData=True, 
                        onDataDriven=True,
                        eras = eras),
             Vary("Muon_pt", 
                        f"MuRoccoR_pT_MC_syst(muRoccoR_{RocEra}(),Muon_pt_uncorr,Muon_eta,Muon_phi,Muon_charge,Muon_genPartIdx,GenPart_pt,2)", 
                        nuisName="CMS_scale_m",
                        onMC=True,
                        onData=False, 
                        onDataDriven=False,
                        eras = eras) ]
MuRocCorrMC2016pre  = _corrPt("2016aUL")
MuRocCorrMC2016post = _corrPt("2016bUL")
MuRocCorrMC2017 = _corrPt("2017UL")
MuRocCorrMC2018 = _corrPt("2018UL")
MuRocCorrMC = sum([ _corrPt(era.replace("pre","a").replace("post","b")+"UL", eras=[era]) for era in run2eras ],[])


