"""
chart_style.py

Shared matplotlib styling for the Bean Machine charts (Phase 3). Importing
this module and calling apply_style() once gives every chart consistent
fonts, colors, and spacing. save() writes PNGs to charts/ at a fixed DPI.

Not a pipeline step (no leading number). It's a helper imported by the
20-/21-/22-chart scripts.
"""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent.parent
CHARTS_DIR = ROOT / "charts"

# --- Palette -------------------------------------------------------------- #
# Bean Machine is always the teal highlight; everyone/everything else is muted.
BEAN = "#2a9d8f"          # Bean Machine highlight
BEAN_DARK = "#1f7a6f"
MUTED = "#c4c4c4"         # other teams / neutral baseline
GOOD = "#2a9d8f"          # wins / positive
BAD = "#e76f51"           # losses / negative
NEUTRAL = "#8d99ae"       # secondary series
INK = "#222222"           # text
SUBTLE = "#888888"        # captions, source notes


def apply_style() -> None:
    """Apply the shared rcParams. Call once at the top of each chart script."""
    plt.rcParams.update({
        "figure.facecolor": "white",
        "figure.dpi": 110,
        "savefig.facecolor": "white",
        "axes.facecolor": "white",
        "axes.edgecolor": "#cccccc",
        "axes.linewidth": 0.8,
        "axes.grid": True,
        "axes.axisbelow": True,
        "axes.titlesize": 13,
        "axes.titleweight": "bold",
        "axes.titlepad": 10,
        "axes.labelsize": 10.5,
        "axes.labelcolor": INK,
        "axes.spines.top": False,
        "axes.spines.right": False,
        "grid.color": "#ededed",
        "grid.linewidth": 0.8,
        "xtick.color": INK,
        "ytick.color": INK,
        "xtick.labelsize": 9.5,
        "ytick.labelsize": 9.5,
        "font.family": "sans-serif",
        "font.size": 10.5,
        "text.color": INK,
        "legend.frameon": False,
        "legend.fontsize": 9.5,
    })


def save(fig, name: str, caption: str | None = None) -> Path:
    """Write a figure to charts/{name}.png. Optional small source caption."""
    CHARTS_DIR.mkdir(exist_ok=True)
    if caption:
        fig.text(0.5, -0.02, caption, ha="center", va="top",
                 fontsize=8, color=SUBTLE)
    out = CHARTS_DIR / f"{name}.png"
    fig.savefig(out, dpi=150, bbox_inches="tight")
    plt.close(fig)
    return out
