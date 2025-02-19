## 1.1.0
- Added matplotlib fast style
- Adjusted errorbars for efficiency plots on hist with reweighted entries
- Improved log settings in defaults. Two possible settings: "counts" and "axis". Count set the log on the last axis (the counts), and "axis" on the variable axis. Both can be applied with "axis,counts"
- Improved density settings in defaults for th2. Density is applied only if both axis have the flag density (or if setted by the user in the user_kwargs)

fix:
- Added safeguards against empty regions (0 events)
- Fixed efficiencyPlots system copy command
- fixed empty plot argument
- Added stack signal option
- Disabled cache by default

cmgrdf commit bump
- Plots cleaned, just TH object saved in TFiles
