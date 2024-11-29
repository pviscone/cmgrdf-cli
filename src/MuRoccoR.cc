#include <RoccoR/RoccoR.h>
#include <MuRoccoR.h>

ROOT::RVec<float> MuRoccoR_pT_data(const RoccoR& rc,
                                   const ROOT::RVec<float>& mu_pt,
                                   const ROOT::RVec<float>& mu_eta,
                                   const ROOT::RVec<float>& mu_phi,
                                   const ROOT::RVec<int>& mu_charge,
                                   const ROOT::RVec<int>& mu_pdgId,
                                   int syst) {
  ROOT::RVec<float> ret(mu_pt);
  for (unsigned int i = 0, n = mu_pt.size(); i < n; ++i) {
    if (abs(mu_pdgId[i]) != 13)
      continue;
    float scalCorr = rc.kScaleDT(mu_charge[i], mu_pt[i], mu_eta[i], mu_phi[i]);
    if (syst == 1 || syst == -1)
      scalCorr += syst * std::abs(rc.kScaleDTerror(mu_charge[i], mu_pt[i], mu_eta[i], mu_phi[i]));
    ret[i] *= scalCorr;
  }
  return ret;
}

ROOT::RVec<float> MuRoccoR_pT_MC(const RoccoR& rc,
                                 const ROOT::RVec<float>& mu_pt,
                                 const ROOT::RVec<float>& mu_eta,
                                 const ROOT::RVec<float>& mu_phi,
                                 const ROOT::RVec<int>& mu_charge,
                                 const ROOT::RVec<int>& mu_genIdx,
                                 const ROOT::RVec<float>& gen_pt,
                                 const ROOT::RVec<int>& mu_pdgId,
                                 int syst) {
  // syst = +/- 1 : scale MC up and down by MC uncertainty
  // syst = +/- 2 : scale MC up and down by MC+data uncertainty (when not applying uncertainties to data)
  ROOT::RVec<float> ret(mu_pt);
  for (unsigned int i = 0, n = mu_pt.size(), ngen = gen_pt.size(); i < n; ++i) {
    if (abs(mu_pdgId[i]) != 13)
      continue;
    if (mu_genIdx[i] >= 0 && unsigned(mu_genIdx[i]) < ngen) {
      float resCorr = rc.kSpreadMC(mu_charge[i], mu_pt[i], mu_eta[i], mu_phi[i], gen_pt[mu_genIdx[i]]);
      if (syst) {
        float shift = std::abs(rc.kSpreadMCerror(mu_charge[i], mu_pt[i], mu_eta[i], mu_phi[i], gen_pt[mu_genIdx[i]]));
        if (syst == 2 || syst == -2) {
          shift += std::abs(rc.kScaleDTerror(mu_charge[i], mu_pt[i], mu_eta[i], mu_phi[i]));
        }
        resCorr += (syst > 0 ? shift : -shift);
      }
      ret[i] *= resCorr;
    }
  }
  return ret;
}
ROOT::RVec<ROOT::RVec<float>> MuRoccoR_pT_MC_syst(const RoccoR& rc,
                                                  const ROOT::RVec<float>& mu_pt_uncorr,
                                                  const ROOT::RVec<float>& mu_eta,
                                                  const ROOT::RVec<float>& mu_phi,
                                                  const ROOT::RVec<int>& mu_charge,
                                                  const ROOT::RVec<int>& mu_genIdx,
                                                  const ROOT::RVec<float>& gen_pt,
                                                  const ROOT::RVec<int>& mu_pdgId,
                                                  int syst) {
  ROOT::RVec<ROOT::RVec<float>> ret(2);
  ret[0] = MuRoccoR_pT_MC(rc, mu_pt_uncorr, mu_eta, mu_phi, mu_charge, mu_genIdx, gen_pt, mu_pdgId, -syst);
  ret[1] = MuRoccoR_pT_MC(rc, mu_pt_uncorr, mu_eta, mu_phi, mu_charge, mu_genIdx, gen_pt, mu_pdgId, syst);
  return ret;
}
