"""
05_join_and_validate.py

Cross-checks the three processed CSVs and prints a validation report.

Reports:
  1. Match-ID alignment between bean_machine_games.csv and
     bean_machine_player_stats.csv (no orphans either way).
  2. Per-match coverage: how many sets of player_stats exist per Bean match.
  3. Standings-vs-cells reconciliation for Bean Machine (the commish-win story).
  4. Per-player tab presence: who appeared in how many games.
  5. Summary of unparsed cells from data/manual_review/league_unparsed.csv.

Exit code is always 0 (this is a report, not a gate). Findings of any
severity print at the bottom in a [WARNING] / [INFO] block.
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
MANUAL_REVIEW = ROOT / "data" / "manual_review"

LEAGUE_MATCHES_CSV = PROCESSED / "league_matches.csv"
BEAN_GAMES_CSV = PROCESSED / "bean_machine_games.csv"
PLAYER_STATS_CSV = PROCESSED / "bean_machine_player_stats.csv"
STANDINGS_CSV = PROCESSED / "league_standings.csv"
UNPARSED_CSV = MANUAL_REVIEW / "league_unparsed.csv"

BEAN_TEAM_NUMBER = 11

RULE = "=" * 80


def banner(title: str) -> None:
    print()
    print(RULE)
    print(title)
    print(RULE)


def main() -> None:
    league = pd.read_csv(LEAGUE_MATCHES_CSV)
    bean = pd.read_csv(BEAN_GAMES_CSV)
    stats = pd.read_csv(PLAYER_STATS_CSV)
    standings = pd.read_csv(STANDINGS_CSV)

    findings: list[tuple[str, str]] = []  # (severity, message)

    # ----- 0. match_id uniqueness -----
    # match_id is the primary key of league_matches.csv. Every match must have
    # a distinct id, or downstream lookups silently grab the wrong row.
    banner("0. MATCH_ID UNIQUENESS (league_matches.csv)")
    dup_mask = league.match_id.duplicated(keep=False)
    if dup_mask.any():
        dups = sorted(league[dup_mask].match_id.unique())
        print(f"  FAIL: {len(dups)} match_id(s) used by more than one match:")
        for d in dups:
            print(f"    {d}")
        findings.append(("WARNING",
            f"league_matches.csv has {len(dups)} non-unique match_id(s)"))
    else:
        print(f"  All {len(league)} match_ids are unique. [OK]")

    # ----- 1. match_id alignment -----
    banner("1. MATCH_ID ALIGNMENT (bean_machine_games <-> player_stats)")
    bean_ids = set(bean.match_id)
    stats_ids = set(stats.match_id)

    in_both = bean_ids & stats_ids
    games_without_stats = bean_ids - stats_ids
    stats_without_games = stats_ids - bean_ids

    print(f"  Bean games: {len(bean_ids)}")
    print(f"  Distinct match_ids in player_stats: {len(stats_ids)}")
    print(f"  Overlap (joinable): {len(in_both)}")
    if games_without_stats:
        print(f"  Bean games with NO player stats: {sorted(games_without_stats)}")
        findings.append(("WARNING", f"{len(games_without_stats)} Bean game(s) lack any player stats"))
    if stats_without_games:
        print(f"  Player stat rows with NO matching Bean game: {sorted(stats_without_games)}")
        findings.append(("WARNING", f"{len(stats_without_games)} player_stats row(s) lack a Bean game"))
    if not games_without_stats and not stats_without_games:
        print("  All Bean games join cleanly to player_stats. [OK]")

    # ----- 2. Per-match game (set) coverage -----
    banner("2. PER-MATCH GAME COVERAGE (player_stats tabs vs complete league scores)")
    cov = (
        stats.groupby(["date", "match_id"])
        .game_number.nunique()
        .reset_index(name="games_with_stats")
        .merge(bean[["match_id", "sets_won_by_bean", "sets_lost_by_bean", "is_playoff"]],
               on="match_id", how="right")
    )
    cov["games_with_stats"] = cov["games_with_stats"].fillna(0).astype(int)
    cov["sets_with_complete_score"] = cov.sets_won_by_bean + cov.sets_lost_by_bean
    # For playoff matches the "sets recorded" can be 0 because set scores aren't known,
    # but we can compute expected_games from the player_stats tab count (max 3).
    print(cov[["match_id", "is_playoff", "games_with_stats",
               "sets_with_complete_score"]].to_string(index=False))
    for _, row in cov.iterrows():
        if row.games_with_stats == 0 and not row.is_playoff:
            findings.append(("WARNING",
                f"{row.match_id}: no player stats for any game"))
        elif row.games_with_stats < row.sets_with_complete_score:
            findings.append(("INFO",
                f"{row.match_id}: {row.games_with_stats} game-tab(s) of player stats but "
                f"{int(row.sets_with_complete_score)} sets recorded in league_matches"))

    # ----- 3. Standings vs parsed cells (Bean Machine) -----
    banner("3. STANDINGS-vs-CELLS RECONCILIATION (Bean Machine)")
    bean_std = standings[standings.team_number == BEAN_TEAM_NUMBER].iloc[0]
    parsed_w = int(bean.sets_won_by_bean.sum())
    parsed_l = int(bean.sets_lost_by_bean.sum())
    parsed_g = parsed_w + parsed_l
    parsed_reg = bean[~bean.is_playoff]
    parsed_reg_w = int(parsed_reg.sets_won_by_bean.sum())
    parsed_reg_l = int(parsed_reg.sets_lost_by_bean.sum())
    parsed_reg_g = parsed_reg_w + parsed_reg_l

    print(f"  League standings (official, regular season):")
    print(f"    {int(bean_std.wins)}W - {int(bean_std.losses)}L "
          f"= {int(bean_std.total_games)} games ({bean_std.win_pct:.3f})")
    print(f"  Parsed cells (regular season, strict):")
    print(f"    {parsed_reg_w}W - {parsed_reg_l}L = {parsed_reg_g} games "
          f"({parsed_reg_w / parsed_reg_g:.3f})")
    print(f"  Including playoffs (parsed cells, strict):")
    print(f"    {parsed_w}W - {parsed_l}L = {parsed_g} games")

    diff_w = int(bean_std.wins) - parsed_reg_w
    diff_g = int(bean_std.total_games) - parsed_reg_g
    if diff_w == 0 and diff_g == 0:
        print("  [OK] Standings match parsed cells exactly.")
    else:
        print()
        print(f"  DISCREPANCY: standings show +{diff_w} win(s) and "
              f"+{diff_g} game(s) more than the parsed cells.")
        print("  Known cause: on 2026-01-21, the league cell only recorded 2 of 3 games")
        print("  played vs Sugar & Spike. User confirmed Bean lost game 3 on the court")
        print("  but the commissioner awarded Bean the win. So league_matches.csv reflects")
        print("  the on-court record; league_standings.csv reflects the official count.")
        findings.append(("INFO",
            f"Bean record divergence: standings={int(bean_std.wins)}W-{int(bean_std.losses)}L, "
            f"cells={parsed_reg_w}W-{parsed_reg_l}L. Known: commissioner-awarded win on 01-21."))

    # ----- 4. Per-player appearances -----
    # A player "appeared" in a game if position is not "-" (the marker for
    # games a player didn't play).
    banner("4. PER-PLAYER GAME APPEARANCES (excludes games where position == '-')")
    played = stats[stats.position.fillna("").str.strip() != "-"].copy()
    appear = (
        played.groupby("player_name")
        .agg(games_played=("match_id", "count"),
             distinct_matches=("match_id", "nunique"))
        .sort_values("games_played", ascending=False)
    )
    # Add did-not-play count for transparency
    out = (
        stats[stats.position.fillna("").str.strip() == "-"]
        .groupby("player_name").size().rename("games_out")
    )
    appear = appear.join(out, how="left").fillna({"games_out": 0})
    appear["games_out"] = appear["games_out"].astype(int)
    print(appear.to_string())

    # ----- 5. Unparsed cells -----
    banner("5. UNPARSED LEAGUE CELLS (data/manual_review/league_unparsed.csv)")
    if UNPARSED_CSV.exists():
        unp = pd.read_csv(UNPARSED_CSV)
        print(f"  {len(unp)} flagged cell(s):")
        for _, row in unp.iterrows():
            print(f"    {row['date']} court {row['court']} "
                  f"({row['matchup_raw']}): {row['score_raw']!r} -- {row['reason']}")
        findings.append(("INFO",
            f"{len(unp)} league cell(s) had source-data gaps (no scores recorded). See manual_review."))
    else:
        print("  (no unparsed cells)")

    # ----- 6. Known limitations (always printed) -----
    banner("6. KNOWN DATA LIMITATIONS")
    print("  - 02-18 G3 player stats: permanent gap (no video). Bean lost 3-15 to")
    print("    Volley these balls per the league sheet; per-player breakdown unknown.")
    print("  - 03-04 G2/G3, 03-11 G1/G2/G3 set scores: not recorded. Bean won both")
    print("    playoff matches 2-0 (confirmed by user). G3 of each was played but irrelevant.")
    print("  - 01-21 G3: played per player_stats tab but score not recorded in league cell.")

    # ----- Final findings block -----
    banner("FINDINGS")
    if not findings:
        print("  [OK] All checks passed with no issues.")
    else:
        for severity, msg in findings:
            print(f"  [{severity}] {msg}")


if __name__ == "__main__":
    main()
