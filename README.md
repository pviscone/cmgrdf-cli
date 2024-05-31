# CMGRDF


The package requires a recent version of ROOT, python3, and related dependencies.
We can install the dependencies either with `cvmfs` or `conda`

## Setup recipe - `cvmfs`

On a EL8 machine with CVMFS, e.g. lxplus8.cern.ch, you can get all dependencies with

```bash
source /cvmfs/sft.cern.ch/lcg/views/LCG_104a_cuda/x86_64-centos8-gcc11-opt/setup.sh
````

To install the package, from outside `CMSSSW` and with `python3` you can run

```bash
git clone --recursive https://:@gitlab.cern.ch:8443/cms-new-cmgtools/cmgrdf-prototype.git # or ssh://git@gitlab.cern.ch:7999/cms-new-cmgtools/cmgrdf-prototype.git
cd cmgrdf-prototype 
make -j 3
```

### Other dependencies

#### Combine (recommended)

```bash
pushd externals/HiggsAnalysis/CombinedLimit 
source /cvmfs/sft.cern.ch/lcg/views/LCG_104a_cuda/x86_64-centos8-gcc11-opt/setup.sh
export PATH=${PATH}:${PWD}/build/bin
export LD_LIBRARY_PATH=${LD_LIBRARY_PATH}:${PWD}/build/lib
export PYTHONPATH=${PYTHONPATH}:${PWD}/build/lib/python:${PWD}/build/lib
export CONDA=1 CONDA_PREFIX=/cvmfs/sft.cern.ch/lcg/views/LCG_104a_cuda/x86_64-centos8-gcc11-opt
make -j 8; make
popd
```


#### Correctionlib (recommended) (already included in LCG 102, 102b, dev3 and dev4 stacks)

If you're using a recent LCG stack, e.g 102 or later, or dev3 or dev4, correctionlib is already installed. You can check for other versions in https://lcginfo.cern.ch/pkg/correctionlib/.

For a manual installation,
```bash
git clone --recursive https://github.com/cms-nanoAOD/correctionlib.git externals/correctionlib
pushd externals/correctionlib 
make -j 4
# on cs8 with LC102, this fails misteriously with a missing -lz, you can fix it with
# /cvmfs/sft.cern.ch/lcg/releases/gcc/11.2.0-8a51a/x86_64-centos8/bin/g++ -pthread /lib64/libz.so.1 -fPIC -shared  build/correction.o build/formula_ast.o -o lib/libcorrectionlib.so
# and rerun make
make install
popd
```

#### ONNX Runtime (optional)

```bash
pushd externals
curl -L https://github.com/microsoft/onnxruntime/releases/download/v1.15.1/onnxruntime-linux-x64-1.15.1.tgz | tar xzv
popd
```

#### CMSJMECalculators (optional)

```bash
pip install -e git+https://gitlab.cern.ch/cms-analysis/CMSJMECalculators.git
```

### Running
To set up your environment (path, python path, ...), from the main directory:
```bash
eval $(make env)
```


## Setup recipe - conda

NB: there's a bug in the 2.5.0 version of `correctionlib`, which is the latest available in `conda`. After setting up the code, you should push [this fix](https://github.com/cms-nanoAOD/correctionlib/commit/fa17477cc87752aba621ae9e97fcd843ba2ba5c9), specifically the changes in `src/correctionlib/binding.py`

```bash
git clone --recursive https://:@gitlab.cern.ch:8443/cms-new-cmgtools/cmgrdf-prototype.git # or ssh://git@gitlab.cern.ch:7999/cms-new-cmgtools/cmgrdf-prototype.git
cd cmgrdf-prototype 
mamba env create -f environment.yml
conda activate cmgrdf
make -j 3
```

### Other dependencies

#### Combine (recommended)
```bash
pushd externals/HiggsAnalysis/CombinedLimit 
source set_conda_env_vars.sh
conda deactivate
conda activate cmgrdf
make CONDA=1 -j 8
popd
```


#### ONNX Runtime (optional)

```bash
pushd externals
curl -L https://github.com/microsoft/onnxruntime/releases/download/v1.15.1/onnxruntime-linux-x64-1.15.1.tgz | tar xzv
popd
```

#### CMSJMECalculators (optional)

```bash
pip install -e git+https://gitlab.cern.ch/cms-analysis/CMSJMECalculators.git
```


### Running
To set up your environment (path, python path, ...), from the main directory:
```bash
eval $(make env)
```

## Overview of the model

An analysis task is characterized by the following items:
 * A list of Processes (MC and Data samples), that defines the source data (and may have some sample-specific processing configuration hooks)
 * One or more Flows, that define how the data is to be processed in general: event selection, definition of new variables, per-event weights, uncertaintes...
 * One or more Plots, Yields or other targets
 * Optionally, a list of eras, e.g. corresponding to data-taking years. There's no specific type for eras, they can be ints, strings, ...
 
The typical processing mode would be to submit one or more tasks, and then tell the code to run all and return the results.
  * The result will be a `MultiReport`, which is a list of `MultiKey` (smart tuples containing information like the flow name, era, plot name, etc...) and values, which has the interface to regroup stuff by removing keys

## Data: Processes, Samples, Sources

* A Source is a file, or set of files, from which a RooDataFrame can be created. It is normally created by internally by the Sample class.
* A Sample is a homoneneous set of events used for one purpose, typically corresponding to a dataset in DAS. There are 3 specific subclasses: `MCSample`, `DataDrivenSample` or `DataSample`, depending on the content.
   * `MCSample` normally must have a cross section (`xsec`) and a gen weight name (the default picks the names used in NanoAOD). The sum of gen weights can be precomputed or the tool itself can compute it later when needed from the Runs tree.
      * The code supports different implementation of computing the sum: early and lazy computation using RDataframe or a simple synchronous one using TChain. The default is the TChain implementation since with the present version of ROOT the RDataframe introduces has a significant overhead for such a simple processing.
      * If using instead MC samples that have already a precomputed per-event weight that accounts for cross section and luminosity, e.g. produced from a `Snapshot`, by setting both  the `xsec` and the `genWeightName` to `None`, and defining `weight` appropriately.
   * All samples can have customizations for the event processing, e.g. extra gen-level cuts, applications of the fake rate, sample-specifc uncertainties, ...
   * If eras are used, a sample has to have a list of one or more eras for which it is available.
   * A sample can be created by passing a path (file name, directory name, file pattern, ...) that may include `{name}` and `{era}` placeholders, or by passing either a Source object or a dictionary mapping eras to source objects
   * Normalization-only uncertainties can be attached to the sample objects, and will be applied after the RDF processing. When caching is used, the normalization uncertainties can be changed without invalidating the cache, as they are applied afterwards.
   * A `MCGroup` object exists, that can be optionally created from a list of related `MCSamples` that are to be processed identically (e.g. different HT or jet bins). It behaves as a single MCSample for all purposes except for the handling of the sum of gen weights, which is done separately for each individual sample. This reduces a bit the RDataframe overhead of processing many files together.
* A Process is a group of samples that is put together as a single entry into plots, yields, datacards.
   * The process defines the display options like a pretty label, colors, etc.
   * Normalization-only uncertainties can be attached to the processes, and will be applied to all the samples they contain

## Processing: Flow, Steps, Targets

* A Flow is a sequence of processing steps: cuts, variable definitions, ...
  * Steps can be shared across multiple flows (e.g. common definitions or preselection cuts)
  * Some steps may apply only on some sample types (MC, Data, ...) or eras, and individual Sample may have further hooks to customize the flow applied to them
* A target is some end result, which currently can be a Plot, a Yield or a Snapshot
* When data has to be processed, the tool takes care of assembling for each source a RooDataFrame the full RooDataFrame graph, and if multiple flows share a common initial part the corresponding RooDataFrame nodes are only created once.

## Uncertainties

There are three kinds of uncertainties that can be applied:
 * Normalization-only uncertainties, that scale the histograms at sample or process level. These are set in the properties of the Sample or Process object, and applied by the framework after the RDF processing is done (or after the histograms are read from the cache) and so they are cheap to compute. 
   * Note that if different samples within a single process are associated different normalization uncertainties, the resulting uncertainty at the level of process will be a shape uncertainty (but it will still be cheap to compute).
 * Event-by-event weight uncertainties, implemented via `CMGRDF.flow.AddWeightUncertainty`, as in the example `run_uncertainties_ttH.py` 
 * Event-by-event arbitrary uncertainties, implemented directly via `CMGRDF.flow.Vary` to change the definition of a given column, e.g. `python/
CMGRDF/cms/MuonRoccoR.py`
   * The extended RDF syntax for a simultaneous variation of multiple columns is not yet supported, but will be added soon

Post-processing of uncertainties, e.g. symmetrization or normalization, is not implemented at the moment but could be added.

When producing plots, the returned results are implemented with the `HistoWithNuisances` class, that contain the nominal template and all the uncertainty variations. Likewise, event yields are implemented `YieldWithNusiances` class.
  * These classes have implemented the support for creation of RooFit objects and computation of post-fit results & uncertainties, ported from CMGTools, but they have not been tested yet in CMGRDF, they will be added soon.

## Caching:

A simplified caching system is implemented and can be optionally used, as in the example `run_simpleCache_sos.py`. The cache can store:
 * the sum of gen weights for all sources, in a single JSON file
 * histograms (nominal + all  uncertainties), except for the graphical part (e.g. labels, legend, etc.)

The caching system relies on hashes of the input file names (and, if the files are local, their modification time) and the whole processing history (cuts, defines, ...) that is implemented via string expressions. It cannot track changes in externally called C++ code or data files.


## Runnig in Jupyter and SWAN

To use CMGRDF in a jupyter notebook, simply start `jupyter-notebook --no-browser --port NNNN` from the PC where CMGRDF is installed and after initializing the environment, and then connect to it from your browser (typically you need to `ssh -L NNNN:127.0.0.1:NNNN` to redirect your local port and avoid the firewall)

The library can also be used under SWAN: https://swan.cern.ch/
 * Open SWAN with a recent LGC stack (e.g. the development version), and create a project under SWAN
 * Clone the CMGRDF repository inside the project, or elsewhere on your EOS user area (this step is more easily done from lxplus)
 * Within SWAN, open a terminal, go into the CMGRDF directory and `make clean && make -j 4` to recompile it so that it is linked to the software stack of SWAN
 * Create a Python3 notebook and put some initialization of the environment, e.g. 
```python
import sys, os
os.environ["CMGRDF"] = "/eos/user/g/gpetrucc/SWAN_projects/CMGRDF-test/cmgrdf-prototype"
os.environ["LD_LIBRARY_PATH"] += ":"+os.environ["CMGRDF"]+"/lib"
sys.path.append(os.environ["CMGRDF"]+"/python")

import ROOT
from CMGRDF import *
 ``` 
 * Configure the PlotSetPrinter to display the png files inline in the jupyter by passing `, plotFormats="png,jupyter"` in the constructor.

### To Do (in random order)

 * MCGroup support for different xsection values per sample
 * Pretty printout of yield tables with uncertainties
 * Using snapshots as friend trees
 * Cache events with snapshots
 * Additional generator weights, e.g. for normalized scale variations
 * Test a fake rate method
 * Test roo-fit related stuff
 * Test distributed processing
 * Batch processing for skimming or friend production?
 * More CI & building reference documentation
