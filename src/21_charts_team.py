"""
21_charts_team.py

Team-internal charts (Phase 3):
  3. allen_story       — Allen's hit% across four contexts (the redemption arc)
  4. defense_vs_offense — opp points & team hit% in wins vs losses
  5. playoff_peak      — team hit% / digs / aces, regular season vs playoffs
  6. paradox_0107      — the 01-07 match: outscored the opponent, lost the match
  7. blowout_autopsy   — team hit% in the two worst losses vs season average

Reads findings_layer1.json, findings_playoff.json, findings_blowouts.json,
and bean_machine_games.csv. Writes PNGs to charts/.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import chart_style as cs

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"


def load_json(name: str) -> dict:
    with open(PROCESSED / name) as f:
        return json.load(f)


# --------------------------------------------------------------------------- #

def chart_allen_story(layer1: dict, playoff: dict) -> None:
    allen = layer1["allen_story"]
    allen_po = playoff["player_comparison"]["Allen"]

    labels = ["In Bean\nlosses", "Season\noverall", "In Bean\nwins", "In the\nplayoffs"]
    values = [
        allen["season_hit_pct_in_losses"],
        allen["season_hit_pct_all_sets"],
        allen["season_hit_pct_in_wins"],
        allen_po["playoffs"]["hit_pct"],
    ]
    colors = [cs.BAD if v < 0 else cs.GOOD for v in values]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bars = ax.bar(labels, values, color=colors, edgecolor="white", width=0.62)
    ax.axhline(0, color="#999999", lw=1)

    for bar, v in zip(bars, values):
        ax.text(bar.get_x() + bar.get_width() / 2,
                v + (0.012 if v >= 0 else -0.012),
                f"{v:+.3f}", ha="center",
                va="bottom" if v >= 0 else "top",
                fontsize=10, fontweight="bold")

    ax.set_ylabel("Allen's attack hit %")
    ax.set_ylim(-0.26, 0.27)
    ax.set_title("The Allen story: a hitter whose efficiency\n"
                 "tracked the team — and peaked in the playoffs")
    cs.save(fig, "allen_story",
            "Source: findings_layer1.json (regular season, n=19 sets) + "
            "findings_playoff.json (n=6 playoff sets). Correlation, not causation.")


def chart_defense_vs_offense(layer1: dict) -> None:
    od = layer1["offense_vs_defense"]
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 5.2))

    # Left: opponent points per set (defense)
    d_vals = [od["opp_points_in_wins"], od["opp_points_in_losses"]]
    ax1.bar(["Bean\nwins", "Bean\nlosses"], d_vals,
            color=[cs.GOOD, cs.BAD], edgecolor="white", width=0.55)
    for i, v in enumerate(d_vals):
        ax1.text(i, v + 0.4, f"{v:.1f}", ha="center", fontweight="bold")
    ax1.set_title(f"Defense — opponent points / set\n"
                  f"(Cohen's d = {od['opp_points_cohens_d']:+.2f})", fontsize=11)
    ax1.set_ylabel("Opponent points per set")
    ax1.set_ylim(0, 27)

    # Right: team hit % (offense)
    o_vals = [od["team_hit_pct_in_wins"], od["team_hit_pct_in_losses"]]
    ax2.bar(["Bean\nwins", "Bean\nlosses"], o_vals,
            color=[cs.GOOD, cs.BAD], edgecolor="white", width=0.55)
    for i, v in enumerate(o_vals):
        ax2.text(i, v + 0.008, f"{v:+.3f}", ha="center", fontweight="bold")
    ax2.set_title(f"Offense — team hit %\n"
                  f"(Cohen's d = {od['team_hit_pct_cohens_d']:+.2f})", fontsize=11)
    ax2.set_ylabel("Team hit %")
    ax2.set_ylim(0, 0.24)

    fig.suptitle("Both ends decided Bean's sets — defense by a nose",
                 fontsize=13, fontweight="bold", y=1.02)
    cs.save(fig, "defense_vs_offense",
            "Source: findings_layer1.json — regular season, 9 win sets / "
            "10 loss sets. A larger |d| means the cleaner wins-vs-losses split.")


def chart_playoff_peak(playoff: dict) -> None:
    cmp = playoff["team_aggregate_comparison"]
    specs = [
        ("team_hit_pct", "Team hit %", "{:+.3f}"),
        ("digs", "Digs per set", "{:.1f}"),
        ("aces", "Aces per set", "{:.2f}"),
    ]
    fig, axes = plt.subplots(1, 3, figsize=(11, 4.6))
    for ax, (key, label, fmt) in zip(axes, specs):
        d = cmp[key]
        vals = [d["regular_season_avg_per_set"], d["playoff_avg_per_set"]]
        bars = ax.bar(["Regular\nseason", "Playoffs"], vals,
                      color=[cs.MUTED, cs.BEAN], edgecolor="white", width=0.55)
        for bar, v in zip(bars, vals):
            ax.text(bar.get_x() + bar.get_width() / 2, v,
                    fmt.format(v), ha="center", va="bottom", fontweight="bold")
        delta = d["delta_pct"]
        ax.set_title(f"{label}\n({delta:+.0%} in playoffs)", fontsize=11)
        ax.set_ylim(0, max(vals) * 1.25)

    fig.suptitle("Bean Machine peaked for the playoff run",
                 fontsize=13, fontweight="bold", y=1.04)
    cs.save(fig, "playoff_peak",
            "Source: findings_playoff.json — per-set averages, 20 regular-season "
            "sets vs 6 playoff sets. Small playoff sample; magnitudes are large.")


def chart_paradox_0107(games: pd.DataFrame) -> None:
    m = games[games.date == "2026-01-07"].iloc[0]
    bean = [m["bean_points_set1_for"], m["bean_points_set2_for"], m["bean_points_set3_for"]]
    opp = [m["bean_points_set1_against"], m["bean_points_set2_against"],
           m["bean_points_set3_against"]]
    opp_name = m["team_a_name"] if m["team_a_number"] != 11 else m["team_b_name"]

    fig, ax = plt.subplots(figsize=(8.5, 5.5))
    x = range(3)
    w = 0.38
    b1 = ax.bar([i - w / 2 for i in x], bean, w, label="Bean Machine",
                color=cs.BEAN, edgecolor="white")
    b2 = ax.bar([i + w / 2 for i in x], opp, w, label=opp_name,
                color=cs.MUTED, edgecolor="white")
    for bars in (b1, b2):
        for bar in bars:
            ax.text(bar.get_x() + bar.get_width() / 2, bar.get_height() + 0.4,
                    f"{int(bar.get_height())}", ha="center", fontweight="bold",
                    fontsize=10)

    ax.set_xticks(list(x))
    ax.set_xticklabels(["Game 1\n(Bean lost)", "Game 2\n(Bean won)",
                        "Game 3\n(Bean lost)"])
    ax.set_ylabel("Points scored")
    ax.set_ylim(0, 35)
    ax.legend(loc="upper right")
    ax.set_title("The 01-07 paradox: Bean outscored the opponent\n"
                 "across the match — and still lost it")

    bean_total, opp_total = int(sum(bean)), int(sum(opp))
    ax.text(0.5, 31.5,
            f"Match total:  Bean Machine {bean_total}  —  {opp_name} {opp_total}\n"
            f"Bean +{bean_total - opp_total} on points — but lost the match, 1 set to 2",
            ha="center", va="center", fontsize=9.5, fontweight="bold", color=cs.INK,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#f4f4f4",
                      edgecolor="#cccccc"))
    cs.save(fig, "paradox_0107",
            "Source: bean_machine_games.csv — 2026-01-07 vs Raw Butt Sets. "
            "Every set is scored independently for seeding in this league.")


def chart_blowout_autopsy(blowouts: dict) -> None:
    """Bean's team hit% in each of the two worst losses vs the season average.
    A collapse would crash well below the line — neither loss did."""
    bl = {b["date"]: b for b in blowouts["blowouts"]}
    ss = bl["2026-01-21"]   # Sugar & Spike, lost by 16
    vtb = bl["2026-02-18"]  # Volley These Balls, lost by 20
    season = ss["team_hit_pct_season"]

    rows = [
        ("Sugar & Spike\n(lost by 16)", ss["team_hit_pct_match"], cs.BEAN),
        ("Volley These Balls\n(lost by 20)", vtb["team_hit_pct_match"], cs.NEUTRAL),
    ]
    fig, ax = plt.subplots(figsize=(8, 5.5))
    labels = [r[0] for r in rows]
    vals = [r[1] for r in rows]
    colors = [r[2] for r in rows]
    bars = ax.bar(labels, vals, color=colors, edgecolor="white", width=0.5)

    ax.axhline(season, color=cs.INK, lw=1.5, ls="--")
    ax.text(-0.46, season + 0.004, f"season average  ({season:+.3f})",
            ha="left", va="bottom", fontsize=9, fontweight="bold")

    for bar, v in zip(bars, vals):
        ax.text(bar.get_x() + bar.get_width() / 2, v + 0.006, f"{v:+.3f}",
                ha="center", va="bottom", fontsize=12, fontweight="bold")

    ax.set_ylabel("Bean Machine team hit %")
    ax.set_ylim(0, 0.23)
    ax.text(0.5, 0.205,
            "Sugar & Spike: hitting ABOVE the season average.\n"
            "Volley These Balls: normal — only 0.021 below.\n"
            "A genuine collapse would fall far below the line.",
            ha="center", va="center", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#f4f4f4",
                      edgecolor="#cccccc"))
    ax.set_title("Bean's two worst losses weren't collapses\n"
                 "Team hitting held its season form in both")
    cs.save(fig, "blowout_autopsy",
            "Source: findings_blowouts.json — Bean's team hit % in each loss "
            "vs the season average. A genuine collapse would fall far below the line.")


def main() -> None:
    cs.apply_style()
    layer1 = load_json("findings_layer1.json")
    playoff = load_json("findings_playoff.json")
    blowouts = load_json("findings_blowouts.json")
    games = pd.read_csv(PROCESSED / "bean_machine_games.csv")

    chart_allen_story(layer1, playoff)
    chart_defense_vs_offense(layer1)
    chart_playoff_peak(playoff)
    chart_paradox_0107(games)
    chart_blowout_autopsy(blowouts)
    for name in ("allen_story", "defense_vs_offense", "playoff_peak",
                 "paradox_0107", "blowout_autopsy"):
        print(f"WROTE charts/{name}.png")


if __name__ == "__main__":
    main()
