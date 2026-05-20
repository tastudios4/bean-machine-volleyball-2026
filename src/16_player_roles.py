"""
16_player_roles.py

Descriptive role identification for the 7-player Bean Machine roster.

Computes per-player season totals + rate stats, then derives a role label
from the stat profile (not from the position field, which changes game to
game). Produces a "roles table" that makes the team legible to a reader who
doesn't know the players.

Role logic (stat-driven):
  - SETTER: dominant share of team assists
  - PRIMARY HITTER: top tier of team kills
  - DEFENSIVE ANCHOR: top tier of team digs / serve-receive volume
  - SERVER: dominant share of team aces
  A player can carry more than one tag.

Output: stdout + data/processed/findings_roles.json
"""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
PLAYER_STATS_CSV = ROOT / "data" / "processed" / "bean_machine_player_stats.csv"
OUT_JSON = ROOT / "data" / "processed" / "findings_roles.json"


def load_played_rows() -> pd.DataFrame:
    df = pd.read_csv(PLAYER_STATS_CSV)
    # Only count games a player actually played (position != "-")
    return df[df.position.fillna("").str.strip() != "-"].copy()


def per_player_totals(df: pd.DataFrame) -> pd.DataFrame:
    agg = df.groupby("player_name").agg(
        sets_played=("game_number", "count"),
        attack_attempts=("attack_attempts", "sum"),
        kills=("kills", "sum"),
        errors=("errors", "sum"),
        assists=("assists", "sum"),
        blocks_solo=("blocks_solo", "sum"),
        blocks_assist=("blocks_assist", "sum"),
        digs=("digs", "sum"),
        aces=("aces", "sum"),
        service_errors=("service_errors", "sum"),
        total_serves=("total_serves", "sum"),
        sr_attempts=("sr_attempts", "sum"),
    ).reset_index()

    # Rate stats
    with np.errstate(divide="ignore", invalid="ignore"):
        agg["hit_pct"] = (agg.kills - agg.errors) / agg.attack_attempts
        agg["kills_per_set"] = agg.kills / agg.sets_played
        agg["digs_per_set"] = agg.digs / agg.sets_played
        agg["assists_per_set"] = agg.assists / agg.sets_played
        agg["ace_pct"] = agg.aces / agg.total_serves
    return agg


def add_team_shares(agg: pd.DataFrame) -> pd.DataFrame:
    for stat in ("kills", "assists", "digs", "aces", "attack_attempts"):
        total = agg[stat].sum()
        agg[f"{stat}_share"] = agg[stat] / total if total else 0.0
    return agg


def assign_roles(agg: pd.DataFrame) -> dict[str, dict]:
    roles = {}
    kills_rank = agg.sort_values("kills", ascending=False).player_name.tolist()
    digs_rank = agg.sort_values("digs", ascending=False).player_name.tolist()

    # Every player on this roster played every set available to them, so they
    # are all everyday starters — there were no true bench/rotational players.
    max_sets = agg["sets_played"].max()

    for _, r in agg.iterrows():
        tags = []
        # Setter: >40% of team assists
        if r["assists_share"] > 0.40:
            tags.append("primary setter")
        elif r["assists_share"] > 0.15:
            tags.append("secondary setter")
        # Primary hitter: top-3 in total kills AND >15% of team kills
        if r["player_name"] in kills_rank[:3] and r["kills_share"] > 0.15:
            tags.append("primary hitter")
        # Secondary hitter: meaningful kill volume but not top-3
        elif r["kills_share"] >= 0.08:
            tags.append("secondary hitter")
        # Defensive anchor: top-2 in digs
        if r["player_name"] in digs_rank[:2]:
            tags.append("defensive anchor")
        # Server: >25% of team aces
        if r["aces_share"] > 0.25:
            tags.append("service leader")
        if not tags:
            # No statistical leader tag, but still an everyday starter
            tags.append("everyday starter")
        roles[r["player_name"]] = {
            "tags": tags,
            "kills_share": float(r["kills_share"]),
            "assists_share": float(r["assists_share"]),
            "digs_share": float(r["digs_share"]),
            "aces_share": float(r["aces_share"]),
        }
    return roles


def banner(t: str) -> None:
    print()
    print("=" * 78)
    print(t)
    print("=" * 78)


def main() -> None:
    df = load_played_rows()
    agg = add_team_shares(per_player_totals(df))
    roles = assign_roles(agg)

    banner("PLAYER ROLES & ARCHETYPES")
    print("Season totals (regular season + playoffs; only games actually played)")
    print()
    show = agg.sort_values("kills", ascending=False)
    print(f"  {'player':<8}{'sets':>5}{'kills':>7}{'errors':>7}{'hit%':>8}"
          f"{'K/set':>7}{'digs':>6}{'D/set':>7}{'assists':>9}{'aces':>6}")
    print(f"  {'-'*8}{'-'*5}{'-'*7}{'-'*7}{'-'*8}{'-'*7}{'-'*6}{'-'*7}{'-'*9}{'-'*6}")
    for _, r in show.iterrows():
        print(f"  {r['player_name']:<8}{r['sets_played']:>5}{r['kills']:>7}"
              f"{r['errors']:>7}{r['hit_pct']:>+8.3f}{r['kills_per_set']:>7.2f}"
              f"{r['digs']:>6}{r['digs_per_set']:>7.2f}{r['assists']:>9}{r['aces']:>6}")

    banner("TEAM SHARES (what fraction of each stat each player produced)")
    print(f"  {'player':<8}{'kills%':>9}{'assists%':>11}{'digs%':>9}{'aces%':>9}")
    print(f"  {'-'*8}{'-'*9}{'-'*11}{'-'*9}{'-'*9}")
    for _, r in show.iterrows():
        print(f"  {r['player_name']:<8}{r['kills_share']:>9.1%}{r['assists_share']:>11.1%}"
              f"{r['digs_share']:>9.1%}{r['aces_share']:>9.1%}")

    banner("DERIVED ROLES (stat-driven, not from the position field)")
    for player in show.player_name:
        tags = roles[player]["tags"]
        print(f"  {player:<8} {', '.join(tags)}")

    banner("ROLE NARRATIVE")
    # Build a couple of plain-English observations
    setter = max(roles, key=lambda p: roles[p]["assists_share"])
    top_hitter = agg.sort_values("kills", ascending=False).iloc[0]
    dig_leader = agg.sort_values("digs", ascending=False).iloc[0]
    ace_leader = agg.sort_values("aces", ascending=False).iloc[0]
    print(f"  - {setter} ran the offense: {roles[setter]['assists_share']:.0%} "
          f"of all team assists.")
    print(f"  - {top_hitter['player_name']} led in kills "
          f"({int(top_hitter['kills'])}, {top_hitter['kills_share']:.0%} of team total).")
    print(f"  - {dig_leader['player_name']} anchored the defense "
          f"({int(dig_leader['digs'])} digs, {dig_leader['digs_share']:.0%} of team total).")
    print(f"  - {ace_leader['player_name']} led in aces "
          f"({int(ace_leader['aces'])}, {ace_leader['aces_share']:.0%} of team total).")

    payload = {
        "meta": {
            "scope": "regular season + playoffs; games played only (position != '-')",
        },
        "player_totals": agg.to_dict(orient="records"),
        "roles": roles,
        "leaders": {
            "setter": setter,
            "top_hitter": top_hitter["player_name"],
            "dig_leader": dig_leader["player_name"],
            "ace_leader": ace_leader["player_name"],
        },
    }
    OUT_JSON.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_JSON, "w") as f:
        json.dump(payload, f, indent=2, default=str)
    print()
    print(f"WROTE {OUT_JSON.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
