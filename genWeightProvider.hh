#ifndef CMGRDF_genWeightProvider_h
#define CMGRDF_genWeightProvider_h

#include <unordered_map>
#include <vector>
#include <string>
#include <TTree.h>
#include <TFile.h>
#include <Compression.h>
#include <TROOT.h>
#include <ROOT/RDataFrame.hxx>
#include <ROOT/RResultHandle.hxx>
#include <ROOT/RDF/RSampleInfo.hxx>

class GenWeightProvider {
    public:
        GenWeightProvider() {}

        bool addSample(const std::string &name, const std::vector<std::string> &files, const std::string & genSumName = "_auto_", bool warn=true) {
            samples_.emplace_back(name,files,genSumName);
            for (auto f : files) {
                int &idx = file2sample_[f];
                if (idx != 0) {
                    if (samples_[idx-1].files == files) {
                        if (warn) {
                            std::cout << "WARNING: duplicate file " << f << " between " << name << " and " << samples_[idx-1].name << " (same files)" << std::endl;
                        }
                    } else {
                        std::cout << "ERROR: duplicate file " << f << " between " << name << " and " << samples_[idx-1].name << " (NOT same files)" << std::endl;
                    }
                    samples_.pop_back();
                    return false;
                } else {
                    idx = samples_.size();
                }
            }
            return true;
        }

        void doAllNow() {
            for (Sample & s : samples_) computeSumNow(s);
        }

        void doAllMulti() {
            std::vector<ROOT::RDF::RResultHandle> handles;
            for (Sample & s : samples_) {
                if (s.bookLazySum()) {
                    handles.emplace_back(s.lazyHandle());
                }
            }
            ROOT::RDF::RunGraphs(handles);
            for (Sample & s : samples_) {
                s.doneLazy();
            }
        }

        double weightSumByName(const std::string & sampleName) {
            for (const Sample & s : samples_) {
                if (s.name == sampleName) return s.weightSum;
            }
            return -99;
        }

        double weightSumByFile(const std::string & fileName) {
            int idx = file2sample_[fileName];
            if (idx) return samples_[idx-1].weightSum;
            return -99;
        }

        unsigned int nSamples() const {
            return samples_.size();
        }

        double weightBySampleInfo(const ROOT::RDF::RSampleInfo &id) {
            const std::string & sid = id.AsString();
            {
                std::lock_guard lock(mutex_);
                
            }
            return weightSumByFile(sid.substr(0,sid.rfind("/")));
        }

        class CopiableCaller {
            public:
                CopiableCaller(GenWeightProvider *provider = nullptr) : provider_(provider) {}
                double operator()(unsigned int slot, const ROOT::RDF::RSampleInfo &id) {
                   return provider_->weightBySampleInfo(id); 
                } 
            private:
                GenWeightProvider * provider_;
        };
        ROOT::RDF::RNode attachAsDefinePerSample(ROOT::RDF::RNode & rdf, const std::string & colName) {
            return rdf.DefinePerSample(colName, CopiableCaller(this));
        }
    private:
        std::mutex mutex_;

        struct LazySum {
           ROOT::RDataFrame rdf;
           ROOT::RDF::RResultPtr<double> sum;
           LazySum(const std::string & genSumName, const std::vector<std::string> &files) :
            rdf("Runs",files),
            sum(rdf.Sum(genSumName == "_auto_" ? autoSum(rdf) : genSumName)) {}
            static std::string autoSum(ROOT::RDataFrame & rdf) {
                auto cols = rdf.GetColumnNames();
                if (std::find(cols.begin(), cols.end(), "genEventSumw") != cols.end()) {
                    return "genEventSumw";
                } else if (std::find(cols.begin(), cols.end(), "genEventSumw_") != cols.end()) {
                    return "genEventSumw_";
                }
                std::cout << "ERROR: can't find gen sum name in data frame" << std::endl;
                return ""; 
            }
        };
        struct Sample {
            std::string name;
            std::vector<std::string> files;
            std::string sumName;
            bool weightSumAvailable;
            double weightSum;
            Sample(const std::string &aname, const std::vector<std::string> &somefiles, const std::string & genSumName = "_auto_") : 
                name(aname), files(somefiles), sumName(genSumName), weightSumAvailable(false), weightSum(-99) {}
            void setSum(double sum) {
                weightSum = sum;
                weightSumAvailable = true;
            }
            std::unique_ptr<LazySum> lazySum;
            bool bookLazySum() {
               if ((!weightSumAvailable) && !lazySum) {
                   lazySum = std::make_unique<LazySum>(sumName,files);
                   return true;
               }
               return false;
            }
            const ROOT::RDF::RResultPtr<double> & lazyHandle() {
                assert(lazySum);
                return(lazySum->sum);
            }
            void doneLazy() {
                if (lazySum) {
                    assert(lazySum->IsReady());
                    setSum(lazySum->sum.GetValue());
                    lazySum.reset();
                }
            }
        };

        std::vector<Sample> samples_;
        std::unordered_map<std::string,int> file2sample_;


        static void computeSumNow(Sample & sample) {
            sample.setSum(LazySum(sample.sumName, sample.files).sum.GetValue());
        }

};

#endif