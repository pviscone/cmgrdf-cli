# CMGRDF examples

Here are some example python scripts for CMGRDF to demonstrate some plotting and basic features of the tool.

## Basic examples
 * `run_simple_MC_nanoAOD.py`: the most basic example, demonstrates processing of a few NanoAOD MC samples out of the box, with a simple set of cuts and plots (and not even valid cross section values)

 * `run_simple_data_ttH.py`: demonstrates basic plotting of data and MC, from the skimmed and processed nanoAOD of the Run 2 ttH analysis:
   * ratio plots
   * making plots from **multiple cut flows** at the same time

* `run_friends_sos.py`: demostration of usage of **eras** and **friend trees**, from the skimmed and processed nanoAOD of the Run 2 SOS  analysis:
   * running on different data years, with some samples that are available for all years and some that are year-specific
   * using friend trees for data and MC
   * use of different ReDefine's for data and MC and different eras

* `run_uncertainties_ttH.py`: demostration of usage of simple **uncertainties** and **C++ functions**:
   * use some Defines and C++ functions from `functions.h` to e.g. define good b-tagged jets, make invariant masses, ...
   * implement uncertainties using weights

* `run_simpleCache_sos.py`: demonstration of caching sums and plots.

## Complex examples

These are mostly for development and stress-testing more complex stuff and replicating CMGTools features.

* `sos/run_sos.py`: runs some plots from the Run 2 SOS  analysis:
  * implement the full MCC corrections as (Re)Defines and DefineDefault
  * create MCSamples for a lot of different MCs, even if not in the most pretty way possible
  * apply gen-level matching to select MC-matched and MC-fake events in the same MC samples
  * use MCGroup to reduce the overhead of processing multiple samples