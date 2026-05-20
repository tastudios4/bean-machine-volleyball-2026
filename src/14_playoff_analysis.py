"""
14_playoff_analysis.py

Bean Machine's championship run analysis. Bean won the Silver bracket as the
#1 seed with a 2-0 sweep in both playoff matches:
  - 03-04 Silver M2 vs Block You-Ah (team 15)
  - 03-11 Silver Final M6 vs Sets Up (team 2)

Six playoff game tabs in player_stats: 03-04 G1/G2/G3, 03-11 G1/G2/G3.
Only 03-04 G1 has a recorded set score (25-19); the other 5 set scores are
absent from the league sheet (notes say "match was decided" — not recorded).

What we compare:
  1. Bean's team-aggregate stats per set, playoff vs regular season
  2. Per-player playoff stats vs regular-season per-set averages
  3. Tae's role coverage: who absorbed his position?
  4. Cole's position shift (regular season was L/OH3 heavy; playoffs were middle)

Caveats:
  - Tiny n: 6 playoff sets vs 20 regular-season sets (with stats)
  - Playoff format is 21-21-15 not 25-25-15. Rate stats (hit%, srv%, ace%) are
    comparable; counting stats are slightly suppressed in playoffs by the
    shorter cap — though Bean was winning both matches so games may not have
    reached the cap anyway.

Output: stdout + data/processed/findings_playoff.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
BEAN_GAMES_CSV = ROOT / "data" / "processed" / "bean_machine_games.csv"
PLAYER_STATS_CSV = ROOT / "data" / "processed" / "bean_machine_player_stats.csv"
OUT_JSON = ROOT / "data" / "processed" / "findings_playoff.json"

COUNTING_STATS = [
    "attack_attempts", "kills", "errors", "assists",
    "blocks_solo", "blocks_assist", "digs",
    "aces", "service_errors", "total_serves",
    "sr_attempts", "sr_0", "sr_1", "sr_2", "sr_3",
]


def load_data() -> tuple[pd.DataFrame, pd.DataFrame]:
    games = pd.read_csv(BEAN_GAMES_CSV)
    stats_df = pd.read_csv(PLAYER_STATS_CSV)
    # Add is_playoff flag onto stats
    stats_df = stats_df.merge(
        games[["match_id", "is_playoff"]], on="match_id", how="left"
    )
    # Filter out games where a player didn't play (position == "-")
    stats_df = stats_df[stats_df.position.fillna("").str.strip() != "-"].copy()
    return games, stats_df


def team_aggregates_by_set(stats_df: pd.DataFrame) -> pd.DataFrame:
    agg = (
        stats_df.groupby(["match_id", "game_number", "is_playoff"])[COUNTING_STATS]
        .sum(min_count=1)
        .reset_index()
    )
    with np.errstate(divide="ignore", invalid="ignore"):
        agg["team_hit_pct"] = (agg.kills - agg.errors) / agg.attack_attempts
        agg["team_srv_pct"] = (agg.total_serves - agg.service_errors) / agg.total_serves
        agg["team_ace_pct"] = agg.aces / agg.total_serves
    return agg


def compare_team_stats(team_agg: pd.DataFrame) -> dict:
    reg = team_agg[~team_agg.is_playoff]
    play = team_agg[team_agg.is_playoff]
    out = {}
    for stat in COUNTING_STATS + ["team_hit_pct", "team_srv_pct", "team_ace_pct"]:
        r_mean = float(reg[stat].mean())
        p_mean = float(play[stat].mean())
        out[stat] = {
            "regular_season_avg_per_set": r_mean,
            "playoff_avg_per_set": p_mean,
            "delta": p_mean - r_mean,
            "delta_pct": (p_mean - r_mean) / r_mean if r_mean else None,
        }
    out["__meta"] = {
        "n_regular_season_sets": int(len(reg)),
        "n_playoff_sets": int(len(play)),
    }
    return out


def player_comparison(stats_df: pd.DataFrame) -> dict:
    reg = stats_df[~stats_df.is_playoff]
    play = stats_df[stats_df.is_playoff]

    players = sorted(stats_df.player_name.unique())
    out = {}
    for p in players:
        r = reg[reg.player_name == p]
        po = play[play.player_name == p]

        def per_set(g, col):
            return float(g[col].mean()) if len(g) else None

        def hit_pct(g):
            att = g.attack_attempts.sum()
            return float((g.kills.sum() - g.errors.sum()) / att) if att else None

        out[p] = {
            "regular_season_sets": int(len(r)),
            "playoff_sets": int(len(po)),
            "regular_season": {
                "kills_per_set": per_set(r, "kills"),
                "errors_per_set": per_set(r, "errors"),
                "hit_pct": hit_pct(r),
                "digs_per_set": per_set(r, "digs"),
                "aces_per_set": per_set(r, "aces"),
                "assists_per_set": per_set(r, "assists"),
            },
            "playoffs": {
                "kills_per_set": per_set(po, "kills"),
                "errors_per_set": per_set(po, "errors"),
                "hit_pct": hit_pct(po),
                "digs_per_set": per_set(po, "digs"),
                "aces_per_set": per_set(po, "aces"),
                "assists_per_set": per_set(po, "assists"),
            },
        }
    return out


def position_shift_analysis(stats_df: pd.DataFrame) -> dict:
    """Specifically: did Cole and others shift positions to cover Tae?"""
    # Tae's regular-season positions
    tae_reg = stats_df[(stats_df.player_name == "Tae") & (~stats_df.is_playoff)]
    tae_pos_counts = tae_reg.position.value_counts().to_dict()

    # Each player's position frequency in regular season vs playoffs
    players = ["Cole", "Cade", "Andy", "Jeremy", "Allen", "Zane"]
    out = {
        "tae_regular_season_positions": tae_pos_counts,
        "tae_playoff_positions": "did not play (injured)",
        "position_shifts": {},
    }
    for p in players:
        r = stats_df[(stats_df.player_name == p) & (~stats_df.is_playoff)]
        po = stats_df[(stats_df.player_name == p) & (stats_df.is_playoff)]
        out["position_shifts"][p] = {
            "regular_season": dict(r.position.value_counts()),
            "playoffs": dict(po.position.value_counts()),
        }
    return out


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def main() -> None:
    games, stats_df = load_data()
    team_agg = team_aggregates_by_set(stats_df)

    banner("PLAYOFF / CHAMPIONSHIP ANALYSIS")
    print(f"Playoff matches: 2 (both Bean wins, 2-0 sweeps)")
    print(f"  03-04 Silver M2 vs Block You-Ah (team 15)")
    print(f"  03-11 Silver Final vs Sets Up (team 2)")
    print(f"Playoff game tabs in player_stats: 6 (3 per match)")
    print(f"Tae missed all 6 playoff games due to injury")

    # 1. Team aggregate comparison
    banner("FINDING 1 — Team aggregate stats: playoffs vs regular season per set")
    cmp = compare_team_stats(team_agg)
    meta = cmp.pop("__meta")
    print(f"  n regular-season sets (with stats): {meta['n_regular_season_sets']}")
    print(f"  n playoff sets (with stats):        {meta['n_playoff_sets']}")
    print(f"\n  {'stat':<22}{'reg':>10}{'playoff':>10}{'delta':>10}{'delta_%':>10}")
    print(f"  {'-'*22}{'-'*10}{'-'*10}{'-'*10}{'-'*10}")
    headline_stats = ["kills", "errors", "team_hit_pct", "digs", "aces",
                       "team_srv_pct", "service_errors", "assists",
                       "blocks_solo", "blocks_assist", "sr_attempts", "sr_3"]
    for stat in headline_stats:
        d = cmp[stat]
        delta_pct = f"{d['delta_pct']:+.1%}" if d['delta_pct'] is not None else "-"
        # Format rate stats with more decimals
        if stat.endswith("_pct"):
            print(f"  {stat:<22}{d['regular_season_avg_per_set']:>+10.3f}"
                  f"{d['playoff_avg_per_set']:>+10.3f}"
                  f"{d['delta']:>+10.3f}{delta_pct:>10}")
        else:
            print(f"  {stat:<22}{d['regular_season_avg_per_set']:>10.2f}"
                  f"{d['playoff_avg_per_set']:>10.2f}"
                  f"{d['delta']:>+10.2f}{delta_pct:>10}")
    print("\n  NOTE: counting stats are slightly suppressed in playoffs because")
    print("  format is 21-21-15 (vs 25-25-15 in regular season). Rate stats")
    print("  (hit%, srv%) are not affected by cap differences.")

    # 2. Per-player comparison
    banner("FINDING 2 — Per-player: playoffs vs regular season (per-set averages)")
    pc = player_comparison(stats_df)
    print(f"\n  {'player':<8}{'reg_n':>6}{'po_n':>5}  "
          f"{'k_R':>6}{'k_P':>6}{'Δ':>7}  "
          f"{'hit_R':>7}{'hit_P':>7}{'Δ':>8}  "
          f"{'d_R':>6}{'d_P':>6}{'Δ':>7}")
    for p, d in pc.items():
        r = d["regular_season"]; po = d["playoffs"]
        if d["playoff_sets"] == 0:
            print(f"  {p:<8}{d['regular_season_sets']:>6}{0:>5}  (did not play in playoffs)")
            continue
        def fmt_delta(a, b, w, dp=1):
            if a is None or b is None:
                return " " * (w - 1) + "-"
            return f"{b - a:>+{w}.{dp}f}"
        def fmt_v(v, w, dp=1):
            if v is None:
                return " " * (w - 1) + "-"
            return f"{v:>{w}.{dp}f}"
        print(f"  {p:<8}{d['regular_season_sets']:>6}{d['playoff_sets']:>5}  "
              f"{fmt_v(r['kills_per_set'], 6)}{fmt_v(po['kills_per_set'], 6)}"
              f"{fmt_delta(r['kills_per_set'], po['kills_per_set'], 7)}  "
              f"{fmt_v(r['hit_pct'], 7, 3)}{fmt_v(po['hit_pct'], 7, 3)}"
              f"{fmt_delta(r['hit_pct'], po['hit_pct'], 8, 3)}  "
              f"{fmt_v(r['digs_per_set'], 6)}{fmt_v(po['digs_per_set'], 6)}"
              f"{fmt_delta(r['digs_per_set'], po['digs_per_set'], 7)}")

    # 3. Position shifts (Tae coverage)
    banner("FINDING 3 — Position shifts: who covered for Tae?")
    ps = position_shift_analysis(stats_df)
    print(f"\n  Tae's regular-season positions (he played 20 sets):")
    for pos, n in sorted(ps["tae_regular_season_positions"].items(), key=lambda x: -x[1]):
        print(f"    {pos}: {n} sets")
    print(f"\n  Each other player's positions, regular season -> playoffs:")
    for p, d in ps["position_shifts"].items():
        r_str = ", ".join(f"{pos}×{n}" for pos, n in sorted(d['regular_season'].items(),
                                                              key=lambda x: -x[1]))
        p_str = ", ".join(f"{pos}×{n}" for pos, n in sorted(d['playoffs'].items(),
                                                             key=lambda x: -x[1])) or "—"
        print(f"    {p:<8}  REG: {r_str}")
        print(f"    {'':<8}  PLY: {p_str}")
        print()

    # Write JSON
    payload = {
        "meta": {
            "playoff_matches": [
                {"date": "2026-03-04", "round": "Silver M2", "opponent": "Block You-Ah",
                 "opponent_team_number": 15, "result": "Bean won 2-0",
                 "scores_recorded": ["G1: 25-19", "G2: unrecorded", "G3: unrecorded"]},
                {"date": "2026-03-11", "round": "Silver Final", "opponent": "Sets Up",
                 "opponent_team_number": 2, "result": "Bean won 2-0 (championship)",
                 "scores_recorded": ["unrecorded"]},
            ],
            "tae_status": "injured, did not play any of 6 playoff games",
            "format_note": "playoff games to 21-21-15; regular season 25-25-15",
        },
        "team_aggregate_comparison": cmp,
        "player_comparison": pc,
        "position_shifts": ps,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"WROTE {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
