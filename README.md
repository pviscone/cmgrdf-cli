# CMGRDF

## Setup recipe

To install, from outside CMSSW, and with python3 (e.g. lxplus8.cern.ch):
```bash
git clone https://:@gitlab.cern.ch:8443/cms-new-cmgtools/cmgrdf-prototype.git
cd cmgrdf-prototype 
make -j 3
```

To set up your environment (path, python path, ...), from the main directory:
```bash
eval $(make env)
```

## Overview of the model

An analysis task is characterized by the following items:
 * A list of Processes (MC and Data samples), that defines the source data (and may have some sample-specific processing configuration hooks)
 * One or more Flows, that define how the data is to be processed in general: event selection, definition of new variables, per-event weights, uncertaintes...
 * One or more Plots or other targets
 * Optionally, a list of eras, e.g. corresponding to data-taking years. There's no specific type for eras, they can be ints, strings, ...
 The typical processing mode would be to submit one or more tasks, and then tell the code to run all and return the results.
  * The result will be a `MultiReport`, which is a list of `MultiKey` (smart tuples containing information like the flow name, era, plot name, etc...) and values, which has the interface to regroup stuff by removing keys

## Data: Processes, Samples, Sources

* A Source is a file, or set of files, from which a RooDataFrame can be created. It is normally created by internally by the Sample class.
* A Sample is a homoneneous set of events used for one purpose, typically corresponding to a dataset in DAS. There are 3 specific subclasses: `MCSample`, `DataDrivenSample` or `DataSample`, depending on the content.
   * `MCSample` must have a cross seciton (`xsec`) and a gen weight name (the default picks the names used in NanoAOD). The sum of gen weights can be precomputed or the tool itself can compute it later when needed from the Runs tree.
   * All samples can have customizations for the event processing, e.g. extra gen-level cuts, applications of the fake rate, ...
   * If eras are used, a sample has to have a list of one or more eras for which it is available.
   * A sample can be created by passing a path (file name, directory name, file pattern, ...) that may include `{name}` and `{era}` placeholders, or by passing either a Source object or a dictionary mapping eras to source objects
* A Process is a group of samples that is put together as a single entry into plots, yields, datacards.
   * The process defines the display options like a pretty label, colors, etc.

## Processing: Flow, Steps 

* A Flow is a sequence of processing steps: cuts, variable definitions, ...
  * Steps can be shared across multiple flows (e.g. common definitions or preselection cuts)
  * Some steps may apply only on some sample types (MC, Data, ...) or eras, and individual Sample may have further hooks to customize the flow applied to them
* When data has to be processed, the tool takes care of assembling for each source a RooDataFrame the full RooDataFrame graph, and if multiple flows share a common initial part the corresponding RooDataFrame nodes are only created once.

### To Do

 * Normalization Uncertainties in a better way
 * Document MCGroup
 * Test a fake rate method
 * Test roo-fit related stuff
 * Implement creating datacards
 * Print cut flow report
 * Luminosity in plot printer: how? attach lumi to PlotResult?
 * Caching