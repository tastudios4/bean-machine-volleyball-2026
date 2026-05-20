"""
15_season_trends.py

Did Bean improve over the 7 regular-season weeks? Did they peak for playoffs,
or were they always going to win Silver?

What's computed:
  1. Team-aggregate stats per week (hit%, errors, kills, digs, aces, margin)
  2. Linear regression slope per stat to detect a trend across weeks 1-7
  3. Per-player trajectory: each player's per-week averages, with slopes
  4. Playoff comparison: where do playoff weeks (8-9) land vs the regular-
     season trend line? Continuation or discontinuity?

Sample: 7 weekly data points for regular season. Tiny. Slopes are computed
but should be read as suggestive — at n=7 you need a very clean trend to
reach statistical significance.

Output: stdout + data/processed/findings_trends.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
BEAN_GAMES_CSV = ROOT / "data" / "processed" / "bean_machine_games.csv"
PLAYER_STATS_CSV = ROOT / "data" / "processed" / "bean_machine_player_stats.csv"
OUT_JSON = ROOT / "data" / "processed" / "findings_trends.json"

COUNTING_STATS = [
    "attack_attempts", "kills", "errors", "assists",
    "blocks_solo", "blocks_assist", "digs",
    "aces", "service_errors", "total_serves",
    "sr_attempts", "sr_0", "sr_1", "sr_2", "sr_3",
]

# Bean's regular season weeks (date -> week number)
WEEK_DATES = {
    "2026-01-07": 1,
    "2026-01-14": 2,
    "2026-01-21": 3,
    "2026-01-28": 4,
    # 2026-02-04 was a bye week
    "2026-02-11": 5,
    "2026-02-18": 6,
    "2026-02-25": 7,
    # Playoffs
    "2026-03-04": 8,
    "2026-03-11": 9,
}


def build_weekly_team_stats() -> pd.DataFrame:
    games = pd.read_csv(BEAN_GAMES_CSV)
    stats_df = pd.read_csv(PLAYER_STATS_CSV)
    stats_df = stats_df[stats_df.position.fillna("").str.strip() != "-"].copy()

    # Aggregate to set level (team totals)
    set_agg = (
        stats_df.groupby(["match_id", "game_number"])[COUNTING_STATS]
        .sum(min_count=1)
        .reset_index()
    )
    # Pull match-level metadata onto set rows
    match_meta = games[["match_id", "date", "is_playoff"]].drop_duplicates()
    set_agg = set_agg.merge(match_meta, on="match_id", how="left")
    set_agg["week"] = set_agg["date"].map(WEEK_DATES)

    # Add Bean's per-set margin (for sets where the score is known)
    margins = []
    for _, r in set_agg.iterrows():
        g = games[games.match_id == r.match_id].iloc[0]
        n = int(r.game_number)
        f = g[f"bean_points_set{n}_for"]
        a = g[f"bean_points_set{n}_against"]
        margins.append((f - a) if pd.notna(f) and pd.notna(a) else np.nan)
    set_agg["bean_margin"] = margins

    # Aggregate sets to weekly team totals + averages
    weekly = (
        set_agg.groupby(["week", "is_playoff"])
        .agg(
            sets=("match_id", "count"),
            kills_per_set=("kills", "mean"),
            errors_per_set=("errors", "mean"),
            attack_attempts_per_set=("attack_attempts", "mean"),
            digs_per_set=("digs", "mean"),
            aces_per_set=("aces", "mean"),
            assists_per_set=("assists", "mean"),
            kills_sum=("kills", "sum"),
            errors_sum=("errors", "sum"),
            attempts_sum=("attack_attempts", "sum"),
            margin_avg=("bean_margin", "mean"),
        )
        .reset_index()
    )
    # Recompute team hit% from weekly sums (correct way; avoids averaging-of-ratios bias)
    weekly["team_hit_pct"] = (weekly.kills_sum - weekly.errors_sum) / weekly.attempts_sum
    return weekly


def compute_trend(weekly: pd.DataFrame, stat: str) -> dict:
    reg = weekly[~weekly.is_playoff].sort_values("week")
    if len(reg) < 3:
        return {"insufficient_data": True}
    x = reg["week"].astype(float).values
    y = reg[stat].values
    valid = ~np.isnan(y)
    if valid.sum() < 3:
        return {"insufficient_data": True}
    x, y = x[valid], y[valid]
    res = stats.linregress(x, y)
    return {
        "stat": stat,
        "slope": float(res.slope),
        "intercept": float(res.intercept),
        "r_value": float(res.rvalue),
        "p_value": float(res.pvalue),
        "n": int(len(x)),
        "values_by_week": {int(w): float(v) for w, v in zip(x, y)},
        "direction": "up" if res.slope > 0 else "down" if res.slope < 0 else "flat",
        "noteworthy": bool(res.pvalue < 0.10),  # loose threshold at n=7
    }


def per_player_trends() -> dict:
    stats_df = pd.read_csv(PLAYER_STATS_CSV)
    stats_df = stats_df[stats_df.position.fillna("").str.strip() != "-"].copy()
    stats_df["week"] = stats_df["date"].map(WEEK_DATES)
    # Restrict to regular season
    reg = stats_df[stats_df.week.between(1, 7)]
    out = {}
    for player in sorted(reg.player_name.unique()):
        sub = reg[reg.player_name == player]
        weekly = sub.groupby("week").agg(
            sets=("game_number", "count"),
            kills_per_set=("kills", "mean"),
            errors_per_set=("errors", "mean"),
            attempts_sum=("attack_attempts", "sum"),
            kills_sum=("kills", "sum"),
            errors_sum=("errors", "sum"),
            digs_per_set=("digs", "mean"),
        ).reset_index()
        weekly["hit_pct"] = (weekly.kills_sum - weekly.errors_sum) / weekly.attempts_sum

        # Trend on weekly hit_pct
        x = weekly["week"].values.astype(float)
        y = weekly["hit_pct"].values
        valid = ~np.isnan(y)
        if valid.sum() >= 3:
            res = stats.linregress(x[valid], y[valid])
            slope = float(res.slope)
            p = float(res.pvalue)
        else:
            slope = None
            p = None

        out[player] = {
            "weekly_hit_pct": {int(w): float(v) if pd.notna(v) else None
                                for w, v in zip(weekly.week, weekly.hit_pct)},
            "weekly_kills_per_set": {int(w): float(v) if pd.notna(v) else None
                                      for w, v in zip(weekly.week, weekly.kills_per_set)},
            "hit_pct_slope_per_week": slope,
            "hit_pct_slope_p_value": p,
        }
    return out


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def main() -> None:
    weekly = build_weekly_team_stats()

    banner("SEASON TRENDS")
    print("Weekly team stats:")
    print(weekly.to_string(index=False, float_format=lambda v: f"{v:.3f}" if abs(v) < 1 else f"{v:.2f}"))

    banner("FINDING 1 — Team-level trends across regular-season weeks 1-7")
    trend_stats = [
        "team_hit_pct", "kills_per_set", "errors_per_set",
        "digs_per_set", "aces_per_set", "margin_avg",
    ]
    trends = {s: compute_trend(weekly, s) for s in trend_stats}
    print(f"\n  {'stat':<22}{'slope/wk':>12}{'r':>8}{'p':>8}{'direction':>12}  noteworthy")
    print(f"  {'-'*22}{'-'*12}{'-'*8}{'-'*8}{'-'*12}  {'-'*10}")
    for s, t in trends.items():
        if t.get("insufficient_data"):
            print(f"  {s:<22}  insufficient data")
            continue
        mark = "*" if t["noteworthy"] else " "
        print(f"  {s:<22}{t['slope']:>+12.4f}{t['r_value']:>+8.3f}"
              f"{t['p_value']:>8.3f}{t['direction']:>12}  {mark}")
    print("\n  noteworthy = p<0.10 (loose threshold given n=7 weekly data points)")

    banner("FINDING 2 — Playoff vs regular-season trend continuation")
    print("  For each stat, where did playoffs land vs the regular-season trend line?")
    print(f"\n  {'stat':<22}{'reg_trend_end':>15}{'playoff_avg':>14}{'verdict':>20}")
    print(f"  {'-'*22}{'-'*15}{'-'*14}{'-'*20}")
    playoff_rows = weekly[weekly.is_playoff]
    for s, t in trends.items():
        if t.get("insufficient_data"):
            continue
        # Extrapolate the regular-season line to week 8 and 9, compare to actual playoff avg
        proj_week_8 = t["intercept"] + t["slope"] * 8
        proj_week_9 = t["intercept"] + t["slope"] * 9
        proj_avg = (proj_week_8 + proj_week_9) / 2
        actual = playoff_rows[s].mean() if s in playoff_rows.columns else float("nan")
        diff = actual - proj_avg
        # Verdict: are playoffs ABOVE or BELOW the extrapolated trend?
        if pd.isna(actual):
            verdict = "no playoff data"
        elif abs(diff) < abs(t['slope']):
            verdict = "continued trend"
        elif (diff > 0 and t['direction'] == 'up') or (diff < 0 and t['direction'] == 'down'):
            verdict = "ACCELERATED trend"
        else:
            verdict = "BROKE trend"
        print(f"  {s:<22}{proj_avg:>+15.4f}{actual:>+14.4f}{verdict:>20}")

    banner("FINDING 3 — Per-player hit% trend across regular season")
    pp = per_player_trends()
    print(f"\n  {'player':<8}{'w1':>7}{'w2':>7}{'w3':>7}{'w4':>7}{'w5':>7}{'w6':>7}{'w7':>7}"
          f"{'slope':>10}{'p':>8}")
    for p, d in pp.items():
        def fmt(v):
            return f"{v:>+7.3f}" if v is not None and not (isinstance(v, float) and np.isnan(v)) else "    -  "
        cells = [fmt(d["weekly_hit_pct"].get(w)) for w in range(1, 8)]
        slope_str = f"{d['hit_pct_slope_per_week']:>+10.4f}" if d['hit_pct_slope_per_week'] is not None else "         -"
        p_str = f"{d['hit_pct_slope_p_value']:>8.3f}" if d['hit_pct_slope_p_value'] is not None else "       -"
        print(f"  {p:<8}{''.join(cells)}{slope_str}{p_str}")

    # Write JSON
    payload = {
        "meta": {
            "weeks": "regular season weeks 1-7; playoffs = weeks 8-9",
            "bye_week": "2026-02-04",
            "n_regular_season_weeks": 7,
        },
        "weekly_team_stats": weekly.to_dict(orient="records"),
        "trends": trends,
        "playoff_vs_trend": {
            s: {
                "projected_playoff_avg": (
                    (t["intercept"] + t["slope"] * 8 + t["intercept"] + t["slope"] * 9) / 2
                    if not t.get("insufficient_data") else None
                ),
                "actual_playoff_avg": (
                    float(weekly[weekly.is_playoff][s].mean())
                    if s in weekly.columns else None
                ),
            }
            for s, t in trends.items()
        },
        "per_player_trends": pp,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print()
    print(f"WROTE {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
