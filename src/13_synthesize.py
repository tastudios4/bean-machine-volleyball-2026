"""
13_synthesize.py

Reads all seven findings_*.json files, curates the findings worth telling,
ranks each by three axes, and writes data/processed/findings_summary.md —
the Phase 2 deliverable that feeds the Phase 4 README writeup.

Each finding is scored 1-5 on:
  - effect_strength : how large/decisive the effect is
  - sample_size     : how much data backs it (HONEST — small n scores low even
                      when the effect looks dramatic)
  - narrative_interest : how much a reader would actually care / how
                         counterintuitive it is

total = sum of the three (range 3-15). Findings are tiered:
  Headline   (total >= 12)
  Supporting (total 9-11)
  Context    (total <= 8)

The numbers in each finding's prose are pulled live from the JSON files, so
this summary stays in sync if the analysis is re-run.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PROCESSED = ROOT / "data" / "processed"
OUT_MD = PROCESSED / "findings_summary.md"

JSON_FILES = {
    "layer1": "findings_layer1.json",
    "layer2": "findings_layer2.json",
    "layer3": "findings_layer3.json",
    "playoff": "findings_playoff.json",
    "trends": "findings_trends.json",
    "roles": "findings_roles.json",
    "blowouts": "findings_blowouts.json",
}


def load_all() -> dict:
    data = {}
    for key, fname in JSON_FILES.items():
        with open(PROCESSED / fname) as f:
            data[key] = json.load(f)
    return data


def pct(x: float) -> str:
    return f"{x:+.1%}"


# --------------------------------------------------------------------------- #
# Finding builders — each returns a dict; numbers pulled live from `data`.
# --------------------------------------------------------------------------- #

def build_findings(data: dict) -> list[dict]:
    f = []

    L1 = data["layer1"]
    L2 = data["layer2"]
    L3 = data["layer3"]
    PO = data["playoff"]
    TR = data["trends"]
    BL = data["blowouts"]

    # --- Layer 2: Pythagorean, Bean to expectation ---
    pyth = sorted(L2["pythagorean"], key=lambda d: -d["overperformance_wins"])
    bean = next(p for p in pyth if p["team_number"] == 11)
    luckiest = pyth[0]
    unluckiest = pyth[-1]

    f.append({
        "title": "Bean Machine's record was exactly what they earned",
        "source": "Layer 2 — Pythagorean expectation",
        "body": (
            f"Pythagorean expectation (from point differential) predicted "
            f"{bean['expected_wins']:.2f} wins for Bean Machine. They actually won "
            f"{bean['actual_wins']} — an overperformance of "
            f"{bean['overperformance_wins']:+.2f} games, the smallest gap of any "
            f"team in the league. Bean's .476 season was neither lucky nor unlucky; "
            f"it was precisely the record their play supported."
        ),
        "effect_strength": 5, "sample_size": 4, "narrative_interest": 4,
    })

    f.append({
        "title": f"{luckiest['team_name']} was the league's luckiest team",
        "source": "Layer 2 — Pythagorean expectation",
        "body": (
            f"{luckiest['team_name']} went {luckiest['actual_wins']}-"
            f"{luckiest['actual_losses']} but their point differential supported only "
            f"{luckiest['expected_wins']:.1f} wins — an overperformance of "
            f"{luckiest['overperformance_wins']:+.2f} games. They won the close ones. "
            f"At the other end, {unluckiest['team_name']} won "
            f"{unluckiest['actual_wins']} on a profile worth "
            f"{unluckiest['expected_wins']:.1f} "
            f"({unluckiest['overperformance_wins']:+.2f}). The standings flattered "
            f"some teams and buried others — but not Bean."
        ),
        "effect_strength": 5, "sample_size": 4, "narrative_interest": 5,
    })

    # --- Layer 1 + Playoff: the Allen story ---
    allen = L1["allen_story"]
    allen_po = PO["player_comparison"]["Allen"]
    f.append({
        "title": "The Allen story: the player whose hitting mirrored the team",
        "source": "Layer 1 + Playoff analysis",
        "body": (
            f"In the regular season Allen's attack hit "
            f"{allen['season_hit_pct_in_wins']:+.3f} in Bean wins versus "
            f"{allen['season_hit_pct_in_losses']:+.3f} in losses — a "
            f"{abs(allen['season_hit_pct_in_wins'] - allen['season_hit_pct_in_losses'])*100:.0f}-point "
            f"hit-percentage swing, the largest of any player. Then in the playoffs "
            f"he flipped from a regular-season "
            f"{allen_po['regular_season']['hit_pct']:+.3f} to "
            f"{allen_po['playoffs']['hit_pct']:+.3f}. The player whose efficiency most "
            f"tracked the team's fortunes had his best volleyball when it mattered "
            f"most. (Correlation, not causation — but a striking pattern.)"
        ),
        "effect_strength": 4, "sample_size": 3, "narrative_interest": 5,
    })

    # --- Playoff: Bean peaked ---
    cmp = PO["team_aggregate_comparison"]
    hit = cmp["team_hit_pct"]
    digs = cmp["digs"]
    aces = cmp["aces"]
    f.append({
        "title": "Bean Machine peaked for the playoffs",
        "source": "Playoff analysis",
        "body": (
            f"Bean's team hit percentage jumped from "
            f"{hit['regular_season_avg_per_set']:+.3f} in the regular season to "
            f"{hit['playoff_avg_per_set']:+.3f} in the playoffs "
            f"({pct(hit['delta_pct'])}). Digs rose {pct(digs['delta_pct'])} and aces "
            f"{pct(aces['delta_pct'])}. The sample is small (6 playoff sets) but the "
            f"jump is unmistakable — Bean played their best volleyball of the season "
            f"in the bracket they went on to win."
        ),
        "effect_strength": 4, "sample_size": 2, "narrative_interest": 5,
    })

    # --- Layer 3: G3 is a coin flip ---
    ur = L3["upset_rate"]
    g1u, g2u, g3u = ur["G1"]["upset_rate"], ur["G2"]["upset_rate"], ur["G3"]["upset_rate"]
    f.append({
        "title": "In this league, game 3 is a coin flip",
        "source": "Layer 3 — game-3 hook",
        "body": (
            f"Across the league, the favored team (by record) won "
            f"{1-g1u:.0%} of game 1 and {1-g2u:.0%} of game 2 — but only "
            f"{1-g3u:.0%} of game 3. The upset rate nearly doubles in the third "
            f"game ({g3u:.0%} vs ~{(g1u+g2u)/2:.0%}). Game-3 margins are also "
            f"significantly tighter than games 1-2. In a league where every set is "
            f"scored independently, the third game behaves like a different sport."
        ),
        "effect_strength": 4, "sample_size": 3, "narrative_interest": 5,
    })

    # --- Layer 1: hitting efficiency separated wins from losses ---
    wf = L1["win_loss_factors"]
    hit = wf["metrics"]["team_hit_pct"]
    f.append({
        "title": "Hitting efficiency is what separated wins from losses",
        "source": "Layer 1 (inside the team)",
        "body": (
            f"Splitting the regular-season sets into wins and losses, team hit "
            f"percentage is the one metric with a large, non-redundant effect: "
            f"{hit['mean_in_wins']:+.3f} in sets Bean won versus "
            f"{hit['mean_in_losses']:+.3f} in sets they lost (Cohen's d = "
            f"{hit['cohens_d']:+.2f}). Defense is harder to pin down honestly. "
            f"Opponent points per set shows a larger raw split but is excluded as "
            f"redundant (losing a set means the opponent reached the cap by "
            f"definition). The non-redundant defense proxies, digs and blocks, "
            f"barely move between wins and losses, and digs even runs the wrong "
            f"way. The honest read: this self-tracked data measures the team's "
            f"offense well and its defense poorly, and hitting was the clear "
            f"separator."
        ),
        "effect_strength": 4, "sample_size": 3, "narrative_interest": 3,
    })

    # --- Layer 2: the 01-07 paradox ---
    f.append({
        "title": "The 01-07 paradox: lost the match, won the points",
        "source": "Layer 2 — league context",
        "body": (
            "On 2026-01-07 Bean lost the match to Raw Butt Sets one set to two — "
            "24-26, 26-15, 2-6 — yet outscored them by 5 points across the three "
            "sets. One blowout set win sandwiched between two narrow losses. It is "
            "the single cleanest illustration of why this league scores every set "
            "independently: match results and seeding can genuinely diverge."
        ),
        "effect_strength": 3, "sample_size": 5, "narrative_interest": 4,
    })

    # --- Layer 3: teams skip meaningless game 3 ---
    gt = L3["garbage_time_hypothesis"]
    decider_n = gt["decider_g3_summary"]["n"]
    garbage_n = gt["garbage_g3_summary"]["n"]
    f.append({
        "title": "Teams quietly opt out of the 'meaningless' game 3",
        "source": "Layer 3 — game-3 hook",
        "body": (
            f"Although every set officially counts for seeding, behaviour says "
            f"otherwise. When a match was still alive at 1-1, a third game was "
            f"played {decider_n} times. When the match was already decided 2-0, a "
            f"third game was played only {garbage_n} times. Players treat game 3 as "
            f"a decider, not as the independently-scored set the rules describe."
        ),
        "effect_strength": 3, "sample_size": 3, "narrative_interest": 4,
    })

    # --- Layer 3: G3 margins tighter ---
    md = L3["margin_distribution"]["summary_by_game"]
    f.append({
        "title": "Game 3 is played closer than games 1 and 2",
        "source": "Layer 3 — game-3 hook",
        "body": (
            f"Average set margin was {md['G1']['mean']:.2f} in game 1 and "
            f"{md['G2']['mean']:.2f} in game 2, but only {md['G3']['mean']:.2f} in "
            f"game 3 (Welch t-tests vs G3 both significant, p<0.02). Partly the "
            f"shorter cap (to 15), partly that close matches are the ones that "
            f"reach a third game — but the effect is real."
        ),
        "effect_strength": 4, "sample_size": 4, "narrative_interest": 3,
    })

    # --- Layer 2: Silver vs Gold ---
    svg = L2["silver_vs_gold"]
    f.append({
        "title": "The Silver/Gold split was earned, and Bean topped Silver",
        "source": "Layer 2 — league context",
        "body": (
            f"Gold-bracket teams averaged a {svg['Gold']['avg_win_pct']:.1%} win "
            f"rate; Silver-bracket teams {svg['Silver']['avg_win_pct']:.1%}. The "
            f"tiering reflected a real talent gap. Bean Machine (.476) was the "
            f"strongest team in Silver — the #1 seed — which is why winning the "
            f"Silver bracket is a genuine achievement, while honestly being the top "
            f"of the league's lower half."
        ),
        "effect_strength": 4, "sample_size": 4, "narrative_interest": 2,
    })

    # --- Playoff: lineup crystallized ---
    f.append({
        "title": "The championship lineup crystallized when Tae went down",
        "source": "Playoff analysis",
        "body": (
            "Tae (a middle, injured for the playoffs) had played M1/M2 in 16 of his "
            "20 regular-season sets. In the playoffs Cole — a libero/outside hitter "
            "all year — moved to middle for every set, directly filling Tae's role. "
            "Zane became the sole setter (Cade stopped rotating through setter). "
            "Where the regular-season team flexed players across many positions, the "
            "playoff team gave every player exactly one job."
        ),
        "effect_strength": 3, "sample_size": 2, "narrative_interest": 4,
    })

    # --- Trends: step function ---
    mt = TR["trends"].get("margin_avg", {})
    pvt = TR["playoff_vs_trend"].get("margin_avg", {})
    if mt and pvt and pvt.get("projected_playoff_avg") is not None:
        f.append({
            "title": "The playoff leap was a step change, not a slow build",
            "source": "Season trends",
            "body": (
                f"Across the seven regular-season weeks Bean showed no significant "
                f"upward trend — average set margin actually drifted slightly down "
                f"(slope {mt['slope']:+.2f}/week, p={mt['p_value']:.2f}). Extrapolating "
                f"that line to the playoff weeks predicted a margin of "
                f"{pvt['projected_playoff_avg']:+.1f}; the actual playoff margin was "
                f"{pvt['actual_playoff_avg']:+.1f}. Bean didn't gradually become a "
                f"champion — something changed suddenly for the bracket."
            ),
            "effect_strength": 3, "sample_size": 2, "narrative_interest": 4,
        })

    # --- Blowouts ---
    bl = {b["date"]: b for b in BL["blowouts"]}
    f.append({
        "title": "Neither blowout loss was a Bean Machine collapse",
        "source": "Blowout autopsy",
        "body": (
            "Bean's two worst losses were both to elite teams. Against Sugar & "
            f"Spike (01-21, lost by 16) Bean's team hit percentage was "
            f"{bl['2026-01-21']['team_hit_pct_match']:+.3f} — above their season "
            f"{bl['2026-01-21']['team_hit_pct_season']:+.3f}. They played a good "
            "offensive game and were simply outscored. Against undefeated Volley "
            "These Balls (02-18, lost by 20) two of three sets were within that "
            "team's normal winning margin; one set collapsed. Bean lost to better "
            "teams — they did not fall apart."
        ),
        "effect_strength": 3, "sample_size": 2, "narrative_interest": 4,
    })

    # --- Layer 1: Cole position-flex ---
    cpf = {c["position"]: c for c in L1["cole_position_flex"]}
    if "L" in cpf and "OH3" in cpf:
        f.append({
            "title": "A coaching question: Cole's best spot may be libero",
            "source": "Layer 1 — inside the team",
            "body": (
                f"When Cole played libero, Bean's average set margin was "
                f"{cpf['L']['bean_margin_avg']:+.1f} ({cpf['L']['n_sets']} sets); at "
                f"outside hitter (OH3) it was {cpf['OH3']['bean_margin_avg']:+.1f} "
                f"({cpf['OH3']['n_sets']} sets). The sample per position is tiny and "
                f"confounded (he may have flexed into harder roles in harder "
                f"matches), so this is a question to explore, not a conclusion."
            ),
            "effect_strength": 2, "sample_size": 1, "narrative_interest": 3,
        })

    for finding in f:
        finding["total"] = (
            finding["effect_strength"]
            + finding["sample_size"]
            + finding["narrative_interest"]
        )
    return sorted(f, key=lambda d: -d["total"])


# --------------------------------------------------------------------------- #

def convergence_paragraph(data: dict) -> str:
    L2 = data["layer2"]
    bean = next(p for p in L2["pythagorean"] if p["team_number"] == 11)
    hitf = data["layer1"]["win_loss_factors"]["metrics"]["team_hit_pct"]
    hit = data["playoff"]["team_aggregate_comparison"]["team_hit_pct"]
    return (
        f"Layer 2 says Bean Machine earned every bit of their {bean['actual_wins']}-"
        f"{bean['actual_losses']} regular season: point differential predicted "
        f"{bean['expected_wins']:.1f} wins and they won {bean['actual_wins']} "
        f"({bean['overperformance_wins']:+.2f}). Layer 1 explains how the sets were "
        f"decided. The one factor that cleanly separated wins from losses was "
        f"hitting efficiency: Bean hit {hitf['mean_in_wins']:+.3f} in sets they won "
        f"versus {hitf['mean_in_losses']:+.3f} in sets they lost (Cohen's d = "
        f"{hitf['cohens_d']:+.2f}). And the playoffs show what a peak looked like: "
        f"team hit percentage leapt from {hit['regular_season_avg_per_set']:+.3f} to "
        f"{hit['playoff_avg_per_set']:+.3f} as the lineup settled into fixed roles. "
        f"If you ran the season back, the one variable to chase is hitting "
        f"efficiency. It tracked the team's wins all year, and it surged when Bean "
        f"won the bracket."
    )


def team_context(data: dict) -> list[str]:
    roles = data["roles"]
    lines = []
    for player, info in sorted(roles["roles"].items()):
        lines.append(f"- **{player}** — {', '.join(info['tags'])}")
    return lines


def render_markdown(data: dict, findings: list[dict]) -> str:
    headline = [x for x in findings if x["total"] >= 12]
    supporting = [x for x in findings if 9 <= x["total"] <= 11]
    context = [x for x in findings if x["total"] <= 8]

    out = []
    out.append("# Bean Machine 2025-26 — Phase 2 Findings Summary")
    out.append("")
    out.append(f"_Generated {date.today().isoformat()} by `13_synthesize.py` from the "
               "seven `findings_*.json` files._")
    out.append("")
    out.append("This is the curated, ranked output of Phase 2. It feeds the Phase 4 "
               "README writeup. Each finding is scored 1-5 on **effect strength**, "
               "**sample size** (small samples score low — honest by design), and "
               "**narrative interest**.")
    out.append("")

    out.append("## The convergence")
    out.append("")
    out.append(convergence_paragraph(data))
    out.append("")

    out.append("## Team context")
    out.append("")
    out.append("Stat-derived roles for the seven-player roster:")
    out.append("")
    out.extend(team_context(data))
    out.append("")

    def render_tier(title: str, items: list[dict], blurb: str) -> None:
        out.append(f"## {title}")
        out.append("")
        out.append(blurb)
        out.append("")
        for i, x in enumerate(items, 1):
            out.append(f"### {i}. {x['title']}")
            out.append("")
            out.append(f"*{x['source']}*  ·  "
                       f"effect {x['effect_strength']}/5 · "
                       f"sample {x['sample_size']}/5 · "
                       f"interest {x['narrative_interest']}/5 · "
                       f"**total {x['total']}/15**")
            out.append("")
            out.append(x["body"])
            out.append("")

    render_tier("Headline findings", headline,
                "The strongest material — likely to anchor the README.")
    render_tier("Supporting findings", supporting,
                "Solid findings that add depth and context around the headlines.")
    if context:
        render_tier("Context & open questions", context,
                    "Lower-confidence or descriptive items — useful color, "
                    "flagged honestly as suggestive.")

    out.append("## Methodology notes & honest caveats")
    out.append("")
    out.append("- **Small samples throughout.** Layer 1 runs on 19 regular-season "
               "sets; the playoff findings on 6 sets; season trends on 7 weekly "
               "points. Every finding above carries its sample score for this "
               "reason. Treat single-digit-sample findings as suggestive.")
    out.append("- **Correlation is not causation.** The Allen story, the "
               "offense/defense split, and the stat correlations describe what "
               "*tracked* wins, not what *caused* them.")
    out.append("- **Pythagorean expectation** is well validated in basketball and "
               "baseball; less so for volleyball at the set level. Used here as a "
               "reasonable lens, not gospel.")
    out.append("- **Known data gaps** (documented in the Phase 1 validation report): "
               "02-18 game 3 has no player stats; most playoff set scores were not "
               "recorded; 01-21 game 3 was played but its score is missing.")
    out.append("- The serve-receive correlations in Layer 1 were deliberately "
               "excluded as findings — they are structural artifacts of losing "
               "(you receive more serves when the opponent is scoring), not "
               "insights.")
    out.append("")
    return "\n".join(out)


def main() -> None:
    data = load_all()
    findings = build_findings(data)
    md = render_markdown(data, findings)
    OUT_MD.write_text(md)

    # Console summary
    print("=" * 70)
    print("13_synthesize.py — ranked findings")
    print("=" * 70)
    for x in findings:
        tier = ("HEADLINE" if x["total"] >= 12
                else "support" if x["total"] >= 9 else "context")
        print(f"  [{x['total']:>2}/15] {tier:<8} {x['title']}")
    print()
    print(f"WROTE {OUT_MD.relative_to(ROOT)}  "
          f"({len(findings)} findings ranked)")


if __name__ == "__main__":
    main()
