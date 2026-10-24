import pytest
from pydantic import ValidationError
from models.schemas import CaseInput, AIAnalysisResult, CaseNote, CaseRecord


def test_valid_case_input():
    case = CaseInput(
        title="Massive crater pothole on Main Street",
        description="A 4-foot wide pothole is causing hazardous traffic slowdowns and bicycle accidents.",
        location="Corner of 4th Ave and Elm St",
        category="Roads & Footpaths",
    )
    assert case.title == "Massive crater pothole on Main Street"
    assert case.category == "Roads & Footpaths"
    assert case.photo_path is None


def test_invalid_short_title():
    with pytest.raises(ValidationError):
        CaseInput(
            title="Pit",
            description="A very detailed description of the road surface issue that has plenty of length.",
            location="Main Gate",
            category="Roads & Footpaths",
        )


def test_invalid_short_description():
    with pytest.raises(ValidationError):
        CaseInput(
            title="Dangerous exposed electrical wires",
            description="Too short",
            location="Campus Quad",
            category="Streetlights & Electricity",
        )


def test_invalid_short_location():
    with pytest.raises(ValidationError):
        CaseInput(
            title="Dangerous exposed electrical wires",
            description="Wires are hanging down low from the lamppost across the walkway.",
            location="X",
            category="Streetlights & Electricity",
        )


def test_valid_ai_analysis_result():
    analysis = AIAnalysisResult(
        summary="Exposed high-voltage wire hanging near pedestrian path.",
        category="Streetlights & Electricity",
        urgency="Critical",
        urgency_reasoning="Direct life-safety electrocution hazard in pedestrian thoroughfare.",
        distinguished_facts=["Wire hanging 5 feet off the ground"],
        assumptions_made=["Line is active and energized"],
        missing_information=["Utility pole serial number"],
        recommended_next_steps=["Cordon off area immediately"],
        responsible_authority_type="City Electricity Board",
        complaint_letter="Dear Electricity Board, please fix wire immediately.",
        evidence_checklist=["Photos from safe distance"],
        follow_up_checklist=["Emergency helpline call in 1 hour"],
        confidence_assessment="High confidence based on stated electrical danger. Urgency is advisory.",
    )
    assert analysis.urgency == "Critical"
    assert len(analysis.distinguished_facts) == 1


def test_invalid_urgency_value():
    with pytest.raises(ValidationError):
        AIAnalysisResult(
            summary="Broken bench in park",
            category="Other",
            urgency="SuperUrgent",  # Invalid, must be Low, Medium, High, or Critical
            urgency_reasoning="Needs repair.",
            responsible_authority_type="Parks Department",
            complaint_letter="Dear Parks...",
            confidence_assessment="Advisory only.",
        )


def test_missing_required_ai_fields():
    with pytest.raises(ValidationError):
        # Missing complaint_letter and summary
        AIAnalysisResult(
            category="Roads & Footpaths",
            urgency="Medium",
            urgency_reasoning="Pothole needs fix.",
            responsible_authority_type="Public Works",
            confidence_assessment="Advisory.",
        )


def test_create_unavailable_analysis():
    from models.schemas import create_unavailable_analysis
    fallback = create_unavailable_analysis(category="Sanitation & Waste", urgency="High")
    assert fallback.category == "Sanitation & Waste"
    assert fallback.urgency == "High"
    assert "without real-time AI analysis" in fallback.summary
    assert "Manual submission" in fallback.confidence_assessment


def test_case_input_with_user_urgency():
    case = CaseInput(
        title="Open excavation on footway",
        description="Contractors dug a 5ft deep trench and left it uncovered overnight.",
        location="Corner of 3rd Street",
        category="Roads & Footpaths",
        user_urgency="High",
    )
    assert case.user_urgency == "High"


def test_closed_status_valid_in_case_record():
    from models.schemas import CaseRecord, create_unavailable_analysis
    record = CaseRecord(
        case_number="CP-2026-TEST01",
        title="Repaired water leak",
        description="Water pipe repaired by municipal engineering team.",
        location="Sector 1",
        category="Water Supply",
        status="Closed",
        urgency="Low",
        ai_analysis=create_unavailable_analysis("Water Supply", "Low"),
        created_at="2026-10-24 10:00:00",
        updated_at="2026-10-24 12:00:00",
        model_used="Manual Offline",
    )
    assert record.status == "Closed"
