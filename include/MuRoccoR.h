#ifndef CMGRDF_include_MuRoccoR_h
#define CMGRDF_include_MuRoccoR_h

struct RoccoR;
#include <ROOT/RVec.hxx>

ROOT::RVec<float> MuRoccoR_pT_data(const RoccoR& rc,
                                   const ROOT::RVec<float>& mu_pt,
                                   const ROOT::RVec<float>& mu_eta,
                                   const ROOT::RVec<float>& mu_phi,
                                   const ROOT::RVec<int>& mu_charge,
                                   const ROOT::RVec<int>& mu_pdgid,
                                   int syst = 0);
ROOT::RVec<float> MuRoccoR_pT_MC(const RoccoR& rc,
                                 const ROOT::RVec<float>& mu_pt,
                                 const ROOT::RVec<float>& mu_eta,
                                 const ROOT::RVec<float>& mu_phi,
                                 const ROOT::RVec<int>& mu_charge,
                                 const ROOT::RVec<int>& mu_genIdx,
                                 const ROOT::RVec<float>& gen_pt,
                                 const ROOT::RVec<int>& mu_pdgId,
                                 int syst = 0);
ROOT::RVec<ROOT::RVec<float>> MuRoccoR_pT_MC_syst(const RoccoR& rc,
                                                  const ROOT::RVec<float>& mu_pt_uncorr,
                                                  const ROOT::RVec<float>& mu_eta,
                                                  const ROOT::RVec<float>& mu_phi,
                                                  const ROOT::RVec<int>& mu_charge,
                                                  const ROOT::RVec<int>& mu_genIdx,
                                                  const ROOT::RVec<float>& gen_pt,
                                                  const ROOT::RVec<int>& mu_pdgId,
                                                  int syst);
#endif
