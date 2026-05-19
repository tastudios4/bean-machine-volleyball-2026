"""
04_extract_player_stats.py

Reads per-game tabs from data/raw/player_stats_raw.xlsx (tab pattern
'26-MMDDGn') and writes a long-format CSV: one row per (player x game).

Each per-game tab has this layout (column index in parentheses):

  col 0 : Name
  col 1 : Position
  col 2 : Attack > Attempts
  col 3 : Attack > Kills
  col 4 : Attack > Errors
  col 5 : Attack > Assists
  col 6 : Attack > %                (hit_pct)
  col 7 : Blocking > Solo
  col 8 : Blocking > Assist
  col 9 : Digs
  col 10: Service > Aces
  col 11: Service > Errors
  col 12: Service > Total Serves
  col 13: Service > % / SRV%        (srv_pct)
  col 14: Service > ACE%            (ace_pct)
  col 15: Serve Receive > Attempts
  col 16: Serve Receive > 0
  col 17: Serve Receive > 1
  col 18: Serve Receive > 2
  col 19: Serve Receive > 3
  col 20: Serve Receive > Average

Rows 0-1 are headers; rows 2-8 are the 7 player rows.

The match_id is joined from bean_machine_games.csv using the tab's date,
so the player-stats rows align cleanly with the games CSV.
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PLAYER_STATS_XLSX = ROOT / "data" / "raw" / "player_stats_raw.xlsx"
BEAN_GAMES_CSV = ROOT / "data" / "processed" / "bean_machine_games.csv"
OUTPUT_CSV = ROOT / "data" / "processed" / "bean_machine_player_stats.csv"

TAB_RE = re.compile(r"^26-(\d{2})(\d{2})G(\d)$")

COLUMN_MAP = {
    "player_name": 0,
    "position": 1,
    "attack_attempts": 2,
    "kills": 3,
    "errors": 4,
    "assists": 5,
    "hit_pct": 6,
    "blocks_solo": 7,
    "blocks_assist": 8,
    "digs": 9,
    "aces": 10,
    "service_errors": 11,
    "total_serves": 12,
    "srv_pct": 13,
    "ace_pct": 14,
    "sr_attempts": 15,
    "sr_0": 16,
    "sr_1": 17,
    "sr_2": 18,
    "sr_3": 19,
    "sr_average": 20,
}

PLAYER_DATA_ROWS = range(2, 9)  # rows 2-8 (7 players)


def date_to_match_id(date_str: str, bean_games: pd.DataFrame) -> str | None:
    """Look up match_id for a given date from bean_machine_games.csv (1:1 per date)."""
    matches = bean_games[bean_games.date == date_str]
    if matches.empty:
        return None
    return matches.iloc[0]["match_id"]


def extract_tab(tab_name: str, df: pd.DataFrame, bean_games: pd.DataFrame) -> list[dict]:
    m = TAB_RE.match(tab_name)
    if not m:
        return []
    month, day, game_n = m.group(1), m.group(2), int(m.group(3))
    date_str = f"2026-{month}-{day}"
    match_id = date_to_match_id(date_str, bean_games)
    if match_id is None:
        print(f"  WARNING: tab {tab_name} has no matching Bean game for date {date_str}; skipping")
        return []

    rows = []
    for r_idx in PLAYER_DATA_ROWS:
        if r_idx >= len(df):
            continue
        name_cell = df.iat[r_idx, COLUMN_MAP["player_name"]]
        if pd.isna(name_cell) or not str(name_cell).strip():
            continue  # empty row, no player
        row = {
            "match_id": match_id,
            "date": date_str,
            "game_number": game_n,
        }
        for field, col_idx in COLUMN_MAP.items():
            val = df.iat[r_idx, col_idx] if col_idx < df.shape[1] else pd.NA
            if field == "player_name":
                row[field] = str(val).strip()
            elif field == "position":
                row[field] = "" if pd.isna(val) else str(val).strip()
            else:
                row[field] = val if pd.notna(val) else pd.NA
        rows.append(row)
    return rows


def main() -> None:
    bean_games = pd.read_csv(BEAN_GAMES_CSV)
    workbook = pd.read_excel(
        PLAYER_STATS_XLSX, sheet_name=None, header=None, engine="openpyxl"
    )

    all_rows: list[dict] = []
    extracted_tabs: list[str] = []
    skipped_tabs: list[str] = []

    for tab_name, df in workbook.items():
        if not TAB_RE.match(tab_name):
            skipped_tabs.append(tab_name)
            continue
        rows = extract_tab(tab_name, df, bean_games)
        all_rows.extend(rows)
        extracted_tabs.append(tab_name)

    out = pd.DataFrame(all_rows)
    # Stable sort: by date, then game_number, then player_name
    out = out.sort_values(["date", "game_number", "player_name"]).reset_index(drop=True)
    out.to_csv(OUTPUT_CSV, index=False)

    print(f"WROTE {OUTPUT_CSV.relative_to(ROOT)}  ({len(out)} rows)")
    print()
    print(f"Per-game tabs extracted: {len(extracted_tabs)}")
    print(f"Tabs skipped (not per-game pattern): {len(skipped_tabs)} -> {skipped_tabs}")
    print()
    print(f"Distinct players: {out.player_name.nunique()} -> {sorted(out.player_name.unique())}")
    print(f"Distinct dates:   {out.date.nunique()}")
    print(f"Distinct game_numbers per date:")
    for d, sub in out.groupby("date"):
        print(f"  {d}: G{sorted(sub.game_number.unique())}")


if __name__ == "__main__":
    main()
