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
  bool addSampleAndRun(const std::string &name,
                       const std::vector<std::string> &files,
                       const std::string &genSumName = "_auto_",
                       bool warn = false);

  void doAllNow() {
    for (Sample &s : samples_)
      computeSumNow(s);
  }

  void doAllOld() {
    for (Sample &s : samples_)
      computeOldStyle(s);
  }

  void doAllMulti();

  double weightSumByName(const std::string &sampleName) {
    for (const Sample &s : samples_) {
      if (s.name == sampleName)
        return s.weightSum;
    }
    return -99;
  }

  double weightSumByFile(const std::string &fileName) {
    int idx = file2sample_[fileName];
    if (idx)
      return samples_[idx - 1].weightSum;
    return -99;
  }

  unsigned int nSamples() const { return samples_.size(); }

  double weightBySampleInfo(const ROOT::RDF::RSampleInfo &id) {
    const std::string &sid = id.AsString();
    return weightSumByFile(sid.substr(0, sid.rfind("/")));
  }

  class CopiableCaller {
  public:
    CopiableCaller(GenWeightProvider *provider = nullptr) : provider_(provider) {}
    double operator()(unsigned int /*slot*/, const ROOT::RDF::RSampleInfo &id) { return provider_->weightBySampleInfo(id); }

  private:
    GenWeightProvider *provider_;
  };
  ROOT::RDF::RNode attachAsDefinePerSample(ROOT::RDF::RNode &rdf, const std::string &colName) {
    return rdf.DefinePerSample(colName, CopiableCaller(this));
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

    Sample(const std::string &aname,
           const std::vector<std::string> &somefiles,
           const std::string &genSumName = "_auto_")
        : name(aname), files(somefiles), sumName(genSumName), weightSumAvailable(false), weightSum(-99) {}

    void setSum(double sum) {
      weightSum = sum;
      weightSumAvailable = true;
    }

    std::unique_ptr<LazySum> lazySum;
    bool bookLazySum();
    const ROOT::RDF::RResultPtr<double> &lazyHandle() ;
    void doneLazy();
  };

  std::vector<Sample> samples_;
  std::unordered_map<std::string, int> file2sample_;

  static void computeSumNow(Sample &sample) { sample.setSum(LazySum(sample.sumName, sample.files).sum.GetValue()); }

  static void computeOldStyle(Sample &sample);
};

#endif