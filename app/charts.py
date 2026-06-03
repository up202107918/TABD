"""
Server-side Matplotlib charts fed by PostgreSQL (assignment §5.5).

Used by Flask routes (`/analytics/chart.png`) and `scripts/export_charts.py`.
"""

from __future__ import annotations

import io
from typing import Any, Dict, List, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

ORGAN_CM_SUBQUERY = (
    "SELECT organ_id FROM operational.electoral_organ WHERE organ_code = 'CM'"
)

PARTY_COMPARISON_SQL = f"""
    SELECT COALESCE(p.party_acronym, co.coalition_acronym) AS party,
           SUM(vr.votes_obtained) AS total_votes,
           SUM(COALESCE(sr.seats_obtained, 0)) AS total_seats,
           ROUND(AVG(vr.vote_percentage), 2) AS avg_percentage
    FROM operational.candidacy c
    LEFT JOIN operational.party p ON c.party_id = p.party_id
    LEFT JOIN operational.coalition co ON c.coalition_id = co.coalition_id
    JOIN operational.vote_result vr ON c.candidacy_id = vr.candidacy_id
    LEFT JOIN operational.seat_result sr ON c.candidacy_id = sr.candidacy_id
    WHERE c.election_id = %s AND c.organ_id = ({ORGAN_CM_SUBQUERY})
    GROUP BY COALESCE(p.party_acronym, co.coalition_acronym)
    HAVING SUM(vr.votes_obtained) > 1000
    ORDER BY total_votes DESC
    LIMIT 10
"""


PARTY_COLORS = [
    "#E91E63",
    "#2196F3",
    "#4CAF50",
    "#FF9800",
    "#9C27B0",
    "#00BCD4",
    "#FFEB3B",
    "#795548",
    "#607D8B",
    "#3F51B5",
]


def fetch_party_comparison_rows(
    db_config: Dict[str, str],
    election_id: int,
) -> List[Dict[str, Any]]:
    import psycopg2
    import psycopg2.extras

    conn = psycopg2.connect(**db_config)
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute("SET search_path TO operational, public")
            cur.execute(PARTY_COMPARISON_SQL, (election_id,))
            return [dict(row) for row in cur.fetchall()]
    finally:
        conn.close()


def fetch_election_year(db_config: Dict[str, str], election_id: int) -> Optional[int]:
    import psycopg2

    conn = psycopg2.connect(**db_config)
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT election_year FROM operational.election WHERE election_id = %s",
                (election_id,),
            )
            row = cur.fetchone()
            return row[0] if row else None
    finally:
        conn.close()


def render_party_bar_chart(
    rows: List[Dict[str, Any]],
    metric: str = "votes",
    election_year: Optional[int] = None,
) -> bytes:
    """
    Build a horizontal bar chart PNG from query rows.
    metric: 'votes' | 'seats'
    """
    if metric not in ("votes", "seats"):
        metric = "votes"

    if not rows:
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.text(0.5, 0.5, "No data", ha="center", va="center")
        ax.axis("off")
    else:
        parties = [str(r["party"]) for r in rows]
        if metric == "seats":
            values = [int(r["total_seats"]) for r in rows]
            xlabel = "Total seats (CM, all municipalities)"
            title_metric = "Seats by party"
        else:
            values = [int(r["total_votes"]) for r in rows]
            xlabel = "Total votes (CM, all municipalities)"
            title_metric = "Votes by party"

        colors = PARTY_COLORS[: len(parties)]
        fig, ax = plt.subplots(figsize=(9, max(4, len(parties) * 0.45)))
        bars = ax.barh(parties[::-1], values[::-1], color=colors[::-1])
        ax.set_xlabel(xlabel)
        year_suffix = f" — Autárquicas {election_year}" if election_year else ""
        ax.set_title(f"{title_metric}{year_suffix}")
        ax.bar_label(bars, padding=4, fmt="%d")
        fig.tight_layout()

    buf = io.BytesIO()
    fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return buf.read()


def write_chart_png(path: str, png_bytes: bytes) -> None:
    with open(path, "wb") as handle:
        handle.write(png_bytes)
