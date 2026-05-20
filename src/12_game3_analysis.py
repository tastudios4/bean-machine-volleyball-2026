"""
12_game3_analysis.py

Layer 3: the league-format hook. Does game 3 matter differently in a league
where EVERY set counts independently for seeding (not just as a tiebreaker)?

The question is unique to this league. In a standard volleyball league, a 3rd
set is only played when the first two are split 1-1 — it's purely a decider.
Here, game 3 gets played whenever there's time, even when one team has already
won 2-0, because each set independently affects seeding/point-differential.

Finding-blocks computed below:
  1. Margin distribution by game number (G1 vs G2 vs G3 across the league)
  2. Scoring rate by game number (total points per set; G3 is to 15 not 25
     so this is largely structural, but worth measuring)
  3. Upset rate by game number (lower-record team's win rate by game number)
  4. "Garbage time" hypothesis: do margins in G3 differ depending on whether
     the match was 2-0 (G3 meaningless to match outcome) or 1-1 (G3 deciding)?
  5. Bean-specific: do Bean's team stats differ by game number? (n=7 of each)

Scope: regular season only (playoffs use 21-21-15 instead of 25-25-15 — mixing
the two would muddy any structural finding).

Output:
  - stdout: human-readable findings with n on every claim
  - data/processed/findings_layer3.json: structured for 13_synthesize.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
LEAGUE_CSV = ROOT / "data" / "processed" / "league_matches.csv"
STANDINGS_CSV = ROOT / "data" / "processed" / "league_standings.csv"
BEAN_GAMES_CSV = ROOT / "data" / "processed" / "bean_machine_games.csv"
PLAYER_STATS_CSV = ROOT / "data" / "processed" / "bean_machine_player_stats.csv"
OUT_JSON = ROOT / "data" / "processed" / "findings_layer3.json"

COUNTING_STATS = [
    "attack_attempts", "kills", "errors", "assists",
    "blocks_solo", "blocks_assist", "digs",
    "aces", "service_errors", "total_serves",
]


def build_league_set_table() -> pd.DataFrame:
    """One row per set (G1, G2, G3) across all regular-season league matches."""
    league = pd.read_csv(LEAGUE_CSV)
    reg = league[~league.is_playoff].copy()
    rows = []
    for _, m in reg.iterrows():
        # Per-match: did one team win the first two sets? (used by garbage-time question)
        s1a, s1b = m["set1_a"], m["set1_b"]
        s2a, s2b = m["set2_a"], m["set2_b"]
        match_status_after_g2 = None
        if pd.notna(s1a) and pd.notna(s1b) and pd.notna(s2a) and pd.notna(s2b):
            w1 = m["team_a_number"] if s1a > s1b else m["team_b_number"]
            w2 = m["team_a_number"] if s2a > s2b else m["team_b_number"]
            match_status_after_g2 = "2-0" if w1 == w2 else "1-1"

        for n in (1, 2, 3):
            a = m[f"set{n}_a"]
            b = m[f"set{n}_b"]
            if pd.isna(a) or pd.isna(b):
                continue
            rows.append({
                "match_id": m["match_id"],
                "game_number": n,
                "team_a": int(m["team_a_number"]),
                "team_b": int(m["team_b_number"]),
                "pts_a": int(a),
                "pts_b": int(b),
                "winner_team_number": int(m["team_a_number"]) if a > b else int(m["team_b_number"]),
                "loser_team_number": int(m["team_b_number"]) if a > b else int(m["team_a_number"]),
                "margin": int(abs(a - b)),
                "total_pts": int(a + b),
                "match_status_after_g2": match_status_after_g2,
            })
    return pd.DataFrame(rows)


def margin_summary(s: pd.Series) -> dict:
    if not len(s):
        return {"n": 0}
    q = s.quantile([0.25, 0.5, 0.75])
    return {
        "n": int(len(s)),
        "mean": float(s.mean()),
        "std": float(s.std()),
        "min": float(s.min()),
        "q1": float(q.loc[0.25]),
        "median": float(q.loc[0.5]),
        "q3": float(q.loc[0.75]),
        "max": float(s.max()),
    }


# --------------------------------------------------------------------------- #

def finding_1_margin_distribution(sets_df: pd.DataFrame) -> dict:
    by_game = {}
    for n in (1, 2, 3):
        sub = sets_df[sets_df.game_number == n]
        by_game[f"G{n}"] = margin_summary(sub.margin)

    # Test for difference: pairwise Welch t-tests (margins are not normal,
    # but with n~50 the test is reasonable as an effect-size sanity check).
    g1 = sets_df[sets_df.game_number == 1].margin
    g2 = sets_df[sets_df.game_number == 2].margin
    g3 = sets_df[sets_df.game_number == 3].margin
    t12 = stats.ttest_ind(g1, g2, equal_var=False)
    t13 = stats.ttest_ind(g1, g3, equal_var=False)
    t23 = stats.ttest_ind(g2, g3, equal_var=False)

    return {
        "summary_by_game": by_game,
        "pairwise_welch_t_tests": {
            "G1_vs_G2": {"t": float(t12.statistic), "p": float(t12.pvalue)},
            "G1_vs_G3": {"t": float(t13.statistic), "p": float(t13.pvalue)},
            "G2_vs_G3": {"t": float(t23.statistic), "p": float(t23.pvalue)},
        },
    }


def finding_2_scoring_rate(sets_df: pd.DataFrame) -> dict:
    """Total points per set, by game number.
    G3 is structurally lower (cap of 15 vs 25), so this is partly mechanical.
    But it's useful to see how close to the cap each game number actually
    gets — i.e., are G3s often deuce-extended or do they end at exactly 15?"""
    by_game = {}
    for n in (1, 2, 3):
        sub = sets_df[sets_df.game_number == n]
        by_game[f"G{n}"] = {
            **margin_summary(sub.total_pts),
            "pct_at_or_above_cap": float(
                ((sub.total_pts >= (50 if n in (1, 2) else 30)).mean())
            ) if len(sub) else None,
        }
    return by_game


def finding_3_upset_rate(sets_df: pd.DataFrame) -> dict:
    """How often does the lower-record team win, by game number?"""
    standings = pd.read_csv(STANDINGS_CSV).set_index("team_number")
    win_pct = standings["win_pct"].to_dict()

    rows = []
    for _, s in sets_df.iterrows():
        wp_a = win_pct.get(s.team_a, 0.0)
        wp_b = win_pct.get(s.team_b, 0.0)
        if wp_a == wp_b:
            continue
        favored = s.team_a if wp_a > wp_b else s.team_b
        favored_won = (s.winner_team_number == favored)
        rows.append({
            "game_number": s.game_number,
            "favored_won": favored_won,
            "win_pct_gap": abs(wp_a - wp_b),
        })
    df = pd.DataFrame(rows)
    out = {}
    for n in (1, 2, 3):
        sub = df[df.game_number == n]
        if not len(sub):
            out[f"G{n}"] = None
            continue
        out[f"G{n}"] = {
            "n": int(len(sub)),
            "favored_win_rate": float(sub.favored_won.mean()),
            "upset_rate": float(1 - sub.favored_won.mean()),
            "mean_win_pct_gap": float(sub.win_pct_gap.mean()),
        }
    return out


def finding_4_garbage_time(sets_df: pd.DataFrame) -> dict:
    """Among games 3, do margins differ when match was already decided
    (2-0 going in, so G3 is 'meaningless' to match outcome) vs when match
    was 1-1 (G3 is the decider)?
    """
    g3 = sets_df[sets_df.game_number == 3].copy()
    g3 = g3[g3.match_status_after_g2.notna()]
    decider = g3[g3.match_status_after_g2 == "1-1"]
    garbage = g3[g3.match_status_after_g2 == "2-0"]

    out = {
        "decider_g3_summary": margin_summary(decider.margin),
        "garbage_g3_summary": margin_summary(garbage.margin),
    }
    if len(decider) >= 2 and len(garbage) >= 2:
        t = stats.ttest_ind(decider.margin, garbage.margin, equal_var=False)
        out["welch_t_test"] = {
            "t": float(t.statistic),
            "p": float(t.pvalue),
        }
    out["interpretation"] = (
        f"Decider G3s (n={len(decider)}): mean margin "
        f"{decider.margin.mean():.2f}; "
        f"Garbage G3s (n={len(garbage)}): mean margin {garbage.margin.mean():.2f}. "
        f"Difference: {garbage.margin.mean() - decider.margin.mean():+.2f}."
    )
    return out


def finding_5_bean_stats_by_game_number(sets_df: pd.DataFrame) -> dict:
    """Do Bean's team-aggregate stats differ across G1/G2/G3?"""
    stats_df = pd.read_csv(PLAYER_STATS_CSV)
    bean_games = pd.read_csv(BEAN_GAMES_CSV)
    reg_bean = bean_games[~bean_games.is_playoff]

    # Aggregate player stats to (match_id, game_number) team totals
    agg = (
        stats_df[stats_df.match_id.isin(reg_bean.match_id)]
        .groupby(["match_id", "game_number"])[COUNTING_STATS]
        .sum(min_count=1)
        .reset_index()
    )
    # Add team-level derived stats
    agg["team_hit_pct"] = (agg.kills - agg.errors) / agg.attack_attempts

    # Add Bean's per-set margin
    bean_margin = []
    for _, r in agg.iterrows():
        g = reg_bean[reg_bean.match_id == r.match_id].iloc[0]
        n = int(r.game_number)
        f = g[f"bean_points_set{n}_for"]
        a = g[f"bean_points_set{n}_against"]
        bean_margin.append((f - a) if pd.notna(f) and pd.notna(a) else np.nan)
    agg["bean_margin"] = bean_margin

    out = {}
    for n in (1, 2, 3):
        sub = agg[agg.game_number == n]
        out[f"G{n}"] = {
            "n_sets": int(len(sub)),
            "team_kills_avg": float(sub.kills.mean()) if len(sub) else None,
            "team_errors_avg": float(sub.errors.mean()) if len(sub) else None,
            "team_hit_pct_avg": float(sub.team_hit_pct.mean()) if len(sub) else None,
            "team_digs_avg": float(sub.digs.mean()) if len(sub) else None,
            "team_aces_avg": float(sub.aces.mean()) if len(sub) else None,
            "bean_margin_avg": float(sub.bean_margin.mean(skipna=True)) if len(sub) else None,
            "bean_margin_median": float(sub.bean_margin.median(skipna=True)) if len(sub) else None,
        }
    out["caveat"] = (
        f"Tiny sample: ~{len(agg) // 3} sets per game number. "
        "Read as descriptive, not statistical."
    )
    return out


# --------------------------------------------------------------------------- #

def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def main() -> None:
    sets_df = build_league_set_table()
    n_by_game = sets_df.groupby("game_number").size().to_dict()

    banner("LAYER 3 — DOES GAME 3 MATTER DIFFERENTLY?")
    print(f"Regular-season league sets (with complete scores):")
    for n in (1, 2, 3):
        print(f"  G{n}: n={n_by_game.get(n, 0)}")
    print(f"  Total: {len(sets_df)}")

    # 1
    banner("FINDING 1 — Margin distribution by game number")
    f1 = finding_1_margin_distribution(sets_df)
    print(f"  {'game':<6}{'n':>5}{'mean':>8}{'std':>8}{'median':>9}{'min':>6}{'max':>6}")
    for k, d in f1["summary_by_game"].items():
        print(f"  {k:<6}{d['n']:>5}{d['mean']:>8.2f}{d['std']:>8.2f}"
              f"{d['median']:>9.1f}{int(d['min']):>6}{int(d['max']):>6}")
    print("\n  Pairwise Welch t-tests on margins:")
    for pair, t in f1["pairwise_welch_t_tests"].items():
        sig = "*" if t["p"] < 0.05 else " "
        print(f"    {pair}: t={t['t']:+.2f}, p={t['p']:.3f}  {sig}")

    # 2
    banner("FINDING 2 — Scoring rate (total points per set) by game number")
    f2 = finding_2_scoring_rate(sets_df)
    print(f"  {'game':<6}{'n':>5}{'mean':>8}{'median':>9}{'min':>6}{'max':>6}{'cap_rate':>12}")
    caps = {1: 50, 2: 50, 3: 30}
    for k, d in f2.items():
        n = k[1]
        cap_label = f"≥{caps[int(n)]}"
        print(f"  {k:<6}{d['n']:>5}{d['mean']:>8.1f}{d['median']:>9.1f}"
              f"{int(d['min']):>6}{int(d['max']):>6}"
              f"  {d['pct_at_or_above_cap']:.1%} {cap_label}")

    # 3
    banner("FINDING 3 — Upset rate by game number (lower-record team wins)")
    f3 = finding_3_upset_rate(sets_df)
    print(f"  {'game':<6}{'n':>5}{'favored_W%':>13}{'upset%':>10}{'mean_gap':>11}")
    for k, d in f3.items():
        if d is None:
            continue
        print(f"  {k:<6}{d['n']:>5}{d['favored_win_rate']:>13.1%}"
              f"{d['upset_rate']:>10.1%}{d['mean_win_pct_gap']:>11.3f}")

    # 4 — the headline question
    banner("FINDING 4 — Garbage-time hypothesis (decider G3 vs already-decided G3)")
    f4 = finding_4_garbage_time(sets_df)
    print(f"  Decider G3s (match was 1-1):")
    d = f4["decider_g3_summary"]
    if d["n"]:
        print(f"    n={d['n']}, mean margin={d['mean']:.2f}, median={d['median']:.1f}, "
              f"std={d['std']:.2f}, max={int(d['max'])}")
    print(f"  'Garbage' G3s (match was already 2-0):")
    d = f4["garbage_g3_summary"]
    if d["n"]:
        print(f"    n={d['n']}, mean margin={d['mean']:.2f}, median={d['median']:.1f}, "
              f"std={d['std']:.2f}, max={int(d['max'])}")
    if "welch_t_test" in f4:
        t = f4["welch_t_test"]
        sig = "*" if t["p"] < 0.05 else " "
        print(f"  Welch t-test: t={t['t']:+.2f}, p={t['p']:.3f}  {sig}")
    print(f"  {f4['interpretation']}")

    # 5 — bean-specific
    banner("FINDING 5 — Bean's team-aggregate stats by game number")
    f5 = finding_5_bean_stats_by_game_number(sets_df)
    print(f"  {'game':<6}{'n':>4}{'kills':>8}{'errors':>9}{'hit%':>9}{'digs':>8}"
          f"{'aces':>7}{'margin_avg':>12}{'margin_med':>12}")
    for n in (1, 2, 3):
        d = f5[f"G{n}"]
        def fmt(v, w, dp=1):
            if v is None or (isinstance(v, float) and np.isnan(v)):
                return " " * (w - 1) + "-"
            return f"{v:>{w}.{dp}f}"
        print(f"  G{n:<5}{d['n_sets']:>4}{fmt(d['team_kills_avg'], 8)}"
              f"{fmt(d['team_errors_avg'], 9)}{fmt(d['team_hit_pct_avg'], 9, 3)}"
              f"{fmt(d['team_digs_avg'], 8)}{fmt(d['team_aces_avg'], 7)}"
              f"{fmt(d['bean_margin_avg'], 12, 2)}{fmt(d['bean_margin_median'], 12, 1)}")
    print(f"  {f5['caveat']}")

    # Write JSON
    payload = {
        "meta": {
            "scope": "regular season only (playoffs use 21-21-15 format)",
            "sets_by_game_number": {f"G{n}": int(v) for n, v in n_by_game.items()},
            "total_sets": int(len(sets_df)),
        },
        "margin_distribution": f1,
        "scoring_rate": f2,
        "upset_rate": f3,
        "garbage_time_hypothesis": f4,
        "bean_stats_by_game": f5,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print()
    print(f"WROTE {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
