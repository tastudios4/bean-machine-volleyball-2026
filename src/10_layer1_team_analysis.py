"""
10_layer1_team_analysis.py

Layer 1: inside-the-team analysis. Why did Bean win or lose at the SET level?

Process:
  1. Build a set-level analytical table. One row per set with:
     - Bean's per-set points + opponent's points (from bean_machine_games.csv)
     - Team-aggregate stats summed across the 7 players (from
       bean_machine_player_stats.csv)
     - Cole's position assignment for that set
  2. Restrict to sets where BOTH a complete set score AND player stats
     are present. Regular season only (playoffs have format differences
     and only 1 usable set; including them would mix apples and oranges).
  3. Compute 5 finding-blocks:
       (1) Stat correlations with set wins
       (2) Offense vs defense decisive comparison
       (3) Threshold patterns ("won every set with X<N")
       (4) Player-level splits + the Allen story
       (5) Cole position-flex
       (6) Margin distribution

Outputs:
  - stdout: human-readable findings, every number with n
  - data/processed/findings_layer1.json: structured for 13_synthesize.py
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats

ROOT = Path(__file__).resolve().parent.parent
BEAN_GAMES_CSV = ROOT / "data" / "processed" / "bean_machine_games.csv"
PLAYER_STATS_CSV = ROOT / "data" / "processed" / "bean_machine_player_stats.csv"
OUT_JSON = ROOT / "data" / "processed" / "findings_layer1.json"

BEAN = 11

# Team-aggregate stats we'll correlate against set wins.
# Counting stats are summed across players; rate stats are recomputed at the
# team level (sums in numerator and denominator) rather than averaged.
COUNTING_STATS = [
    "attack_attempts", "kills", "errors", "assists",
    "blocks_solo", "blocks_assist", "digs",
    "aces", "service_errors", "total_serves",
    "sr_attempts", "sr_0", "sr_1", "sr_2", "sr_3",
]


def build_set_table() -> tuple[pd.DataFrame, dict[str, Any]]:
    games = pd.read_csv(BEAN_GAMES_CSV)
    stats_df = pd.read_csv(PLAYER_STATS_CSV)

    # Aggregate player stats to (match_id, game_number) level — team totals.
    grouped = stats_df.groupby(["match_id", "game_number"])
    team_stats = grouped[COUNTING_STATS].sum(min_count=1).reset_index()

    # Recompute rate stats at team level (don't average player percentages)
    with np.errstate(divide="ignore", invalid="ignore"):
        team_stats["team_hit_pct"] = (
            (team_stats["kills"] - team_stats["errors"]) / team_stats["attack_attempts"]
        )
        team_stats["team_srv_pct"] = (
            (team_stats["total_serves"] - team_stats["service_errors"])
            / team_stats["total_serves"]
        )
        team_stats["team_ace_pct"] = team_stats["aces"] / team_stats["total_serves"]
        sr_weighted = (
            team_stats["sr_1"] * 1 + team_stats["sr_2"] * 2 + team_stats["sr_3"] * 3
        )
        team_stats["team_sr_average"] = sr_weighted / team_stats["sr_attempts"]
    # Treat an unrecorded block column as 0 (not NaN) so a set with, say,
    # assist blocks but no solo blocks still gets a real team_blocks total.
    team_stats["team_blocks"] = (
        team_stats["blocks_solo"].fillna(0) + team_stats["blocks_assist"].fillna(0)
    )

    # Cole's position per set (for the Cole position-flex analysis)
    cole = stats_df[stats_df.player_name == "Cole"][["match_id", "game_number", "position"]]
    cole = cole.rename(columns={"position": "cole_position"})

    # Reshape games table to long form: one row per set
    set_rows = []
    for _, g in games.iterrows():
        for set_n in (1, 2, 3):
            bean_for = g[f"bean_points_set{set_n}_for"]
            bean_against = g[f"bean_points_set{set_n}_against"]
            set_rows.append({
                "match_id": g["match_id"],
                "game_number": set_n,
                "date": g["date"],
                "is_playoff": g["is_playoff"],
                "bean_pts_for": bean_for,
                "bean_pts_against": bean_against,
                "bean_won_set": (
                    pd.NA if pd.isna(bean_for) or pd.isna(bean_against)
                    else bool(bean_for > bean_against)
                ),
                "bean_set_margin": (
                    pd.NA if pd.isna(bean_for) or pd.isna(bean_against)
                    else bean_for - bean_against
                ),
            })
    sets = pd.DataFrame(set_rows)

    # Join with team stats and Cole's position
    sets = sets.merge(team_stats, on=["match_id", "game_number"], how="left")
    sets = sets.merge(cole, on=["match_id", "game_number"], how="left")
    sets["has_stats"] = sets["kills"].notna()
    sets["has_score"] = sets["bean_won_set"].notna()

    # Inclusion criteria for the main analysis: regular season + both score and stats
    meta = {
        "total_sets": len(sets),
        "regular_season_sets": int((~sets.is_playoff).sum()),
        "playoff_sets": int(sets.is_playoff.sum()),
        "with_score_and_stats_regular": int(
            (~sets.is_playoff & sets.has_score & sets.has_stats).sum()
        ),
        "with_score_and_stats_playoff": int(
            (sets.is_playoff & sets.has_score & sets.has_stats).sum()
        ),
        "excluded": [],
    }
    for _, r in sets.iterrows():
        if not r.has_score or not r.has_stats:
            meta["excluded"].append({
                "match_id": r.match_id,
                "game_number": int(r.game_number),
                "is_playoff": bool(r.is_playoff),
                "reason": (
                    "missing both" if not r.has_score and not r.has_stats
                    else "missing score" if not r.has_score
                    else "missing stats"
                ),
            })

    analysis = sets[(~sets.is_playoff) & sets.has_score & sets.has_stats].copy()
    analysis["bean_won_set"] = analysis["bean_won_set"].astype(bool)
    return analysis, meta


# --------------------------------------------------------------------------- #

CRITICAL_R_TABLE = {
    # df -> critical |r| for two-tailed p<0.05
    3: 0.997, 4: 0.950, 5: 0.878, 6: 0.811, 7: 0.755, 8: 0.707, 9: 0.666,
    10: 0.632, 11: 0.602, 12: 0.576, 13: 0.553, 14: 0.532, 15: 0.514,
    16: 0.497, 17: 0.482, 18: 0.468, 19: 0.456, 20: 0.444, 22: 0.423,
    25: 0.396, 30: 0.361, 40: 0.312, 50: 0.279, 100: 0.197,
}


def critical_r(n: int, alpha: float = 0.05) -> float:
    df = max(n - 2, 1)
    keys = sorted(CRITICAL_R_TABLE.keys())
    if df <= keys[0]:
        return CRITICAL_R_TABLE[keys[0]]
    if df >= keys[-1]:
        return CRITICAL_R_TABLE[keys[-1]]
    for i in range(len(keys) - 1):
        if keys[i] <= df <= keys[i + 1]:
            lo, hi = keys[i], keys[i + 1]
            frac = (df - lo) / (hi - lo)
            return CRITICAL_R_TABLE[lo] + frac * (CRITICAL_R_TABLE[hi] - CRITICAL_R_TABLE[lo])
    return 0.5


# --------------------------------------------------------------------------- #
# Finding-block 1: stat correlations
# --------------------------------------------------------------------------- #

CORRELATION_STATS = COUNTING_STATS + [
    "team_hit_pct", "team_srv_pct", "team_ace_pct", "team_sr_average",
]


def find_correlations(df: pd.DataFrame) -> list[dict]:
    y = df["bean_won_set"].astype(int)
    out = []
    for stat in CORRELATION_STATS:
        x = df[stat]
        valid = x.notna() & y.notna()
        x_v, y_v = x[valid], y[valid]
        if len(x_v) < 4 or x_v.nunique() < 2:
            continue
        r, p = stats.pearsonr(x_v, y_v)
        out.append({
            "stat": stat,
            "r": float(r),
            "p_value": float(p),
            "n": int(len(x_v)),
            "noteworthy": bool(abs(r) >= critical_r(len(x_v))),
        })
    out.sort(key=lambda d: abs(d["r"]), reverse=True)
    return out


# --------------------------------------------------------------------------- #
# Finding-block 2: what separated wins from losses
# --------------------------------------------------------------------------- #

def win_loss_factors(df: pd.DataFrame) -> dict:
    """For each candidate metric, compare wins vs losses with Cohen's d.

    IMPORTANT: opponent points per set is included but flagged as
    redundant. At the set level, losing a set means the opponent reached
    the cap by definition, so opponent points is mostly a restatement of the
    outcome, not a measure of defense quality. It is reported for
    transparency but excluded from the conclusion. The non-redundant
    defense proxies are digs and blocks.
    """
    wins = df[df.bean_won_set]
    losses = df[~df.bean_won_set]

    def cohens_d(col: str) -> float:
        pooled = float(df[col].std())
        if not pooled:
            return 0.0
        return (float(wins[col].mean()) - float(losses[col].mean())) / pooled

    specs = [
        ("team_hit_pct", "team hit %", "offense", False),
        ("digs", "digs per set", "defense", False),
        ("team_blocks", "blocks per set", "defense", False),
        ("bean_pts_against", "opponent points", "defense (redundant)", True),
    ]
    metrics = {}
    for col, label, kind, taut in specs:
        metrics[col] = {
            "label": label,
            "kind": kind,
            "mean_in_wins": float(wins[col].mean()),
            "mean_in_losses": float(losses[col].mean()),
            "cohens_d": cohens_d(col),
            "redundant": taut,
        }

    valid = {k: v for k, v in metrics.items() if not v["redundant"]}
    strongest = max(valid, key=lambda k: abs(valid[k]["cohens_d"]))

    return {
        "n_wins": int(len(wins)),
        "n_losses": int(len(losses)),
        "metrics": metrics,
        "strongest_valid_metric": strongest,
        "conclusion": (
            "Team hit % is the only metric with a large, non-redundant "
            "wins-vs-losses effect. Opponent points shows a larger raw effect "
            "but is excluded as redundant. The defense proxies (digs, "
            "blocks) are weak, and digs even runs the wrong way, so this data "
            "measures the team's offense well and its defense poorly."
        ),
    }


# --------------------------------------------------------------------------- #
# Finding-block 3: threshold patterns
# --------------------------------------------------------------------------- #

def find_thresholds(df: pd.DataFrame) -> list[dict]:
    """For each stat, find the cleanest split: a value V such that nearly all
    sets with stat <= V have one outcome and stat > V have the other.

    'Cleanness' = sum of in-bucket purity (max(w, l) / total) for both sides.
    Maximum possible cleanness = 2.0 (perfect split). Anything >= 1.8 reported.
    """
    out = []
    for stat in CORRELATION_STATS:
        x = df[stat]
        y = df.bean_won_set.astype(int)
        valid = x.notna() & y.notna()
        x_v, y_v = x[valid].reset_index(drop=True), y[valid].reset_index(drop=True)
        if len(x_v) < 6 or x_v.nunique() < 3:
            continue

        # Try splits at each unique value
        best = None
        for v in sorted(x_v.unique())[:-1]:  # don't try the max as a threshold
            low_mask = x_v <= v
            high_mask = ~low_mask
            n_low, n_high = low_mask.sum(), high_mask.sum()
            if n_low < 2 or n_high < 2:
                continue
            low_y, high_y = y_v[low_mask], y_v[high_mask]
            low_purity = max(low_y.mean(), 1 - low_y.mean())
            high_purity = max(high_y.mean(), 1 - high_y.mean())
            cleanness = low_purity + high_purity
            cand = {
                "threshold": float(v),
                "n_low": int(n_low),
                "n_high": int(n_high),
                "low_win_rate": float(low_y.mean()),
                "high_win_rate": float(high_y.mean()),
                "cleanness": float(cleanness),
            }
            if best is None or cand["cleanness"] > best["cleanness"]:
                best = cand
        if best and best["cleanness"] >= 1.8:
            best["stat"] = stat
            best["interpretation"] = (
                f"sets with {stat} <= {best['threshold']:.3g}: win rate "
                f"{best['low_win_rate']:.1%} (n={best['n_low']}); "
                f"sets with {stat} > {best['threshold']:.3g}: win rate "
                f"{best['high_win_rate']:.1%} (n={best['n_high']})"
            )
            out.append(best)
    out.sort(key=lambda d: d["cleanness"], reverse=True)
    return out


# --------------------------------------------------------------------------- #
# Finding-block 4: player splits + the Allen story
# --------------------------------------------------------------------------- #

def player_splits(set_table: pd.DataFrame) -> tuple[dict, dict]:
    """For each player, compare mean stats in won sets vs lost sets.
    Returns (per_player_splits, allen_story).
    """
    stats_df = pd.read_csv(PLAYER_STATS_CSV)
    set_outcome = set_table[["match_id", "game_number", "bean_won_set"]].copy()
    merged = stats_df.merge(set_outcome, on=["match_id", "game_number"], how="inner")
    merged = merged[merged.position.fillna("").str.strip() != "-"]

    per_player_splits = {}
    for player, grp in merged.groupby("player_name"):
        wins = grp[grp.bean_won_set]
        losses = grp[~grp.bean_won_set]
        per_player_splits[player] = {
            "sets_in_wins": int(len(wins)),
            "sets_in_losses": int(len(losses)),
            "kills_per_set_in_wins": float(wins.kills.mean()) if len(wins) else None,
            "kills_per_set_in_losses": float(losses.kills.mean()) if len(losses) else None,
            "errors_per_set_in_wins": float(wins.errors.mean()) if len(wins) else None,
            "errors_per_set_in_losses": float(losses.errors.mean()) if len(losses) else None,
            "digs_per_set_in_wins": float(wins.digs.mean()) if len(wins) else None,
            "digs_per_set_in_losses": float(losses.digs.mean()) if len(losses) else None,
            "aces_per_set_in_wins": float(wins.aces.mean()) if len(wins) else None,
            "aces_per_set_in_losses": float(losses.aces.mean()) if len(losses) else None,
        }

    # The Allen story
    allen = merged[merged.player_name == "Allen"]
    a_wins = allen[allen.bean_won_set]
    a_losses = allen[~allen.bean_won_set]

    def hit_pct(grp):
        att = grp.attack_attempts.sum()
        k = grp.kills.sum()
        e = grp.errors.sum()
        return float((k - e) / att) if att > 0 else float("nan")

    allen_story = {
        "season_hit_pct_all_sets": hit_pct(allen),
        "season_hit_pct_in_wins": hit_pct(a_wins),
        "season_hit_pct_in_losses": hit_pct(a_losses),
        "n_sets_in_wins": int(len(a_wins)),
        "n_sets_in_losses": int(len(a_losses)),
        "attempts_in_wins": int(a_wins.attack_attempts.sum()),
        "attempts_in_losses": int(a_losses.attack_attempts.sum()),
        "kills_in_wins": int(a_wins.kills.sum()),
        "kills_in_losses": int(a_losses.kills.sum()),
        "errors_in_wins": int(a_wins.errors.sum()),
        "errors_in_losses": int(a_losses.errors.sum()),
    }
    return per_player_splits, allen_story


# --------------------------------------------------------------------------- #
# Finding-block 5: Cole position-flex
# --------------------------------------------------------------------------- #

def cole_position_flex(set_table: pd.DataFrame) -> list[dict]:
    out = []
    for pos, grp in set_table.groupby("cole_position"):
        if pos in ("", "-") or pd.isna(pos):
            continue
        out.append({
            "position": str(pos),
            "n_sets": int(len(grp)),
            "win_rate": float(grp.bean_won_set.mean()),
            "team_kills_avg": float(grp.kills.mean()),
            "team_errors_avg": float(grp.errors.mean()),
            "team_hit_pct_avg": float(grp.team_hit_pct.mean()),
            "bean_margin_avg": float(grp.bean_set_margin.mean()),
        })
    out.sort(key=lambda d: d["n_sets"], reverse=True)
    return out


# --------------------------------------------------------------------------- #
# Finding-block 6: margin distribution
# --------------------------------------------------------------------------- #

def margin_distribution(set_table: pd.DataFrame) -> dict:
    def summary(s):
        if not len(s):
            return None
        q = s.quantile([0.25, 0.5, 0.75])
        return {
            "n": int(len(s)),
            "min": float(s.min()),
            "q1": float(q.loc[0.25]),
            "median": float(q.loc[0.5]),
            "q3": float(q.loc[0.75]),
            "max": float(s.max()),
            "mean": float(s.mean()),
            "std": float(s.std()),
        }
    wins = set_table[set_table.bean_won_set].bean_set_margin
    losses = set_table[~set_table.bean_won_set].bean_set_margin
    return {
        "wins": summary(wins),
        "losses": summary(losses),
        "interpretation": (
            f"Bean won by {wins.mean():.1f} on average (median {wins.median():.1f}); "
            f"lost by {-losses.mean():.1f} on average (median {-losses.median():.1f})."
        ),
    }


# --------------------------------------------------------------------------- #
# Main / printout
# --------------------------------------------------------------------------- #

def print_section(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def main() -> None:
    set_table, meta = build_set_table()

    print_section("LAYER 1 — INSIDE THE TEAM")
    print(f"Regular-season sets total: {meta['regular_season_sets']}")
    print(f"  with score AND stats: {meta['with_score_and_stats_regular']} (analysis sample)")
    print(f"Playoff sets total: {meta['playoff_sets']}")
    print(f"  with score AND stats: {meta['with_score_and_stats_playoff']} (excluded from main analysis)")
    print(f"Excluded sets: {len(meta['excluded'])}")
    for e in meta["excluded"]:
        print(f"  - {e['match_id']} G{e['game_number']}: {e['reason']}"
              f"{' (playoff)' if e['is_playoff'] else ''}")
    n = len(set_table)
    bean_w = int(set_table.bean_won_set.sum())
    bean_l = n - bean_w
    print(f"\nAnalysis sample: n={n} sets ({bean_w} Bean wins, {bean_l} Bean losses)")
    print(f"At n={n}, |r|>={critical_r(n):.3f} is roughly p<0.05 (two-tailed).")

    # 1. Correlations
    print_section("FINDING 1 — Stat correlations with set wins")
    corrs = find_correlations(set_table)
    print(f"  {'stat':<22}{'r':>8}{'p':>8}{'n':>5}  noteworthy")
    print(f"  {'-'*22}{'-'*8}{'-'*8}{'-'*5}  {'-'*10}")
    for c in corrs:
        mark = "*" if c["noteworthy"] else " "
        print(f"  {c['stat']:<22}{c['r']:>+8.3f}{c['p_value']:>8.3f}{c['n']:>5}  {mark}")

    # 2. What separated wins from losses
    print_section("FINDING 2 — What separated wins from losses")
    wf = win_loss_factors(set_table)
    print(f"  n_wins={wf['n_wins']}, n_losses={wf['n_losses']}")
    print(f"  {'metric':<20}{'wins':>9}{'losses':>9}{'cohen_d':>9}   note")
    print(f"  {'-'*20}{'-'*9}{'-'*9}{'-'*9}   {'-'*24}")
    for m in wf["metrics"].values():
        note = "EXCLUDED: redundant" if m["redundant"] else m["kind"]
        print(f"  {m['label']:<20}{m['mean_in_wins']:>9.3f}{m['mean_in_losses']:>9.3f}"
              f"{m['cohens_d']:>+9.2f}   {note}")
    strongest = wf["metrics"][wf["strongest_valid_metric"]]["label"]
    print(f"  Strongest non-redundant factor: {strongest}")
    print(f"  {wf['conclusion']}")

    # 3. Thresholds
    print_section("FINDING 3 — Threshold patterns (cleanness >= 1.8)")
    thresholds = find_thresholds(set_table)
    if not thresholds:
        print("  No clean threshold patterns found at this sample size.")
    for t in thresholds:
        print(f"  [{t['stat']}] cleanness={t['cleanness']:.3f}")
        print(f"    {t['interpretation']}")

    # 4. Player splits + Allen
    print_section("FINDING 4 — Player splits (per-set means) + Allen story")
    splits, allen = player_splits(set_table)
    print(f"\n  {'player':<8}{'k_W':>6}{'k_L':>6}{'e_W':>6}{'e_L':>6}{'d_W':>6}{'d_L':>6}{'a_W':>6}{'a_L':>6}")
    for p in sorted(splits.keys()):
        s = splits[p]
        def fmt(v):
            return f"{v:>5.1f}" if v is not None else "  -  "
        print(f"  {p:<8}{fmt(s['kills_per_set_in_wins'])}{fmt(s['kills_per_set_in_losses'])}"
              f"{fmt(s['errors_per_set_in_wins'])}{fmt(s['errors_per_set_in_losses'])}"
              f"{fmt(s['digs_per_set_in_wins'])}{fmt(s['digs_per_set_in_losses'])}"
              f"{fmt(s['aces_per_set_in_wins'])}{fmt(s['aces_per_set_in_losses'])}")
    print("\n  ALLEN STORY:")
    print(f"    Hit % across all sets: {allen['season_hit_pct_all_sets']:+.3f} "
          f"(K-E={allen['kills_in_wins']+allen['kills_in_losses']}-"
          f"{allen['errors_in_wins']+allen['errors_in_losses']} on "
          f"{allen['attempts_in_wins']+allen['attempts_in_losses']} attempts)")
    print(f"    In Bean wins:   hit % = {allen['season_hit_pct_in_wins']:+.3f} "
          f"(K-E={allen['kills_in_wins']}-{allen['errors_in_wins']} on "
          f"{allen['attempts_in_wins']} attempts across {allen['n_sets_in_wins']} sets)")
    print(f"    In Bean losses: hit % = {allen['season_hit_pct_in_losses']:+.3f} "
          f"(K-E={allen['kills_in_losses']}-{allen['errors_in_losses']} on "
          f"{allen['attempts_in_losses']} attempts across {allen['n_sets_in_losses']} sets)")

    # 5. Cole position-flex
    print_section("FINDING 5 — Cole position-flex")
    cpf = cole_position_flex(set_table)
    print(f"  {'pos':<6}{'n':>4}{'win%':>8}{'team_k':>9}{'team_e':>9}{'hit%':>8}{'margin':>9}")
    for c in cpf:
        print(f"  {c['position']:<6}{c['n_sets']:>4}{c['win_rate']:>8.1%}"
              f"{c['team_kills_avg']:>9.1f}{c['team_errors_avg']:>9.1f}"
              f"{c['team_hit_pct_avg']:>+8.3f}{c['bean_margin_avg']:>+9.1f}")
    print("  (n per position is tiny — read as suggestive, not statistical)")

    # 6. Margin distribution
    print_section("FINDING 6 — Margin distribution")
    md = margin_distribution(set_table)
    for k in ("wins", "losses"):
        d = md[k]
        if d:
            print(f"  {k.capitalize()}: n={d['n']}, mean={d['mean']:+.1f}, "
                  f"min={d['min']:+.0f}, q1={d['q1']:+.1f}, median={d['median']:+.1f}, "
                  f"q3={d['q3']:+.1f}, max={d['max']:+.0f}")
    print(f"  {md['interpretation']}")

    # Write JSON
    payload = {
        "meta": meta | {
            "analysis_n": n,
            "bean_wins": bean_w,
            "bean_losses": bean_l,
            "critical_r_for_p05": critical_r(n),
            "scope": "regular season only; playoffs excluded due to format differences "
                     "and only 1 usable set with both score and stats",
        },
        "stat_correlations": corrs,
        "win_loss_factors": wf,
        "thresholds": thresholds,
        "player_splits": splits,
        "allen_story": allen,
        "cole_position_flex": cpf,
        "margin_distribution": md,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print()
    print(f"WROTE {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
