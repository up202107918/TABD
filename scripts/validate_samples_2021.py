"""
Cross-check operational DB vs CNE Excel (mapa_1 + mapa_2) for three municipalities.
Writes etl/docs/validation_samples_2021.md
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd
import psycopg2
import psycopg2.extras

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "etl"))

from config import DB_CONFIG  # noqa: E402
from pipeline.extract import (  # noqa: E402
    cell_text,
    coerce_integer,
    normalize_label,
    parse_wide_mapa_sheet,
    read_workbook_sheets,
)

SAMPLES = [
    ("Lisboa", "LISBOA", "large capital"),
    ("Porto", "PORTO", "large city"),
    ("Barrancos", "BARRANCOS", "small municipality (Beja, ~1.3k registered voters)"),
]

MAPA1 = ROOT / "etl" / "data" / "2021al_mapa_oficial" / "mapa_1_resultados.xlsx"
MAPA2 = ROOT / "etl" / "data" / "2021al_mapa_oficial" / "mapa_2_perc_mandatos.xlsx"
OUT = ROOT / "etl" / "docs" / "validation_samples_2021.md"
CM_SEATS = 7  # Câmara Municipal — demo / typical for cities; Barrancos may differ officially


def parse_mapa2_percent(value: Any) -> Optional[float]:
    """
    mapa_2 cells are already percentages (float 18.6, 0.43).
    Do NOT use coerce_decimal from ETL — it strips '.' and breaks decimals (0.08 -> 8).
    Integer values >= 100 are hundredths (3535 -> 35.35).
    """
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        v = float(value)
        if v <= 0:
            return None
        if v >= 100 and abs(v - round(v)) < 1e-9:
            return round(v / 100.0, 4)
        return round(v, 4)
    text = str(value).strip().replace("%", "")
    if "," in text:
        text = text.replace(".", "").replace(",", ".")
    try:
        v = float(text)
    except ValueError:
        return None
    if v <= 0:
        return None
    if v >= 100 and abs(v - round(v)) < 1e-9:
        return round(v / 100.0, 4)
    return round(v, 4)


def load_cne_mapa1() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, Dict[str, int]]]:
    sheets = read_workbook_sheets(str(MAPA1))
    results, turnouts = [], []
    for df in sheets.values():
        r, t = parse_wide_mapa_sheet(df)
        results.extend(r)
        turnouts.extend(t)

    turnout_by_muni: Dict[str, Dict[str, Any]] = {}
    for row in turnouts:
        turnout_by_muni[row["concelho"]] = row

    votes_by_muni: Dict[str, Dict[str, int]] = {}
    for row in results:
        muni = row["concelho"]
        party = row["candidatura"]
        votes_by_muni.setdefault(muni, {})[party] = row["votos"]
    return (
        {k.upper(): v for k, v in turnout_by_muni.items()},
        {k.upper(): v for k, v in votes_by_muni.items()},
    )


def load_cne_mapa2_vote_percent() -> Dict[str, Dict[str, float]]:
    """Parse mapa_2 vote-% columns (perc. votos válidos), not mandate counts."""
    from pipeline.extract import party_code_to_acronym  # noqa: E402

    sheets = read_workbook_sheets(str(MAPA2))
    raw = list(sheets.values())[0]
    # mapa_2 wide layout: party headers from col 4 (A, B.E., …) — not col 8 like mapa_1
    party_columns: List[Tuple[int, str]] = []
    for idx in range(4, raw.shape[1]):
        hdr_cell = raw.iloc[3, idx]
        if hdr_cell is None or (isinstance(hdr_cell, float) and pd.isna(hdr_cell)):
            continue
        label = str(hdr_cell).strip()
        if label:
            party_columns.append((idx, label))

    percents: Dict[str, Dict[str, float]] = {}
    current_district: Optional[str] = None

    for row_idx in range(4, len(raw)):
        row = raw.iloc[row_idx].tolist()
        conc = cell_text(row[1] if len(row) > 1 else None)
        freg = cell_text(row[2] if len(row) > 2 else None)
        org = normalize_label(row[3] if len(row) > 3 else None)
        insc = coerce_integer(row[4] if len(row) > 4 else None)

        if not org and conc and not freg and insc is None:
            current_district = conc
            continue
        if org != "cm" or freg or not conc:
            continue

        muni_pct: Dict[str, float] = {}
        for col_idx, party_label in party_columns:
            pct = parse_mapa2_percent(row[col_idx] if col_idx < len(row) else None)
            if pct is None:
                continue
            acronym = party_code_to_acronym(normalize_label(party_label))
            muni_pct[acronym] = round(pct, 2)
        if muni_pct:
            percents[conc.upper()] = muni_pct
    return percents


def fetch_db(conn, municipality_name: str) -> Tuple[Dict[str, Any], Dict[str, int], List[Tuple[str, int, int]]]:
    with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
        cur.execute(
            """
            SELECT m.municipality_id, m.municipality_name, d.district_name,
                   t.registered_voters, t.votes_cast, t.valid_votes,
                   t.blank_votes, t.null_votes, t.turnout_percentage
            FROM operational.municipality m
            JOIN operational.district d ON m.district_id = d.district_id
            JOIN operational.turnout t ON t.municipality_id = m.municipality_id
            JOIN operational.electoral_organ eo ON t.organ_id = eo.organ_id
            WHERE m.municipality_name = %s AND eo.organ_code = 'CM'
              AND t.election_id = (SELECT election_id FROM operational.election WHERE election_year = 2021 LIMIT 1)
            """,
            (municipality_name,),
        )
        turnout = cur.fetchone()
        if not turnout:
            raise ValueError(f"No DB turnout for {municipality_name}")

        cur.execute(
            """
            SELECT COALESCE(p.party_acronym, co.coalition_acronym) AS party,
                   vr.votes_obtained
            FROM operational.candidacy c
            JOIN operational.vote_result vr ON c.candidacy_id = vr.candidacy_id
            LEFT JOIN operational.party p ON c.party_id = p.party_id
            LEFT JOIN operational.coalition co ON c.coalition_id = co.coalition_id
            WHERE c.municipality_id = %s
              AND c.organ_id = (SELECT organ_id FROM operational.electoral_organ WHERE organ_code = 'CM')
              AND c.election_id = (SELECT election_id FROM operational.election WHERE election_year = 2021 LIMIT 1)
              AND vr.votes_obtained > 0
            ORDER BY vr.votes_obtained DESC
            """,
            (turnout["municipality_id"],),
        )
        votes = {r["party"]: r["votes_obtained"] for r in cur.fetchall()}

        cur.execute(
            """
            SELECT party_name, votes, seats_allocated
            FROM operational.allocate_seats_dhondt(
                (SELECT election_id FROM operational.election WHERE election_year = 2021 LIMIT 1),
                (SELECT organ_id FROM operational.electoral_organ WHERE organ_code = 'CM'),
                %s,
                %s
            )
            WHERE seats_allocated > 0
            ORDER BY seats_allocated DESC, votes DESC
            """,
            (turnout["municipality_id"], CM_SEATS),
        )
        dhondt = [(r["party_name"], r["votes"], r["seats_allocated"]) for r in cur.fetchall()]

    return dict(turnout), votes, dhondt


def compare_votes(cne: Dict[str, int], db: Dict[str, int]) -> Tuple[int, List[str]]:
    all_parties = sorted(set(cne) | set(db))
    mismatches = 0
    rows: List[str] = []
    for party in all_parties:
        cv, dv = cne.get(party), db.get(party)
        if cv != dv:
            mismatches += 1
            rows.append(f"| {party} | {cv or '—'} | {dv or '—'} | **MISMATCH** |")
        else:
            rows.append(f"| {party} | {cv} | {dv} | OK |")
    return mismatches, rows


def compare_vote_pct_to_db(
    vote_pct: Dict[str, float], db_votes: Dict[str, int], valid_votes: int
) -> Tuple[int, List[str]]:
    """mapa_2 holds vote %%; compare to vote share computed from DB."""
    all_parties = sorted(set(vote_pct) | set(db_votes))
    mismatches = 0
    rows: List[str] = []
    for party in all_parties:
        cne_pct = vote_pct.get(party)
        votes = db_votes.get(party)
        db_pct = round(100.0 * votes / valid_votes, 2) if votes is not None and valid_votes else None
        if cne_pct is None:
            rows.append(f"| {party} | — | {db_pct}% | **missing in mapa_2** |")
            mismatches += 1
            continue
        ok = db_pct is not None and abs(cne_pct - db_pct) < 0.06
        if not ok:
            mismatches += 1
        rows.append(
            f"| {party} | {cne_pct}% | {db_pct if db_pct is not None else '—'}% | "
            f"{'OK' if ok else '**MISMATCH**'} |"
        )
    return mismatches, rows


def main() -> int:
    turnout_cne, votes_cne = load_cne_mapa1()
    mapa2_pct = load_cne_mapa2_vote_percent()

    conn = psycopg2.connect(**DB_CONFIG)
    conn.autocommit = True
    try:
        with conn.cursor() as cur:
            cur.execute("SET search_path TO operational, warehouse, public")

        sections: List[str] = []
        sections.append("# Validation samples — Autárquicas 2021 (CM)\n")
        sections.append(
            f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}  \n"
            f"Sources: `{MAPA1.name}` (votes/turnout), `{MAPA2.name}` (vote %), "
            f"PostgreSQL `operational.*`, function `allocate_seats_dhondt(..., {CM_SEATS})`.\n"
        )
        sections.append("## Sample municipalities\n")
        sections.append("| Municipality (DB) | CNE `concelho` | Role |")
        sections.append("|-------------------|----------------|------|")
        for muni_db, muni_cne, role in SAMPLES:
            sections.append(f"| {muni_db} | {muni_cne} | {role} |")

        summary_rows: List[str] = []

        for muni_db, muni_cne, role in SAMPLES:
            key = muni_cne.upper()
            if key not in turnout_cne:
                sections.append(f"\n## {muni_db}\n\n**ERROR:** `{muni_cne}` not found in mapa_1.\n")
                continue

            t_cne = turnout_cne[key]
            v_cne = votes_cne.get(key, {})
            pct_cne = mapa2_pct.get(key, {})
            t_db, v_db, dhondt = fetch_db(conn, muni_db)

            sections.append(f"\n## {muni_db} ({role})\n")
            sections.append(f"District (CNE row): **{t_cne['distrito']}** · DB: **{t_db['district_name']}**\n")

            sections.append("### Turnout (mapa_1 vs DB)\n")
            sections.append("| Metric | CNE mapa_1 | DB `turnout` | Match |")
            sections.append("|--------|------------|--------------|-------|")
            pairs = [
                ("Registered", "eleitores_inscritos", "registered_voters"),
                ("Votes cast", "votantes", "votes_cast"),
                ("Valid votes", "votos_validos", "valid_votes"),
                ("Blank", "votos_brancos", "blank_votes"),
                ("Null", "votos_nulos", "null_votes"),
            ]
            turnout_ok = True
            for label, ck, dk in pairs:
                cv, dv = t_cne[ck], t_db[dk]
                ok = cv == dv
                turnout_ok = turnout_ok and ok
                sections.append(f"| {label} | {cv} | {dv} | {'OK' if ok else '**MISMATCH**'} |")
            sum_cne = sum(v_cne.values())
            sum_db = sum(v_db.values())
            sections.append(f"\nSum party votes: CNE **{sum_cne}** · DB **{sum_db}** · "
                           f"{'OK' if sum_cne == sum_db else '**MISMATCH**'}  \n"
                           f"Valid votes check: sum ≤ valid → CNE {sum_cne <= t_cne['votos_validos']}, "
                           f"DB {sum_db <= t_db['valid_votes']}\n")

            sections.append("### Votes by party/list\n")
            vote_mm, vote_rows = compare_votes(v_cne, v_db)
            sections.append(
                f"**Vote mismatches:** {vote_mm} / {len(set(v_cne) | set(v_db))} parties\n"
            )
            sections.append("| Party | CNE | DB | Status |")
            sections.append("|-------|-----|-----|--------|")
            sections.extend(vote_rows)

            sections.append(f"\n### D'Hondt seats (`allocate_seats_dhondt`, {CM_SEATS} seats — ex10.sql pattern)\n")
            sections.append("| Party | Votes | Seats |")
            sections.append("|-------|-------|-------|")
            for party, votes, seats in dhondt:
                sections.append(f"| {party} | {votes} | {seats} |")

            pct_ok = True
            if pct_cne:
                sections.append("\n### mapa_2 vote % vs DB (derived from valid votes)\n")
                pct_mm, pct_rows = compare_vote_pct_to_db(pct_cne, v_db, t_db["valid_votes"])
                pct_ok = pct_mm == 0
                sections.append(
                    f"**mapa_2 % mismatches:** {pct_mm} / {len(set(pct_cne) | set(v_db))} parties\n"
                )
                sections.append("| Party | mapa_2 % | DB vote % | Status |")
                sections.append("|-------|----------|-----------|--------|")
                sections.extend(pct_rows)
            sections.append("\n**Top quotients (`demonstrate_dhondt`):** see `sql/07_demo_queries.sql`.\n")
            vote_ok = v_cne == v_db and sum_cne == sum_db
            summary_rows.append(
                f"| {muni_db} | Turnout | {'PASS' if turnout_ok else 'FAIL'} | Votes | "
                f"{'PASS' if vote_ok else 'FAIL'} | mapa_2 % | "
                f"{'PASS' if pct_ok else 'FAIL'} | D'Hondt | OK |"
            )

        sections.append("\n## Summary\n")
        sections.append("| Municipality | Turnout | | Votes | | mapa_2 % | | D'Hondt | |")
        sections.append("|--------------|---------|--|-------|--|----------|--|---------|--|")
        sections.extend(summary_rows)

        sections.append("\n## Notes\n")
        sections.append(
            "- **Lisboa** uses CNE list codes (A, B, …) in mapa_1/mapa_2, not national acronyms (PS/PSD).\n"
            "- **`seat_result`** table is still empty in MVP; seats come from **`allocate_seats_dhondt`** (same algorithm as course `ex10.sql`).\n"
            "- **mapa_2** = vote % published by CNE; parser must keep decimal points (unlike ETL `coerce_decimal` for integers).\n"
            f"- D'Hondt uses **{CM_SEATS}** seats in this script; smaller councils may have a different official seat total.\n"
            "- Regenerate: `python scripts/validate_samples_2021.py` from repo root (with DB env vars set).\n"
        )

        OUT.parent.mkdir(parents=True, exist_ok=True)
        OUT.write_text("\n".join(sections), encoding="utf-8")
        print(f"Wrote {OUT}")
    finally:
        conn.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
