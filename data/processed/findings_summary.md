# Bean Machine 2025-26 — Phase 2 Findings Summary

_Generated 2026-05-21 by `13_synthesize.py` from the seven `findings_*.json` files._

This is the curated, ranked output of Phase 2. It feeds the Phase 4 README writeup. Each finding is scored 1-5 on **effect strength**, **sample size** (small samples score low — honest by design), and **narrative interest**.

## The convergence

Layer 2 says Bean Machine earned every bit of their 10-11 regular season: point differential predicted 10.1 wins and they won 10 (-0.05). Layer 1 explains how the sets were decided. The one factor that cleanly separated wins from losses was hitting efficiency: Bean hit +0.197 in sets they won versus +0.049 in sets they lost (Cohen's d = +0.98). And the playoffs show what a peak looked like: team hit percentage leapt from +0.121 to +0.217 as the lineup settled into fixed roles. If you ran the season back, the one variable to chase is hitting efficiency. It tracked the team's wins all year, and it surged when Bean won the bracket.

## Team context

Stat-derived roles for the seven-player roster:

- **Allen** — secondary hitter
- **Andy** — primary hitter
- **Cade** — secondary setter, secondary hitter, defensive anchor
- **Cole** — secondary hitter, defensive anchor
- **Jeremy** — primary hitter
- **Tae** — everyday starter
- **Zane** — primary setter, service leader

## Headline findings

The strongest material — likely to anchor the README.

### 1. Volley these balls was the league's luckiest team

*Layer 2 — Pythagorean expectation*  ·  effect 5/5 · sample 4/5 · interest 5/5 · **total 14/15**

Volley these balls went 11-0 but their point differential supported only 7.0 wins — an overperformance of +4.01 games. They won the close ones. At the other end, Tape Ticklers won 3 on a profile worth 7.1 (-4.12). The standings flattered some teams and buried others — but not Bean.

### 2. Bean Machine's record was exactly what they earned

*Layer 2 — Pythagorean expectation*  ·  effect 5/5 · sample 4/5 · interest 4/5 · **total 13/15**

Pythagorean expectation (from point differential) predicted 10.05 wins for Bean Machine. They actually won 10 — an overperformance of -0.05 games, the smallest gap of any team in the league. Bean's .476 season was neither lucky nor unlucky; it was precisely the record their play supported.

### 3. The Allen story: the player whose hitting mirrored the team

*Layer 1 + Playoff analysis*  ·  effect 4/5 · sample 3/5 · interest 5/5 · **total 12/15**

In the regular season Allen's attack hit +0.024 in Bean wins versus -0.189 in losses — a 21-point hit-percentage swing, the largest of any player. Then in the playoffs he flipped from a regular-season -0.102 to +0.200. The player whose efficiency most tracked the team's fortunes had his best volleyball when it mattered most. (Correlation, not causation — but a striking pattern.)

### 4. In this league, game 3 is a coin flip

*Layer 3 — game-3 hook*  ·  effect 4/5 · sample 3/5 · interest 5/5 · **total 12/15**

Across the league, the favored team (by record) won 72% of game 1 and 74% of game 2 — but only 53% of game 3. The upset rate nearly doubles in the third game (47% vs ~27%). Game-3 margins are also significantly tighter than games 1-2. In a league where every set is scored independently, the third game behaves like a different sport.

### 5. The 01-07 paradox: lost the match, won the points

*Layer 2 — league context*  ·  effect 3/5 · sample 5/5 · interest 4/5 · **total 12/15**

On 2026-01-07 Bean lost the match to Raw Butt Sets one set to two — 24-26, 26-15, 2-6 — yet outscored them by 5 points across the three sets. One blowout set win sandwiched between two narrow losses. It is the single cleanest illustration of why this league scores every set independently: match results and seeding can genuinely diverge.

## Supporting findings

Solid findings that add depth and context around the headlines.

### 1. Bean Machine peaked for the playoffs

*Playoff analysis*  ·  effect 4/5 · sample 2/5 · interest 5/5 · **total 11/15**

Bean's team hit percentage jumped from +0.121 in the regular season to +0.217 in the playoffs (+79.5%). Digs rose +26.1% and aces +50.0%. The sample is small (6 playoff sets) but the jump is unmistakable — Bean played their best volleyball of the season in the bracket they went on to win.

### 2. Game 3 is played closer than games 1 and 2

*Layer 3 — game-3 hook*  ·  effect 4/5 · sample 4/5 · interest 3/5 · **total 11/15**

Average set margin was 5.43 in game 1 and 6.11 in game 2, but only 3.58 in game 3 (Welch t-tests vs G3 both significant, p<0.02). Partly the shorter cap (to 15), partly that close matches are the ones that reach a third game — but the effect is real.

### 3. Hitting efficiency is what separated wins from losses

*Layer 1 (inside the team)*  ·  effect 4/5 · sample 3/5 · interest 3/5 · **total 10/15**

Splitting the regular-season sets into wins and losses, team hit percentage is the one metric with a large, non-redundant effect: +0.197 in sets Bean won versus +0.049 in sets they lost (Cohen's d = +0.98). Defense is harder to pin down honestly. Opponent points per set shows a larger raw split but is excluded as redundant (losing a set means the opponent reached the cap by definition). The non-redundant defense proxies, digs and blocks, barely move between wins and losses, and digs even runs the wrong way. The honest read: this self-tracked data measures the team's offense well and its defense poorly, and hitting was the clear separator.

### 4. Teams quietly opt out of the 'meaningless' game 3

*Layer 3 — game-3 hook*  ·  effect 3/5 · sample 3/5 · interest 4/5 · **total 10/15**

Although every set officially counts for seeding, behaviour says otherwise. When a match was still alive at 1-1, a third game was played 17 times. When the match was already decided 2-0, a third game was played only 2 times. Players treat game 3 as a decider, not as the independently-scored set the rules describe.

### 5. The Silver/Gold split was earned, and Bean topped Silver

*Layer 2 — league context*  ·  effect 4/5 · sample 4/5 · interest 2/5 · **total 10/15**

Gold-bracket teams averaged a 67.4% win rate; Silver-bracket teams 30.8%. The tiering reflected a real talent gap. Bean Machine (.476) was the strongest team in Silver — the #1 seed — which is why winning the Silver bracket is a genuine achievement, while honestly being the top of the league's lower half.

### 6. The championship lineup crystallized when Tae went down

*Playoff analysis*  ·  effect 3/5 · sample 2/5 · interest 4/5 · **total 9/15**

Tae (a middle, injured for the playoffs) had played M1/M2 in 16 of his 20 regular-season sets. In the playoffs Cole — a libero/outside hitter all year — moved to middle for every set, directly filling Tae's role. Zane became the sole setter (Cade stopped rotating through setter). Where the regular-season team flexed players across many positions, the playoff team gave every player exactly one job.

### 7. The playoff leap was a step change, not a slow build

*Season trends*  ·  effect 3/5 · sample 2/5 · interest 4/5 · **total 9/15**

Across the seven regular-season weeks Bean showed no significant upward trend — average set margin actually drifted slightly down (slope -0.15/week, p=0.85). Extrapolating that line to the playoff weeks predicted a margin of -1.5; the actual playoff margin was +6.0. Bean didn't gradually become a champion — something changed suddenly for the bracket.

### 8. Neither blowout loss was a Bean Machine collapse

*Blowout autopsy*  ·  effect 3/5 · sample 2/5 · interest 4/5 · **total 9/15**

Bean's two worst losses were both to elite teams. Against Sugar & Spike (01-21, lost by 16) Bean's team hit percentage was +0.163 — above their season +0.129. They played a good offensive game and were simply outscored. Against undefeated Volley These Balls (02-18, lost by 20) two of three sets were within that team's normal winning margin; one set collapsed. Bean lost to better teams — they did not fall apart.

## Context & open questions

Lower-confidence or descriptive items — useful color, flagged honestly as suggestive.

### 1. A coaching question: Cole's best spot may be libero

*Layer 1 — inside the team*  ·  effect 2/5 · sample 1/5 · interest 3/5 · **total 6/15**

When Cole played libero, Bean's average set margin was +2.0 (6 sets); at outside hitter (OH3) it was -0.3 (7 sets). The sample per position is tiny and confounded (he may have flexed into harder roles in harder matches), so this is a question to explore, not a conclusion.

## Methodology notes & honest caveats

- **Small samples throughout.** Layer 1 runs on 19 regular-season sets; the playoff findings on 6 sets; season trends on 7 weekly points. Every finding above carries its sample score for this reason. Treat single-digit-sample findings as suggestive.
- **Correlation is not causation.** The Allen story, the offense/defense split, and the stat correlations describe what *tracked* wins, not what *caused* them.
- **Pythagorean expectation** is well validated in basketball and baseball; less so for volleyball at the set level. Used here as a reasonable lens, not gospel.
- **Known data gaps** (documented in the Phase 1 validation report): 02-18 game 3 has no player stats; most playoff set scores were not recorded; 01-21 game 3 was played but its score is missing.
- The serve-receive correlations in Layer 1 were deliberately excluded as findings — they are structural artifacts of losing (you receive more serves when the opponent is scoring), not insights.
