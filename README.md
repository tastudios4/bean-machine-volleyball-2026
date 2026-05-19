# Bean Machine — Mercer Island Men's Volleyball, Winter 2025-26

Analytics project for the Bean Machine volleyball team's 2025-26 winter season in
the Mercer Island Wednesday Men's Volleyball League.

> This README is a placeholder. It will be expanded once Phase 2 (analysis) begins.

## Phase 1: Data Pipeline

First-time setup:

```
make venv
```

Run the pipeline:

```
make data
```

Runs the full pipeline: `01_extract_xlsx → 02_parse_league → 03_build_bean_machine_games → 04_extract_player_stats → 05_join_and_validate`.

### Outputs

- `data/processed/league_matches.csv` — every match in the league across all 15 teams
- `data/processed/bean_machine_games.csv` — Bean Machine's matches with per-set scoring
- `data/processed/bean_machine_player_stats.csv` — long-format per-player per-set stats
- `data/manual_review/league_unparsed.csv` — score cells the parser couldn't confidently handle

### Source data

The `.xlsx` files in `data/raw/` are exports of two original Google Sheets that
were maintained throughout the season:

- `data/raw/league_raw.xlsx` — league schedule and scores for all 15 teams
  ([original Google Sheet](https://docs.google.com/spreadsheets/d/1fUR2kJy3ZEeiIz9mfyUbWO2I-rPgxGcQ44nToddjqaE/edit?usp=sharing))
- `data/raw/player_stats_raw.xlsx` — Bean Machine per-player per-set stats
  ([original Google Sheet](https://docs.google.com/spreadsheets/d/1Mk5XCqo7_MVq0_m-4yvjRVieMh7UwWcEXsp1RCRQ-Oc/edit?usp=sharing))

### Game footage

Video of the games was recorded throughout the season and is available on YouTube:
[@cadetanaka7543](https://www.youtube.com/@cadetanaka7543). Player stats were
logged by reviewing this footage.
