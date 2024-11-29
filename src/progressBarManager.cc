#include "progressBarManager.h"

ProgressHelper::ProgressHelper(std::size_t increment,
                               unsigned int progressBarWidth,
                               unsigned int printInterval,
                               bool useColors)
    : fPrintInterval(printInterval),
      fIncrement{increment},
      fBarWidth{progressBarWidth = int(get_tty_size() / 4)},
      fTotalEvents{0},
#if defined(_WIN32) || defined(_WIN64)
      fIsTTY{_isatty(_fileno(stdout)) != 0},
      fUseShellColours{false && useColors}
#else
      fIsTTY{isatty(fileno(stdout)) == 1},
      fUseShellColours{useColors && fIsTTY}  // Control characters only with terminals.
#endif
{
}

/// Compute a running mean of events/s.
double ProgressHelper::EvtPerSec() const {
  if (fEventsPerSecondStatisticsIndex < fEventsPerSecondStatistics.size())
    return std::accumulate(fEventsPerSecondStatistics.begin(),
                           fEventsPerSecondStatistics.begin() + fEventsPerSecondStatisticsIndex,
                           0.) /
           fEventsPerSecondStatisticsIndex;
  else
    return std::accumulate(fEventsPerSecondStatistics.begin(), fEventsPerSecondStatistics.end(), 0.) /
           fEventsPerSecondStatistics.size();
}

/// Record current event counts and time stamp, populate evts/s statistics array.
std::pair<std::size_t, std::chrono::seconds> ProgressHelper::RecordEvtCountAndTime() {
  using namespace std::chrono;

  auto currentEventCount = fProcessedEvents.load();
  auto eventsPerTimeInterval = currentEventCount - fLastProcessedEvents;
  fLastProcessedEvents = currentEventCount;

  auto oldPrintTime = fLastPrintTime;
  auto newPrintTime = system_clock::now();
  fLastPrintTime = newPrintTime;

  duration<double> secondsCurrentInterval = newPrintTime - oldPrintTime;
  fEventsPerSecondStatistics[fEventsPerSecondStatisticsIndex++ % fEventsPerSecondStatistics.size()] =
      eventsPerTimeInterval / secondsCurrentInterval.count();

  return {currentEventCount, duration_cast<seconds>(newPrintTime - fBeginTime)};
}

namespace {

  struct RestoreStreamState {
    RestoreStreamState(std::ostream &stream) : fStream(stream), fFlags(stream.flags()), fFillChar(stream.fill()) {}
    ~RestoreStreamState() {
      fStream.flags(fFlags);
      fStream.fill(fFillChar);
    }

    std::ostream &fStream;
    std::ios_base::fmtflags fFlags;
    std::ostream::char_type fFillChar;
  };

  /// Format std::chrono::seconds as `1:30m`.
  std::ostream &operator<<(std::ostream &stream, std::chrono::seconds elapsedSeconds) {
    RestoreStreamState restore(stream);
    auto h = std::chrono::duration_cast<std::chrono::hours>(elapsedSeconds);
    auto m = std::chrono::duration_cast<std::chrono::minutes>(elapsedSeconds - h);
    auto s = (elapsedSeconds - h - m).count();

    if (h.count() > 0)
      stream << h.count() << ':' << std::setw(2) << std::right << std::setfill('0');
    stream << m.count() << ':' << std::setw(2) << std::right << std::setfill('0') << s;
    return stream << (h.count() > 0 ? 'h' : 'm');
  }

}  // namespace

/// Print event and time statistics.
void ProgressHelper::PrintStats(std::ostream &stream,
                                std::size_t currentEventCount,
                                std::chrono::seconds elapsedSeconds) const {
  RestoreStreamState restore(stream);
  auto evtpersec = EvtPerSec();

  if (fUseShellColours)
    stream << "\033[35m";
  stream << "["
         << "Elapsed time: " << elapsedSeconds << "  ";

  stream << "processed evts: " << currentEventCount;
  if (fTotalEvents != 0) {
    stream << " / " << std::scientific << std::setprecision(2) << fTotalEvents;
  }
  stream << "  ";

  if (fUseShellColours)
    stream << "\033[0m";

  // events/s
  stream << std::scientific << std::setprecision(2) << evtpersec << " evt/s";

  // Time statistics:
  if (fUseShellColours)
    stream << "\033[35m";
  std::chrono::seconds remainingSeconds(static_cast<long long>((fTotalEvents - currentEventCount) / evtpersec));
  stream << " " << remainingSeconds << " "
         << " remaining time";
  if (fUseShellColours)
    stream << "\033[0m";

  stream << "]   ";
}

/// Print a progress bar of width `ProgressHelper::fBarWidth` if `fGetNEventsOfCurrentFile` is known.
void ProgressHelper::PrintProgressBar(std::ostream &stream, std::size_t currentEventCount) const {
  RestoreStreamState restore(stream);

  double completion = double(currentEventCount) / fTotalEvents;
  unsigned int nBar = std::min(completion, 1.) * fBarWidth;

  std::string bars(std::max(nBar, 1u), '=');
  bars.back() = (nBar == fBarWidth) ? '=' : '>';

  if (fUseShellColours)
    stream << "\033[33m";
  stream << '|' << std::setfill(' ') << std::setw(fBarWidth) << std::left << bars << "|   ";
  if (fUseShellColours)
    stream << "\033[0m";
}
