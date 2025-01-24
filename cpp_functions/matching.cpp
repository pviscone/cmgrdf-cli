#pragma once
#include "ROOT/RVec.hxx"
#include "Math/Vector4Dfwd.h"

using namespace ROOT::VecOps;
using namespace ROOT::Math;
using namespace ROOT;

//_____________________________________________________________________________

RVecF dR(
        const RVecF &eta1,
        const float &eta2,
        const RVecF &phi1,
        const float &phi2){

    RVecF dR = ROOT::VecOps::sqrt(ROOT::VecOps::pow(eta1 - eta2, 2) +
            ROOT::VecOps::pow(ROOT::VecOps::DeltaPhi(phi1, phi2), 2));
    return dR;
}

float deltaVtx(
        const float &obj1_vtx_x,
        const float &obj1_vtx_y,
        const float &obj1_vtx_z,
        const float &obj2_vtx_x,
        const float &obj2_vtx_y,
        const float &obj2_vtx_z){
    float dx = obj1_vtx_x - obj2_vtx_x;
    float dy = obj1_vtx_y - obj2_vtx_y;
    float dz = obj1_vtx_z - obj2_vtx_z;
    return sqrt(dx*dx + dy*dy + dz*dz);
}

RVecF deltaVtx(
        const RVecF &obj1_vtx_x,
        const RVecF &obj1_vtx_y,
        const RVecF &obj1_vtx_z,
        const float &obj2_vtx_x,
        const float &obj2_vtx_y,
        const float &obj2_vtx_z){
    RVecF dx = obj1_vtx_x - obj2_vtx_x;
    RVecF dy = obj1_vtx_y - obj2_vtx_y;
    RVecF dz = obj1_vtx_z - obj2_vtx_z;
    return ROOT::VecOps::sqrt(dx*dx + dy*dy + dz*dz);
}

struct matching_info {
    RVec<bool> match;
    RVec<bool> l1match;
    RVec<bool> l2match;
    RVec<bool> vtx_match;
    RVecI l1genidx;
    RVecI l2genidx;

    // To make RDF shut up
    matching_info(){};

    // To instanciate with the right size
    matching_info(int n){
        match = RVec<bool>(n, false);
        l1match = RVec<bool>(n, false);
        l2match = RVec<bool>(n, false);
        vtx_match = RVec<bool>(n, false);
        l1genidx = RVecI(n, -1);
        l2genidx = RVecI(n, -1);
    }

    // To allow masking
    matching_info operator[](RVec<bool> mask) const {
        //TODO change to instanciation by initializer list
        matching_info match_info(mask.size());
        match_info.match = std::move(match[mask]);
        match_info.l1match = std::move(l1match[mask]);
        match_info.l2match = std::move(l2match[mask]);
        match_info.vtx_match = std::move(vtx_match[mask]);
        match_info.l1genidx = std::move(l1genidx[mask]);
        match_info.l2genidx = std::move(l2genidx[mask]);
        return match_info;
    }
};

//FIXME: 3% efficiency, something wrong
matching_info SOS_matching(
    const RVecF &diEle_l1idx,
    const RVecF &diEle_l2idx,
    const RVecF &diEle_dVtx,
    const RVecF &ele_dR1,
    const RVecF &ele_dR2,
    const RVecF &ele_dPt1,
    const RVecF &ele_dPt2,
    float max_dR = 0.3,
    float max_dPt = 0.5,
    float max_dVtx = 0.2
){
    int nDiEle = diEle_l1idx.size();
    matching_info info(nDiEle);
    RVec<RVecF> dR_gen = {ele_dR1,ele_dR2};
    RVec<RVecF> dPt_gen = {ele_dPt1,ele_dPt2};
    for (int i = 0; i < nDiEle; i++) {
        float lep1_min_dR = -99;
        float lep2_min_dR = -99;
        for (int j = 0; j < 2; j++) {
            float dR_lep1 = dR_gen[j][diEle_l1idx[i]];
            float dR_lep2 = dR_gen[j][diEle_l2idx[i]];
            float dPt_lep1 = dPt_gen[j][diEle_l1idx[i]];
            float dPt_lep2 = dPt_gen[j][diEle_l2idx[i]];
            if (dR_lep1 < dR_lep2 && dR_lep1 < max_dR && dPt_lep1 < max_dPt && (!info.l1match[i] || dR_lep1 < lep1_min_dR)) {
                info.l1match[i] = true;
                info.l1genidx[i] = j;
                lep1_min_dR = dR_lep1;
            } else if (dR_lep2 < dR_lep1 && dR_lep2 < max_dR && dPt_lep2 < max_dPt && (!info.l2match[i] || dR_lep2 < lep2_min_dR)) {
                info.l2match[i] = true;
                info.l2genidx[i] = j;
                lep2_min_dR = dR_lep2;
            }
        }
        if (info.l1match[i] && info.l2match[i]) {
            float dVtx = diEle_dVtx[i];
            if (dVtx < max_dVtx) {
                info.vtx_match[i] = true;
            }
        }
        info.match[i] = info.l1match[i] && info.l2match[i] && info.vtx_match[i];
    }
    return info;
}


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

