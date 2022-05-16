#include "TFile.h"
#include "TH2.h"
#include "TGraphAsymmErrors.h"
#include "TRandom3.h"

#include "Math/GenVector/LorentzVector.h"
#include "Math/GenVector/PtEtaPhiM4D.h"
#include "Math/GenVector/PxPyPzM4D.h"

#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>

// we need to declare the functions we use from functions.cc
float pt_2(float,float,float,float) ;
float pt_3(float,float,float,float,float,float) ;
float pt_4(float, float, float, float , float, float , float, float);

float metmm_pt(int pdg1, float pt1, float phi1, int pdg2, float pt2, float phi2, float metpt, float metphi) {
  if (std::abs(pdg1)==13 && std::abs(pdg2)==13) return pt_3(pt1,phi1,pt2,phi2,metpt,metphi);
  else if (std::abs(pdg1)==13 && !(std::abs(pdg2)==13)) return pt_2(pt1,phi1,metpt,metphi);
  else if (!(std::abs(pdg1)==13) && std::abs(pdg2)==13) return pt_2(pt2,phi2,metpt,metphi);
  else if (!(std::abs(pdg1)==13) && !(std::abs(pdg2)==13)) return metpt;
  else {
    std::cout << "Error in metmm_pt" << std::endl;
    return -99;
  }
}

float lepton_Id_selection(int pdg1, int pdg2, int pdg3){
  if (std::abs(pdg1)==13 && std::abs(pdg2)==13 && std::abs(pdg3) ==13) return 123;
  else if (std::abs(pdg1)==13 && std::abs(pdg2)==13 && !(std::abs(pdg3)==13))return 12;
  else if (std::abs(pdg1)==13 && !(std::abs(pdg2)==13) && std::abs(pdg3) == 13)return 13;
  else if (!(std::abs(pdg1)==13) && std::abs(pdg2)==13 && std::abs(pdg3)==13)return 23;
  else if (std::abs(pdg1)==13 && !(std::abs(pdg2)==13) && !(std::abs(pdg3)==13))return 1;
  else if (!(std::abs(pdg1)==13) && std::abs(pdg2)==13 && !(std::abs(pdg3)==13)) return 2;
  else if (!(std::abs(pdg1)==13) && !(std::abs(pdg2)==13) && (std::abs(pdg3)==13))return 3;
  else if (!(std::abs(pdg1)==13) && !(std::abs(pdg2)==13) && !(std::abs(pdg3)==13)) return 4;
  else {
    std::cout << "Error in lepton_Id_selection" << std::endl;
    return -99;
  }
}

float metmmm_pt( float pt1, float phi1, float pt2, float phi2, float pt3, float phi3, float metpt, float metphi, int lepton_code) {
  if (lepton_code == 123)  return pt_4(pt1, phi1, pt2, phi2, pt3, phi3, metpt, metphi);
  else if (lepton_code == 12) return pt_3(pt1,phi1,pt2,phi2,metpt,metphi);
  else if (lepton_code == 13) return pt_3(pt1, phi1, pt3, phi3, metpt, metphi);
  else if (lepton_code == 23) return pt_3(pt2, phi2, pt3, phi3, metpt, metphi);
  else if (lepton_code == 1) return pt_2(pt1, phi1, metpt, metphi);
  else if (lepton_code == 2) return pt_2(pt2,phi2,metpt,metphi);
  else if (lepton_code == 3) return pt_2(pt3,phi3, metpt, metphi);
  else if (lepton_code == 4) return metpt;
  else {
    std::cout << "Error in metmmm_pt" << std::endl;
    return -99;
  }
}

float mass_tautau( float Met_Pt, float Met_Phi,  float l1_Pt, float l1_Eta, float l1_Phi, float l2_Pt, float l2_Eta, float l2_Phi ) {
  typedef ROOT::Math::LorentzVector<ROOT::Math::PtEtaPhiM4D<double> > PtEtaPhiMVector;
  typedef ROOT::Math::LorentzVector<ROOT::Math::PxPyPzM4D<double>   > PxPyPzMVector;
  PtEtaPhiMVector Met( Met_Pt, 0.     , Met_Phi , 0.   );
  PtEtaPhiMVector L1(  l1_Pt , l1_Eta , l1_Phi  , 0.106 );
  PtEtaPhiMVector L2(  l2_Pt , l2_Eta , l2_Phi  , 0.106 );   // 0.106 mu mass                                                                                                                                                 
  float A00,A01,A10,A11,  C0,C1,  X0,X1,  inv_det;     // Define A:2x2 matrix, C,X 2x1 vectors & det[A]^-1                                                                                                                    
  inv_det = 1./( L1.Px()*L2.Py() - L2.Px()*L1.Py() );
  A00 = inv_det*L2.Py();     A01 =-inv_det*L2.Px();
  A10 =-inv_det*L1.Py();     A11 = inv_det*L1.Px();
  C0  = (Met+L1+L2).Px();    C1  = (Met+L1+L2).Py();
  X0  = A00*C0 + A01*C1;     X1  = A10*C0 + A11*C1;
  PxPyPzMVector T1( L1.Px()*X0 , L1.Py()*X0 , L1.Pz()*X0 , 1.777 );    // 1.777 tau mass                                                                                                                                      
  PxPyPzMVector T2( L2.Px()*X1 , L2.Py()*X1 , L2.Pz()*X1 , 1.777 );
  if(X0>0.&&X1>0.)return  (T1+T2).M();
  else            return -(T1+T2).M();
}

std::vector<int> boundaries_runPeriod2016 = {272007,275657,276315,276831,277772,278820,280919};
std::vector<int> boundaries_runPeriod2017 = {297020,299337,302030,303435,304911};
std::vector<int> boundaries_runPeriod2018 = {315252,316998,319313,320394};

std::vector<double> lumis_runPeriod2016 = {5.75, 2.573, 4.242, 4.025, 3.105, 7.576, 8.651};
std::vector<double> lumis_runPeriod2017 = {4.802,9.629,4.235,9.268,13.433};
std::vector<double> lumis_runPeriod2018 = {13.978 , 7.064 , 6.899 , 31.748};

bool cumul_lumis_isInit = false;
std::vector<float> cumul_lumis_runPeriod2016;
std::vector<float> cumul_lumis_runPeriod2017;
std::vector<float> cumul_lumis_runPeriod2018;

int runPeriod(int run, int year){
  std::vector<int> boundaries;
  if (year == 2016)
    boundaries = boundaries_runPeriod2016;
  else if (year == 2017)
    boundaries = boundaries_runPeriod2017;
  else if (year == 2018)
    boundaries = boundaries_runPeriod2018;
  else{
    std::cout << "Wrong year " << year << std::endl;
    return -99;
  }
  auto period = std::find_if(boundaries.begin(),boundaries.end(),[run](const int &y){return y>run;});
  return std::distance(boundaries.begin(),period)-1 + ( (year == 2017) ? 7 : 0 ) + ( (year == 2018) ? 12 : 0 ) ;
}

TRandom3 rand_generator_RunDependentMC(0);
int hashBasedRunPeriod2017(int isData, int run, int lumi, int event, int year){
  if (isData) return runPeriod(run,year);
  if (!cumul_lumis_isInit){
    cumul_lumis_runPeriod2016.push_back(0);
    cumul_lumis_runPeriod2017.push_back(0);
    cumul_lumis_runPeriod2018.push_back(0);
    float tot_lumi_2016 = std::accumulate(lumis_runPeriod2016.begin(),lumis_runPeriod2016.end(),float(0.0));
    float tot_lumi_2017 = std::accumulate(lumis_runPeriod2017.begin(),lumis_runPeriod2017.end(),float(0.0));
    float tot_lumi_2018 = std::accumulate(lumis_runPeriod2018.begin(),lumis_runPeriod2018.end(),float(0.0));

    for (uint i=0; i<lumis_runPeriod2016.size(); i++) cumul_lumis_runPeriod2016.push_back(cumul_lumis_runPeriod2016.back()+lumis_runPeriod2016[i]/tot_lumi_2016);
    for (uint i=0; i<lumis_runPeriod2017.size(); i++) cumul_lumis_runPeriod2017.push_back(cumul_lumis_runPeriod2017.back()+lumis_runPeriod2017[i]/tot_lumi_2017);
    for (uint i=0; i<lumis_runPeriod2018.size(); i++) cumul_lumis_runPeriod2018.push_back(cumul_lumis_runPeriod2018.back()+lumis_runPeriod2018[i]/tot_lumi_2018);
    cumul_lumis_isInit = true;
  }
  Int_t x = 161248*run+2136324*lumi+12781432*event;
  unsigned int hash = TString::Hash(&x,sizeof(Int_t));
  rand_generator_RunDependentMC.SetSeed(hash);
  float val = rand_generator_RunDependentMC.Uniform();
  
  vector<float> cumul;
  if (year == 2016) cumul = cumul_lumis_runPeriod2016;
  else if (year == 2017) cumul = cumul_lumis_runPeriod2017;
  else if (year == 2018) cumul = cumul_lumis_runPeriod2018;
  else{
    std::cout << "Wrong year " << year << std::endl;
    return -99;
  }
  auto period = std::find_if(cumul.begin(),cumul.end(),[val](const float &y){return y>val;});
  return std::distance(cumul.begin(),period)-1 + ( (year == 2017) ? 7 : 0 ) + ( (year == 2018) ? 12 : 0 );
}
