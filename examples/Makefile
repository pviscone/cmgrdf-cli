.PHONY: clean simple

all: clean simple

clean:
	@rm -rf *_cache.dir 2> /dev/null || true

simple:
	@python3 run_simple_mc_nanoAOD.py
	@python3 run_simple_data_ttH.py
	@python3 run_simpleCache_sos.py
	@python3 run_simpleCache_sos.py # second time
	@python3 run_friends_sos.py
	@python3 run_uncertainties_ttH.py
	@python3 run_datacards_ttV_ttHH_2018c.py
	@python3 run_SFs_ttHH_2018c.py
	@python3 run_snapshots_ttHH_2018c.py
	@python3 run_snapshots_ttHH_2018c.py # second time