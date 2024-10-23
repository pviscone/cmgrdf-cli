#include "genWeightProvider.h"

#include <TTree.h>
#include <TFile.h>
#include <TChain.h>
#include <TH1.h>
#include <TROOT.h>
#include <ROOT/RDFHelpers.hxx>



bool GenWeightProvider::addSampleWithSum(const std::string &name,
                                         const std::vector<std::string> &files,
                                         const std::string &genSumName,
                                         double sum,
                                         bool warn) {
  bool added = addSample(name, files, genSumName, warn);
  if (added) {
    samples_.back().setSum(sum);
  } else {
    double existingSum = weightSumByFile(files.front());
    double minScale = std::min(std::abs(sum), std::abs(existingSum));
    if (std::abs(sum - existingSum) > 1e-7 * minScale) {
      std::cout << "ERROR: for sample " << name << " (file " << files.front() << "), mismatch of sum. found " << sum
                << ", exising " << existingSum << ", diff " << std::abs(sum - existingSum)
                << ", relative: " << std::abs(sum - existingSum) / (minScale ? minScale : 1) << std::endl;
    }
  }
  return added;
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

void GenWeightProvider::registerXSec(const std::string &name, const std::vector<std::string> &files, float xsec) {
  auto match = file2sample_.find(files.front());
  if (match == file2sample_.end())
    throw std::logic_error("Missing sample " + name + " file: " + files.front());
  samples_[match->second - 1].xsec = xsec;
}

void GenWeightProvider::registerExtraWeight(const std::string &name,
                                            const std::vector<std::string> &files,
                                            float weight) {
  auto match = file2sample_.find(files.front());
  if (match == file2sample_.end())
    throw std::logic_error("Missing sample " + name + " file: " + files.front());
  samples_[match->second - 1].extraWeight = weight;
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
    } else {
      throw std::logic_error("ERROR: can't find gen sum name in sample " + sample.name);
    }
  }
  chain.Draw("0.5>>htemp(1,0,1)", sample.sumName.c_str(), "GOFF");
  TH1 *hist = dynamic_cast<TH1 *>(gROOT->FindObject("htemp"));
  sample.setSum(hist->GetBinContent(1));
}
