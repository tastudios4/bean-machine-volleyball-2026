"""
02_parse_league.py

Parses data/raw/league_raw.xlsx into:

  - data/processed/league_matches.csv   (one row per match, sets nested as columns)
  - data/processed/league_standings.csv (final-season W-L-pct per team)
  - data/manual_review/league_unparsed.csv (any score cell the regex couldn't handle)

Three passes over the single 'Wed BB 26' tab:

  Pass 1 — Standings (rows 4-18): canonical team_number -> team_name lookup
           and final-season standings.

  Pass 2 — Regular season weekly blocks: every "2026-MM-DD" date row marks
           the start of a week. The next 3 rows are a header + 2 time slots
           with 4 courts each (8 matches per week).

  Pass 3 — Playoffs: the bracket section (rows 66+) does NOT contain set
           scores. Instead of parsing it, we emit a pre-filled template
           data/raw/playoff_scores_manual.csv listing the playoff dates
           inferred from player_stats tab names (03-04, 03-11). On
           subsequent runs the user fills in scores and they get merged.
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
RAW_XLSX = ROOT / "data" / "raw" / "league_raw.xlsx"
PLAYER_STATS_XLSX = ROOT / "data" / "raw" / "player_stats_raw.xlsx"
PROCESSED_DIR = ROOT / "data" / "processed"
MANUAL_REVIEW_DIR = ROOT / "data" / "manual_review"
PLAYOFF_MANUAL_CSV = ROOT / "data" / "raw" / "playoff_scores_manual.csv"

LEAGUE_MATCHES_CSV = PROCESSED_DIR / "league_matches.csv"
STANDINGS_CSV = PROCESSED_DIR / "league_standings.csv"
UNPARSED_CSV = MANUAL_REVIEW_DIR / "league_unparsed.csv"

SHEET_NAME = "Wed BB 26"

# Regular-season block layout: matchup and score for each of 4 courts
COURT_COLS = [
    (1, 2, 4),   # (court_number, matchup_col, score_col)
    (2, 5, 6),
    (3, 7, 8),
    (4, 9, 10),
]
TIME_SLOTS = [
    ("8:10", 0),  # row offset 0 from the header row (header_row + 1)
    ("9:10", 1),
]

DATE_CELL_RE = re.compile(r"^2026-\d{2}-\d{2}")
MATCHUP_RE = re.compile(r"^\s*(\d+)\s*[vV]s?\.?\s*(\d+)\s*$")
SCORE_PAIR_RE = re.compile(r"(\d{1,2})\s*-\s*(\d{1,2})")
# Winner cues: leading "(N win)", "N win", "Nw", "N:" patterns.
WINNER_RE = re.compile(
    r"""
    ^\s*\(?\s*                       # optional opening paren and spaces
    (?P<n>\d{1,2})                   # winner team number
    \s*                              # optional spaces
    (?:                              # one of: 'win', 'w', or ':' / ';'
        win\b
      | w\b
      | (?=[:;])                     # bare colon/semicolon follows
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)
TIE_RE = re.compile(r"\b(tie|both teams won)\b", re.IGNORECASE)


@dataclass
class ParsedScore:
    """Result of parsing one score cell."""

    winner_team_number: Optional[int]
    is_tie: bool
    set_scores: list[tuple[int, int]]  # (a, b) pairs in cell order — caller maps to team_a/team_b
    confidence: str  # 'high', 'low'
    note: str = ""


def load_sheet() -> pd.DataFrame:
    return pd.read_excel(RAW_XLSX, sheet_name=SHEET_NAME, header=None, engine="openpyxl")


# --------------------------------------------------------------------------- #
# Pass 1: Standings + team lookup
# --------------------------------------------------------------------------- #

def parse_standings(df: pd.DataFrame) -> tuple[pd.DataFrame, dict[int, str]]:
    """Rows 4-18, cols: 1=team_number, 2=team_name, 4=wins, 5=losses, 6=total, 7=pct."""
    rows = []
    for r in range(4, 19):
        try:
            tn = int(df.iat[r, 1])
        except (ValueError, TypeError):
            continue
        rows.append(
            {
                "team_number": tn,
                "team_name": str(df.iat[r, 2]).strip(),
                "wins": int(df.iat[r, 4]),
                "losses": int(df.iat[r, 5]),
                "total_games": int(df.iat[r, 6]),
                "win_pct": float(df.iat[r, 7]),
            }
        )
    standings = pd.DataFrame(rows)
    lookup = dict(zip(standings["team_number"], standings["team_name"]))
    return standings, lookup


# --------------------------------------------------------------------------- #
# Pass 2: Regular season
# --------------------------------------------------------------------------- #

def find_week_blocks(df: pd.DataFrame) -> list[tuple[int, date]]:
    """Find rows where col[1] is a 2026-MM-DD date (start of a weekly block).
    Also handles the special-case row 22 ('Jan 7th' under a 'Week 1' label on row 21).
    """
    blocks: list[tuple[int, date]] = []
    # Special-case first week (it doesn't have an ISO date in col 1)
    blocks.append((22, date(2026, 1, 7)))

    for r in range(22, len(df)):
        cell = df.iat[r, 1]
        if pd.isna(cell):
            continue
        s = str(cell).strip()
        if DATE_CELL_RE.match(s):
            # Stop at playoffs (the playoff section reuses date strings differently)
            if r >= 66:
                break
            blocks.append((r, pd.to_datetime(s).date()))
    return blocks


def parse_matchup(cell) -> Optional[tuple[int, int]]:
    if pd.isna(cell):
        return None
    m = MATCHUP_RE.match(str(cell))
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def parse_score_cell(cell, team_a: int, team_b: int) -> ParsedScore:
    if pd.isna(cell) or not str(cell).strip():
        return ParsedScore(None, False, [], "low", "empty cell")

    text = str(cell).strip()
    pairs = [(int(a), int(b)) for a, b in SCORE_PAIR_RE.findall(text)]
    is_tie = bool(TIE_RE.search(text))

    # Winner: explicit if matched; for ties, no winner.
    winner = None
    wm = WINNER_RE.match(text)
    if wm:
        winner = int(wm.group("n"))
    elif is_tie:
        winner = None
    else:
        # Fallback: cell may lead with just a number like "4   15-25, 14-25" — first integer.
        m = re.match(r"^\s*(\d{1,2})\b", text)
        if m:
            cand = int(m.group(1))
            if cand in (team_a, team_b):
                winner = cand

    if is_tie:
        if len(pairs) >= 2:
            return ParsedScore(None, True, pairs[:2], "high", "tie, 2 sets")
        return ParsedScore(None, True, pairs, "low", "tie but score count unexpected")

    if winner is None:
        return ParsedScore(None, False, pairs, "low", "no clear winner")
    if winner not in (team_a, team_b):
        return ParsedScore(winner, False, pairs, "low",
                            f"winner {winner} not in matchup {team_a} vs {team_b}")
    if len(pairs) not in (2, 3):
        return ParsedScore(winner, False, pairs, "low",
                            f"unexpected set count: {len(pairs)}")
    return ParsedScore(winner, False, pairs, "high", "")


def parse_regular_season(
    df: pd.DataFrame,
    team_lookup: dict[int, str],
) -> tuple[list[dict], list[dict]]:
    matches: list[dict] = []
    unparsed: list[dict] = []
    week_blocks = find_week_blocks(df)

    for week_idx, (date_row, match_date) in enumerate(week_blocks, start=1):
        # header is the next row; time slots are header_row + 1 and header_row + 2
        header_row = date_row + 1
        for slot_label, offset in TIME_SLOTS:
            row_idx = header_row + 1 + offset
            if row_idx >= len(df):
                continue
            for court_n, matchup_col, score_col in COURT_COLS:
                matchup_cell = df.iat[row_idx, matchup_col]
                score_cell = df.iat[row_idx, score_col]
                matchup = parse_matchup(matchup_cell)
                if matchup is None:
                    if not pd.isna(matchup_cell) and str(matchup_cell).strip():
                        unparsed.append(
                            {
                                "row": row_idx,
                                "court": court_n,
                                "date": match_date.isoformat(),
                                "matchup_raw": str(matchup_cell),
                                "score_raw": "" if pd.isna(score_cell) else str(score_cell),
                                "reason": "could not parse matchup",
                            }
                        )
                    continue

                team_a, team_b = matchup
                parsed = parse_score_cell(score_cell, team_a, team_b)

                match_id = f"{match_date.isoformat()}_C{court_n}_M{week_idx}"
                # Map cell-order set scores to team_a / team_b columns.
                # The score cell uses the matchup order (team_a first), so pairs[i][0]=team_a points.
                set_points = parsed.set_scores + [(None, None)] * (3 - len(parsed.set_scores))
                row = {
                    "match_id": match_id,
                    "date": match_date.isoformat(),
                    "week_number": week_idx,
                    "court": court_n,
                    "time_slot": slot_label,
                    "team_a_number": team_a,
                    "team_a_name": team_lookup.get(team_a, f"Team {team_a}"),
                    "team_b_number": team_b,
                    "team_b_name": team_lookup.get(team_b, f"Team {team_b}"),
                    "set1_a": set_points[0][0],
                    "set1_b": set_points[0][1],
                    "set2_a": set_points[1][0],
                    "set2_b": set_points[1][1],
                    "set3_a": set_points[2][0],
                    "set3_b": set_points[2][1],
                    "winner_team_number": parsed.winner_team_number,
                    "is_tie": parsed.is_tie,
                    "raw_text_source": "" if pd.isna(score_cell) else str(score_cell),
                    "is_playoff": False,
                }
                matches.append(row)

                if parsed.confidence == "low":
                    unparsed.append(
                        {
                            "row": row_idx,
                            "court": court_n,
                            "date": match_date.isoformat(),
                            "matchup_raw": str(matchup_cell),
                            "score_raw": "" if pd.isna(score_cell) else str(score_cell),
                            "team_a": team_a,
                            "team_b": team_b,
                            "best_guess_winner": parsed.winner_team_number,
                            "best_guess_sets": parsed.set_scores,
                            "reason": parsed.note,
                        }
                    )

    return matches, unparsed


# --------------------------------------------------------------------------- #
# Pass 3: Playoffs (template-driven)
# --------------------------------------------------------------------------- #

PLAYOFF_TEMPLATE_HEADER = [
    "match_id", "date", "week_number", "bracket", "round", "court", "time_slot",
    "team_a_number", "team_b_number",
    "set1_a", "set1_b", "set2_a", "set2_b", "set3_a", "set3_b",
    "winner_team_number", "is_tie", "notes",
]


def playoff_dates_from_player_stats() -> list[date]:
    """Read player_stats_raw.xlsx tab names; return distinct playoff dates (>= Mar 1)."""
    sheets = pd.read_excel(PLAYER_STATS_XLSX, sheet_name=None, header=None, engine="openpyxl")
    dates = set()
    for name in sheets.keys():
        m = re.match(r"^26-(\d{2})(\d{2})G\d$", name)
        if not m:
            continue
        month, day = int(m.group(1)), int(m.group(2))
        d = date(2026, month, day)
        if d >= date(2026, 3, 1):
            dates.add(d)
    return sorted(dates)


def write_playoff_template_if_missing() -> bool:
    """If data/raw/playoff_scores_manual.csv doesn't exist, create a pre-filled template.
    Returns True if a template was just created (caller will print guidance)."""
    if PLAYOFF_MANUAL_CSV.exists():
        return False

    playoff_dates = playoff_dates_from_player_stats()
    rows = []
    for i, d in enumerate(playoff_dates, start=1):
        # We know Bean Machine (team 11) played on both playoff dates.
        rows.append(
            {
                "match_id": f"{d.isoformat()}_CTBD_PO{i}",
                "date": d.isoformat(),
                "week_number": 7 + i,  # playoff dates become "weeks" 8 and 9 to match TotalW8/W9
                "bracket": "Silver",
                "round": "",
                "court": "",
                "time_slot": "",
                "team_a_number": 11,
                "team_b_number": "",
                "set1_a": "", "set1_b": "",
                "set2_a": "", "set2_b": "",
                "set3_a": "", "set3_b": "",
                "winner_team_number": 11,
                "is_tie": False,
                "notes": "Bean Machine won the Silver bracket. Format: first 2 games to 21, 3rd to 15.",
            }
        )
    pd.DataFrame(rows, columns=PLAYOFF_TEMPLATE_HEADER).to_csv(PLAYOFF_MANUAL_CSV, index=False)
    return True


def read_playoff_manual(team_lookup: dict[int, str]) -> list[dict]:
    """Read the manual playoff CSV (if user has filled in scores) and return league_matches rows."""
    if not PLAYOFF_MANUAL_CSV.exists():
        return []
    df = pd.read_csv(PLAYOFF_MANUAL_CSV)
    matches = []
    for _, r in df.iterrows():
        # Skip rows where the user hasn't filled in the opponent yet.
        if pd.isna(r["team_b_number"]) or str(r["team_b_number"]).strip() == "":
            continue
        team_a = int(r["team_a_number"])
        team_b = int(r["team_b_number"])
        winner = r["winner_team_number"]
        winner = int(winner) if pd.notna(winner) and str(winner).strip() != "" else None
        matches.append(
            {
                "match_id": r["match_id"],
                "date": r["date"],
                "week_number": int(r["week_number"]) if pd.notna(r["week_number"]) else None,
                "court": r.get("court", ""),
                "time_slot": r.get("time_slot", ""),
                "team_a_number": team_a,
                "team_a_name": team_lookup.get(team_a, f"Team {team_a}"),
                "team_b_number": team_b,
                "team_b_name": team_lookup.get(team_b, f"Team {team_b}"),
                "set1_a": r.get("set1_a"), "set1_b": r.get("set1_b"),
                "set2_a": r.get("set2_a"), "set2_b": r.get("set2_b"),
                "set3_a": r.get("set3_a"), "set3_b": r.get("set3_b"),
                "winner_team_number": winner,
                "is_tie": bool(r.get("is_tie", False)),
                "raw_text_source": f"manual: {r.get('notes', '')}",
                "is_playoff": True,
            }
        )
    return matches


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #

def main() -> None:
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    MANUAL_REVIEW_DIR.mkdir(parents=True, exist_ok=True)

    df = load_sheet()

    print("=" * 60)
    print("Pass 1: standings + team lookup")
    print("=" * 60)
    standings, team_lookup = parse_standings(df)
    standings.to_csv(STANDINGS_CSV, index=False)
    print(f"  -> {len(standings)} teams written to {STANDINGS_CSV.relative_to(ROOT)}")
    print(f"  Bean Machine row: {standings[standings.team_number == 11].to_dict('records')}")

    print()
    print("=" * 60)
    print("Pass 2: regular season")
    print("=" * 60)
    matches, unparsed = parse_regular_season(df, team_lookup)
    print(f"  -> parsed {len(matches)} regular-season matches")
    print(f"  -> {len(unparsed)} cell(s) flagged for manual review")

    print()
    print("=" * 60)
    print("Pass 3: playoffs (manual)")
    print("=" * 60)
    created = write_playoff_template_if_missing()
    if created:
        print(f"  -> created template {PLAYOFF_MANUAL_CSV.relative_to(ROOT)}")
        print(f"     FILL IN team_b_number and set scores, then re-run `make data`.")
    else:
        print(f"  -> template {PLAYOFF_MANUAL_CSV.relative_to(ROOT)} already exists")
    playoff_matches = read_playoff_manual(team_lookup)
    print(f"  -> {len(playoff_matches)} playoff match(es) loaded from manual CSV")

    all_matches = matches + playoff_matches
    pd.DataFrame(all_matches).to_csv(LEAGUE_MATCHES_CSV, index=False)
    print()
    print(f"WROTE {LEAGUE_MATCHES_CSV.relative_to(ROOT)}  ({len(all_matches)} rows)")

    if unparsed:
        pd.DataFrame(unparsed).to_csv(UNPARSED_CSV, index=False)
        print(f"WROTE {UNPARSED_CSV.relative_to(ROOT)}  ({len(unparsed)} rows)")
    elif UNPARSED_CSV.exists():
        UNPARSED_CSV.unlink()


if __name__ == "__main__":
    main()
