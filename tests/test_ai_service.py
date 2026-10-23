import json
import pytest
from unittest.mock import MagicMock, patch
from models.schemas import CaseInput, AIAnalysisResult
from services.nebius_client import (
    get_openai_client,
    verify_nebius_connection,
    NebiusMissingCredentialsError,
    NebiusClientError,
)
from services.case_analyzer import analyze_civic_case, _clean_json_response


def test_clean_json_response_raw():
    raw = '{"summary": "Test", "category": "Roads & Footpaths"}'
    assert _clean_json_response(raw) == raw


def test_clean_json_response_with_markdown_fences():
    fenced = """```json
{
  "summary": "Pothole hazard",
  "category": "Roads & Footpaths"
}
```"""
    cleaned = _clean_json_response(fenced)
    parsed = json.loads(cleaned)
    assert parsed["summary"] == "Pothole hazard"


def test_clean_json_response_with_surrounding_commentary():
    text = """Here is the structured analysis requested:
{
  "summary": "Water pipe leak",
  "urgency": "High"
}
Hope this helps!"""
    cleaned = _clean_json_response(text)
    parsed = json.loads(cleaned)
    assert parsed["summary"] == "Water pipe leak"
    assert parsed["urgency"] == "High"


def test_missing_credentials_raises_error():
    case_input = CaseInput(
        title="Fallen tree branch blocking street",
        description="A large tree branch snapped during the storm and is blocking both lanes.",
        location="Elm Street, Sector 2",
        category="Public Safety",
    )
    with pytest.raises(NebiusMissingCredentialsError):
        analyze_civic_case(case_input, api_key="", base_url="https://api.tokenfactory.us-central1.nebius.com/v1/")


def test_verify_nebius_connection_missing_key():
    res = verify_nebius_connection(api_key="")
    assert res["success"] is False
    assert res["error_type"] == "MissingCredentials"


@patch("services.case_analyzer.get_openai_client")
def test_successful_mocked_analysis(mock_get_client):
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = json.dumps({
        "summary": "Severe open manhole on pedestrian path.",
        "category": "Drainage & Flooding",
        "urgency": "Critical",
        "urgency_reasoning": "Direct fall and drowning danger for pedestrians.",
        "distinguished_facts": ["Manhole cover missing since yesterday"],
        "assumptions_made": ["No protective barricades or lights in place"],
        "missing_information": ["Depth of drainage chamber"],
        "recommended_next_steps": ["Erect emergency cones around opening"],
        "responsible_authority_type": "City Water and Sewerage Board",
        "complaint_letter": "Urgent complaint regarding missing manhole cover.",
        "evidence_checklist": ["Photo showing unbarricaded chamber"],
        "follow_up_checklist": ["Emergency desk escalation within 2 hours"],
        "confidence_assessment": "High confidence. Urgency is advisory.",
    })
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_completion.usage.prompt_tokens = 120
    mock_completion.usage.completion_tokens = 340
    mock_completion.usage.total_tokens = 460
    mock_client.chat.completions.create.return_value = mock_completion
    mock_get_client.return_value = mock_client

    case_input = CaseInput(
        title="Dangerous missing manhole cover on walking path",
        description="The metal lid is missing and leaves an open 10-foot vertical shaft.",
        location="Pedestrian path next to City Park",
        category="Drainage & Flooding",
    )

    result = analyze_civic_case(case_input, api_key="test_valid_key")
    assert result["success"] is True
    assert result["analysis"].urgency == "Critical"
    assert result["analysis"].responsible_authority_type == "City Water and Sewerage Board"
    assert result["usage"]["total_tokens"] == 460


@patch("services.case_analyzer.get_openai_client")
def test_malformed_json_handling(mock_get_client):
    mock_client = MagicMock()
    mock_choice = MagicMock()
    mock_choice.message.content = "This is not JSON at all."
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    mock_client.chat.completions.create.return_value = mock_completion
    mock_get_client.return_value = mock_client

    case_input = CaseInput(
        title="Water leak in street",
        description="Water is gushing out of broken valve on 5th Cross Road.",
        location="5th Cross",
        category="Water Supply",
    )

    with pytest.raises(NebiusClientError) as exc_info:
        analyze_civic_case(case_input, api_key="test_key")
    assert "Invalid JSON format" in str(exc_info.value) or "invalid JSON" in str(exc_info.value)


def test_is_nebius_configured_helper():
    from config import is_nebius_configured
    assert is_nebius_configured("real_valid_key_123") is True
    assert is_nebius_configured("") is False
    assert is_nebius_configured("your_nebius_api_key_here") is False
    assert is_nebius_configured("placeholder") is False


def test_update_env_file(tmp_path, monkeypatch):
    import config
    fake_env = tmp_path / ".env"
    monkeypatch.setattr(config, "BASE_DIR", tmp_path)
    config.update_env_file("TEST_NEBIUS_KEY", "secret_123")

    content = fake_env.read_text()
    assert "TEST_NEBIUS_KEY=secret_123" in content

