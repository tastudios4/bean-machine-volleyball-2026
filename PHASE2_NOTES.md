# Phase 2 — Analysis Progress

> This file captures Phase 2 state so any Claude session can re-acquire context
> by reading this file alone. Updated 2026-05-20.

## Status

| Layer / script | What | Status | Output |
|---|---|---|---|
| 1 — `10_layer1_team_analysis.py` | Inside the team (why we won/lost at set level) | **DONE** | `findings_layer1.json` |
| 2 — `11_layer2_league_analysis.py` | League context (Pythagorean, SoS, Silver vs Gold) | **DONE** | `findings_layer2.json` |
| 3 — `12_game3_analysis.py` | Game-3 hook (does game 3 matter differently?) | **DONE** | `findings_layer3.json` |
| `14_playoff_analysis.py` | Championship run; who covered Tae | **DONE** | `findings_playoff.json` |
| `15_season_trends.py` | Did Bean improve over the season? | **DONE** | `findings_trends.json` |
| `16_player_roles.py` | Stat-driven role identification | **DONE** | `findings_roles.json` |
| `17_blowout_analysis.py` | Autopsy of the two worst losses | **DONE** | `findings_blowouts.json` |
| `13_synthesize.py` | Combine all findings, rank, write summary | **DONE** | `findings_summary.md` |

## Decisions made during scoping (LOCKED IN, don't re-decide)

- **Unit of analysis**: set-level (each game/set as the row). Match-level is infeasible at n=9.
- **Scope for Layer 1**: regular season only. Playoffs excluded — different format (21-21-15 vs 25-25-15) and only 1 of 6 playoff sets has both a complete score and player stats.
- **Sample size for Layer 1**: n=19 sets after exclusions (9 Bean wins, 10 Bean losses). At n=19, |r| ≥ 0.482 ≈ p<0.05.
- **Dropped**: the "Tae story" sub-narrative (no mid-season before/after — he played all regular season, missed all playoffs).
- **Kept**: the Allen story and the Cole position-flex.
- **Bracket assignments** (from `league_raw.xlsx` rows 67–95):
  - Gold (8 teams): 4 Volley these balls, 5 Spikachu, 6 DNJJ, 8 Sugar & Spike, 9 Emerald City, 10 Pineapple, 12 Raw Butt Sets, 14 Modelo
  - Silver (7 teams): 1 Tape Ticklers, 2 Sets Up, 3 Casual Sets, 7 Blue Dynasty, 11 Bean Machine, 13 Student Divers, 15 Block You-ah

## Phase 1 bug found & fixed during Phase 2 (2026-05-20)

- **Bug**: `league_matches.csv` `match_id` was `{date}_C{court}_M{week}`. Each court hosts 2 matches/week (8:10 and 9:10 slots), so every regular-season match_id collided — 56 matches shared only 28 ids.
- **Fix**: `match_id` is now `{date}_C{court}_M{slot}` where M1 = 8:10 match, M2 = 9:10 match (restores the original intended meaning of M). Playoff ids keep `_M{bracket-round}` and were always unique.
- **Blast radius**: only `17_blowout_analysis.py` was actually corrupted (it did `.iloc[0]` on a non-unique key). Layers 1/2/3, playoff, trends, roles were unaffected — they only ever join on Bean's match_ids, which are date-unique (Bean plays once/week). Layer 2 doesn't use match_id at all.
- **Defensive fix**: `05_join_and_validate.py` now has a section 0 that checks match_id uniqueness in `league_matches.csv`.

## Layer 1 — Key findings (regular season, n=19)

- **Two real stat correlations with set wins**: `team_hit_pct` (+0.50, p=.028) and `errors` (−0.49, p=.033). The strong negatives on `sr_attempts`/`sr_3` are structural artifacts (you receive more serves when you're losing), NOT insights.
- **Offense vs defense — defense edges it**: opp points/set Cohen's d = −1.15; team hit% d = +0.98. Both huge; defense slightly more decisive. In wins Bean held opponents to 15.1/set, in losses 23.2.
- **Threshold patterns**: none clean at n=19.
- **The Allen story**: hit% +0.024 in wins vs −0.189 in losses — a 21-point swing, biggest of any player. Correlation, not causation.
- **Cole position-flex** (suggestive only, tiny n/position): Bean's best avg margin came with Cole at Libero (+2.0) vs OH3 (−0.3) / M3 (−3.3).
- **Margin distribution**: Bean played close sets — wins by median +3, losses by median −4.5.

## Layer 2 — Key findings

- **Strength of schedule**: avg opponent win% .566. Bean beat the teams they should and lost to the teams they should — no flukes either direction.
- **Pythagorean expectation (THE BIG ONE)**: Volley These Balls went 11-0 but "should" have won ~7 → luckiest team. Tape Ticklers won 3, should have won ~7 → unluckiest. **Bean played EXACTLY to expectation (−0.05).** Their .476 was earned.
- **League margin distribution**: league sets avg 5.4 pts; Bean's sets avg 4.8 — Bean played tighter-than-average games.
- **The 01-07 paradox**: Bean LOST the match to Raw Butt Sets 1-2 but had +5 net points (24-26, 26-15, 2-6). Microcosm of why every-set-counts is the right format.
- **Silver vs Gold**: Gold avg win% .674 / net +1.78 per set; Silver .308 / −2.18. The tiering was earned. Bean (.476) was the strongest Silver team.

## Layer 3 — Key findings (game-3 hook)

- **G3 margins are significantly tighter**: mean 3.58 vs G1 5.43 / G2 6.11 (Welch p=.013 and .002). Game 3 in this league is closer.
- **G3 upset rate nearly doubles**: favored team wins 52.6% in G3 vs ~72% in G1/G2. Game 3 is a coin flip. (Partly selection effect — close matches reach G3 — partly the shorter cap adding variance.)
- **Teams self-select out of meaningless G3s**: only 2 of ~27 already-decided (2-0) matches bothered to play G3, vs 17 of ~27 still-alive (1-1) matches. The "every set counts for seeding" rule is not how players actually behave.
- **Bean was a positive-margin G3 team**: avg +0.80 in G3 vs −1.14 (G1) and 0.00 (G2). Tiny n, suggestive.

## Playoff analysis — Key findings

- **Bean PEAKED in playoffs**: team hit% +.121 → +.217 (+80%). Digs +26%, aces +50%, assists +22%. n=6 sets — small but the magnitudes are large.
- **The Allen story, sequel**: Allen flipped from −.102 regular-season hit% to **+.200** in playoffs. The player whose stats most tracked outcomes had his best stretch when it mattered most.
- **The lineup crystallized**: in the regular season players rotated through many positions; in playoffs each had ONE role. Zane became sole setter (Cade stopped covering setter). **Cole shifted from L/OH3 to middle (M1/M2) — directly covering Tae's vacated role** (Tae was M1×10/M2×6 in the regular season).

## Season trends — Key findings

- **No significant week-by-week trend** in regular season — all stats directionally positive but p>0.10 at n=7 weeks. Margin actually trended slightly DOWN.
- **The playoff jump was a step function, not a trend continuation**. Regular-season margin trend projected −1.5 for the playoff weeks; actual was +6.0. Bean didn't gradually improve into a champion — something specific changed for playoffs (see lineup crystallization above).

## Player roles — Key findings

| Player | Role | Signature numbers |
|---|---|---|
| Zane | primary setter + service leader | 138 assists (74% of team), 12 aces (30%) |
| Jeremy | primary hitter | 58 kills (27%), +.222 hit% |
| Andy | primary hitter | 57 kills (26%), +.203 hit% |
| Cole | secondary hitter + defensive anchor | 61 digs (most on team), position-flex |
| Cade | secondary setter + hitter + defensive anchor | 34 assists, 59 digs — the hybrid |
| Allen | secondary hitter | 25 kills but −.062 hit%, most errors (32) |
| Tae | everyday starter (middle) | 13 kills in 20 sets; missed playoffs (injury) |

## Blowout autopsy — Key findings

Neither of Bean's two worst losses (02-18 −20 vs Volley These Balls; 01-21 −16 vs Sugar & Spike) was a Bean collapse:

- **02-18 vs Volley These Balls**: Bean's hit% was roughly normal (.108 vs .129 season). 2 of 3 sets (−3, −5) were within VTB's typical winning margin (7.3) — Bean hung with the undefeated team. Set 3 was a 3-15 collapse — and is the one set with NO player stats (permanent data gap).
- **01-21 vs Sugar & Spike**: Bean's hit% was ABOVE season average (.163 vs .129); kills up, errors down, digs way up. Bean played a fine offensive game and lost by 16 anyway. The high dig count shows Bean defending nonstop — Sugar & Spike's attack overwhelmed them. Got outplayed, did not collapse.

## Cole's position for every set (full reference)

```
date        game  position           date        game  position
2026-01-07   1     L                 2026-02-11   3    OH2
2026-01-07   2     L                 2026-02-18   1    OH3
2026-01-07   3     L                 2026-02-18   2    OH3
2026-01-14   1    OH3                2026-02-25   1    OH3
2026-01-14   2    OH3                2026-02-25   2    OH3
2026-01-14   3    OH1                2026-02-25   3    OH3
2026-01-21   1    OH2                2026-03-04   1     M1   (playoff)
2026-01-21   2     M3                2026-03-04   2     M1   (playoff)
2026-01-21   3    OH2                2026-03-04   3    OH1   (playoff)
2026-01-28   1     L                 2026-03-11   1     M2   (playoff)
2026-01-28   2     L                 2026-03-11   2     M2   (playoff)
2026-01-28   3     L                 2026-03-11   3     M2   (playoff)
2026-02-11   1     M3
2026-02-11   2     M3
```

## Phase 2 deliverable — `data/processed/findings_summary.md`

`13_synthesize.py` ranks 14 curated findings by effect strength + sample size +
narrative interest (each 1-5, total /15). Tiers:

**Headline (>=12):**
1. Volley These Balls was the league's luckiest team (14/15)
2. Bean's record was exactly what they earned (13/15)
3. The Allen story — hitting mirrored the team (12/15)
4. In this league, game 3 is a coin flip (12/15)
5. The 01-07 paradox — lost the match, won the points (12/15)

**Supporting (9-11):** Bean peaked for playoffs · G3 played closer · defense
edged offense · teams skip meaningless G3 · Silver/Gold split earned · lineup
crystallized for playoffs · playoff leap was a step change · neither blowout
was a collapse.

**Context (<=8):** Cole's best spot may be libero (suggestive only).

## Phase 3 — charts (DONE)

9 charts in `charts/`, built by 3 scripts (`20_charts_league.py`,
`21_charts_team.py`, `22_charts_game3.py`) sharing `src/chart_style.py`:

- `pythagorean_luck.png` · `silver_vs_gold.png`
- `allen_story.png` · `defense_vs_offense.png` · `playoff_peak.png` · `paradox_0107.png` · `blowout_autopsy.png`
- `game3_coinflip.png` · `game3_margins.png`

Charts read the Phase 2 `findings_*.json` (plus a couple of CSVs for raw
distributions) — they visualize findings, they don't recompute them.

## Reproducing the whole project

- `make data` — Phase 1 data layer (scripts 01-05)
- `make analysis` — Phase 2 analysis (scripts 10-12, 14-17, then 13)
- `make charts` — Phase 3 charts (scripts 20-22)
- `make all` — all three

## Next steps

1. (Phase 4) README writeup — narrative built from `findings_summary.md`, embedding the 8 charts.
