#pragma once
#include "ROOT/RVec.hxx"
#include "Math/Vector4Dfwd.h"

using namespace ROOT::VecOps;
using namespace ROOT::Math;
using namespace ROOT;

//_____________________________________________________________________________

RVec<bool> match_mask(
        const RVecF &obj1_eta,
        const RVecF &obj1_phi,
        const float &obj2_eta,
        const float &obj2_phi,
        float dRcut = 0.1){

    RVec<bool> mask(obj1_eta.size(), false);
    RVecF dR=DeltaR(obj1_eta, RVecF(obj1_eta.size(),obj2_eta), obj1_phi, RVecF(obj1_eta.size(),obj2_phi));

    for (int i = 0; i < obj1_eta.size(); i++) {
        if (dR[i] < dRcut) {
            mask[i] = true;
        }
    }
    return mask;
}

RVec<bool> match_mask(
        const RVecF &obj1_pt,
        const RVecF &obj1_eta,
        const RVecF &obj1_phi,
        const float &obj2_pt,
        const float &obj2_eta,
        const float &obj2_phi,
        float dRcut = 0.1){

    RVec<bool> mask(obj1_eta.size(), false);
    RVecF dR=DeltaR(obj1_eta, RVecF(obj1_eta.size(),obj2_eta), obj1_phi, RVecF(obj1_eta.size(),obj2_phi));
    float minabs_pt=FLT_MAX;
    int minabs_pt_index=-1;
    for (int i = 0; i < obj1_eta.size(); i++) {
        if (dR[i] < dRcut && abs(obj1_pt[i]-obj2_pt)<minabs_pt) {
            minabs_pt=abs(obj1_pt[i]-obj2_pt);
            minabs_pt_index=i;
        }
    }
    if (minabs_pt_index!=-1) {
        mask[minabs_pt_index] = true;
    }
    return mask;
}