#ifndef CMGRDF_jsonFilter_h
#define CMGRDF_jsonFilter_h

#include <unordered_map>
#include <vector>
#include <string>
#include <algorithm>

class JsonFilter {
public:
  JsonFilter() {}
  static const JsonFilter& load(const std::string& filename);
  bool operator()(unsigned int run) const;
  bool operator()(unsigned int run, unsigned short int lumi) const;

private:
  typedef unsigned short int lumi;
  typedef std::pair<lumi, lumi> lumi_range;
  std::unordered_map<unsigned int, std::vector<lumi_range>> data;
};

#endif