import os
from pathlib import Path
from dotenv import load_dotenv
from typing import Optional

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# Load .env file
load_dotenv(BASE_DIR / ".env")

# Nebius Token Factory Configuration
NEBIUS_API_KEY = os.getenv("NEBIUS_API_KEY", "").strip()
NEBIUS_BASE_URL = os.getenv(
    "NEBIUS_BASE_URL", "https://api.tokenfactory.us-central1.nebius.com/v1/"
).strip()
NEBIUS_MODEL = os.getenv(
    "NEBIUS_MODEL", "nvidia/Llama-3.1-Nemotron-70B-Instruct"
).strip()

# Database Path
DATABASE_PATH = os.getenv("DATABASE_PATH", str(BASE_DIR / "civicpulse.db")).strip()

# Supported Issue Categories
ISSUE_CATEGORIES = [
    "Roads & Footpaths",
    "Sanitation & Waste",
    "Streetlights & Electricity",
    "Water Supply",
    "Drainage & Flooding",
    "Public Safety",
    "Accessibility",
    "Other",
]

# Supported Urgency Levels
URGENCY_LEVELS = ["Low", "Medium", "High", "Critical"]

# Supported Case Statuses
CASE_STATUSES = ["Open", "In Progress", "Resolved"]

def is_nebius_configured(key: Optional[str] = None) -> bool:
    """Returns True if a non-placeholder Nebius API key is set."""
    check_key = key if key is not None else os.getenv("NEBIUS_API_KEY", NEBIUS_API_KEY)
    placeholder_keys = [
        "",
        "your_nebius_api_key_here",
        "your_api_key",
        "placeholder",
    ]
    return bool(check_key and check_key.strip() not in placeholder_keys)


def update_env_file(key: str, value: str) -> None:
    """Updates or adds an environment variable in the local .env file."""
    env_file = BASE_DIR / ".env"
    lines = []
    found = False
    prefix = f"{key}="

    if env_file.exists():
        with open(env_file, "r") as f:
            lines = f.readlines()
        for i, line in enumerate(lines):
            if line.strip().startswith(prefix):
                lines[i] = f"{key}={value}\n"
                found = True
                break
    if not found:
        lines.append(f"{key}={value}\n")

    with open(env_file, "w") as f:
        f.writelines(lines)
    os.environ[key] = value

# Pre-packaged Demo Scenarios for 1-click test in UI
DEMO_SCENARIOS = {
    "Pothole Near College Gate": {
        "title": "Severe deep pothole at main campus entrance gate",
        "category": "Roads & Footpaths",
        "location": "North Campus Gate 2, Ring Road Intersection",
        "description": (
            "A hazardous pothole approximately 3 feet wide and 6 inches deep has formed right outside "
            "the college pedestrian crossing. During monsoon rains, it fills completely with murky water, "
            "making it invisible to two-wheelers and cyclists. Yesterday, two students slipped on motorbikes. "
            "Traffic backs up daily for 200 meters as buses brake abruptly to avoid it."
        ),
        "observed_date": "2026-10-20",
    },
    "Overflowing Public Garbage Bin": {
        "title": "Overflowing municipal waste dumpster attracting strays & blocking sidewalk",
        "category": "Sanitation & Waste",
        "location": "Corner of 5th Avenue and Oak Street Market",
        "description": (
            "The community waste collection dumpster has not been emptied for over 5 days. Rotting organic waste "
            "has spilled across 15 meters of the public pedestrian walkway. Stray animals are scattering plastic waste, "
            "and a strong noxious odor has forced nearby fruit vendors and pedestrians into oncoming road traffic. "
            "Local residents report breeding mosquitoes and flies."
        ),
        "observed_date": "2026-10-21",
    },
    "Dark Streetlights on Pedestrian Walkway": {
        "title": "Continuous stretch of 6 unlit streetlights on student transit path",
        "category": "Streetlights & Electricity",
        "location": "University Metro Station to Girls Hostel Walkway (Path B)",
        "description": (
            "Six consecutive sodium-vapor streetlights along the 400-meter pedestrian pathway between the metro station "
            "and student housing have been pitch dark for two weeks. Several students returning from evening library sessions "
            "after 7 PM have reported feeling unsafe. Tree foliage completely blocks ambient light from adjacent buildings."
        ),
        "observed_date": "2026-10-18",
    },
}
