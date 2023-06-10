#include "jsonFilter.h"
#include <fstream>
#include <nlohmann/json.hpp>

const JsonFilter& JsonFilter::load(const std::string& filename) {
  static std::unordered_map<std::string, JsonFilter> cache;
  auto match = cache.find(filename);
  if (match == cache.end()) {
    std::ifstream in(filename);
    nlohmann::json data = nlohmann::json::parse(in);
    JsonFilter parsedData;
    for (nlohmann::json::iterator it = data.begin(); it != data.end(); ++it) {
      unsigned int run = std::atoi(it.key().c_str());
      std::vector<lumi_range>& lumis = parsedData.data[run];
      for (auto& el : it.value())
        lumis.emplace_back(el[0], el[1]);
    }
    cache[filename] = parsedData;
    match = cache.find(filename);
  }
  return match->second;
}

bool JsonFilter::operator()(unsigned int run) const {
  auto match = data.find(run);
  return (match != data.end()) && !match->second.empty();
}

bool JsonFilter::operator()(unsigned int run, unsigned short int lumi) const {
  auto match = data.find(run);
  if (match != data.end())
    for (const lumi_range& r : match->second)
      if (r.first <= lumi && lumi <= r.second)
        return true;
  return false;
}