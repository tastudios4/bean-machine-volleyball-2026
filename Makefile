.PHONY: data extract parse-league bean-games player-stats validate clean

PY := .venv/bin/python

.PHONY: venv
venv:
	python3 -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install -r requirements.txt

data: extract parse-league bean-games player-stats validate

extract:
	$(PY) src/01_extract_xlsx.py

parse-league:
	$(PY) src/02_parse_league.py

bean-games:
	$(PY) src/03_build_bean_machine_games.py

player-stats:
	$(PY) src/04_extract_player_stats.py

validate:
	$(PY) src/05_join_and_validate.py

clean:
	rm -rf data/raw/sheets data/processed/*.csv data/manual_review/*.csv
