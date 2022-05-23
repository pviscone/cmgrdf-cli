#include "genWeightProvider.h"

#include <TTree.h>
#include <TFile.h>
#include <TChain.h>
#include <TH1.h>
#include <TROOT.h>
#include <ROOT/RDFHelpers.hxx>

bool GenWeightProvider::addSample(const std::string &name,
                                  const std::vector<std::string> &files,
                                  const std::string &genSumName,
                                  bool warn) {
  samples_.emplace_back(name, files, genSumName);
  for (auto f : files) {
    int &idx = file2sample_[f];
    if (idx != 0) {
      if (samples_[idx - 1].files == files) {
        if (warn) {
          std::cout << "WARNING: duplicate file " << f << " between " << name << " and " << samples_[idx - 1].name
                    << " (same files)" << std::endl;
        }
      } else {
        std::cout << "ERROR: duplicate file " << f << " between " << name << " and " << samples_[idx - 1].name
                  << " (NOT same files)" << std::endl;
      }
      samples_.pop_back();
      return false;
    } else {
      idx = samples_.size();
    }
  }
  return true;
}

bool GenWeightProvider::addSampleAndRun(const std::string &name,
                                        const std::vector<std::string> &files,
                                        const std::string &genSumName,
                                        bool warn) {
  bool added = addSample(name, files, genSumName, warn);
  if (added) {
    computeOldStyle(samples_.back());
  }
  return added;
}

void GenWeightProvider::doAllMulti() {
  std::vector<ROOT::RDF::RResultHandle> handles;
  for (Sample &s : samples_) {
    if (s.bookLazySum()) {
      handles.emplace_back(s.lazyHandle());
    }
  }
  ROOT::RDF::RunGraphs(handles);
  for (Sample &s : samples_) {
    s.doneLazy();
  }
}

std::string GenWeightProvider::LazySum::autoSum(ROOT::RDataFrame &rdf) {
  auto cols = rdf.GetColumnNames();
  if (std::find(cols.begin(), cols.end(), "genEventSumw") != cols.end()) {
    return "genEventSumw";
  } else if (std::find(cols.begin(), cols.end(), "genEventSumw_") != cols.end()) {
    return "genEventSumw_";
  }
  std::cout << "ERROR: can't find gen sum name in data frame" << std::endl;
  return "";
}

bool GenWeightProvider::Sample::bookLazySum() {
  if ((!weightSumAvailable) && !lazySum) {
    lazySum = std::make_unique<LazySum>(sumName, files);
    return true;
  }
  return false;
}
const ROOT::RDF::RResultPtr<double> & GenWeightProvider::Sample::lazyHandle() {
  assert(lazySum);
  return (lazySum->sum);
}

void GenWeightProvider::Sample::doneLazy() {
  if (lazySum) {
    assert(lazySum->sum.IsReady());
    setSum(lazySum->sum.GetValue());
    lazySum.reset();
  }
}

void GenWeightProvider::computeOldStyle(GenWeightProvider::Sample &sample) {
  TChain chain("Runs");
  for (auto &f : sample.files) {
    chain.Add(f.c_str());
  }
  if (sample.sumName == "_auto_") {
    if (chain.GetBranch("genEventSumw") != nullptr) {
      sample.sumName = "genEventSumw";
    } else if (chain.GetBranch("genEventSumw_") != nullptr) {
      sample.sumName = "genEventSumw_";
    }
  }
  chain.Draw("0.5>>htemp(1,0,1)", sample.sumName.c_str(), "GOFF");
  TH1 *hist = dynamic_cast<TH1 *>(gROOT->FindObject("htemp"));
  sample.setSum(hist->GetBinContent(1));
}
