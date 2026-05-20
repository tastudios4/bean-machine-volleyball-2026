.PHONY: all data analysis extract parse-league bean-games player-stats validate \
        layer1 layer2 game3 playoff trends roles blowouts synthesize clean venv

PY := .venv/bin/python

venv:
	python3 -m venv .venv && .venv/bin/pip install --upgrade pip && .venv/bin/pip install -r requirements.txt

# Full project: Phase 1 data layer + Phase 2 analysis
all: data analysis

# ---- Phase 1: data layer ----
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

# ---- Phase 2: analysis ----
# 13_synthesize.py must run last — it reads every findings_*.json.
analysis: layer1 layer2 game3 playoff trends roles blowouts synthesize

layer1:
	$(PY) src/10_layer1_team_analysis.py

layer2:
	$(PY) src/11_layer2_league_analysis.py

game3:
	$(PY) src/12_game3_analysis.py

playoff:
	$(PY) src/14_playoff_analysis.py

trends:
	$(PY) src/15_season_trends.py

roles:
	$(PY) src/16_player_roles.py

blowouts:
	$(PY) src/17_blowout_analysis.py

synthesize:
	$(PY) src/13_synthesize.py

clean:
	rm -rf data/raw/sheets data/processed/*.csv data/manual_review/*.csv \
	       data/processed/findings_*.json data/processed/findings_summary.md
