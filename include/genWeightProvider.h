#ifndef CMGRDF_genWeightProvider_h
#define CMGRDF_genWeightProvider_h

#include <unordered_map>
#include <vector>
#include <string>
#include <ROOT/RDataFrame.hxx>
#include <ROOT/RResultHandle.hxx>
#include <ROOT/RDF/RSampleInfo.hxx>

class GenWeightProvider {
public:
  GenWeightProvider() {}

  bool addSample(const std::string &name,
                 const std::vector<std::string> &files,
                 const std::string &genSumName = "_auto_",
                 bool warn = false);
  bool addSampleWithSum(const std::string &name,
                        const std::vector<std::string> &files,
                        const std::string &genSumName,
                        double sum,
                        bool warn = false);
  bool addSampleAndRun(const std::string &name,
                       const std::vector<std::string> &files,
                       const std::string &genSumName = "_auto_",
                       bool warn = false);

  void registerXSec(const std::string &name, const std::vector<std::string> &files, float xsec);

  void registerExtraWeight(const std::string &name, const std::vector<std::string> &files, float weight);

  void doAllNow() {
    for (Sample &s : samples_)
      if (!s.weightSumAvailable)
        computeSumNow(s);
  }

  void doAllOld() {
    for (Sample &s : samples_)
      if (!s.weightSumAvailable)
        computeOldStyle(s);
  }

  void doAllMulti();

  double weightSumByName(const std::string &sampleName) {
    auto match = name2sample_.find(sampleName);
    if (match == name2sample_.end())
      throw std::logic_error("Missing weight sum for sample " + sampleName);
    return samples_[match->second].weightSum;
  }

  double weightSumByFile(const std::string &fileName) {
    int idx = file2sample_[fileName];
    if (idx)
      return samples_[idx - 1].weightSum;
    throw std::logic_error("Missing weight sum for file " + fileName);
  }

  unsigned int nSamples() const { return samples_.size(); }

  double weightBySampleInfo(const ROOT::RDF::RSampleInfo &id) {
    const std::string &sid = id.AsString();
    return weightSumByFile(sid.substr(0, sid.rfind("/")));
  }

  double extraWeightBySampleInfo(const ROOT::RDF::RSampleInfo &id) {
    const std::string &sid = id.AsString();
    const std::string &fname = sid.substr(0, sid.rfind("/"));
    int idx = file2sample_[fname];
    if (idx)
      return samples_[idx - 1].extraWeight;
    throw std::logic_error("Missing extra weight for file " + fname);
  }

  double xsecBySampleInfo(const ROOT::RDF::RSampleInfo &id) {
    const std::string &sid = id.AsString();
    const std::string &fname = sid.substr(0, sid.rfind("/"));
    int idx = file2sample_[fname];
    if (idx)
      return samples_[idx - 1].xsec;
    throw std::logic_error("Missing cross section for file " + fname);
  }

  class CopiableCaller {
  public:
    enum class WhatToFetch { WeightSum, XSec, ExtraWeight };
    CopiableCaller(GenWeightProvider *provider = nullptr, WhatToFetch what = WhatToFetch::WeightSum)
        : provider_(provider), what_(what) {}
    double operator()(unsigned int /*slot*/, const ROOT::RDF::RSampleInfo &id) {
      switch (what_) {
        case WhatToFetch::WeightSum:
          return provider_->weightBySampleInfo(id);
        case WhatToFetch::XSec:
          return provider_->xsecBySampleInfo(id);
        case WhatToFetch::ExtraWeight:
          return provider_->extraWeightBySampleInfo(id);
      }
      throw std::logic_error("Unreachable");
    }

  private:
    GenWeightProvider *provider_;
    WhatToFetch what_;
  };
  ROOT::RDF::RNode attachAsDefinePerSample(ROOT::RDF::RNode &rdf,
                                           const std::string &colName,
                                           const std::string &whatToFetch = "weightSum") {
    if (whatToFetch == "weightSum")
      return rdf.DefinePerSample(colName, CopiableCaller(this));
    else if (whatToFetch == "xsec")
      return rdf.DefinePerSample(colName, CopiableCaller(this, CopiableCaller::WhatToFetch::XSec));
    else if (whatToFetch == "extraWeight")
      return rdf.DefinePerSample(colName, CopiableCaller(this, CopiableCaller::WhatToFetch::ExtraWeight));
    throw std::logic_error("unsupported value for whatToFetch = " + whatToFetch);
  }

private:
  std::mutex mutex_;

  struct LazySum {
    ROOT::RDataFrame rdf;
    ROOT::RDF::RResultPtr<double> sum;
    LazySum(const std::string &genSumName, const std::vector<std::string> &files)
        : rdf("Runs", files), sum(rdf.Sum(genSumName == "_auto_" ? autoSum(rdf) : genSumName)) {}
    static std::string autoSum(ROOT::RDataFrame &rdf);
  };

  struct Sample {
    std::string name;
    std::vector<std::string> files;
    std::string sumName;
    bool weightSumAvailable;
    double weightSum;
    float xsec, extraWeight;

    Sample(const std::string &aname,
           const std::vector<std::string> &somefiles,
           const std::string &genSumName = "_auto_")
        : name(aname),
          files(somefiles),
          sumName(genSumName),
          weightSumAvailable(false),
          weightSum(-99),
          xsec(-99),
          extraWeight(-99) {}

    void setSum(double sum) {
      weightSum = sum;
      weightSumAvailable = true;
    }

    std::unique_ptr<LazySum> lazySum;
    bool bookLazySum();
    const ROOT::RDF::RResultPtr<double> &lazyHandle();
    void doneLazy();
  };

  std::vector<Sample> samples_;
  std::unordered_map<std::string, int> file2sample_;
  std::unordered_map<std::string, int> name2sample_;

  static void computeSumNow(Sample &sample) { sample.setSum(LazySum(sample.sumName, sample.files).sum.GetValue()); }

  static void computeOldStyle(Sample &sample);
};

#endif