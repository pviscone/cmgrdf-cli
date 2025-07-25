run_analysis.py --cfg cfg/base_cfg.py --mc data/Zd_nJet2_pT0p5_eta2p5_VBFcuts.py --flow flows/VBFFlow_baseline_GenMatch.py --plots plots/GenMatchPlots.py -o tempVBF --eras 2023

run_analysis.py --cfg cfg/base_cfg.py --mc data/Zd_nj012_pte5_eta1p2.py  --flow flows/DoubleEleFlow_baseline_GenMatch.py --plots plots/GenMatchPlots.py -o tempInclusive --eras 2023

efficiencyPlots.py -i tempVBF -c scripts/eff_cfg/VBFFlow_baselise_GenMatch_eff.yaml --rebin 2 --allEras

efficiencyPlots.py -i tempInclusive -c scripts/eff_cfg/DoubleEleFlow_baseline_GenMatch_eff.yaml  --rebin 2 --allEras