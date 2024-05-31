.PHONY: clean simple

all: clean simple

clean:
	@rm -rf *_cache.dir 2> /dev/null || true

simple:
	python3 run_simple_mc_nanoAOD.py
	@echo
	@echo ---------------------------------
	python3 run_simple_data_ttH.py
	@echo
	@echo ---------------------------------
	python3 run_simpleCache_sos.py
	@echo
	@echo ---------------------------------
	python3 run_simpleCache_sos.py # second time
	@echo
	@echo ---------------------------------
	python3 run_friends_sos.py
	@echo
	@echo ---------------------------------
	python3 run_uncertainties_ttH.py
	@echo
	@echo ---------------------------------
	#python3 run_datacards_ttV_ttHH_2018c.py
	@echo
	@echo ---------------------------------
	python3 run_SFs_ttHH_2018c.py
	@echo
	@echo ---------------------------------
	python3 run_snapshots_ttHH_2018c.py
	@echo
	@echo ---------------------------------
	python3 run_snapshots_ttHH_2018c.py # second time
	@echo ---------------------------------