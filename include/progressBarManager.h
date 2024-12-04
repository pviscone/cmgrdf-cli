#include "ROOT/RDFHelpers.hxx"
#include "TROOT.h"   // IsImplicitMTEnabled
#include "TError.h"  // Warning
#include "TStopwatch.h"
#include "RConfigure.h"  // R__USE_IMT
#include "ROOT/RLogger.hxx"
#include "ROOT/RDF/RLoopManager.hxx"  // for RLoopManager
#include "ROOT/RDF/Utils.hxx"
#include "ROOT/RResultHandle.hxx"  // for RResultHandle, RunGraphs
#ifdef R__USE_IMT
#include "ROOT/TThreadExecutor.hxx"
#endif  // R__USE_IMT

#include "ROOT/RDFHelpers.hxx"
#include "TROOT.h"   // IsImplicitMTEnabled
#include "TError.h"  // Warning
#include "TStopwatch.h"
#include "RConfigure.h"  // R__USE_IMT
#include "ROOT/RLogger.hxx"
#include "ROOT/RDF/RLoopManager.hxx"  // for RLoopManager
#include "ROOT/RDF/Utils.hxx"
#include "ROOT/RResultHandle.hxx"  // for RResultHandle, RunGraphs
#ifdef R__USE_IMT
#include "ROOT/TThreadExecutor.hxx"
#endif  // R__USE_IMT

#include <algorithm>
#include <iostream>
#include <set>
#include <cstdio>

// TODO, this function should be part of core libraries
#include <numeric>
#if (!defined(_WIN32)) && (!defined(_WIN64))
#include <unistd.h>
#endif

#if defined(_WIN32) || defined(_WIN64)
#define WIN32_LEAN_AND_MEAN
#define VC_EXTRALEAN
#include <io.h>
#include <Windows.h>
#else
#include <sys/ioctl.h>
#endif

#include <array>
#include <chrono>
#include <fstream>
#include <functional>
#include <map>
#include <memory>
#include <mutex>
#include <type_traits>
#include <utility>  // std::index_sequence
#include <vector>

#include <algorithm>
#include <iostream>
#include <set>
#include <cstdio>

int get_tty_size() {
#if defined(_WIN32) || defined(_WIN64)
  if (!_isatty(_fileno(stdout)))
    return 0;
  int width = 0;
  CONSOLE_SCREEN_BUFFER_INFO csbi;
  if (GetConsoleScreenBufferInfo(GetStdHandle(STD_OUTPUT_HANDLE), &csbi))
    width = (int)(csbi.srWindow.Right - csbi.srWindow.Left + 1);
  return width;
#else
  int width = 0;
  struct winsize w;
  ioctl(fileno(stdout), TIOCGWINSZ, &w);
  width = (int)(w.ws_col);
  return width;
#endif
}

class ProgressHelper {
private:
  double EvtPerSec() const;
  std::pair<std::size_t, std::chrono::seconds> RecordEvtCountAndTime();
  void PrintStats(std::ostream &stream, std::size_t currentEventCount, std::chrono::seconds totalElapsedSeconds) const;
  void PrintProgressBar(std::ostream &stream, std::size_t currentEventCount) const;

  std::chrono::time_point<std::chrono::system_clock> fBeginTime = std::chrono::system_clock::now();
  std::chrono::time_point<std::chrono::system_clock> fLastPrintTime = fBeginTime;
  std::chrono::seconds fPrintInterval{1};

  std::atomic<std::size_t> fProcessedEvents{0};
  std::size_t fLastProcessedEvents{0};
  std::size_t fIncrement;

  mutable std::mutex fSampleNameToEventEntriesMutex;
  std::map<std::string, ULong64_t> fSampleNameToEventEntries;  // Filename, events in the file

  std::array<double, 20> fEventsPerSecondStatistics;
  std::size_t fEventsPerSecondStatisticsIndex{0};

  unsigned int fBarWidth;
  unsigned int fTotalEvents;

  std::mutex fPrintMutex;
  bool fIsTTY;
  bool fUseShellColours;

  std::shared_ptr<TTree> fTree{nullptr};

public:
  /// Create a progress helper.
  /// \param increment RDF callbacks are called every `n` events. Pass this `n` here.
  /// \param totalFiles read total number of files in the RDF.
  /// \param progressBarWidth Number of characters the progress bar will occupy.
  /// \param printInterval Update every stats every `n` seconds.
  /// \param useColors Use shell colour codes to colour the output. Automatically disabled when
  /// we are not writing to a tty.
  ProgressHelper(std::size_t increment,
                 unsigned int progressBarWidth = 40,
                 unsigned int printInterval = 1,
                 bool useColors = true);

  ~ProgressHelper() = default;

  friend class ProgressBarAction;
  void incretmentTotalEvents(unsigned int totalEvents) { fTotalEvents += totalEvents; }

  /// Register a new sample for completion statistics.
  /// \see ROOT::RDF::RInterface::DefinePerSample().
  /// The *id.AsString()* refers to the name of the currently processed file.
  /// The idea is to populate the  event entries in the *fSampleNameToEventEntries* map
  /// by selecting the greater of the two values:
  /// *id.EntryRange().second* which is the upper event entry range of the processed sample
  /// and the current value of the event entries in the *fSampleNameToEventEntries* map.
  /// In the single threaded case, the two numbers are the same as the entry range corresponds
  /// to the number of events in an individual file (each sample is simply a single file).
  /// In the multithreaded case, the idea is to accumulate the higher event entry value until
  /// the total number of events in a given file is reached.
  void registerNewSample(unsigned int /*slot*/, const ROOT::RDF::RSampleInfo &id) {
    std::lock_guard<std::mutex> lock(fSampleNameToEventEntriesMutex);
    fSampleNameToEventEntries[id.AsString()] =
        std::max(id.EntryRange().second, fSampleNameToEventEntries[id.AsString()]);
  }

  /// Thread-safe callback for RDataFrame.
  /// It will record elapsed times and event statistics, and print a progress bar every n seconds (set by the
  /// fPrintInterval). \param slot Ignored. \param value Ignored.
  template <typename T>
  void operator()(unsigned int /*slot*/, T &value) {
    operator()(value);
  }
  // clang-format off
   /// Thread-safe callback for RDataFrame.
   /// It will record elapsed times and event statistics, and print a progress bar every n seconds (set by the fPrintInterval).
   /// \param value Ignored.
  // clang-format on
  template <typename T>
  void operator()(T & /*value*/) {
    using namespace std::chrono;
    // ***************************************************
    // Warning: Here, everything needs to be thread safe:
    // ***************************************************
    fProcessedEvents += fIncrement;

    // We only print every n seconds.
    if (duration_cast<seconds>(system_clock::now() - fLastPrintTime) < fPrintInterval) {
      return;
    }

    // ***************************************************
    // Protected by lock from here:
    // ***************************************************
    if (!fPrintMutex.try_lock())
      return;
    std::lock_guard<std::mutex> lockGuard(fPrintMutex, std::adopt_lock);

    std::size_t eventCount;
    seconds elapsedSeconds;
    std::tie(eventCount, elapsedSeconds) = RecordEvtCountAndTime();

    if (fIsTTY)
      std::cout << "\r";

    PrintProgressBar(std::cout, eventCount);
    PrintStats(std::cout, eventCount, elapsedSeconds);

    if (fIsTTY)
      std::cout << std::flush;
    else
      std::cout << std::endl;
  }

  std::size_t ComputeNEventsSoFar() const {
    std::unique_lock<std::mutex> lock(fSampleNameToEventEntriesMutex);
    std::size_t result = 0;
    for (const auto &item : fSampleNameToEventEntries)
      result += item.second;
    return result;
  }

  unsigned int ComputeCurrentFileIdx() const {
    std::unique_lock<std::mutex> lock(fSampleNameToEventEntriesMutex);
    return fSampleNameToEventEntries.size();
  }
};

class ProgressBarAction final : public ROOT::Detail::RDF::RActionImpl<ProgressBarAction> {
public:
  using Result_t = int;

private:
  std::shared_ptr<ProgressHelper> fHelper;
  std::shared_ptr<int> fDummyResult = std::make_shared<int>();

public:
  ProgressBarAction(std::shared_ptr<ProgressHelper> r) : fHelper(std::move(r)) {}

  std::shared_ptr<Result_t> GetResultPtr() const { return fDummyResult; }

  void Initialize() {}
  void InitTask(TTreeReader *, unsigned int) {}

  void Exec(unsigned int) {}

  void Finalize() {}

  std::string GetActionName() { return "ProgressBar"; }
  // dummy implementation of PartialUpdate
  int &PartialUpdate(unsigned int) { return *fDummyResult; }
};

class ProgressBarManager {
public:
  ProgressBarManager() : fProgress(std::make_shared<ProgressHelper>(1000, 0)), fAction(fProgress), fEnabled(true) {}

  void AddDataFrame(ROOT::RDataFrame dataframe, unsigned int nentries = 0) {
    auto node = ROOT::RDF::AsRNode(dataframe);
    auto r = node.Book<>(fAction);
    r.OnPartialResultSlot(1000, [this](unsigned int slot, auto &&arg) { (*(this->fProgress))(slot, arg); });
    fProgress->incretmentTotalEvents(nentries);
    return;
  }

  bool Enabled() const { return fEnabled; }
  void Enable() { fEnabled = true; }
  void Disable() { fEnabled = false; }

protected:
  std::shared_ptr<ProgressHelper> fProgress;
  ProgressBarAction fAction;
  std::vector<ROOT::RDataFrame> fDataframes;
  std::vector<int> fNentries;
  bool fEnabled;
};
