"""
20_charts_league.py

League-context charts (Phase 3):
  1. pythagorean_luck:  actual vs Pythagorean-expected wins, all 15 teams
  2. silver_vs_gold:    per-team win% by bracket, Bean Machine highlighted

Reads data/processed/findings_layer2.json and data/processed/league_standings.csv.
Writes PNGs to charts/.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import chart_style as cs

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
BEAN = 11

GOLD_TEAMS = {4, 5, 6, 8, 9, 10, 12, 14}
SILVER_TEAMS = {1, 2, 3, 7, 11, 13, 15}


def load_layer2() -> dict:
    with open(PROCESSED / "findings_layer2.json") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #

def chart_pythagorean(layer2: dict) -> None:
    # Sort ascending so the luckiest team lands at the top of a horizontal bar.
    pyth = sorted(layer2["pythagorean"], key=lambda d: d["overperformance_wins"])
    names = [p["team_name"] for p in pyth]
    over = [p["overperformance_wins"] for p in pyth]

    colors = []
    for p in pyth:
        if p["team_number"] == BEAN:
            colors.append(cs.BEAN)
        elif p["overperformance_wins"] >= 0:
            colors.append(cs.NEUTRAL)
        else:
            colors.append(cs.BAD)

    fig, ax = plt.subplots(figsize=(9, 6.5))
    y = range(len(pyth))
    ax.barh(list(y), over, color=colors, edgecolor="white", height=0.72)
    ax.set_yticks(list(y))
    ax.set_yticklabels(names)
    ax.axvline(0, color="#999999", lw=1)

    # Value label at the end of each bar
    for i, p in enumerate(pyth):
        v = p["overperformance_wins"]
        ax.text(v + (0.12 if v >= 0 else -0.12), i, f"{v:+.1f}",
                va="center", ha="left" if v >= 0 else "right",
                fontsize=8.5, color=cs.INK)

    # Callouts for the three teams worth naming
    callouts = {
        "Volley these balls": "won every close one",
        "Tape Ticklers": "lost every close one",
        "Bean Machine": "exactly as expected",
    }
    for i, p in enumerate(pyth):
        if p["team_name"] in callouts:
            weight = "bold" if p["team_number"] == BEAN else "normal"
            ax.get_yticklabels()[i].set_fontweight("bold")

    ax.set_xlabel("Wins above / below Pythagorean expectation")
    ax.set_title("Luck in the standings: who the point differential says\n"
                 "should have won more, and who actually did")
    ax.set_xlim(-5.2, 5.2)
    # Legend via proxy patches
    import matplotlib.patches as mpatches
    handles = [
        mpatches.Patch(color=cs.NEUTRAL, label="Overperformed (lucky)"),
        mpatches.Patch(color=cs.BAD, label="Underperformed (unlucky)"),
        mpatches.Patch(color=cs.BEAN, label="Bean Machine"),
    ]
    ax.legend(handles=handles, loc="lower right")

    cs.save(fig, "pythagorean_luck",
            "Source: findings_layer2.json. Pythagorean expectation (exponent 2) "
            "vs actual wins, all 15 teams.")


def chart_silver_vs_gold(layer2: dict) -> None:
    standings = pd.read_csv(PROCESSED / "league_standings.csv")
    svg = layer2["silver_vs_gold"]

    fig, ax = plt.subplots(figsize=(7.5, 6))

    brackets = [("Gold", GOLD_TEAMS, 0), ("Silver", SILVER_TEAMS, 1)]
    for label, teamset, x in brackets:
        sub = standings[standings.team_number.isin(teamset)]
        # jittered dots for each team
        for offset, (_, row) in zip(
            _spread(len(sub)), sub.sort_values("win_pct").iterrows()
        ):
            is_bean = row.team_number == BEAN
            ax.scatter(
                x + offset, row.win_pct,
                s=190 if is_bean else 90,
                color=cs.BEAN if is_bean else cs.MUTED,
                edgecolor=cs.BEAN_DARK if is_bean else "#999999",
                linewidth=1.5 if is_bean else 0.8,
                zorder=3 if is_bean else 2,
            )
            if is_bean:
                ax.annotate("Bean Machine\n(.476, top of Silver)",
                            (x + offset, row.win_pct),
                            textcoords="offset points", xytext=(14, 0),
                            va="center", fontsize=9, fontweight="bold",
                            color=cs.BEAN_DARK)
        # bracket mean line
        mean = svg[label]["avg_win_pct"]
        ax.plot([x - 0.22, x + 0.22], [mean, mean],
                color=cs.INK, lw=2.2, zorder=4)
        ax.text(x, mean + 0.045, f"avg {mean:.0%}", ha="center",
                fontsize=9.5, fontweight="bold")

    ax.set_xticks([0, 1])
    ax.set_xticklabels(["Gold bracket\n(8 teams)", "Silver bracket\n(7 teams)"])
    ax.set_ylabel("Regular-season win %")
    ax.set_ylim(-0.05, 1.08)
    ax.set_xlim(-0.5, 1.6)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("The bracket tiers were earned\n"
                 "Bean Machine was the strongest team in Silver")
    cs.save(fig, "silver_vs_gold",
            "Source: league_standings.csv + findings_layer2.json. "
            "Each dot is one team; black bar is the bracket average.")


def _spread(n: int) -> list[float]:
    """Symmetric horizontal offsets so dots in a column don't fully overlap.
    Kept tight (max half-width ~0.21) so the two bracket columns stay distinct."""
    if n == 1:
        return [0.0]
    step = 0.06
    start = -step * (n - 1) / 2
    return [start + i * step for i in range(n)]


def main() -> None:
    cs.apply_style()
    layer2 = load_layer2()
    chart_pythagorean(layer2)
    chart_silver_vs_gold(layer2)
    print("WROTE charts/pythagorean_luck.png")
    print("WROTE charts/silver_vs_gold.png")


if __name__ == "__main__":
    main()
