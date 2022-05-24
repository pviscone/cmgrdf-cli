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
      * The code supports different implementation of computing the sum: early and lazy computation using RDataframe or a simple synchronous one using TChain. The default is the TChain implementation since with the present version of ROOT the RDataframe introduces has a significant overhead for such a simple processing.
   * All samples can have customizations for the event processing, e.g. extra gen-level cuts, applications of the fake rate, ...
   * If eras are used, a sample has to have a list of one or more eras for which it is available.
   * A sample can be created by passing a path (file name, directory name, file pattern, ...) that may include `{name}` and `{era}` placeholders, or by passing either a Source object or a dictionary mapping eras to source objects
   * A `MCGroup` object exists, that can be optionally created from a list of related `MCSamples` that are to be processed identically (e.g. different HT or jet bins). It behaves as a single MCSample for all purposes except for the handling of the sum of gen weights, which is done separately for each individual sample. This reduces a bit the RDataframe overhead of processing many files together.
* A Process is a group of samples that is put together as a single entry into plots, yields, datacards.
   * The process defines the display options like a pretty label, colors, etc.

## Processing: Flow, Steps 

* A Flow is a sequence of processing steps: cuts, variable definitions, ...
  * Steps can be shared across multiple flows (e.g. common definitions or preselection cuts)
  * Some steps may apply only on some sample types (MC, Data, ...) or eras, and individual Sample may have further hooks to customize the flow applied to them
* When data has to be processed, the tool takes care of assembling for each source a RooDataFrame the full RooDataFrame graph, and if multiple flows share a common initial part the corresponding RooDataFrame nodes are only created once.

## Uncertainties

For the moment, the only implemented kind of uncertainty is a weight variation via `CMGRDF.flow.AddWeightUncertainty`, as in the example `run_uncertainties_ttH.py`. 

More complex uncertainties that re-define other branches should also be implementable easily.

Normalization-only uncertainties could be implemented for free scaling the existing histograms, either at the sample or at the process level. This feature was available in CMGTools and is not yet implemented here. Likewise, post-processing of uncertainties (e.g. symmetrization of an uncertainty defined with a single variation) is not implemented.

## Caching:

A simplified caching system is implemented and can be optionally used, as in the example `run_simpleCache_sos.py`. The cache can store:
 * the sum of gen weights for all sources, in a single JSON file
 * histograms (nominal + all  uncertainties), except for the graphical part (e.g. labels, legend, etc.)

The caching system relies on hashes of the input file names (and, if the files are local, their modification time) and the whole processing history (cuts, defines, ...) that is implemented via string expressions. It cannot track changes in externally called C++ code or data files.

Support for caching of the full set of selected events via `Snapshot()` will also soon be added.

### To Do (in random order)

 * Normalization Uncertainties in a better way
 * MCGroup support for different xsection values per sample
 * Yield tables with uncertainties
 * Additional generator weights, e.g. for normalized scale variations
 * Test a fake rate method
 * Test uncertainties that modify non-weight columns (e.g. JECs)
 * Test using a CMGTools sample file to process NanoAODs
 * Test roo-fit related stuff
 * Implement creating datacards
 * Test creating friends and skimming
 * Caching of datasets
