"""
17_blowout_analysis.py

Autopsy of Bean Machine's two worst losses:
  - 2026-02-18 vs Volley These Balls (team 4): match margin -20, swept 0-3
  - 2026-01-21 vs Sugar & Spike (team 8):     match margin -16, swept 0-2(+1)

Both opponents were elite (Volley These Balls finished 11-0; Sugar & Spike
13-4). So the losses themselves were expected. The question is whether the
*margins* were unusually bad, and whether the whole team collapsed or a few
players had outlier-bad games.

What's computed:
  1. Bean's team-aggregate stats in each blowout vs Bean's season average
  2. Per-player stats in each blowout vs that player's season per-set average
  3. Context: how did Volley These Balls / Sugar & Spike beat their OTHER
     opponents? Was Bean's loss margin typical of facing these teams, or
     was Bean blown out worse than most?

Output: stdout + data/processed/findings_blowouts.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LEAGUE_CSV = ROOT / "data" / "processed" / "league_matches.csv"
BEAN_GAMES_CSV = ROOT / "data" / "processed" / "bean_machine_games.csv"
PLAYER_STATS_CSV = ROOT / "data" / "processed" / "bean_machine_player_stats.csv"
OUT_JSON = ROOT / "data" / "processed" / "findings_blowouts.json"

COUNTING_STATS = [
    "attack_attempts", "kills", "errors", "assists",
    "blocks_solo", "blocks_assist", "digs",
    "aces", "service_errors", "total_serves",
]

# Identified by date (Bean plays exactly one match per date, so date is a
# unique key for Bean's matches — match_id is resolved at runtime).
BLOWOUTS = [
    {"date": "2026-02-18", "opponent": "Volley These Balls",
     "opponent_team": 4, "match_margin": -20},
    {"date": "2026-01-21", "opponent": "Sugar & Spike",
     "opponent_team": 8, "match_margin": -16},
]


def opponent_set_margins(league: pd.DataFrame, team: int) -> list[int]:
    """All set margins (from `team`'s perspective) across their regular-season
    matches. Positive = team won the set by that many."""
    reg = league[~league.is_playoff]
    margins = []
    for _, m in reg.iterrows():
        if m["team_a_number"] == team:
            sign = 1
        elif m["team_b_number"] == team:
            sign = -1
        else:
            continue
        for n in (1, 2, 3):
            a, b = m[f"set{n}_a"], m[f"set{n}_b"]
            if pd.isna(a) or pd.isna(b):
                continue
            margins.append(int(sign * (a - b)))
    return margins


def team_stats_for_match(stats_df: pd.DataFrame, match_id: str) -> pd.Series:
    sub = stats_df[stats_df.match_id == match_id]
    sub = sub[sub.position.fillna("").str.strip() != "-"]
    agg = sub.groupby("game_number")[COUNTING_STATS].sum(min_count=1)
    per_set = agg.mean()  # average across the sets in that match
    return per_set


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def main() -> None:
    league = pd.read_csv(LEAGUE_CSV)
    games = pd.read_csv(BEAN_GAMES_CSV)
    stats_df = pd.read_csv(PLAYER_STATS_CSV)
    stats_df = stats_df.merge(games[["match_id", "is_playoff"]], on="match_id", how="left")
    played = stats_df[stats_df.position.fillna("").str.strip() != "-"].copy()

    # Resolve each blowout's match_id from its date (Bean plays once per date)
    date_to_match_id = dict(zip(games.date, games.match_id))
    for b in BLOWOUTS:
        b["match_id"] = date_to_match_id[b["date"]]

    # Bean's season per-set baseline (regular season, games played)
    reg = played[~played.is_playoff]
    reg_team = reg.groupby(["match_id", "game_number"])[COUNTING_STATS].sum(min_count=1)
    season_team_per_set = reg_team.mean()
    with np.errstate(divide="ignore", invalid="ignore"):
        season_hit = (
            (reg_team.kills.sum() - reg_team.errors.sum()) / reg_team.attack_attempts.sum()
        )

    banner("BLOWOUT-LOSS AUTOPSY")
    print("Bean's two worst losses, both to elite teams:")
    for b in BLOWOUTS:
        print(f"  {b['date']} vs {b['opponent']} (team {b['opponent_team']}): "
              f"match margin {b['match_margin']}")

    findings = {"blowouts": []}

    for b in BLOWOUTS:
        banner(f"{b['date']} vs {b['opponent']} (match margin {b['match_margin']})")

        # 1. Team stats this match vs season
        match_team = team_stats_for_match(played, b["match_id"])
        mt = played[(played.match_id == b["match_id"])]
        mt = mt[mt.position.fillna("").str.strip() != "-"]
        mt_team = mt.groupby("game_number")[COUNTING_STATS].sum(min_count=1)
        with np.errstate(divide="ignore", invalid="ignore"):
            match_hit = (
                (mt_team.kills.sum() - mt_team.errors.sum())
                / mt_team.attack_attempts.sum()
            )
        n_sets_with_stats = len(mt_team)

        print(f"  Sets with player stats: {n_sets_with_stats}")
        print(f"\n  TEAM per-set: this match vs season")
        print(f"    {'stat':<18}{'match':>10}{'season':>10}{'delta':>10}")
        for stat in ["kills", "errors", "digs", "aces", "assists", "service_errors"]:
            mv = match_team[stat]
            sv = season_team_per_set[stat]
            print(f"    {stat:<18}{mv:>10.2f}{sv:>10.2f}{mv - sv:>+10.2f}")
        print(f"    {'team_hit_pct':<18}{match_hit:>+10.3f}{season_hit:>+10.3f}"
              f"{match_hit - season_hit:>+10.3f}")

        # 2. Per-player this match vs season per-set average
        print(f"\n  PER-PLAYER hit% & kills: this match vs season per-set average")
        print(f"    {'player':<8}{'k_match':>9}{'k_season':>10}"
              f"{'hit_match':>11}{'hit_season':>12}")
        player_lines = {}
        for player in sorted(played.player_name.unique()):
            p_season = reg[reg.player_name == player]
            p_match = mt[mt.player_name == player]
            if len(p_match) == 0:
                continue

            def hit(g):
                att = g.attack_attempts.sum()
                return float((g.kills.sum() - g.errors.sum()) / att) if att else np.nan

            k_match = p_match.kills.mean()
            k_season = p_season.kills.mean()
            h_match = hit(p_match)
            h_season = hit(p_season)
            player_lines[player] = {
                "kills_per_set_match": float(k_match),
                "kills_per_set_season": float(k_season),
                "hit_pct_match": None if np.isnan(h_match) else float(h_match),
                "hit_pct_season": None if np.isnan(h_season) else float(h_season),
            }
            def f(v, dp=2):
                return f"{v:.{dp}f}" if v is not None and not (isinstance(v, float) and np.isnan(v)) else "  -"
            print(f"    {player:<8}{f(k_match):>9}{f(k_season):>10}"
                  f"{f(h_match, 3):>11}{f(h_season, 3):>12}")

        # 3. Context — how did this opponent treat everyone else?
        opp_margins = opponent_set_margins(league, b["opponent_team"])
        opp_wins = [m for m in opp_margins if m > 0]
        # Bean's set margins vs this opponent
        bean_match = league[league.match_id == b["match_id"]].iloc[0]
        bean_is_a = bean_match["team_a_number"] == 11
        bean_set_margins = []
        for n in (1, 2, 3):
            a, bb = bean_match[f"set{n}_a"], bean_match[f"set{n}_b"]
            if pd.isna(a) or pd.isna(bb):
                continue
            m = (a - bb) if bean_is_a else (bb - a)
            bean_set_margins.append(int(m))

        print(f"\n  CONTEXT — {b['opponent']}'s set margins all season:")
        print(f"    They won {len(opp_wins)} sets; avg winning margin "
              f"{np.mean(opp_wins):.1f} (range {min(opp_wins)} to {max(opp_wins)})")
        print(f"    Bean lost sets to them by: {bean_set_margins}")
        worse_than = [m for m in opp_wins if m >= abs(min(bean_set_margins))]
        print(f"    Bean's worst set loss ({min(bean_set_margins)}) — "
              f"{b['opponent']} beat {len(worse_than)} of {len(opp_wins)} "
              f"opponents' sets by that much or more")

        findings["blowouts"].append({
            **b,
            "n_sets_with_stats": int(n_sets_with_stats),
            "team_hit_pct_match": float(match_hit),
            "team_hit_pct_season": float(season_hit),
            "team_per_set_match": {s: float(match_team[s]) for s in COUNTING_STATS},
            "team_per_set_season": {s: float(season_team_per_set[s]) for s in COUNTING_STATS},
            "player_lines": player_lines,
            "opponent_winning_margin_avg": float(np.mean(opp_wins)),
            "opponent_winning_margin_max": int(max(opp_wins)),
            "bean_set_margins_vs_opponent": bean_set_margins,
        })

    # Summary verdict
    banner("VERDICT")
    for fb in findings["blowouts"]:
        hit_drop = fb["team_hit_pct_match"] - fb["team_hit_pct_season"]
        margins = fb["bean_set_margins_vs_opponent"]
        opp_avg = fb["opponent_winning_margin_avg"]
        # A set is "competitive" if Bean lost it by no more than the opponent's
        # typical winning margin — i.e. Bean kept it within the opponent's norm.
        competitive = [m for m in margins if abs(m) <= opp_avg]
        print(f"  {fb['date']} vs {fb['opponent']}:")
        print(f"    Team hit% {fb['team_hit_pct_match']:+.3f} vs season "
              f"{fb['team_hit_pct_season']:+.3f}  (delta {hit_drop:+.3f})")
        print(f"    {fb['opponent']}'s avg winning margin all season: {opp_avg:.1f}")
        print(f"    Bean's set margins: {margins} — {len(competitive)} of "
              f"{len(margins)} within the opponent's typical winning margin")
        # Distinguish "Bean's offense broke down" from "Bean got outscored anyway"
        if hit_drop < -0.03:
            verdict = ("Bean's own offense underperformed (hit% well below season "
                       "average) — a genuine off night.")
        elif hit_drop > 0.03:
            verdict = ("Bean's offense was ABOVE its season average — this loss "
                       "was about the opponent's attack, not a Bean collapse.")
        else:
            verdict = ("Bean's offense was roughly normal — the loss came from "
                       "the opponent outscoring them, not a Bean breakdown.")
        print(f"    -> {verdict}")
        fb["verdict"] = verdict
        fb["competitive_sets"] = len(competitive)
        fb["total_sets_scored"] = len(margins)

    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(findings, f, indent=2, default=str)
    print()
    print(f"WROTE {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
