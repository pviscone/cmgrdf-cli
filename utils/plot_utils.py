import os
import multiprocessing as mp
import uproot
import matplotlib.pyplot as plt
from plothist import plot_comparison
from utils.plotters import TH1, TH2
from utils import folders


def _drawPyPlots(path, all_processes, plot, plot_lumi, cmstext, lumitext, noStack, ratio, ratiorange, ratiotype):
    if "{lumi" in lumitext:
        lumitext = lumitext.format(lumi=plot_lumi)
    density = getattr(plot, "density", False)
    log = getattr(plot, "log", "")
    file = uproot.open(path)
    hist_type = str(type(file[list(all_processes.keys())[0]]))
    if "TH1" in hist_type:
        fig, ax = None ,[None, None]
        if ratio:
            fig, ax =plt.subplots(2, 1, gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.}, sharex=True)
        h = TH1(cmstext = cmstext,
            lumitext= lumitext,
            xlabel = plot.xlabel if not ratio else None,
            ylabel = "Density" if density else "Events",
            log = log,
            fig = fig,
            ax = ax[0],
            grid=False,
        )

        data_hist = file.get("data", False)
        if data_hist:
            data_hist = data_hist.to_hist()
            h.add(data_hist, label="Data", density = density, color = "black", histtype = "errorbar", w2method="poisson")

        bkgs = [process_name for process_name, process_dict in all_processes.items() if not process_dict.get("signal", False)]
        if noStack or len(bkgs) == 0:
            for process_name, process_dict in all_processes.items():
                hist = file[process_name].to_hist()
                color = process_dict.get("color", None)
                h.add(hist, label=process_dict["label"], density = density, color = color, w2method="poisson")
        else: #stack
            signals = [process_name for process_name, process_dict in all_processes.items() if process_dict.get("signal", False)]

            bkg_hist = [file[bkg].to_hist() for bkg in bkgs]
            bkg_labels = [all_processes[bkg]["label"] for bkg in bkgs]
            bkg_colors = [all_processes[bkg].get("color", None) for bkg in bkgs]

            signal_hist = [file[signal].to_hist() for signal in signals]
            signal_labels = [all_processes[signal]["label"] for signal in signals]
            signal_colors = [all_processes[signal].get("color", None) for signal in signals]

            stack_total = sum(bkg_hist)
            h.add(bkg_hist, label=bkg_labels, density = density, color = bkg_colors, stack = True, histtype = "fill")
            h.add(signal_hist, label=signal_labels, density = density, color = signal_colors, stack = False, histtype = "step", w2method="poisson")
            h.add(stack_total, density = density, color = "black", histtype = "step", yerr=False, linewidth=1)
            h.add(stack_total, density = density, color = "black", histtype = "band", label="Total Unc.", w2method="poisson")

            if ratio:
                plt.setp(ax[0].get_yticklabels()[0], visible=False)
                ax[0].set_xlabel("")
                plot_comparison(
                    data_hist,
                    stack_total,
                    xlabel=plot.xlabel,
                    comparison=ratiotype,
                    ax=ax[1],
                    h1_label="Data",
                    h2_label="Pred.",
                    comparison_ylim = ratiorange
                    )

        h.save(f"{path.replace('.root','.png')}")
        h.save(f"{path.replace('.root','.pdf')}")
    elif "TH2" in hist_type:
        for process_name, process_dict in all_processes.items():
            h = TH2(cmstext = cmstext,
                    lumitext= lumitext,
                    xlabel = plot.xlabel,
                    ylabel = plot.ylabel,
                    log = log)
            hist = file[process_name].to_hist()
            h.add(hist, density = density)
            folder = path.replace('.root','')
            folder = folder.rsplit('/',1)[0]+"/2D_"+folder.rsplit('/',1)[1]
            os.makedirs(folder, exist_ok=True)
            os.system(f"cp $CMGRDF/externals/index.php {folder}")
            h.save(os.path.join(folder,f"{process_name}.png"))
            h.save(os.path.join(folder,f"{process_name}.pdf"))


def DrawPyPlots(plots_lumi, flow_plots, all_processes, cmstext, lumitext, noStack, ratio, ratiorange, ratiotype, ncpu=16):
    paths=[f"{folders.outfolder}/{flow}/{plot.name}.root" for (flow, plots) in flow_plots for plot in plots]
    plots = [plot for (_, plots) in flow_plots for plot in plots]
    pool_data=[(path, all_processes, plot, plot_lumi, cmstext, lumitext, noStack, ratio, ratiorange, ratiotype) for path, plot, plot_lumi in zip(paths, plots, plots_lumi)]
    p=mp.Pool(ncpu)
    p.starmap(_drawPyPlots, pool_data)