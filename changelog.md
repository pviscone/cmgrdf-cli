## 1.2.0
- removed ANALYSIS_DIR env var
- added cmg_checkout command
- added method to load defaults
- added option to plot arbitrary ratios
- pyplots reformatted and optimized
- option to snap only selected eras
- Tree kwargs safeguard to not overwrite flowstep options
- Tree segment naming now can use {leaf-n} to get the name of the n-th parent
- now you can add `plot_kwargs` to the process dict, kwargs will be passed to the plotter add method (only for non stacked, to be implemented for the rest)
fix:
- log option in histo1d_defaults was always overriden by the pattern_kwarg default

cmgrdf commit bump
- Added XRootD globbing

## 1.1.0
- Added matplotlib fast style
- Adjusted errorbars for efficiency plots on hist with reweighted entries
- Improved log settings in defaults. Two possible settings: "counts" and "axis". Count set the log on the last axis (the counts), and "axis" on the variable axis. Both can be applied with "axis,counts"
- Improved density settings in defaults for th2. Density is applied only if both axis have the flag density (or if setted by the user in the user_kwargs)
- Added stack signal option
- Disabled cache by default
- Added plotFormats option
- tree.add forward the kwargs to all the flowsteps
- Plots have better handling of the `log` and `density` options. `density` can be `axis` or `counts`
- implemented processPattern option
- in pyplots manually compute poissonian yerr to set yerr to 0 for empty bins
- reformatted parse_function util to accept None return arguments
- added declare argument to declare cpp code after str manipulation
- saved cli command in cmgrdf_cli_command env var
- added is_in_command util to perform regex matching on the cli command
- added fullTraceback debug option
- Added Hist3D
- Outputting in the same folder merge the different logs
- disables snapshot for all plotsteps + snapAllSteps option
- added ncpuPyPlot option
- save yields tables also as csv

fix:
- Added safeguards against empty regions (0 events)
- Fixed efficiencyPlots system copy command
- fixed empty plot argument
- caught exception in print_yield to handle Cut with samplePattern
- corrected print yield handling of zero events after cuts
- fixed simoultaneous log and density th2 pyplots
- fixed verbosity option
- wrong indentation caused missing cpp imports
- common flows were randomly created due to the usage of dict instead of orderedDict
- added cmin guards for logz hist2d
- using orderedSets instead of sets in trees to avoid random ordering of common flow segments
- fixed mixed bin definition for th2
- delayed drawpyplot import from plots submodule to allow prior definition of defaults
- safeguard to avoid crash in stacked plots without signals

cmgrdf commit bump
- Plots cleaned, just TH object saved in TFiles
- implemented gensumw == nevents with genSumWeightName = "_nevents_"
- Implemented AliasCollection
- Implemented `define` argument in DefineSkimmedCollection
- added weight argument to plot
- added TH3
- fixed behaviour for multiple defineskimmedcollection step on the same collection
