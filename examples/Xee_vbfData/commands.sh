run_analysis.py --cfg cfg/base_cfg.py --mc data/InclusiveMinBias.py  --flow flows/VBFFlow_baseline.py  -o tempVBFData/MinBias --eras "2024"

run_analysis.py --cfg cfg/base_cfg.py --data data/VBFdata.py --mc data/Signal3p1.py --flow flows/VBFFlow_baseline.py  --plots plots/DiElePlots.py -o tempVBFData/dataAllTrigger --eras "2024" --signalMultiplier 100. --ratiotype "ratio:log" --ratio HAHM_13p6TeV_M3p1_VBF data --ratiorange 0.00001 1.

run_analysis.py --cfg cfg/base_cfg.py --data data/VBFdata.py --mc data/Signal3p1.py --flow flows/VBFFlow_baseline.py:hlt=\"splitted\"  --plots plots/DiElePlots.py -o tempVBFData/dataSplitted --eras "2024" --signalMultiplier 100. --ratiotype "ratio:log" --ratio HAHM_13p6TeV_M3p1_VBF data --ratiorange 0.00001 1.
