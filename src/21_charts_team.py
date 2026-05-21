"""
21_charts_team.py

Team-internal charts (Phase 3):
  3. allen_story:      Allen's hit% across four contexts (the redemption arc)
  4. win_loss_factors: Cohen's d per metric, what separated wins from losses
  5. playoff_peak:     team hit% / digs / aces, regular season vs playoffs
  6. paradox_0107:     the 01-07 match: outscored the opponent, lost the match
  7. blowout_autopsy:  team hit% in the two worst losses vs season average

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

    labels = ["In Bean Machine\nlosses", "Season\noverall", "In Bean Machine\nwins",
              "In the\nplayoffs"]
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
                 "tracked the team, then peaked in the playoffs")
    cs.save(fig, "allen_story",
            "Source: findings_layer1.json (regular season, n=19 sets) + "
            "findings_playoff.json (n=6 playoff sets). Correlation, not causation.")


def chart_win_loss_factors(layer1: dict) -> None:
    """Cohen's d for each candidate metric, wins vs losses. Opponent points has
    the largest raw effect but is redundant and shown excluded; team hit %
    is the strongest valid signal."""
    wf = layer1["win_loss_factors"]
    metrics = wf["metrics"]
    # Sort by |d| so the magnitudes read top to bottom
    order = sorted(metrics.values(), key=lambda m: abs(m["cohens_d"]))

    fig, ax = plt.subplots(figsize=(9, 5))
    y = range(len(order))
    for i, m in enumerate(order):
        taut = m["redundant"]
        is_hit = (m["label"] == "team hit %")
        color = cs.MUTED if taut else (cs.BEAN if is_hit else cs.NEUTRAL)
        d = m["cohens_d"]
        ax.barh(i, d, color=color, edgecolor="white", height=0.66,
                hatch="//" if taut else None)
        # d value just past the bar tip
        ax.text(d + (0.07 if d >= 0 else -0.07), i, f"d = {d:+.2f}",
                va="center", ha="left" if d >= 0 else "right",
                fontsize=9.5, fontweight="bold")
        # the redundant bar gets an "excluded" tag inside it
        if taut:
            ax.text(d / 2, i, "excluded: redundant", va="center", ha="center",
                    fontsize=8.5, fontweight="bold", color="#444444",
                    bbox=dict(boxstyle="round,pad=0.3", facecolor="white",
                              edgecolor="none", alpha=0.9))

    ax.set_yticks(list(y))
    ax.set_yticklabels([m["label"] for m in order])
    ax.axvline(0, color="#999999", lw=1)
    ax.set_xlabel("Cohen's d  (wins vs losses, per set)")
    ax.set_xlim(-1.9, 1.9)
    ax.set_title("What separated our wins from losses\n"
                 "Only hitting efficiency is a strong, non-redundant signal")
    cs.save(fig, "win_loss_factors",
            "Source: findings_layer1.json, 19 regular-season sets (9 wins, 10 "
            "losses). Opponent points is excluded: losing a set means the "
            "opponent reached the cap by definition.")


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
            "Source: findings_playoff.json. Per-set averages, 20 regular-season "
            "games vs 6 playoff games. Small playoff sample; magnitudes are large.")


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
    ax.set_xticklabels(["Game 1\n(Bean Machine lost)", "Game 2\n(Bean Machine won)",
                        "Game 3\n(Bean Machine lost)"])
    ax.set_ylabel("Points scored")
    ax.set_ylim(0, 35)
    ax.legend(loc="upper right")
    ax.set_title("The 01-07 paradox: Bean Machine outscored the opponent\n"
                 "across the match, yet still lost it")

    bean_total, opp_total = int(sum(bean)), int(sum(opp))
    ax.text(0.5, 31.5,
            f"Match total:  Bean Machine {bean_total}, {opp_name} {opp_total}\n"
            f"Bean Machine +{bean_total - opp_total} on points, but lost the match 1 game to 2",
            ha="center", va="center", fontsize=9.5, fontweight="bold", color=cs.INK,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#f4f4f4",
                      edgecolor="#cccccc"))
    cs.save(fig, "paradox_0107",
            "Source: bean_machine_games.csv. 2026-01-07 vs Raw Butt Sets. "
            "Every game is scored independently for seeding in this league.")


def chart_blowout_autopsy(blowouts: dict) -> None:
    """Bean Machine's team hit% in each of the two worst losses vs the season
    average. A collapse would crash well below the line; neither loss did."""
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
            "Volley These Balls: normal, only 0.021 below.\n"
            "A genuine collapse would fall far below the line.",
            ha="center", va="center", fontsize=9,
            bbox=dict(boxstyle="round,pad=0.5", facecolor="#f4f4f4",
                      edgecolor="#cccccc"))
    ax.set_title("Bean Machine's two worst losses weren't collapses\n"
                 "Team hitting held its season form in both")
    cs.save(fig, "blowout_autopsy",
            "Source: findings_blowouts.json. Bean Machine's team hit % in each loss "
            "vs the season average. A genuine collapse would fall far below the line.")


def main() -> None:
    cs.apply_style()
    layer1 = load_json("findings_layer1.json")
    playoff = load_json("findings_playoff.json")
    blowouts = load_json("findings_blowouts.json")
    games = pd.read_csv(PROCESSED / "bean_machine_games.csv")

    chart_allen_story(layer1, playoff)
    chart_win_loss_factors(layer1)
    chart_playoff_peak(playoff)
    chart_paradox_0107(games)
    chart_blowout_autopsy(blowouts)
    for name in ("allen_story", "win_loss_factors", "playoff_peak",
                 "paradox_0107", "blowout_autopsy"):
        print(f"WROTE charts/{name}.png")


if __name__ == "__main__":
    main()
