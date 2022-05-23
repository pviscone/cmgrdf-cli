#ifndef CMGRDF_functions_h
#define CMGRDF_functions_h
#include <cmath>
#include <cassert>
#include "Math/GenVector/LorentzVector.h"
#include "Math/GenVector/PtEtaPhiM4D.h"
#include "Math/GenVector/PxPyPzM4D.h"
#include "Math/GenVector/Boost.h"

inline float safeRatio(float num, float denom) {
  if (denom == 0)
    return 0;
  return num / denom;
}

inline float deltaPhi(float phi1, float phi2) {
  float result = phi1 - phi2;
  while (result > float(M_PI))
    result -= float(2 * M_PI);
  while (result <= -float(M_PI))
    result += float(2 * M_PI);
  return result;
}

inline float deltaR2(float eta1, float phi1, float eta2, float phi2) {
  float deta = std::abs(eta1 - eta2);
  float dphi = deltaPhi(phi1, phi2);
  return deta * deta + dphi * dphi;
}

inline float deltaR(float eta1, float phi1, float eta2, float phi2) {
  return std::sqrt(deltaR2(eta1, phi1, eta2, phi2));
}

float pt_2(float pt1, float phi1, float pt2, float phi2);
float mt_2(float pt1, float phi1, float pt2, float phi2);
float mass_2(float pt1, float eta1, float phi1, float m1, float pt2, float eta2, float phi2, float m2);
float phi_2(float pt1, float phi1, float pt2, float phi2);
float eta_2(float pt1, float eta1, float phi1, float m1, float pt2, float eta2, float phi2, float m2);

float pt_3(float pt1, float phi1, float pt2, float phi2, float pt3, float phi3);
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
             float m3);
float phi_3(float pt1, float phi1, float pt2, float phi2, float pt3, float phi3);

float pt_4(float pt1, float phi1, float pt2, float phi2, float pt3, float phi3, float pt4, float phi4) ;
float mass_4(
    float pt1,
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
    float m4);

float mt_llv(float ptl1, float phil1, float ptl2, float phil2, float ptv, float phiv);
float mt_lllv(float ptl1, float phil1, float ptl2, float phil2, float ptl3, float phil3, float ptv, float phiv);

float u1_2(float met_pt, float met_phi, float ref_pt, float ref_phi);

float u2_2(float met_pt, float met_phi, float ref_pt, float ref_phi);

// reconstructs a top mass from lepton, met, b-jet, applying the W mass constraint and taking the smallest neutrino pZ
float mtop_lvb(
    float ptl, float etal, float phil, float ml, float met, float metphi, float ptb, float etab, float phib, float mb);

float DPhi_CMLep_Zboost(float l_pt,
                        float l_eta,
                        float l_phi,
                        float l_M,
                        float l_other_pt,
                        float l_other_eta,
                        float l_other_phi,
                        float l_other_M);

inline float lnN1D_p1(float kappa, float x, float xmin, float xmax) {
  return std::pow(kappa, (x - xmin) / (xmax - xmin));
}

inline float deepFlavB_WPLoose(int year) {
  float wp[3] = {0.0614, 0.0521, 0.0494};
  return wp[year - 2016];
}
inline float deepFlavB_WPMedium(int year) {
  float wp[3] = {0.3093, 0.3033, 0.2770};
  return wp[year - 2016];
}
inline float deepFlavB_WPTight(int year) {
  float wp[3] = {0.7221, 0.7489, 0.7264};
  return wp[year - 2016];
}

float deepFlavB_WP(int year, int wp /*0 = loose, 1 = medium, 2=tight*/);

#endif