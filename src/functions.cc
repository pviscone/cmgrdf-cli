#include "functions.h"

#include "Math/GenVector/LorentzVector.h"
#include "Math/GenVector/PtEtaPhiM4D.h"
#include "Math/GenVector/PxPyPzM4D.h"
#include "Math/GenVector/Boost.h"

ROOT::RVec<float> deltaR2(float eta1, float phi1, const ROOT::RVec<float> &eta2, const ROOT::RVec<float> &phi2) {
  ROOT::RVec<float> veta1(eta2.size(), eta1);
  ROOT::RVec<float> vphi1(phi2.size(), phi1);
  return ROOT::VecOps::DeltaR2(veta1, vphi1, eta2, phi2);
}

float pt_2(float pt1, float phi1, float pt2, float phi2) {
  phi2 -= phi1;
  return std::hypot(pt1 + pt2 * std::cos(phi2), pt2 * std::sin(phi2));
}

float mt_2(float pt1, float phi1, float pt2, float phi2) {
  return std::sqrt(2 * pt1 * pt2 * (1 - std::cos(phi1 - phi2)));
}

float mass_2(float pt1, float eta1, float phi1, float m1, float pt2, float eta2, float phi2, float m2) {
  typedef ROOT::Math::LorentzVector<ROOT::Math::PtEtaPhiM4D<double>> PtEtaPhiMVector;
  PtEtaPhiMVector p41(pt1, eta1, phi1, m1);
  PtEtaPhiMVector p42(pt2, eta2, phi2, m2);
  return (p41 + p42).M();
}

float phi_2(float pt1, float phi1, float pt2, float phi2) {
  float px1 = pt1 * std::cos(phi1);
  float py1 = pt1 * std::sin(phi1);
  float px2 = pt2 * std::cos(phi2);
  float py2 = pt2 * std::sin(phi2);
  return std::atan2(py1 + py2, px1 + px2);
}

float phi_3(float pt1, float phi1, float pt2, float phi2, float pt3, float phi3) {
  float px1 = pt1 * std::cos(phi1);
  float py1 = pt1 * std::sin(phi1);
  float px2 = pt2 * std::cos(phi2);
  float py2 = pt2 * std::sin(phi2);
  float px3 = pt3 * std::cos(phi3);
  float py3 = pt3 * std::sin(phi3);
  return std::atan2(py1 + py2 + py3, px1 + px2 + px3);
}

float eta_2(float pt1, float eta1, float phi1, float m1, float pt2, float eta2, float phi2, float m2) {
  typedef ROOT::Math::LorentzVector<ROOT::Math::PtEtaPhiM4D<double>> PtEtaPhiMVector;
  PtEtaPhiMVector p41(pt1, eta1, phi1, m1);
  PtEtaPhiMVector p42(pt2, eta2, phi2, m2);
  return (p41 + p42).Eta();
}

float pt_3(float pt1, float phi1, float pt2, float phi2, float pt3, float phi3) {
  phi2 -= phi1;
  phi3 -= phi1;
  return std::hypot(pt1 + pt2 * std::cos(phi2) + pt3 * std::cos(phi3), pt2 * std::sin(phi2) + pt3 * std::sin(phi3));
}

float mass_3(float pt1,
             float eta1,
             float phi1,
             float m1,
             float pt2,
             float eta2,
             float phi2,
             float m2,
             float pt3,
             float eta3,
             float phi3,
             float m3) {
  typedef ROOT::Math::LorentzVector<ROOT::Math::PtEtaPhiM4D<double>> PtEtaPhiMVector;
  PtEtaPhiMVector p41(pt1, eta1, phi1, m1);
  PtEtaPhiMVector p42(pt2, eta2, phi2, m2);
  PtEtaPhiMVector p43(pt3, eta3, phi3, m3);
  return (p41 + p42 + p43).M();
}

float pt_4(float pt1, float phi1, float pt2, float phi2, float pt3, float phi3, float pt4, float phi4) {
  phi2 -= phi1;
  phi3 -= phi1;
  phi4 -= phi1;
  return std::hypot(pt1 + pt2 * std::cos(phi2) + pt3 * std::cos(phi3) + pt4 * std::cos(phi4),
                    pt2 * std::sin(phi2) + pt3 * std::sin(phi3) + pt4 * std::sin(phi4));
}

float mass_4(float pt1,
             float eta1,
             float phi1,
             float m1,
             float pt2,
             float eta2,
             float phi2,
             float m2,
             float pt3,
             float eta3,
             float phi3,
             float m3,
             float pt4,
             float eta4,
             float phi4,
             float m4) {
  typedef ROOT::Math::LorentzVector<ROOT::Math::PtEtaPhiM4D<double>> PtEtaPhiMVector;
  PtEtaPhiMVector p41(pt1, eta1, phi1, m1);
  PtEtaPhiMVector p42(pt2, eta2, phi2, m2);
  PtEtaPhiMVector p43(pt3, eta3, phi3, m3);
  PtEtaPhiMVector p44(pt4, eta4, phi4, m4);
  return (p41 + p42 + p43 + p44).M();
}

float mt_llv(float ptl1, float phil1, float ptl2, float phil2, float ptv, float phiv) {
  float px = ptl1 * std::cos(phil1) + ptl2 * std::cos(phil2) + ptv * std::cos(phiv);
  float py = ptl1 * std::sin(phil1) + ptl2 * std::sin(phil2) + ptv * std::sin(phiv);
  float ht = ptl1 + ptl2 + ptv;
  return std::sqrt(std::max(0.f, ht * ht - px * px - py * py));
}

float mt_lllv(float ptl1, float phil1, float ptl2, float phil2, float ptl3, float phil3, float ptv, float phiv) {
  float px = ptl1 * std::cos(phil1) + ptl2 * std::cos(phil2) + ptl3 * std::cos(phil3) + ptv * std::cos(phiv);
  float py = ptl1 * std::sin(phil1) + ptl2 * std::sin(phil2) + ptl3 * std::sin(phil3) + ptv * std::sin(phiv);
  float ht = ptl1 + ptl2 + ptl3 + ptv;
  return std::sqrt(std::max(0.f, ht * ht - px * px - py * py));
}

float u1_2(float met_pt, float met_phi, float ref_pt, float ref_phi) {
  float met_px = met_pt * std::cos(met_phi), met_py = met_pt * std::sin(met_phi);
  float ref_px = ref_pt * std::cos(ref_phi), ref_py = ref_pt * std::sin(ref_phi);
  float ux = -met_px + ref_px, uy = -met_py + ref_py;
  return (ux * ref_px + uy * ref_py) / ref_pt;
}

float u2_2(float met_pt, float met_phi, float ref_pt, float ref_phi) {
  float met_px = met_pt * std::cos(met_phi), met_py = met_pt * std::sin(met_phi);
  float ref_px = ref_pt * std::cos(ref_phi), ref_py = ref_pt * std::sin(ref_phi);
  float ux = -met_px + ref_px, uy = -met_py + ref_py;
  return (ux * ref_py - uy * ref_px) / ref_pt;
}

ROOT::RVec<ROOT::Math::PtEtaPhiMVector> makeP4(const ROOT::RVecF &pt,
                                               const ROOT::RVecF &eta,
                                               const ROOT::RVecF &phi,
                                               const ROOT::RVecF &mass) {
  return ROOT::VecOps::Construct<ROOT::Math::PtEtaPhiMVector>(pt, eta, phi, mass);
}

ROOT::RVec<ROOT::Math::PtEtaPhiMVector> makeP4(const ROOT::RVecF &pt,
                                               const ROOT::RVecF &eta,
                                               const ROOT::RVecF &phi,
                                               float mass) {
  return ROOT::VecOps::Construct<ROOT::Math::PtEtaPhiMVector>(pt, eta, phi, ROOT::RVecF(pt.size(), mass));
}

ROOT::RVec<std::pair<size_t, size_t>> allPairs(std::size_t n) {
  ROOT::RVec<std::pair<size_t, size_t>> ret;
  for (size_t i = 0; i < n - 1; ++i) {
    for (size_t j = i + 1; j < n; ++j) {
      ret.emplace_back(i, j);
    }
  }
  return ret;
}

ROOT::RVec<std::pair<size_t, size_t>> pairsOS(const ROOT::RVecI &charge) {
  size_t n = charge.size();
  ROOT::RVec<std::pair<size_t, size_t>> ret;
  for (size_t i = 0; i < n - 1; ++i) {
    for (size_t j = i + 1; j < n; ++j) {
      if (charge[i] * charge[j] < 0) {
        ret.emplace_back(i, j);
      }
    }
  }
  return ret;
}

ROOT::RVec<std::pair<size_t, size_t>> pairsSS(const ROOT::RVecI &charge) {
  size_t n = charge.size();
  ROOT::RVec<std::pair<size_t, size_t>> ret;
  for (size_t i = 0; i < n - 1; ++i) {
    for (size_t j = i + 1; j < n; ++j) {
      if (charge[i] * charge[j] > 0) {
        ret.emplace_back(i, j);
      }
    }
  }
  return ret;
}

ROOT::RVec<std::pair<size_t, size_t>> pairsSFOS(const ROOT::RVecI &pdgId) {
  size_t n = pdgId.size();
  ROOT::RVec<std::pair<size_t, size_t>> ret;
  for (size_t i = 0; i < n - 1; ++i) {
    for (size_t j = i + 1; j < n; ++j) {
      if (pdgId[i] == -pdgId[j]) {
        ret.emplace_back(i, j);
      }
    }
  }
  return ret;
}

ROOT::RVec<std::pair<size_t, size_t>> pairsSFSS(const ROOT::RVecI &pdgId) {
  size_t n = pdgId.size();
  ROOT::RVec<std::pair<size_t, size_t>> ret;
  for (size_t i = 0; i < n - 1; ++i) {
    for (size_t j = i + 1; j < n; ++j) {
      if (pdgId[i] == pdgId[j]) {
        ret.emplace_back(i, j);
      }
    }
  }
  return ret;
}

ROOT::RVec<std::pair<size_t, size_t>> pairsDFOS(const ROOT::RVecI &pdgId) {
  size_t n = pdgId.size();
  ROOT::RVec<std::pair<size_t, size_t>> ret;
  for (size_t i = 0; i < n - 1; ++i) {
    for (size_t j = i + 1; j < n; ++j) {
      if (pdgId[i] * pdgId[j] < 0 && pdgId[i] != -pdgId[j]) {
        ret.emplace_back(i, j);
      }
    }
  }
  return ret;
}

ROOT::RVec<ROOT::Math::PtEtaPhiMVector> pairP4(const ROOT::RVec<std::pair<size_t, size_t>> &pairs,
                                               const ROOT::RVec<ROOT::Math::PtEtaPhiMVector> &p4s) {
  ROOT::RVec<ROOT::Math::PtEtaPhiMVector> ret;
  ret.reserve(pairs.size());
  for (const auto &p : pairs) {
    ret.emplace_back(p4s[p.first] + p4s[p.second]);
  }
  return ret;
}

std::pair<size_t, size_t> bestPairByMass(const ROOT::RVec<std::pair<size_t, size_t>> &pairs,
                                         const ROOT::RVec<ROOT::Math::PtEtaPhiMVector> &p4s,
                                         const float target) {
  std::pair<size_t, size_t> ret(0, 0);
  float diff = -1;
  for (const auto &p : pairs) {
    float m = (p4s[p.first] + p4s[p.second]).M();
    float dm = std::abs(m - target);
    if (diff < 0 || dm < diff) {
      ret = p;
      diff = dm;
    }
  }
  return ret;
}

float minPairMass(const ROOT::RVec<std::pair<size_t, size_t>> &pairs,
                  const ROOT::RVec<ROOT::Math::PtEtaPhiMVector> &p4s) {
  float minMass2 = 9e99;
  for (const auto &p : pairs) {
    minMass2 = std::min<float>(minMass2, (p4s[p.first] + p4s[p.second]).M2());
  }
  return std::sqrt(minMass2);
}

ROOT::RVec<int> cleanByIndex(size_t nJets, const ROOT::RVec<int> &Lep_sel, const ROOT::RVec<int> &Lep_jetIdx) {
  ROOT::RVec<int> mask(nJets, 1);
  for (unsigned i = 0, n = Lep_jetIdx.size(); i < n; ++i) {
    if (Lep_sel[i]) {
      if (Lep_jetIdx[i] >= 0 && Lep_jetIdx[i] < int(nJets)) {
        mask[Lep_jetIdx[i]] = 0;
      }
    }
  }
  return mask;
}

ROOT::RVec<int> cleanByDR(const ROOT::RVec<float> &Jet_eta,
                          const ROOT::RVec<float> &Jet_phi,
                          const ROOT::RVec<float> &Lep_eta,
                          const ROOT::RVec<float> &Lep_phi,
                          float minDR) {
  unsigned int nJets = Jet_eta.size();
  unsigned int nLeps = Lep_eta.size();
  float minDR2 = minDR * minDR;
  ROOT::RVec<int> mask(nJets, 1);
  for (unsigned i = 0; i < nLeps; ++i) {
    for (unsigned j = 0; j < nJets; ++j) {
      if (deltaR2(Lep_eta[i], Lep_phi[i], Jet_eta[j], Jet_phi[j]) < minDR2) {
        mask[j] = 0;
      }
    }
  }
  return mask;
}

ROOT::RVec<int> cleanByDR(const ROOT::RVec<float> &Jet_eta,
                          const ROOT::RVec<float> &Jet_phi,
                          const ROOT::RVec<float> &Lep_eta,
                          const ROOT::RVec<float> &Lep_phi,
                          const ROOT::RVec<int> &Lep_sel,
                          float minDR) {
  unsigned int nJets = Jet_eta.size();
  unsigned int nLeps = Lep_eta.size();
  float minDR2 = minDR * minDR;
  ROOT::RVec<int> mask(nJets, 1);
  for (unsigned i = 0; i < nLeps; ++i) {
    if (!Lep_sel[i])
      continue;
    for (unsigned j = 0; j < nJets; ++j) {
      if (deltaR2(Lep_eta[i], Lep_phi[i], Jet_eta[j], Jet_phi[j]) < minDR2) {
        mask[j] = 0;
      }
    }
  }
  return mask;
}

// reconstructs a top from lepton, met, b-jet, applying the W mass constraint and taking the smallest neutrino pZ
float mtop_lvb(
    float ptl, float etal, float phil, float ml, float met, float metphi, float ptb, float etab, float phib, float mb) {
  typedef ROOT::Math::LorentzVector<ROOT::Math::PtEtaPhiM4D<double>> PtEtaPhiMVector;
  typedef ROOT::Math::LorentzVector<ROOT::Math::PxPyPzM4D<double>> PxPyPzMVector;
  PtEtaPhiMVector p4l(ptl, etal, phil, ml);
  PtEtaPhiMVector p4b(ptb, etab, phib, mb);
  double MW = 80.4;
  double a = (1 - std::pow(p4l.Z() / p4l.E(), 2));
  double ppe = met * ptl * std::cos(phil - metphi) / p4l.E();
  double brk = MW * MW / (2 * p4l.E()) + ppe;
  double b = (p4l.Z() / p4l.E()) * brk;
  double c = met * met - brk * brk;
  double delta = b * b - a * c;
  double sqdelta = delta > 0 ? std::sqrt(delta) : 0;
  double pz1 = (b + sqdelta) / a, pz2 = (b - sqdelta) / a;
  double pznu = (abs(pz1) <= abs(pz2) ? pz1 : pz2);
  PxPyPzMVector p4v(met * std::cos(metphi), met * std::sin(metphi), pznu, 0);
  return (p4l + p4b + p4v).M();
}

float DPhi_CMLep_Zboost(float l_pt,
                        float l_eta,
                        float l_phi,
                        float l_M,
                        float l_other_pt,
                        float l_other_eta,
                        float l_other_phi,
                        float l_other_M) {
  typedef ROOT::Math::LorentzVector<ROOT::Math::PtEtaPhiM4D<double>> PtEtaPhiMVector;
  PtEtaPhiMVector l1(l_pt, l_eta, l_phi, l_M);
  PtEtaPhiMVector l2(l_other_pt, l_other_eta, l_other_phi, l_other_M);
  PtEtaPhiMVector Z = l1 + l2;
  ROOT::Math::Boost boost(Z.BoostToCM());
  l1 = boost * l1;
  return deltaPhi(l1.Phi(), Z.Phi());
}

float deepFlavB_WP(int year, int wp /*0 = loose, 1 = medium, 2=tight*/) {
  switch (wp) {
    case 0:
      return deepFlavB_WPLoose(year);
    case 1:
      return deepFlavB_WPMedium(year);
    case 2:
      return deepFlavB_WPTight(year);
  }
  return -99;
}
