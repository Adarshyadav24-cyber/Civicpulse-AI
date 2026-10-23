import os
from typing import Dict, Any, List, Optional
from openai import OpenAI
from config import NEBIUS_API_KEY, NEBIUS_BASE_URL, NEBIUS_MODEL, is_nebius_configured


class NebiusClientError(Exception):
    """Custom exception for Nebius Token Factory communication issues."""
    pass


class NebiusMissingCredentialsError(NebiusClientError):
    """Raised when the NEBIUS_API_KEY is not configured or is a placeholder."""
    pass


def get_openai_client(api_key: Optional[str] = None, base_url: Optional[str] = None) -> OpenAI:
    """
    Initializes and returns an official OpenAI client pointed at Nebius Token Factory.
    Does not log or expose raw credentials.
    """
    key = (api_key if api_key is not None else NEBIUS_API_KEY).strip()
    url = (base_url if base_url is not None else NEBIUS_BASE_URL).strip()

    if not key or key in ["your_nebius_api_key_here", "your_api_key", "placeholder"]:
        raise NebiusMissingCredentialsError(
            "NEBIUS_API_KEY is missing or contains a placeholder value. "
            "Please configure your real API key in .env or via the application settings."
        )

    return OpenAI(
        api_key=key,
        base_url=url,
        timeout=60.0,
        max_retries=2,
    )


def verify_nebius_connection(
    api_key: Optional[str] = None,
    base_url: Optional[str] = None,
    model: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Verifies actual connectivity to the Nebius Token Factory API by querying available models.
    Does NOT fabricate responses. Returns real verification telemetry.
    """
    target_model = model or NEBIUS_MODEL
    key = (api_key if api_key is not None else NEBIUS_API_KEY).strip()
    url = (base_url if base_url is not None else NEBIUS_BASE_URL).strip()

    if not key or key in ["your_nebius_api_key_here", "your_api_key", "placeholder"]:
        return {
            "success": False,
            "connected": False,
            "configured_model": target_model,
            "available_models": [],
            "error_type": "MissingCredentials",
            "message": "Nebius API key is not configured. Set NEBIUS_API_KEY in your .env file or Settings panel.",
        }

    try:
        client = get_openai_client(api_key=key, base_url=url)
        models_page = client.models.list()
        available_ids = [m.id for m in models_page.data] if hasattr(models_page, "data") else []

        model_present = target_model in available_ids or any(
            target_model.lower() in m_id.lower() for m_id in available_ids
        )

        return {
            "success": True,
            "connected": True,
            "endpoint": url,
            "configured_model": target_model,
            "model_present": model_present,
            "available_models": available_ids,
            "message": f"Successfully connected to Nebius Token Factory. Found {len(available_ids)} models.",
        }
    except Exception as e:
        error_msg = str(e)
        return {
            "success": False,
            "connected": False,
            "configured_model": target_model,
            "available_models": [],
            "error_type": type(e).__name__,
            "message": f"Nebius API connection failed: {error_msg}",
        }
