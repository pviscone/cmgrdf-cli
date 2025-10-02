#ifndef TRIGGER_EMULATION_H
#define TRIGGER_EMULATION_H
#include "ROOT/RVec.hxx"
#include "Math/Vector4Dfwd.h"

// https://cmshltinfo-dev.app.cern.ch/path/HLT_VBF_DiPFJet125_45_Mjj1050_v
// https://github.com/cms-sw/cmssw/blob/e00eab5ecfe439676b2530e8e10f758d60bd36e6/HLTrigger/JetMET/src/HLTJetVBFFilter.cc
using namespace ROOT;
using namespace ROOT::VecOps;

bool HLTPFJetVBFFilter(
    const RVecF &jet_pt,
    const RVecF &jet_eta,
    const RVecF &jet_phi,
    const RVecF &jet_mass,
    float pt1,
    float pt2,
    float inv_mass){
    int nJets = jet_pt.size();
    for (int i1 = 0; i1 < nJets; i1++) {
        if (jet_pt[i1] < pt1) {
            return false;
        }
        for (int i2 = i1 + 1; i2 < nJets; i2++) {
            if (jet_pt[i2] < pt2) {
                break;
            }
            if (jet_eta[i1] * jet_eta[i2] > 0) {
                continue; // jets must be in opposite hemispheres
            }
            if (ROOT::VecOps::InvariantMass<float>({jet_pt[i1], jet_pt[i2]},
                                           {jet_eta[i1], jet_eta[i2]},
                                           {jet_phi[i1], jet_phi[i2]},
                                           {jet_mass[i1], jet_mass[i2]}) > inv_mass) {
                return true;
            }
        }
    }
    return false;
}

// https://github.com/cms-sw/cmssw/blob/0dd653a8498d7cc8c3188d210599c02f145a2b21/HLTrigger/JetMET/plugins/HLTL1TMatchedJetsVBFFilter.h#L160-L324
bool HLTL1TMatchedJetsVBFFilter(
    const RVecF &jet_pt,
    const RVecF &jet_eta,
    const RVecF &jet_phi,
    const RVecF &jet_mass,
    float pt1,
    float pt2,
    float inv_mass
){
    int nJets = jet_pt.size();
    float mjj;
    int i1_max = -1;
    int i2_max = -1;
    float mjj_max = -1.;
    for (int i1 = 0; i1 < nJets; i1++){
        for (int i2 = i1 + 1; i2 < nJets; i2++){
            mjj = ROOT::VecOps::InvariantMass<float>({jet_pt[i1], jet_pt[i2]},
                                           {jet_eta[i1], jet_eta[i2]},
                                           {jet_phi[i1], jet_phi[i2]},
                                           {jet_mass[i1], jet_mass[i2]});
            if (mjj > mjj_max) {
                mjj_max = mjj;
                i1_max = i1;
                i2_max = i2;
            }
        }
    }
    if (!(mjj_max >=  inv_mass)){
        return false;
    }
    if (!(jet_pt[i2_max] >= pt2)) {
        return false;
    }
    if (jet_pt[i1_max] >= pt1) {
        return true;
    } else if (jet_pt[0]>= pt1) {
        return true;
    } else {
        return false;
    }
}


bool inclusiveVBFemu(
    const RVecF &jet_pt,
    const RVecF &jet_eta,
    const RVecF &jet_phi,
    const RVecF &jet_mass,
    float multiplier = 1.1,
    float pt1 = 125.,
    float pt2 = 45.,
    float inv_mass = 1050.
){
    if (jet_pt.size() < 2) {
        return false;
    }

    pt1*= multiplier;
    pt2 *= multiplier;
    inv_mass *= multiplier;

    if (!(jet_pt[0] >= pt1 && jet_pt[1] >= pt2)) {
        return false;
    }

    if (!HLTPFJetVBFFilter(jet_pt, jet_eta, jet_phi, jet_mass, pt2, pt2, inv_mass)){
        return false;
    };

    return HLTL1TMatchedJetsVBFFilter(jet_pt, jet_eta, jet_phi, jet_mass, pt1, pt2, inv_mass);

}

// https://cmshltinfo-dev.app.cern.ch/path/HLT_VBF_DiPFJet50_Mjj650_Photon22_v
bool VBFgammaEmu(
    const RVecF &jet_pt,
    const RVecF &jet_eta,
    const RVecF &jet_phi,
    const RVecF &jet_mass,
    float multiplier = 1.1,
    float pt = 50.,
    float inv_mass = 650.
){
    if (jet_pt.size() < 2) {
        return false;
    }

    pt*= multiplier;
    inv_mass *= multiplier;

    return HLTPFJetVBFFilter(jet_pt, jet_eta, jet_phi, jet_mass, pt, pt, inv_mass);
    //Missing photon cut emulation (needs matching with online objects + geometrical cuts)
}

// https://cmshltinfo-dev.app.cern.ch/path/HLT_VBF_DiPFJet50_Mjj600_Ele22_eta2p1_WPTight_Gsf_v
bool VBFeleEmu(
    const RVecF &jet_pt,
    const RVecF &jet_eta,
    const RVecF &jet_phi,
    const RVecF &jet_mass,
    float multiplier = 1.1,
    float pt = 50.,
    float inv_mass = 600.
){

    if (jet_pt.size() < 2) {
        return false;
    }


    pt*= multiplier;
    inv_mass *= multiplier;

    return HLTPFJetVBFFilter(jet_pt, jet_eta, jet_phi, jet_mass, pt, pt, inv_mass);
    //Missing electron cut emulation (needs matching with online objects + geometrical cuts)
}


#endif // !TRIGGER_EMULATION_H
