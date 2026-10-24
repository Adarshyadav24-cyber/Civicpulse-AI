import os
import pytest
from pathlib import Path
from models.schemas import AIAnalysisResult
from database.repository import (
    init_db,
    create_case,
    get_case_by_id,
    get_all_cases,
    update_case_status,
    add_case_note,
    delete_case,
    get_case_statistics,
    export_case_to_markdown,
)


@pytest.fixture
def test_db(tmp_path):
    db_file = str(tmp_path / "test_civicpulse.db")
    init_db(db_file)
    return db_file


@pytest.fixture
def sample_analysis():
    return AIAnalysisResult(
        summary="Clogged storm drain causing severe road flooding during rain.",
        category="Drainage & Flooding",
        urgency="High",
        urgency_reasoning="Waterlogging threatens pedestrian access and damages road base.",
        distinguished_facts=["Drain completely blocked with silt and debris"],
        assumptions_made=["Monsoon runoff will flood nearby shops"],
        missing_information=["Ward storm drain diameter"],
        recommended_next_steps=["Dispatch desilting suction truck"],
        responsible_authority_type="City Municipal Drainage Department",
        complaint_letter="Dear Drainage Dept, please clear the clogged drain on 10th Cross.",
        evidence_checklist=["Photos of standing water depth"],
        follow_up_checklist=["Check status after 48 hours"],
        confidence_assessment="High confidence. Advisory recommendation.",
    )


def test_create_and_retrieve_case(test_db, sample_analysis):
    case = create_case(
        title="Severe storm drain flooding on 10th Cross",
        description="Every rainfall brings 1 foot of standing water because the main drain inlet is blocked.",
        location="10th Cross, Indiranagar",
        category="Drainage & Flooding",
        ai_analysis=sample_analysis,
        model_used="nvidia/Llama-3.1-Nemotron-70B-Instruct",
        db_path=test_db,
    )

    assert case.id is not None
    assert case.case_number.startswith("CP-2026-")
    assert case.status == "Open"
    assert case.urgency == "High"

    fetched = get_case_by_id(case.id, db_path=test_db)
    assert fetched is not None
    assert fetched.title == case.title
    assert fetched.ai_analysis.responsible_authority_type == "City Municipal Drainage Department"


def test_update_case_status(test_db, sample_analysis):
    case = create_case(
        title="Broken streetlight",
        description="Streetlight has been flickering and completely turned off for three nights.",
        location="Sector 7 Park",
        category="Streetlights & Electricity",
        ai_analysis=sample_analysis,
        model_used="nvidia/Llama-3.1-Nemotron-70B-Instruct",
        db_path=test_db,
    )

    success = update_case_status(case.id, "In Progress", db_path=test_db)
    assert success is True

    updated = get_case_by_id(case.id, db_path=test_db)
    assert updated.status == "In Progress"

    update_case_status(case.id, "Resolved", db_path=test_db)
    resolved = get_case_by_id(case.id, db_path=test_db)
    assert resolved.status == "Resolved"


def test_add_case_notes(test_db, sample_analysis):
    case = create_case(
        title="Illegal debris dumping on sidewalk",
        description="Construction contractor dumped 3 truckloads of concrete rubble onto public walkway.",
        location="Ring Road near Metro Pillar 142",
        category="Sanitation & Waste",
        ai_analysis=sample_analysis,
        model_used="nvidia/Llama-3.1-Nemotron-70B-Instruct",
        db_path=test_db,
    )

    add_case_note(case.id, "Community Lead", "Grievance ticket #7789 registered with ward officer.", db_path=test_db)
    add_case_note(case.id, "Ward Officer", "Inspection scheduled for tomorrow morning.", db_path=test_db)

    fetched = get_case_by_id(case.id, db_path=test_db)
    assert len(fetched.notes) == 2
    assert fetched.notes[0].author == "Community Lead"
    assert fetched.notes[1].author == "Ward Officer"


def test_filtering_and_search(test_db, sample_analysis):
    create_case(
        title="Sanitation overflow near market",
        description="Garbage bin overflowing with organic waste near fruit vendors.",
        location="City Market Gate 1",
        category="Sanitation & Waste",
        ai_analysis=sample_analysis,
        model_used="nvidia/Llama-3.1-Nemotron-70B-Instruct",
        db_path=test_db,
    )

    # Filter by category
    waste_cases = get_all_cases(db_path=test_db, category_filter="Sanitation & Waste")
    assert len(waste_cases) == 1

    road_cases = get_all_cases(db_path=test_db, category_filter="Roads & Footpaths")
    assert len(road_cases) == 0

    # Search keyword
    search_res = get_all_cases(db_path=test_db, search_query="Market")
    assert len(search_res) == 1

    search_empty = get_all_cases(db_path=test_db, search_query="NonExistentTermXYZ")
    assert len(search_empty) == 0


def test_delete_case(test_db, sample_analysis):
    case = create_case(
        title="Temporary road closure warning missing",
        description="Work ongoing without required road signs or barricades.",
        location="Bridge approach",
        category="Public Safety",
        ai_analysis=sample_analysis,
        model_used="nvidia/Llama-3.1-Nemotron-70B-Instruct",
        db_path=test_db,
    )

    deleted = delete_case(case.id, db_path=test_db)
    assert deleted is True

    fetched = get_case_by_id(case.id, db_path=test_db)
    assert fetched is None


def test_statistics_aggregation(test_db, sample_analysis):
    create_case(
        title="Issue 1",
        description="First issue description with sufficient length.",
        location="Loc 1",
        category="Roads & Footpaths",
        ai_analysis=sample_analysis,
        model_used="nvidia/Llama-3.1-Nemotron-70B-Instruct",
        db_path=test_db,
    )
    stats = get_case_statistics(db_path=test_db)
    assert stats["total"] == 1
    assert stats["open"] == 1
    assert stats["resolved"] == 0


def test_markdown_export(test_db, sample_analysis):
    case = create_case(
        title="Export Test Case",
        description="Testing markdown generation with full complaint draft.",
        location="Main Square",
        category="Roads & Footpaths",
        ai_analysis=sample_analysis,
        model_used="nvidia/Llama-3.1-Nemotron-70B-Instruct",
        db_path=test_db,
    )

    md = export_case_to_markdown(case)
    assert case.case_number in md
    assert "Official Complaint Draft" in md
    assert sample_analysis.responsible_authority_type in md
    assert "Evidence Checklist" in md


def test_closed_status_and_activity_logging(test_db, sample_analysis):
    case = create_case(
        title="Pothole repair lifecycle",
        description="Pothole that goes from open to in progress, resolved, then closed.",
        location="7th Main Road",
        category="Roads & Footpaths",
        ai_analysis=sample_analysis,
        model_used="nvidia/Llama-3.1-Nemotron-70B-Instruct",
        db_path=test_db,
    )

    # Transition to In Progress with activity note
    update_case_status(case.id, "In Progress", author="Municipal Staff", activity_note="Team deployed", db_path=test_db)
    # Transition to Resolved
    update_case_status(case.id, "Resolved", author="Field Inspector", activity_note="Asphalt laid", db_path=test_db)
    # Transition to Closed
    update_case_status(case.id, "Closed", author="Admin", activity_note="Verified with citizen", db_path=test_db)

    updated = get_case_by_id(case.id, db_path=test_db)
    assert updated.status == "Closed"
    assert len(updated.notes) == 3
    assert "Status changed from 'Open' to 'In Progress'" in updated.notes[0].content
    assert "Status changed from 'Resolved' to 'Closed'" in updated.notes[2].content


def test_high_priority_statistics(test_db, sample_analysis):
    create_case(
        title="High urgency hazard",
        description="Live electrical wire spark causing fire risk.",
        location="Sector 4",
        category="Streetlights & Electricity",
        ai_analysis=sample_analysis,  # urgency is "High"
        model_used="nvidia/Llama-3.1-Nemotron-70B-Instruct",
        db_path=test_db,
    )
    stats = get_case_statistics(db_path=test_db)
    assert stats["high_priority"] >= 1
    assert "closed" in stats


def test_get_community_insights(test_db, sample_analysis):
    from database.repository import get_community_insights
    # Empty DB insights check
    empty_insights = get_community_insights(db_path=test_db + "_empty")
    assert empty_insights["total_cases"] == 0

    create_case(
        title="Water pipeline rupture",
        description="Drinking water pipe burst flooding road and walkway.",
        location="Indiranagar 100ft Road",
        category="Water Supply",
        ai_analysis=sample_analysis,
        model_used="nvidia/Llama-3.1-Nemotron-70B-Instruct",
        db_path=test_db,
    )

    insights = get_community_insights(db_path=test_db)
    assert insights["total_cases"] >= 1
    assert len(insights["category_distribution"]) >= 1
    assert len(insights["hotspot_areas"]) >= 1


def test_duplicate_case_detection(test_db, sample_analysis):
    from database.repository import check_duplicate_case
    title = "Clogged drain flooding gate"
    loc = "North Campus Gate 2"

    assert check_duplicate_case(title, loc, db_path=test_db) is None

    create_case(
        title=title,
        description="Drain has been completely blocked for two days.",
        location=loc,
        category="Drainage & Flooding",
        ai_analysis=sample_analysis,
        model_used="nvidia/Llama-3.1-Nemotron-70B-Instruct",
        db_path=test_db,
    )

    dup = check_duplicate_case(title, loc, db_path=test_db)
    assert dup is not None
    assert dup.title == title
