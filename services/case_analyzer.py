import json
import re
from typing import Dict, Any, Optional
from openai import OpenAI

from models.schemas import AIAnalysisResult, CaseInput
from services.nebius_client import get_openai_client, NebiusClientError, NebiusMissingCredentialsError
from config import NEBIUS_MODEL


SYSTEM_PROMPT = """You are CivicPulse AI, an expert Senior Civic Infrastructure & Public Policy Case Analyst.
Your duty is to transform unstructured citizen reports into structured, actionable civic case plans.

MANDATORY RULES:
1. Distinguish user-provided facts from your own assumptions or inferences.
2. Treat urgency as an ADVISORY RECOMMENDATION based on safety, health hazards, and disruption, NOT as an official governmental decision.
3. Suggest responsible AUTHORITY TYPES (e.g., "Municipal Roads & Infrastructure Maintenance Division", "State Electricity Distribution Corporation", "City Public Health Department") and NEVER invent fictional individual official names or fake contact numbers.
4. If details are missing (e.g., exact dimensions, municipal ward number, duration, water pipe material), explicitly list them in missing_information.
5. Provide a formal, respectful, and authoritative complaint letter that a resident or student can immediately copy and submit to the grievance portal.
6. Return your entire response strictly as a single valid JSON object with the following schema:

{
  "summary": "1-2 sentence executive overview of the civic issue",
  "category": "Roads & Footpaths | Sanitation & Waste | Streetlights & Electricity | Water Supply | Drainage & Flooding | Public Safety | Accessibility | Other",
  "urgency": "Low" | "Medium" | "High" | "Critical",
  "urgency_reasoning": "Clear factual reasoning for the urgency classification",
  "distinguished_facts": ["Directly stated fact 1", "Directly stated fact 2"],
  "assumptions_made": ["Contextual risk assumption 1", "Inferred consequence 2"],
  "missing_information": ["Missing detail 1", "Missing detail 2"],
  "recommended_next_steps": ["Step 1", "Step 2", "Step 3"],
  "responsible_authority_type": "Institutional authority category",
  "complaint_letter": "Complete professional formal complaint letter with citizen placeholders [Your Name], [Contact Info]",
  "evidence_checklist": ["Checklist item 1", "Checklist item 2"],
  "follow_up_checklist": ["Follow-up timeline item 1", "Follow-up timeline item 2"],
  "confidence_assessment": "Clear explanation of model confidence, limitations of provided report, and explicit reminder that urgency is advisory"
}

Do not include any conversational filler, markdown code block wrappers (unless necessary), or explanation outside the JSON object.
"""


def _clean_json_response(raw_text: str) -> str:
    """Strips Markdown fences and extracts clean JSON object string."""
    cleaned = raw_text.strip()
    if cleaned.startswith("```json"):
        cleaned = cleaned[7:]
    elif cleaned.startswith("```"):
        cleaned = cleaned[3:]
    if cleaned.endswith("```"):
        cleaned = cleaned[:-3]
    cleaned = cleaned.strip()

    # If extra text precedes or follows the first { and last }, slice between them
    first_brace = cleaned.find("{")
    last_brace = cleaned.rfind("}")
    if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
        cleaned = cleaned[first_brace : last_brace + 1]

    return cleaned


def analyze_civic_case(
    case_input: CaseInput,
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Submits the civic report to Nebius Token Factory for analysis using NVIDIA Nemotron.
    Validates output against Pydantic schema AIAnalysisResult.
    """
    target_model = model or NEBIUS_MODEL
    client = get_openai_client(api_key=api_key, base_url=base_url)

    user_prompt = f"""Analyze the following civic issue report:

TITLE: {case_input.title}
CATEGORY: {case_input.category}
LOCATION: {case_input.location}
DATE OBSERVED: {case_input.observed_date or "Recent / Unspecified"}
EVIDENCE PHOTO ATTACHED: {"Yes (stored locally as evidence)" if case_input.photo_path else "No photo attached"}

DETAILED DESCRIPTION:
{case_input.description}

Analyze this situation thoroughly and output the complete JSON object according to the system instructions.
"""

    try:
        response = client.chat.completions.create(
            model=target_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.2,
            max_tokens=2500,
        )

        content = response.choices[0].message.content or ""
        cleaned_json = _clean_json_response(content)

        # Explicitly validate JSON syntax first
        try:
            parsed_dict = json.loads(cleaned_json)
        except json.JSONDecodeError as jde:
            raise NebiusClientError(
                f"Model returned invalid JSON format: {str(jde)}. Raw snippet: {content[:150]}"
            )

        # Validate schema with Pydantic
        analysis_result = AIAnalysisResult.model_validate(parsed_dict)

        return {
            "success": True,
            "analysis": analysis_result,
            "raw_response": content,
            "model_used": target_model,
            "usage": {
                "prompt_tokens": getattr(response.usage, "prompt_tokens", 0) if response.usage else 0,
                "completion_tokens": getattr(response.usage, "completion_tokens", 0) if response.usage else 0,
                "total_tokens": getattr(response.usage, "total_tokens", 0) if response.usage else 0,
            },
        }

    except json.JSONDecodeError as jde:
        raise NebiusClientError(
            f"Model returned invalid JSON format: {str(jde)}. Raw output snippet: {content[:200]}"
        )
    except Exception as e:
        if isinstance(e, (NebiusMissingCredentialsError, NebiusClientError)):
            raise e
        err_str = str(e)
        if api_key and len(api_key) > 4:
            err_str = err_str.replace(api_key, "[REDACTED_API_KEY]")
        raise NebiusClientError(f"Inference request to Nebius Token Factory failed: {err_str}")
