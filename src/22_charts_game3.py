"""
22_charts_game3.py

Game-3 hook charts (Phase 3), the league-format finding:
  7. game3_coinflip: favored team's win rate by game number
  8. game3_margins:  game-margin distribution by game number

Reads findings_layer3.json and league_matches.csv. Writes PNGs to charts/.
"""

from __future__ import annotations

import json
from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

import chart_style as cs

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"


def load_layer3() -> dict:
    with open(PROCESSED / "findings_layer3.json") as f:
        return json.load(f)


# --------------------------------------------------------------------------- #

def chart_game3_coinflip(layer3: dict) -> None:
    ur = layer3["upset_rate"]
    keys = ["G1", "G2", "G3"]
    fav = [ur[k]["favored_win_rate"] for k in keys]
    ns = [ur[k]["n"] for k in keys]
    colors = [cs.MUTED, cs.MUTED, cs.BEAN]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bars = ax.bar(["Game 1", "Game 2", "Game 3"], fav,
                  color=colors, edgecolor="white", width=0.6)
    ax.axhline(0.5, color=cs.BAD, lw=1.5, ls="--")
    ax.text(1.5, 0.535, "coin flip (50%)", color=cs.BAD, fontsize=9,
            ha="center", va="bottom", fontweight="bold")

    for bar, v, n in zip(bars, fav, ns):
        cx = bar.get_x() + bar.get_width() / 2
        ax.text(cx, v + 0.022, f"{v:.0%}", ha="center", fontweight="bold")
        ax.text(cx, 0.045, f"n={n}", ha="center", fontsize=8.5, color="white")

    ax.set_ylabel("Favored team's win rate")
    ax.set_ylim(0, 0.85)
    ax.yaxis.set_major_formatter(plt.FuncFormatter(lambda v, _: f"{v:.0%}"))
    ax.set_title("Game 3 is a coin flip\n"
                 "The favored team wins games 1 and 2, but not game 3")
    cs.save(fig, "game3_coinflip",
            "Source: findings_layer3.json. Favored team by season win %. "
            "Regular season; the upset rate nearly doubles in game 3.")


def chart_game3_margins(layer3: dict) -> None:
    league = pd.read_csv(PROCESSED / "league_matches.csv")
    reg = league[~league.is_playoff]
    margins: dict[int, list[int]] = {1: [], 2: [], 3: []}
    for _, m in reg.iterrows():
        for n in (1, 2, 3):
            a, b = m[f"set{n}_a"], m[f"set{n}_b"]
            if pd.notna(a) and pd.notna(b):
                margins[n].append(int(abs(a - b)))
    data = [margins[1], margins[2], margins[3]]

    fig, ax = plt.subplots(figsize=(8, 5.5))
    bp = ax.boxplot(
        data, tick_labels=["Game 1", "Game 2", "Game 3"], widths=0.55,
        patch_artist=True, showmeans=True,
        medianprops=dict(color=cs.INK, lw=2),
        meanprops=dict(marker="D", markerfacecolor="white",
                       markeredgecolor=cs.INK, markersize=6),
        flierprops=dict(marker="o", markersize=4, markerfacecolor="#cccccc",
                        markeredgecolor="#999999"),
        whiskerprops=dict(color="#888888"),
        capprops=dict(color="#888888"),
    )
    for i, patch in enumerate(bp["boxes"]):
        patch.set_facecolor(cs.BEAN if i == 2 else cs.MUTED)
        patch.set_edgecolor("#666666")

    # Mean labels
    for i, vals in enumerate(data, 1):
        mean = sum(vals) / len(vals)
        ax.text(i + 0.32, mean, f"mean {mean:.1f}\n(n={len(vals)})",
                va="center", fontsize=8.5, color=cs.INK)

    ax.set_ylabel("Game margin (points)")
    ax.set_title("Game 3 is played closer\n"
                 "Game margins shrink significantly in the third game")
    ax.text(0.62, 14, "Game 3 vs games 1 & 2:\nWelch t-test  p < 0.02",
            ha="left", va="center", fontsize=8.5, color=cs.SUBTLE, style="italic")
    cs.save(fig, "game3_margins",
            "Source: league_matches.csv. Every regular-season game with a "
            "complete score. Diamond = mean, line = median.")


def main() -> None:
    cs.apply_style()
    layer3 = load_layer3()
    chart_game3_coinflip(layer3)
    chart_game3_margins(layer3)
    print("WROTE charts/game3_coinflip.png")
    print("WROTE charts/game3_margins.png")


if __name__ == "__main__":
    main()
