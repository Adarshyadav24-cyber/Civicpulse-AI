import sqlite3
import json
import uuid
from datetime import datetime
from typing import List, Optional, Dict, Any
from pathlib import Path

from models.schemas import CaseRecord, AIAnalysisResult, CaseNote
from config import DATABASE_PATH, DEMO_SCENARIOS


def get_db_connection(db_path: str = DATABASE_PATH) -> sqlite3.Connection:
    """Creates a sqlite3 connection with dict-like row access."""
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = DATABASE_PATH) -> None:
    """Initializes SQLite database tables with proper indexing."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS cases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_number TEXT UNIQUE NOT NULL,
            title TEXT NOT NULL,
            description TEXT NOT NULL,
            location TEXT NOT NULL,
            category TEXT NOT NULL,
            photo_path TEXT,
            observed_date TEXT,
            status TEXT NOT NULL DEFAULT 'Open',
            urgency TEXT NOT NULL DEFAULT 'Medium',
            ai_analysis_json TEXT NOT NULL,
            model_used TEXT NOT NULL,
            is_demo INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS case_notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            case_id INTEGER NOT NULL,
            timestamp TEXT NOT NULL,
            author TEXT NOT NULL,
            content TEXT NOT NULL,
            FOREIGN KEY (case_id) REFERENCES cases (id) ON DELETE CASCADE
        )
        """
    )

    # Indices for high-performance searching and filtering
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_category ON cases(category)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_urgency ON cases(urgency)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_status ON cases(status)")
    cursor.execute("CREATE INDEX IF NOT EXISTS idx_cases_case_number ON cases(case_number)")

    conn.commit()
    conn.close()


def generate_case_number() -> str:
    """Generates a memorable, unique civic case identifier e.g. CP-2026-A1B2."""
    short_uuid = uuid.uuid4().hex[:6].upper()
    return f"CP-2026-{short_uuid}"


def create_case(
    title: str,
    description: str,
    location: str,
    category: str,
    ai_analysis: AIAnalysisResult,
    model_used: str,
    photo_path: Optional[str] = None,
    observed_date: Optional[str] = None,
    is_demo: bool = False,
    db_path: str = DATABASE_PATH,
) -> CaseRecord:
    """Inserts a new analyzed case into the database and returns the CaseRecord."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    case_number = generate_case_number()
    urgency = ai_analysis.urgency

    cursor.execute(
        """
        INSERT INTO cases (
            case_number, title, description, location, category,
            photo_path, observed_date, status, urgency,
            ai_analysis_json, model_used, is_demo, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Open', ?, ?, ?, ?, ?, ?)
        """,
        (
            case_number,
            title,
            description,
            location,
            category,
            photo_path,
            observed_date,
            urgency,
            ai_analysis.model_dump_json(),
            model_used,
            1 if is_demo else 0,
            now,
            now,
        ),
    )

    case_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return CaseRecord(
        id=case_id,
        case_number=case_number,
        title=title,
        description=description,
        location=location,
        category=category,
        photo_path=photo_path,
        observed_date=observed_date,
        status="Open",
        urgency=urgency,
        ai_analysis=ai_analysis,
        notes=[],
        created_at=now,
        updated_at=now,
        model_used=model_used,
        is_demo=is_demo,
    )


def _row_to_case_record(row: sqlite3.Row, notes: List[CaseNote] = None) -> CaseRecord:
    """Converts a database row to a validated CaseRecord."""
    ai_data = json.loads(row["ai_analysis_json"])
    ai_analysis = AIAnalysisResult(**ai_data)

    return CaseRecord(
        id=row["id"],
        case_number=row["case_number"],
        title=row["title"],
        description=row["description"],
        location=row["location"],
        category=row["category"],
        photo_path=row["photo_path"],
        observed_date=row["observed_date"],
        status=row["status"],
        urgency=row["urgency"],
        ai_analysis=ai_analysis,
        notes=notes or [],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
        model_used=row["model_used"],
        is_demo=bool(row["is_demo"]),
    )


def get_case_notes(case_id: int, db_path: str = DATABASE_PATH) -> List[CaseNote]:
    """Retrieves all chronological notes for a given case."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "SELECT timestamp, author, content FROM case_notes WHERE case_id = ? ORDER BY id ASC",
        (case_id,),
    )
    rows = cursor.fetchall()
    conn.close()

    return [
        CaseNote(
            timestamp=r["timestamp"],
            author=r["author"],
            content=r["content"],
        )
        for r in rows
    ]


def get_case_by_id(case_id: int, db_path: str = DATABASE_PATH) -> Optional[CaseRecord]:
    """Retrieves a single case record by ID with attached notes."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM cases WHERE id = ?", (case_id,))
    row = cursor.fetchone()
    conn.close()

    if not row:
        return None

    notes = get_case_notes(case_id, db_path)
    return _row_to_case_record(row, notes)


def get_all_cases(
    db_path: str = DATABASE_PATH,
    category_filter: Optional[str] = None,
    urgency_filter: Optional[str] = None,
    status_filter: Optional[str] = None,
    search_query: Optional[str] = None,
) -> List[CaseRecord]:
    """Queries cases with flexible filters and text search."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    query = "SELECT * FROM cases WHERE 1=1"
    params: List[Any] = []

    if category_filter and category_filter != "All":
        query += " AND category = ?"
        params.append(category_filter)

    if urgency_filter and urgency_filter != "All":
        query += " AND urgency = ?"
        params.append(urgency_filter)

    if status_filter and status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)

    if search_query and search_query.strip():
        term = f"%{search_query.strip()}%"
        query += " AND (title LIKE ? OR description LIKE ? OR location LIKE ? OR case_number LIKE ?)"
        params.extend([term, term, term, term])

    query += " ORDER BY id DESC"

    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()

    cases = []
    for r in rows:
        notes = get_case_notes(r["id"], db_path)
        cases.append(_row_to_case_record(r, notes))
    return cases


def update_case_status(
    case_id: int, new_status: str, db_path: str = DATABASE_PATH
) -> bool:
    """Updates the workflow status of a case."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE cases SET status = ?, updated_at = ? WHERE id = ?",
        (new_status, now, case_id),
    )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def add_case_note(
    case_id: int, author: str, content: str, db_path: str = DATABASE_PATH
) -> bool:
    """Appends an update note to the case history."""
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO case_notes (case_id, timestamp, author, content) VALUES (?, ?, ?, ?)",
        (case_id, now, author.strip(), content.strip()),
    )
    cursor.execute(
        "UPDATE cases SET updated_at = ? WHERE id = ?",
        (now, case_id),
    )
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def delete_case(case_id: int, db_path: str = DATABASE_PATH) -> bool:
    """Deletes a case and cascading notes from SQLite."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()
    cursor.execute("DELETE FROM case_notes WHERE case_id = ?", (case_id,))
    cursor.execute("DELETE FROM cases WHERE id = ?", (case_id,))
    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def get_case_statistics(db_path: str = DATABASE_PATH) -> Dict[str, Any]:
    """Computes aggregate analytics for dashboard presentation."""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute("SELECT COUNT(*) FROM cases")
    total_cases = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM cases WHERE status = 'Open'")
    open_cases = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM cases WHERE status = 'In Progress'")
    in_progress_cases = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM cases WHERE status = 'Resolved'")
    resolved_cases = cursor.fetchone()[0]

    cursor.execute("SELECT COUNT(*) FROM cases WHERE is_demo = 1")
    demo_cases_count = cursor.fetchone()[0]

    cursor.execute("SELECT category, COUNT(*) as count FROM cases GROUP BY category")
    category_counts = {r["category"]: r["count"] for r in cursor.fetchall()}

    cursor.execute("SELECT urgency, COUNT(*) as count FROM cases GROUP BY urgency")
    urgency_counts = {r["urgency"]: r["count"] for r in cursor.fetchall()}

    conn.close()

    return {
        "total": total_cases,
        "open": open_cases,
        "in_progress": in_progress_cases,
        "resolved": resolved_cases,
        "category_counts": category_counts,
        "urgency_counts": urgency_counts,
        "demo_count": demo_cases_count,
        "user_count": total_cases - demo_cases_count,
        "is_all_demo": (total_cases > 0 and total_cases == demo_cases_count),
    }


def export_case_to_markdown(case: CaseRecord) -> str:
    """Formats a case and its AI generated case plan into clean markdown."""
    ai = case.ai_analysis
    notes_section = ""
    if case.notes:
        notes_section = "### Case History & Follow-up Notes\n" + "\n".join(
            f"- **[{n.timestamp}] {n.author}**: {n.content}" for n in case.notes
        ) + "\n\n"

    facts_list = "\n".join(f"- {f}" for f in ai.distinguished_facts)
    assumptions_list = "\n".join(f"- {a}" for a in ai.assumptions_made)
    missing_list = "\n".join(f"- [ ] {m}" for m in ai.missing_information)
    steps_list = "\n".join(f"1. {s}" for s in ai.recommended_next_steps)
    evidence_list = "\n".join(f"- [ ] {e}" for e in ai.evidence_checklist)
    followup_list = "\n".join(f"- [ ] {f}" for f in ai.follow_up_checklist)

    doc = f"""# CivicPulse AI - Official Case Action Plan
**Case Number:** {case.case_number}
**Status:** {case.status} | **Recommended Urgency:** {case.urgency}
**Created At:** {case.created_at} | **Model:** {case.model_used}
{"*(Sample Demo Case)*" if case.is_demo else "*(User Community Report)*"}

---

## 1. Issue Overview
- **Title:** {case.title}
- **Category:** {case.category}
- **Location:** {case.location}
- **Observed Date:** {case.observed_date or "Not specified"}

### Detailed Description
{case.description}

---

## 2. AI Executive Assessment
**Summary:** {ai.summary}

**Target Authority Type:** {ai.responsible_authority_type}

**Urgency Rationale:**
{ai.urgency_reasoning}

**Confidence & Advisory Notice:**
{ai.confidence_assessment}

---

## 3. Fact vs. Assumption Separation
### Factual Observations from Report:
{facts_list if facts_list else "- (None directly specified)"}

### Inferred Assumptions & Impact Risks:
{assumptions_list if assumptions_list else "- (Standard baseline impact)"}

---

## 4. Missing Information Needed
{missing_list if missing_list else "- No critical missing details identified."}

---

## 5. Recommended Action Steps
{steps_list}

---

## 6. Official Complaint Draft
```text
{ai.complaint_letter}
```

---

## 7. Action Checklists
### Evidence Checklist
{evidence_list}

### Follow-Up Checklist
{followup_list}

---

{notes_section}
*Generated by CivicPulse AI powered by NVIDIA Nemotron on Nebius Token Factory.*
*Advisory Disclaimer: Urgency and jurisdiction are algorithmic recommendations designed for citizen empowerment and do not constitute an official governmental determination.*
"""
    return doc.strip()
