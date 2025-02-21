import os
import concurrent
import uproot
import matplotlib.pyplot as plt
from plothist import plot_comparison
from utils.plotters import TH1, TH2
from utils.folders import folders

def __drawPyPlots(path, all_processes, plot, plot_lumi, cmstext, lumitext, noStack, ratio, ratiorange, ratiotype, grid, stackSignal):
    if "{lumi" in lumitext:
        lumitext = lumitext.format(lumi=plot_lumi)
    file = uproot.open(path)
    hist_type = str(type(file[list(all_processes.keys())[0]]))
    if "TH1" in hist_type:
        fig, ax = None ,[None, None]
        bkgs = [process_name for process_name, process_dict in all_processes.items() if not process_dict.get("signal", False)]
        signals = [process_name for process_name, process_dict in all_processes.items() if process_dict.get("signal", False)]
        if ratio and len(bkgs) > 0:
            fig, ax =plt.subplots(2, 1, gridspec_kw={'height_ratios': [3, 1], 'hspace': 0.}, sharex=True)

        h = TH1(cmstext = cmstext,
            lumitext= lumitext,
            xlabel = plot.xlabel if not ratio else None,
            ylabel = "Density" if getattr(plot, "density", False) else "Events",
            log = plot.log,
            fig = fig,
            ax = ax[0],
            grid=grid,
        )

        data_hist = file.get("data", False)
        if data_hist:
            data_hist = data_hist.to_hist()
            h.add(data_hist, label="Data", density = getattr(plot, "density", False), color = "black", histtype = "errorbar", w2method="poisson")

        if noStack or len(bkgs) == 0:
            for process_name, process_dict in all_processes.items():
                if process_name not in file:
                    continue
                hist = file[process_name].to_hist()
                color = process_dict.get("color", None)
                h.add(hist, label=process_dict["label"], density = getattr(plot, "density", False), color = color, w2method="poisson")
        else: #stack
            bkg_hist = [file[bkg].to_hist() for bkg in bkgs if bkg in file]
            bkg_labels = [all_processes[bkg]["label"] for bkg in bkgs if bkg in file]
            bkg_colors = [all_processes[bkg].get("color", None) for bkg in bkgs if bkg in file]

            signal_hist = [file[signal].to_hist() for signal in signals if signal in file]
            signal_labels = [all_processes[signal]["label"] for signal in signals if signal in file]
            signal_colors = [all_processes[signal].get("color", None) for signal in signals if signal in file]

            stack_total = sum(bkg_hist)
            if stackSignal:
                stack_total = stack_total + sum(signal_hist)
            h.add(bkg_hist, label=bkg_labels, density = getattr(plot, "density", False), color = bkg_colors, stack = True, histtype = "fill")
            signal_histtype = "step" if not stackSignal else "fill"
            h.add(signal_hist, label=signal_labels, density = getattr(plot, "density", False), color = signal_colors, stack = stackSignal, histtype = signal_histtype, w2method="poisson")
            h.add(stack_total, density = getattr(plot, "density", False), color = "black", histtype = "step", yerr=False, linewidth=1)
            h.add(stack_total, density = getattr(plot, "density", False), color = "black", histtype = "band", label="Total Unc.", w2method="poisson")

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

        pdf_Path = path.replace('.root','.pdf')
        png_Path = path.replace('.root','')
        h.save(f"{pdf_Path}")
        os.system(f"pdftocairo {pdf_Path} -png -r 200 {png_Path}")
        os.system(f"mv {png_Path}-1.png {png_Path}.png")

    elif "TH2" in hist_type:
        for process_name, process_dict in all_processes.items():
            if process_name not in file:
                continue

            h = TH2(cmstext = cmstext,
                    lumitext= lumitext,
                    xlabel = plot.xlabel,
                    ylabel = plot.ylabel,
                    log = plot.log,
                    grid=grid)
            hist = file[process_name].to_hist()
            h.add(hist, density = getattr(plot, "density", False))
            folder = path.replace('.root','')
            folder = folder.rsplit('/',1)[0]+"/2D_"+folder.rsplit('/',1)[1]
            os.makedirs(folder, exist_ok=True)
            h.save(os.path.join(folder,f"{process_name}.pdf"))
            os.system(f"pdftocairo {os.path.join(folder,f'{process_name}.pdf')} -png -r 200 {os.path.join(folder,f'{process_name}')}")
            os.system(f"mv {os.path.join(folder,f'{process_name}-1.png')} {os.path.join(folder,f'{process_name}.png')}")

def _drawPyPlots(args):
    return __drawPyPlots(*args)

def DrawPyPlots(plots_lumi, eras, mergeEras, flow_plots, all_processes, cmstext, lumitext, noStack, ratio, ratiorange, ratiotype, grid=False, ncpu=None, stackSignal=False):
    for era in eras:
        format_dict = {"era": era} if not mergeEras else {}
        paths=[os.path.join(folders.plots_path.format(flow=flow, **format_dict), f"{plot.name}.root") for (flow, plots) in flow_plots for plot in plots]
        plots = [plot for (_, plots) in flow_plots for plot in plots]
        pool_data=[(path, all_processes, plot, plot_lumi, cmstext, lumitext, noStack, ratio, ratiorange, ratiotype, grid, stackSignal) for path, plot, plot_lumi in zip(paths, plots, plots_lumi)]
        with concurrent.futures.ProcessPoolExecutor(max_workers=ncpu) as executor:
            chunksize = len(pool_data)//ncpu if len(pool_data)//ncpu > 0 else 1
            list(executor.map(_drawPyPlots, pool_data, chunksize = chunksize))
