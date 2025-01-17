import os
from typing import Optional

from CMGRDF.flow import FlowStep, Define, ReDefine, Vary
from CMGRDF.cms.eras import run2eras

roccorPath = os.path.expandvars("${CMGRDF}/externals/RoccoR")

from CMGRDF.init import AddHeader, Declare
AddHeader('MuRoccoR.h')
AddHeader('RoccoR.h', roccorPath)

for _era in "2016aUL 2016bUL 2017UL 2018UL".split():
    Declare("""
        const RoccoR & muRoccoR_<ERA>() {
           static RoccoR rc("<PATH>/RoccoR<ERA>.txt");
           return rc;
        }
    """.replace("<PATH>", roccorPath).replace("<ERA>", _era))


def _corrPt(RocEra : str,
            eras : Optional[list[str]] = None,
            collection : str = "Muon") -> list[FlowStep]:
    return [Define(f"{collection}_pt_uncorr",
                   f"{collection}_pt",
                   eras=eras),
            ReDefine(f"{collection}_pt",
                     f"MuRoccoR_pT_MC(muRoccoR_{RocEra}(),{collection}_pt,{collection}_eta,{collection}_phi,{collection}_charge,{collection}_genPartIdx,GenPart_pt,{collection}_pdgId)",
                     onMC=True,
                     onData=False,
                     onDataDriven=False,
                     eras=eras),
            ReDefine(f"{collection}_pt",
                     f"MuRoccoR_pT_data(muRoccoR_{RocEra}(),{collection}_pt,{collection}_eta,{collection}_phi,{collection}_charge,{collection}_pdgId)",
                     onMC=False,
                     onData=True,
                     onDataDriven=True,
                     eras=eras),
            Vary(f"{collection}_pt",
                 f"MuRoccoR_pT_MC_syst(muRoccoR_{RocEra}(),{collection}_pt_uncorr,{collection}_eta,{collection}_phi,{collection}_charge,{collection}_genPartIdx,GenPart_pt,{collection}_pdgId,2)",
                 nuisName="CMS_scale_m",
                 onMC=True,
                 onData=False,
                 onDataDriven=False,
                 eras=eras)]


MuRocCorr2016pre = _corrPt("2016aUL")
MuRocCorr2016post = _corrPt("2016bUL")
MuRocCorr2017 = _corrPt("2017UL")
MuRocCorr2018 = _corrPt("2018UL")

eramapping = {"2016APV": "2016aUL",
              "2016"   : "2016bUL",
              "2017"   : "2017UL",
              "2018"   : "2018UL",
              }

MuRocCorr = sum([_corrPt(eramapping[era], eras=[era]) for era in run2eras], [])
MuRocCorrLepGood = sum([_corrPt(eramapping[era], eras=[era], collection="LepGood") for era in run2eras], [])
