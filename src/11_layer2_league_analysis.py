"""
11_layer2_league_analysis.py

Layer 2: outside-the-team analysis using league_matches.csv and
league_standings.csv. Puts Bean's season into league context.

Computes 5 finding-blocks:
  1. Strength of schedule for Bean (opponent win % per match)
  2. Pythagorean expectation for all 15 teams (k=2)
  3. League-wide margin distribution (where does Bean sit?)
  4. Bean's per-opponent margin (head-to-head context)
  5. Silver vs Gold bracket comparison

Output: stdout findings + data/processed/findings_layer2.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
LEAGUE_MATCHES_CSV = ROOT / "data" / "processed" / "league_matches.csv"
STANDINGS_CSV = ROOT / "data" / "processed" / "league_standings.csv"
BEAN_GAMES_CSV = ROOT / "data" / "processed" / "bean_machine_games.csv"
OUT_JSON = ROOT / "data" / "processed" / "findings_layer2.json"

BEAN = 11
PYTH_EXPONENT = 2.0  # standard volleyball/baseball default

# Bracket assignments observed in league_raw.xlsx (rows 67-95)
GOLD_TEAMS = {4, 5, 6, 8, 9, 10, 12, 14}    # 8 teams
SILVER_TEAMS = {1, 2, 3, 7, 11, 13, 15}     # 7 teams


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #

def per_team_set_totals(league: pd.DataFrame) -> pd.DataFrame:
    """Sum points scored and conceded per team across all sets of all matches
    (regular season only). Also count sets won, lost, played."""
    reg = league[~league.is_playoff].copy()
    rows = []
    for team in range(1, 16):
        pf = pa = sets_won = sets_lost = sets_played = 0
        for _, m in reg.iterrows():
            if m.team_a_number == team:
                self_cols, opp_cols = (("set1_a","set2_a","set3_a"),
                                       ("set1_b","set2_b","set3_b"))
            elif m.team_b_number == team:
                self_cols, opp_cols = (("set1_b","set2_b","set3_b"),
                                       ("set1_a","set2_a","set3_a"))
            else:
                continue
            for s, o in zip(self_cols, opp_cols):
                sv, ov = m[s], m[o]
                if pd.isna(sv) or pd.isna(ov):
                    continue
                pf += sv
                pa += ov
                sets_played += 1
                if sv > ov:
                    sets_won += 1
                elif sv < ov:
                    sets_lost += 1
        rows.append({
            "team_number": team,
            "points_for": int(pf),
            "points_against": int(pa),
            "sets_won_parsed": sets_won,
            "sets_lost_parsed": sets_lost,
            "sets_played_parsed": sets_played,
        })
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- #
# Finding 1: Strength of schedule
# --------------------------------------------------------------------------- #

def strength_of_schedule(bean: pd.DataFrame, standings: pd.DataFrame) -> dict:
    reg = bean[~bean.is_playoff].copy()
    reg["opponent_number"] = reg.apply(
        lambda r: r.team_b_number if r.team_a_number == BEAN else r.team_a_number, axis=1
    )
    win_pct_lookup = dict(zip(standings.team_number, standings.win_pct))
    rec_lookup = dict(zip(standings.team_number,
                          standings.wins.astype(str) + "W-" + standings.losses.astype(str) + "L"))
    name_lookup = dict(zip(standings.team_number, standings.team_name))

    matches = []
    for _, r in reg.iterrows():
        opp = int(r.opponent_number)
        matches.append({
            "date": r.date,
            "opponent_team_number": opp,
            "opponent_name": name_lookup[opp],
            "opponent_record": rec_lookup[opp],
            "opponent_win_pct": float(win_pct_lookup[opp]),
            "bean_sets_won": int(r.sets_won_by_bean),
            "bean_sets_lost": int(r.sets_lost_by_bean),
            "bean_won_match": bool(r.bean_won),
        })

    avg_opp_pct = float(np.mean([m["opponent_win_pct"] for m in matches]))
    # Split by opponent strength
    strong = [m for m in matches if m["opponent_win_pct"] > 0.5]
    weak = [m for m in matches if m["opponent_win_pct"] < 0.5]
    median = [m for m in matches if m["opponent_win_pct"] == 0.5]
    return {
        "average_opponent_win_pct": avg_opp_pct,
        "matches": matches,
        "vs_strong_opponents": {
            "n": len(strong),
            "bean_set_wins": sum(m["bean_sets_won"] for m in strong),
            "bean_set_losses": sum(m["bean_sets_lost"] for m in strong),
        },
        "vs_weak_opponents": {
            "n": len(weak),
            "bean_set_wins": sum(m["bean_sets_won"] for m in weak),
            "bean_set_losses": sum(m["bean_sets_lost"] for m in weak),
        },
        "vs_median_opponents": {
            "n": len(median),
            "bean_set_wins": sum(m["bean_sets_won"] for m in median),
            "bean_set_losses": sum(m["bean_sets_lost"] for m in median),
        },
    }


# --------------------------------------------------------------------------- #
# Finding 2: Pythagorean expectation
# --------------------------------------------------------------------------- #

def pythagorean(team_totals: pd.DataFrame, standings: pd.DataFrame) -> list[dict]:
    out = []
    for _, t in team_totals.iterrows():
        pf, pa = t.points_for, t.points_against
        if pf + pa == 0:
            continue
        exp_win_pct = (pf ** PYTH_EXPONENT) / (pf ** PYTH_EXPONENT + pa ** PYTH_EXPONENT)
        # Use the standings' total_games (official) so comparison is apples-to-apples
        actual = standings.loc[standings.team_number == t.team_number].iloc[0]
        expected_wins = exp_win_pct * actual.total_games
        out.append({
            "team_number": int(t.team_number),
            "team_name": actual.team_name,
            "points_for": int(pf),
            "points_against": int(pa),
            "actual_wins": int(actual.wins),
            "actual_losses": int(actual.losses),
            "total_games": int(actual.total_games),
            "win_pct_actual": float(actual.win_pct),
            "win_pct_expected": float(exp_win_pct),
            "expected_wins": float(expected_wins),
            "overperformance_wins": float(actual.wins - expected_wins),
        })
    out.sort(key=lambda d: d["overperformance_wins"], reverse=True)
    return out


# --------------------------------------------------------------------------- #
# Finding 3: League margin distribution
# --------------------------------------------------------------------------- #

def league_margin_distribution(league: pd.DataFrame) -> dict:
    reg = league[~league.is_playoff].copy()
    margins_abs = []
    for _, m in reg.iterrows():
        for sa, sb in (("set1_a","set1_b"),("set2_a","set2_b"),("set3_a","set3_b")):
            a, b = m[sa], m[sb]
            if pd.notna(a) and pd.notna(b):
                margins_abs.append(abs(int(a) - int(b)))
    s = pd.Series(margins_abs)
    q = s.quantile([0.25, 0.5, 0.75])
    # Where does Bean sit?
    bean_reg = league[((league.team_a_number == BEAN) | (league.team_b_number == BEAN))
                      & (~league.is_playoff)]
    bean_margins_abs = []
    for _, m in bean_reg.iterrows():
        for sa, sb in (("set1_a","set1_b"),("set2_a","set2_b"),("set3_a","set3_b")):
            a, b = m[sa], m[sb]
            if pd.notna(a) and pd.notna(b):
                bean_margins_abs.append(abs(int(a) - int(b)))
    bs = pd.Series(bean_margins_abs)
    bq = bs.quantile([0.25, 0.5, 0.75])
    return {
        "league_all_sets": {
            "n": int(len(s)),
            "min": int(s.min()), "q1": float(q.loc[0.25]),
            "median": float(q.loc[0.5]), "q3": float(q.loc[0.75]),
            "max": int(s.max()), "mean": float(s.mean()),
        },
        "bean_sets": {
            "n": int(len(bs)),
            "min": int(bs.min()), "q1": float(bq.loc[0.25]),
            "median": float(bq.loc[0.5]), "q3": float(bq.loc[0.75]),
            "max": int(bs.max()), "mean": float(bs.mean()),
        },
    }


# --------------------------------------------------------------------------- #
# Finding 4: Bean's per-opponent margin
# --------------------------------------------------------------------------- #

def bean_per_opponent(bean: pd.DataFrame, standings: pd.DataFrame) -> list[dict]:
    reg = bean[~bean.is_playoff].copy()
    name_lookup = dict(zip(standings.team_number, standings.team_name))
    win_pct_lookup = dict(zip(standings.team_number, standings.win_pct))
    rows = []
    for _, r in reg.iterrows():
        opp = int(r.team_b_number if r.team_a_number == BEAN else r.team_a_number)
        # Sum bean's per-set margin across this match (only counting measurable sets)
        total_margin = 0
        measurable = 0
        for n in (1, 2, 3):
            f, a = r[f"bean_points_set{n}_for"], r[f"bean_points_set{n}_against"]
            if pd.notna(f) and pd.notna(a):
                total_margin += int(f - a)
                measurable += 1
        rows.append({
            "date": r.date,
            "opponent_number": opp,
            "opponent_name": name_lookup[opp],
            "opponent_final_win_pct": float(win_pct_lookup[opp]),
            "bean_set_record": f"{int(r.sets_won_by_bean)}-{int(r.sets_lost_by_bean)}",
            "match_margin": int(total_margin),
            "measurable_sets": measurable,
            "bean_won_match": bool(r.bean_won),
        })
    rows.sort(key=lambda d: d["match_margin"], reverse=True)
    return rows


# --------------------------------------------------------------------------- #
# Finding 5: Silver vs Gold
# --------------------------------------------------------------------------- #

def silver_vs_gold(team_totals: pd.DataFrame, standings: pd.DataFrame) -> dict:
    merged = team_totals.merge(standings, on="team_number")
    merged["bracket"] = merged.team_number.apply(
        lambda t: "Gold" if t in GOLD_TEAMS else "Silver" if t in SILVER_TEAMS else "?"
    )
    out = {}
    for bracket in ("Gold", "Silver"):
        b = merged[merged.bracket == bracket]
        if len(b) == 0:
            continue
        out[bracket] = {
            "n_teams": int(len(b)),
            "avg_win_pct": float(b.win_pct.mean()),
            "avg_points_for_per_set": float((b.points_for / b.sets_played_parsed).mean()),
            "avg_points_against_per_set": float((b.points_against / b.sets_played_parsed).mean()),
            "avg_point_differential_per_set": float(
                ((b.points_for - b.points_against) / b.sets_played_parsed).mean()
            ),
            "teams": sorted(b.team_name.tolist()),
        }
    out["gap_in_win_pct"] = out["Gold"]["avg_win_pct"] - out["Silver"]["avg_win_pct"]
    return out


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def banner(title: str) -> None:
    print()
    print("=" * 78)
    print(title)
    print("=" * 78)


def main() -> None:
    league = pd.read_csv(LEAGUE_MATCHES_CSV)
    standings = pd.read_csv(STANDINGS_CSV)
    bean = pd.read_csv(BEAN_GAMES_CSV)

    banner("LAYER 2 — LEAGUE CONTEXT")
    print(f"Total league matches: {len(league)} ({(~league.is_playoff).sum()} regular, "
          f"{league.is_playoff.sum()} playoff)")
    print(f"Teams: {len(standings)}")

    team_totals = per_team_set_totals(league)

    # 1
    banner("FINDING 1 — Strength of schedule (Bean's 7 regular-season opponents)")
    sos = strength_of_schedule(bean, standings)
    print(f"  Average opponent final win %: {sos['average_opponent_win_pct']:.3f}")
    print()
    print(f"  {'date':<12}{'opponent':<26}{'opp record':<12}{'opp w%':>8}"
          f"{'bean sets':>11}  W/L")
    for m in sos["matches"]:
        print(f"  {m['date']:<12}{m['opponent_name'][:25]:<26}"
              f"{m['opponent_record']:<12}{m['opponent_win_pct']:>8.3f}"
              f"{m['bean_sets_won']:>5}-{m['bean_sets_lost']:<5}"
              f"  {'W' if m['bean_won_match'] else 'L'}")
    print(f"\n  vs strong (opp w%>.500): n={sos['vs_strong_opponents']['n']} matches, "
          f"sets {sos['vs_strong_opponents']['bean_set_wins']}-{sos['vs_strong_opponents']['bean_set_losses']}")
    print(f"  vs weak (opp w%<.500):   n={sos['vs_weak_opponents']['n']} matches, "
          f"sets {sos['vs_weak_opponents']['bean_set_wins']}-{sos['vs_weak_opponents']['bean_set_losses']}")
    print(f"  vs median (opp w%=.500): n={sos['vs_median_opponents']['n']} matches, "
          f"sets {sos['vs_median_opponents']['bean_set_wins']}-{sos['vs_median_opponents']['bean_set_losses']}")

    # 2
    banner(f"FINDING 2 — Pythagorean expectation (exponent k={PYTH_EXPONENT})")
    pyth = pythagorean(team_totals, standings)
    print(f"  {'team':<28}{'PF':>5}{'PA':>5}{'actW':>6}{'expW':>7}{'+/-':>7}")
    for p in pyth:
        print(f"  {p['team_name'][:27]:<28}{p['points_for']:>5}{p['points_against']:>5}"
              f"{p['actual_wins']:>6}{p['expected_wins']:>7.2f}"
              f"{p['overperformance_wins']:>+7.2f}")
    bean_pyth = next(p for p in pyth if p["team_number"] == BEAN)
    print(f"\n  BEAN MACHINE: actual {bean_pyth['actual_wins']} wins, "
          f"expected {bean_pyth['expected_wins']:.2f} -> "
          f"{bean_pyth['overperformance_wins']:+.2f} over expected")
    print(f"  Caveat: 01-21 G3 score wasn't recorded (commish-awarded win), so Bean's")
    print(f"  PF and PA both miss one set. Adds noise to the estimate.")

    # 3
    banner("FINDING 3 — League margin distribution (absolute |score gap| per set)")
    md = league_margin_distribution(league)
    L = md["league_all_sets"]
    B = md["bean_sets"]
    print(f"  All league sets (n={L['n']}): mean={L['mean']:.1f}, min={L['min']}, "
          f"q1={L['q1']:.1f}, median={L['median']:.1f}, q3={L['q3']:.1f}, max={L['max']}")
    print(f"  Bean's sets   (n={B['n']}): mean={B['mean']:.1f}, min={B['min']}, "
          f"q1={B['q1']:.1f}, median={B['median']:.1f}, q3={B['q3']:.1f}, max={B['max']}")
    if B["mean"] < L["mean"]:
        diff = L["mean"] - B["mean"]
        print(f"  -> Bean's sets were CLOSER than the league average by {diff:.1f} points")
    elif B["mean"] > L["mean"]:
        diff = B["mean"] - L["mean"]
        print(f"  -> Bean's sets had WIDER margins than the league average by {diff:.1f} points")

    # 4
    banner("FINDING 4 — Bean's match margins by opponent (sorted by margin)")
    pmo = bean_per_opponent(bean, standings)
    print(f"  {'date':<12}{'opponent':<26}{'opp w%':>8}{'sets':>7}{'margin':>9}")
    for r in pmo:
        print(f"  {r['date']:<12}{r['opponent_name'][:25]:<26}"
              f"{r['opponent_final_win_pct']:>8.3f}"
              f"{r['bean_set_record']:>7}"
              f"{r['match_margin']:>+9d}"
              f"  {'W' if r['bean_won_match'] else 'L'}")

    # 5
    banner("FINDING 5 — Silver vs Gold bracket comparison")
    svg = silver_vs_gold(team_totals, standings)
    for b in ("Gold", "Silver"):
        d = svg[b]
        print(f"  {b}  (n={d['n_teams']} teams):")
        print(f"    avg win %:           {d['avg_win_pct']:.3f}")
        print(f"    avg pts for/set:     {d['avg_points_for_per_set']:.2f}")
        print(f"    avg pts against/set: {d['avg_points_against_per_set']:.2f}")
        print(f"    avg net per set:     {d['avg_point_differential_per_set']:+.2f}")
        print(f"    teams: {', '.join(d['teams'])}")
    print(f"\n  Gap in avg win %: Gold {svg['Gold']['avg_win_pct']:.3f} vs "
          f"Silver {svg['Silver']['avg_win_pct']:.3f}  -> {svg['gap_in_win_pct']:+.3f}")

    payload = {
        "meta": {
            "league_matches_regular_season": int((~league.is_playoff).sum()),
            "league_matches_playoff": int(league.is_playoff.sum()),
            "pythagorean_exponent": PYTH_EXPONENT,
            "bracket_assignments": {
                "Gold": sorted(GOLD_TEAMS),
                "Silver": sorted(SILVER_TEAMS),
            },
        },
        "strength_of_schedule": sos,
        "pythagorean": pyth,
        "margin_distribution": md,
        "bean_per_opponent": pmo,
        "silver_vs_gold": svg,
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"\nWROTE {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
