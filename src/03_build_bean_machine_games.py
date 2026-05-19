"""
03_build_bean_machine_games.py

Filters data/processed/league_matches.csv to matches involving Bean Machine
(team 11) and adds Bean-perspective columns:

  - bean_points_set{1..3}_for, _against : per-set points (Bean's side)
  - sets_won_by_bean, sets_lost_by_bean : strict counts (only sets with both
        scores present and decided)
  - bean_won           : True/False from winner_team_number; NaN if tie/unknown
  - bean_point_differential : sum of (bean - opp) across sets where both known
  - has_player_stats   : True if player_stats_raw.xlsx has any 26-MMDDG* tab
                          matching this match's date

Writes: data/processed/bean_machine_games.csv
"""

from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LEAGUE_MATCHES_CSV = ROOT / "data" / "processed" / "league_matches.csv"
PLAYER_STATS_XLSX = ROOT / "data" / "raw" / "player_stats_raw.xlsx"
OUTPUT_CSV = ROOT / "data" / "processed" / "bean_machine_games.csv"

BEAN_TEAM_NUMBER = 11
PLAYER_STATS_TAB_RE = re.compile(r"^26-(\d{2})(\d{2})G\d$")


def player_stats_dates() -> set[str]:
    """Return the set of dates (YYYY-MM-DD) that have at least one G* tab."""
    sheets = pd.read_excel(
        PLAYER_STATS_XLSX, sheet_name=None, header=None, engine="openpyxl"
    )
    dates: set[str] = set()
    for name in sheets.keys():
        m = PLAYER_STATS_TAB_RE.match(name)
        if not m:
            continue
        dates.add(f"2026-{m.group(1)}-{m.group(2)}")
    return dates


def bean_perspective_set(row: pd.Series, set_n: int) -> tuple[float, float]:
    """Return (bean_points_for, bean_points_against) for set_n of the match."""
    a = row[f"set{set_n}_a"]
    b = row[f"set{set_n}_b"]
    if row["team_a_number"] == BEAN_TEAM_NUMBER:
        return a, b
    return b, a


def main() -> None:
    df = pd.read_csv(LEAGUE_MATCHES_CSV)
    bean = df[
        (df.team_a_number == BEAN_TEAM_NUMBER) | (df.team_b_number == BEAN_TEAM_NUMBER)
    ].copy()

    # Per-set Bean-perspective points
    for set_n in (1, 2, 3):
        for_col = f"bean_points_set{set_n}_for"
        against_col = f"bean_points_set{set_n}_against"
        pts = bean.apply(lambda r, n=set_n: bean_perspective_set(r, n), axis=1)
        bean[for_col] = [p[0] for p in pts]
        bean[against_col] = [p[1] for p in pts]

    # Strict per-set wins/losses: only count if BOTH scores known and unequal
    def count_sets(row: pd.Series, predicate) -> int:
        n = 0
        for set_n in (1, 2, 3):
            f = row[f"bean_points_set{set_n}_for"]
            a = row[f"bean_points_set{set_n}_against"]
            if pd.notna(f) and pd.notna(a) and predicate(f, a):
                n += 1
        return n

    bean["sets_won_by_bean"] = bean.apply(
        lambda r: count_sets(r, lambda f, a: f > a), axis=1
    )
    bean["sets_lost_by_bean"] = bean.apply(
        lambda r: count_sets(r, lambda f, a: f < a), axis=1
    )

    # Point differential: sum across sets where both scores known
    def point_diff(row: pd.Series) -> float:
        diff = 0.0
        had_any = False
        for set_n in (1, 2, 3):
            f = row[f"bean_points_set{set_n}_for"]
            a = row[f"bean_points_set{set_n}_against"]
            if pd.notna(f) and pd.notna(a):
                diff += f - a
                had_any = True
        return diff if had_any else float("nan")

    bean["bean_point_differential"] = bean.apply(point_diff, axis=1)

    # Match-level win flag: from winner_team_number; NaN on tie / unknown
    def bean_won_flag(row: pd.Series):
        if row["is_tie"]:
            return pd.NA
        w = row["winner_team_number"]
        if pd.isna(w):
            return pd.NA
        return int(w) == BEAN_TEAM_NUMBER

    bean["bean_won"] = bean.apply(bean_won_flag, axis=1)

    # has_player_stats: does the player_stats workbook have any G* tab for this date?
    ps_dates = player_stats_dates()
    bean["has_player_stats"] = bean["date"].isin(ps_dates)

    bean = bean.sort_values("date").reset_index(drop=True)
    bean.to_csv(OUTPUT_CSV, index=False)

    print(f"WROTE {OUTPUT_CSV.relative_to(ROOT)}  ({len(bean)} rows)")
    print()
    print("Summary:")
    print(f"  Total Bean matches: {len(bean)}")
    print(f"  Regular season:     {(~bean.is_playoff).sum()}")
    print(f"  Playoffs:           {bean.is_playoff.sum()}")
    print(f"  has_player_stats:   {bean.has_player_stats.sum()}/{len(bean)}")
    won = (bean.bean_won == True).sum()
    lost = (bean.bean_won == False).sum()
    print(f"  Match record:       {won}W-{lost}L (from winner_team_number)")
    print(f"  Sets won (strict):  {bean.sets_won_by_bean.sum()}")
    print(f"  Sets lost (strict): {bean.sets_lost_by_bean.sum()}")
    diff = bean["bean_point_differential"].sum(skipna=True)
    print(f"  Point differential: {int(diff):+d} (sum across all measurable sets)")


if __name__ == "__main__":
    main()
