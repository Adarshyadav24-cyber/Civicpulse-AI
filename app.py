import streamlit as st
import os
import json
from pathlib import Path
from datetime import datetime, date
import pandas as pd
import altair as alt

from config import (
    BASE_DIR,
    NEBIUS_API_KEY,
    NEBIUS_BASE_URL,
    NEBIUS_MODEL,
    ISSUE_CATEGORIES,
    URGENCY_LEVELS,
    CASE_STATUSES,
    DEMO_SCENARIOS,
    is_nebius_configured,
    update_env_file,
)
from models.schemas import CaseInput, AIAnalysisResult

try:
    from models.schemas import create_unavailable_analysis
except ImportError:
    def create_unavailable_analysis(category: str, urgency: str = "Medium") -> AIAnalysisResult:
        valid_urgency = urgency if urgency in ["Low", "Medium", "High", "Critical"] else "Medium"
        return AIAnalysisResult(
            summary="Case logged directly by citizen without real-time AI analysis.",
            category=category,
            urgency=valid_urgency,  # type: ignore
            urgency_reasoning="Direct user-specified urgency. Live AI triage was unavailable at submission time.",
            distinguished_facts=["Directly recorded by resident via community submission."],
            assumptions_made=["Pending automated AI analysis upon next service availability."],
            missing_information=["Awaiting municipal inspection or resident follow-up details."],
            recommended_next_steps=[
                "Submit report reference number to local municipal ward office.",
                "Gather additional timestamped photos or witness statements.",
                "Check case progress after 3-5 business days."
            ],
            responsible_authority_type="Municipal Grievance Cell",
            complaint_letter="Dear Municipal Authority,\n\nPlease register this citizen complaint for priority inspection and resolution.",
            evidence_checklist=["Timestamped photographs of the incident site", "Landmark or GPS coordinates"],
            follow_up_checklist=["Check status after 3-5 business days", "Escalate if no inspection is scheduled"],
            confidence_assessment="Manual submission - no AI analysis was performed for this case.",
        )
from database.repository import (
    init_db,
    create_case,
    get_all_cases,
    get_case_by_id,
    update_case_status,
    add_case_note,
    delete_case,
    get_case_statistics,
    get_community_insights,
    check_duplicate_case,
    export_case_to_markdown,
)
from services.nebius_client import (
    verify_nebius_connection,
    NebiusMissingCredentialsError,
    NebiusClientError,
)
from services.case_analyzer import analyze_civic_case

# Set Streamlit page configuration
st.set_page_config(
    page_title="CivicPulse AI — Citizen Infrastructure Action Platform",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize database schema
init_db()

# Ensure uploads directory exists
UPLOADS_DIR = BASE_DIR / "uploads"
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Load CSS Design System
css_file = BASE_DIR / "assets" / "style.css"
if css_file.exists():
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Seed initial demo cases on first run if database is empty
def seed_demo_cases():
    stats = get_case_statistics()
    if stats["total"] == 0:
        demo_1 = AIAnalysisResult(
            summary="Dangerous deep pothole obstructing college entrance gate and causing frequent two-wheeler accidents.",
            category="Roads & Footpaths",
            urgency="High",
            urgency_reasoning="Immediate physical safety hazard situated at a pedestrian crossing with documented recent vehicle accidents.",
            distinguished_facts=[
                "Pothole is approximately 3 ft wide and 6 inches deep",
                "Located right outside North Campus Gate 2",
                "Two student motorbike accidents observed yesterday",
                "Traffic backup extends ~200 meters during peak hours"
            ],
            assumptions_made=[
                "Subsurface drainage collapse or asphalt erosion accelerated by recent monsoon rain",
                "Risk of severe pedestrian injury during low-visibility nighttime hours"
            ],
            missing_information=[
                "Exact municipal ward number and road designation (PWD vs Municipal)",
                "Underground utility pipe integrity beneath the depression"
            ],
            recommended_next_steps=[
                "Submit priority complaint to the Municipal Road Maintenance division",
                "Place temporary warning reflective markers or barricade around the depression",
                "Collect photographic evidence with timestamp and GPS coordinates"
            ],
            responsible_authority_type="Municipal Public Works & Road Maintenance Division",
            complaint_letter="""To:
The Executive Engineer,
Public Works & Road Maintenance Division,
Municipal Corporation.

Subject: URGENT: Hazardous pothole causing vehicular accidents outside College Gate 2

Respected Sir/Madam,

I am writing to formally report an escalating public safety hazard located at North Campus Gate 2 on the Ring Road intersection.

A deep pothole measuring approximately 3 feet in width and 6 inches in depth has developed directly across the student pedestrian crossing. Due to monsoon rainwater accumulation, the cavity becomes completely submerged, rendering it invisible to oncoming two-wheelers and cyclists. On 20th October 2026, two students suffered falls from their motorbikes at this exact spot.

This condition is causing severe vehicular swerving and daily traffic backups of up to 200 meters, putting hundreds of college students and pedestrians at grave risk of fatal collision.

I respectfully urge your office to:
1. Conduct an immediate on-site inspection.
2. Deploy temporary reflective barricades to prevent imminent injury.
3. Perform emergency cold-mix or hot-mix asphalt patching.

Photographic evidence and precise location coordinates are attached for immediate action.

Yours faithfully,
[Citizen / Student Name]
[Contact Number]
[Email Address]""",
            evidence_checklist=[
                "High-resolution photos showing scale with a ruler or foot",
                "Geo-tagged coordinates (latitude & longitude)",
                "Date and time-stamped video of vehicle avoidance swerves",
                "Names/statements of students involved in recent slips"
            ],
            follow_up_checklist=[
                "Day 1: Submit formal grievance via Citizen Grievance Portal and obtain tracking ID",
                "Day 3: Call Municipal Ward Road Inspector referencing the case ID",
                "Day 7: If unaddressed, escalate to Zonal Commissioner and file Public Grievance Escalation"
            ],
            confidence_assessment="High confidence based on detailed spatial and situational description. Note: Urgency is an advisory algorithmic recommendation."
        )

        create_case(
            title=DEMO_SCENARIOS["Pothole Near College Gate"]["title"],
            description=DEMO_SCENARIOS["Pothole Near College Gate"]["description"],
            location=DEMO_SCENARIOS["Pothole Near College Gate"]["location"],
            category=DEMO_SCENARIOS["Pothole Near College Gate"]["category"],
            ai_analysis=demo_1,
            model_used="nvidia/Llama-3.1-Nemotron-70B-Instruct (Demo Baseline)",
            observed_date=DEMO_SCENARIOS["Pothole Near College Gate"]["observed_date"],
            status="Open",
            add_initial_note=True,
            is_demo=True,
        )

seed_demo_cases()

# Navigation items definition
NAV_ITEMS = [
    ("📊", "Dashboard"),
    ("📝", "Report an Issue"),
    ("📁", "Case Management"),
    ("📈", "Community Insights"),
    ("⚙️", "Settings & API Status"),
]
NAV_OPTIONS = [f"{icon} {name}" for icon, name in NAV_ITEMS]
TAB_NAMES = [name for _, name in NAV_ITEMS]

# Session State Initialization
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Dashboard"
if "nebius_api_key" not in st.session_state:
    st.session_state.nebius_api_key = NEBIUS_API_KEY
if "connection_status" not in st.session_state:
    st.session_state.connection_status = "UNVERIFIED" if is_nebius_configured(NEBIUS_API_KEY) else "UNCONFIGURED"
if "connection_message" not in st.session_state:
    st.session_state.connection_message = "Key loaded from environment. Run test in Settings to verify." if is_nebius_configured(NEBIUS_API_KEY) else "No API key configured."
if "selected_case_id" not in st.session_state:
    st.session_state.selected_case_id = None
if "report_title" not in st.session_state:
    st.session_state.report_title = ""
if "report_desc" not in st.session_state:
    st.session_state.report_desc = ""
if "report_loc" not in st.session_state:
    st.session_state.report_loc = ""
if "report_cat" not in st.session_state:
    st.session_state.report_cat = ISSUE_CATEGORIES[0]
if "report_user_urgency" not in st.session_state:
    st.session_state.report_user_urgency = "Let AI Recommend"
if "report_date" not in st.session_state:
    st.session_state.report_date = date.today()
if "pending_report" not in st.session_state:
    st.session_state.pending_report = None
if "api_test_result" not in st.session_state:
    st.session_state.api_test_result = None

# Helper functions for API Key resolution
def get_effective_key() -> str:
    """Retrieves active Nebius API key from session or environment."""
    sess_k = st.session_state.get("nebius_api_key", "").strip()
    if sess_k:
        return sess_k
    return os.getenv("NEBIUS_API_KEY", NEBIUS_API_KEY).strip()

def has_configured_key() -> bool:
    """Checks if a non-placeholder key is currently present."""
    return is_nebius_configured(get_effective_key())

# Sidebar Navigation & Diagnostics
with st.sidebar:
    st.markdown("### 🏛️ CivicPulse AI")
    st.caption("Nebius × NVIDIA Global AI Hackathon 2026")

    # Honest, Real AI Connection Status Badge
    conn_status = st.session_state.connection_status
    eff_key = get_effective_key()

    if conn_status == "CONNECTED":
        masked = f"{eff_key[:4]}...{eff_key[-4:]}" if len(eff_key) > 8 else "Active"
        st.success(f"🟢 **Nebius Connected (Verified)**\n\nModel: `{NEBIUS_MODEL}`\n\nKey: `{masked}`")
    elif conn_status == "UNVERIFIED" and has_configured_key():
        masked = f"{eff_key[:4]}...{eff_key[-4:]}" if len(eff_key) > 8 else "Entered"
        st.info(f"⚪ **Key Provided (Unverified)**\n\nKey: `{masked}`\n\n*Click 'Test AI Connection' in Settings to verify.*")
    elif conn_status == "ERROR":
        st.error(f"🔴 **Connection Error**\n\n{st.session_state.connection_message}")
    else:
        st.warning("🟡 **API Key Not Configured**\n\n*Enter your key in Settings or below to enable real AI triage.*")

    with st.expander("🔑 Quick Key Configuration", expanded=(not has_configured_key())):
        sb_key = st.text_input(
            "Nebius API Key",
            type="password",
            placeholder="nbf-...",
            key="sb_key_input",
            help="Your key from tokenfactory.nebius.com",
        )
        sb_save = st.checkbox("Save to local .env", value=True, key="sb_save_env")
        if st.button("Apply Key", key="sb_apply_btn", use_container_width=True):
            if sb_key.strip():
                st.session_state.nebius_api_key = sb_key.strip()
                if sb_save:
                    update_env_file("NEBIUS_API_KEY", sb_key.strip())
                st.session_state.connection_status = "UNVERIFIED"
                st.session_state.connection_message = "Key updated. Run verification test in Settings."
                st.success("API Key saved!")
                st.rerun()

    st.markdown("---")

    # Navigation menu
    current_active = st.session_state.get("active_tab", "Dashboard")
    for _, name in NAV_ITEMS:
        if name in current_active:
            current_active = name
            break
    tab_idx = TAB_NAMES.index(current_active) if current_active in TAB_NAMES else 0

    nav_selection = st.radio(
        "Navigation",
        NAV_OPTIONS,
        index=tab_idx,
    )
    current_tab = nav_selection.split(" ", 1)[1]
    st.session_state.active_tab = current_tab

    st.markdown("---")
    st.markdown(
        """
        <div style="font-size: 0.78rem; color: #94a3b8; line-height: 1.4;">
        <b>Privacy Notice:</b> Civic reports and notes are stored strictly in local SQLite (<code>civicpulse.db</code>). No sensitive identity documents, bank accounts, or passwords are collected.
        </div>
        """,
        unsafe_allow_html=True,
    )

# Header Banner
st.markdown(
    f"""
    <div class="civic-hero">
        <h1>CivicPulse AI</h1>
        <p><b>AI-powered community issue reporting and accountable case management.</b></p>
        <p style="font-size: 0.95rem; color: #ccfbf1; margin-top: 0.25rem;">
            Turning grassroots civic infrastructure & community grievances into structured, accountable case plans powered by NVIDIA Nemotron on Nebius Token Factory.
        </p>
        <div class="civic-badge-container">
            <span class="civic-badge badge-teal">⚡ Nebius Token Factory</span>
            <span class="civic-badge badge-lime">🤖 NVIDIA Nemotron 70B</span>
            <span class="civic-badge">🏆 Best Apps & Agents Track</span>
            <span class="civic-badge">🛡️ Advisory Citizen Triage</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------
# PAGE 1: DASHBOARD (Phase 2)
# -------------------------------------------------------------
if current_tab == "Dashboard":
    stats = get_case_statistics()

    # Top CTA Bar
    cta_col1, cta_col2 = st.columns([3, 1])
    with cta_col1:
        if stats["total"] == 0:
            st.info("ℹ️ No cases currently in database. Click 'Report an Issue' to file your first community complaint.")
        elif stats["is_all_demo"]:
            st.info("ℹ️ **Notice:** The statistics shown include initial demo baselines. As you submit reports in 'Report an Issue', real resident records appear automatically.")
        else:
            st.success(f"📊 Active Tracking: **{stats['total']}** total civic cases (**{stats['user_count']}** resident-submitted, **{stats['demo_count']}** demo baselines).")
    with cta_col2:
        if st.button("📝 Report an Issue Now", type="primary", use_container_width=True):
            st.session_state.active_tab = "Report an Issue"
            st.rerun()

    # Exact 4 Metric Cards requested in Phase 2: Total, Open, High-Priority, Resolved
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label">Total Cases</div>
            <div class="stat-value">{stats['total']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c2:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label" style="color: #d97706;">Open Cases</div>
            <div class="stat-value" style="color: #d97706;">{stats['open']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label" style="color: #ef4444;">High-Priority Cases</div>
            <div class="stat-value" style="color: #ef4444;">{stats['high_priority']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label" style="color: #16a34a;">Resolved Cases</div>
            <div class="stat-value" style="color: #16a34a;">{stats['resolved']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Real Charts
    col_left, col_right = st.columns(2)
    with col_left:
        st.subheader("Urgency Breakdown")
        urgency_data = stats["urgency_counts"]
        if urgency_data and stats["total"] > 0:
            df_urg = pd.DataFrame([
                {"Urgency": u, "Count": urgency_data.get(u, 0)} for u in URGENCY_LEVELS
            ])
            chart = alt.Chart(df_urg).mark_bar(cornerRadius=6).encode(
                x=alt.X("Urgency:N", sort=URGENCY_LEVELS),
                y=alt.Y("Count:Q"),
                color=alt.Color("Urgency:N", scale=alt.Scale(
                    domain=["Low", "Medium", "High", "Critical"],
                    range=["#84cc16", "#eab308", "#f97316", "#ef4444"]
                ), legend=None),
                tooltip=["Urgency", "Count"]
            ).properties(height=260)
            st.altair_chart(chart, use_container_width=True)
        else:
            st.caption("No urgency records currently available.")

    with col_right:
        st.subheader("Category Distribution")
        cat_data = stats["category_counts"]
        if cat_data and stats["total"] > 0:
            df_cat = pd.DataFrame([
                {"Category": k, "Count": v} for k, v in cat_data.items()
            ])
            chart_cat = alt.Chart(df_cat).mark_bar(cornerRadius=6, color="#0d9488").encode(
                x=alt.X("Count:Q"),
                y=alt.Y("Category:N", sort="-x"),
                tooltip=["Category", "Count"]
            ).properties(height=260)
            st.altair_chart(chart_cat, use_container_width=True)
        else:
            st.caption("No category records currently available.")

    st.markdown("---")
    st.subheader("Recent Case Activity")
    recent_cases = get_all_cases()[:5]

    if recent_cases:
        for c in recent_cases:
            urg_class = f"urgency-{c.urgency.lower()}"
            status_class = f"status-{c.status.lower().replace(' ', '-')}"
            tag = " [Demo]" if c.is_demo else " [Resident Report]"

            with st.container():
                st.markdown(f"""
                <div class="civic-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span style="font-weight: 700; color: #2dd4bf;">{c.case_number} {tag}</span>
                        <div>
                            <span class="status-badge {status_class}">{c.status}</span>
                            <span class="urgency-badge {urg_class}">{c.urgency} Urgency</span>
                        </div>
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #f8fafc; margin-bottom: 0.3rem;">{c.title}</div>
                    <div style="font-size: 0.85rem; color: #94a3b8; margin-bottom: 0.5rem;">📍 {c.location} &nbsp;|&nbsp; 🏷️ {c.category} &nbsp;|&nbsp; 📅 {c.created_at}</div>
                    <div style="font-size: 0.95rem; color: #cbd5e1; line-height: 1.5;">{c.ai_analysis.summary}</div>
                </div>
                """, unsafe_allow_html=True)
                btn_col1, _ = st.columns([1, 4])
                with btn_col1:
                    if st.button(f"View Case Plan #{c.case_number}", key=f"dash_rec_{c.id}"):
                        st.session_state.selected_case_id = c.id
                        st.session_state.active_tab = "Case Management"
                        st.rerun()
    else:
        st.info("No cases logged yet. Click 'Report an Issue Now' above to submit your first community report.")

# -------------------------------------------------------------
# PAGE 2: REPORT AN ISSUE (Phase 3)
# -------------------------------------------------------------
elif current_tab == "Report an Issue":
    st.subheader("📝 Report a Community Issue")
    st.caption("Submit your grievance for analysis by NVIDIA Nemotron on Nebius Token Factory. You will review and confirm all findings before saving.")

    # Emergency Guidance Callout
    st.markdown(
        """
        <div class="emergency-banner">
            🚨 <b>Immediate Emergency Notice:</b> If this issue involves an active life-threatening danger (e.g., active gas leak, downed high-voltage power lines, structural building collapse, or severe fire), immediately contact emergency services (<b>112 / 911 / Local Fire & Rescue</b>). CivicPulse AI is an administrative civic triage system, not an emergency dispatch provider.
        </div>
        """,
        unsafe_allow_html=True,
    )

    # 1-Click Fast-Fill Scenarios
    st.markdown("##### 🚀 Fast-Fill 1-Click Demo Scenarios")
    d_col1, d_col2, d_col3 = st.columns(3)

    with d_col1:
        if st.button("🚧 Campus Gate Pothole", use_container_width=True):
            pothole = DEMO_SCENARIOS["Pothole Near College Gate"]
            st.session_state.report_title = pothole["title"]
            st.session_state.report_desc = pothole["description"]
            st.session_state.report_loc = pothole["location"]
            st.session_state.report_cat = pothole["category"]
            st.session_state.report_user_urgency = "High"
            st.session_state.report_date = datetime.strptime(pothole["observed_date"], "%Y-%m-%d").date()
            st.session_state.pending_report = None
            st.rerun()

    with d_col2:
        if st.button("🗑️ Overflowing Dumpster", use_container_width=True):
            dumpster = DEMO_SCENARIOS["Overflowing Public Garbage Bin"]
            st.session_state.report_title = dumpster["title"]
            st.session_state.report_desc = dumpster["description"]
            st.session_state.report_loc = dumpster["location"]
            st.session_state.report_cat = dumpster["category"]
            st.session_state.report_user_urgency = "Medium"
            st.session_state.report_date = datetime.strptime(dumpster["observed_date"], "%Y-%m-%d").date()
            st.session_state.pending_report = None
            st.rerun()

    with d_col3:
        if st.button("💡 Unlit Pedestrian Walkway", use_container_width=True):
            lights = DEMO_SCENARIOS["Dark Streetlights on Pedestrian Walkway"]
            st.session_state.report_title = lights["title"]
            st.session_state.report_desc = lights["description"]
            st.session_state.report_loc = lights["location"]
            st.session_state.report_cat = lights["category"]
            st.session_state.report_user_urgency = "High"
            st.session_state.report_date = datetime.strptime(lights["observed_date"], "%Y-%m-%d").date()
            st.session_state.pending_report = None
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Input Form
    with st.form("civic_report_form"):
        form_title = st.text_input(
            "Issue Title *",
            value=st.session_state.report_title,
            placeholder="e.g. Deep pothole causing motorbike accidents near university entrance",
            help="At least 5 characters summarizing the problem."
        )

        col_c1, col_c2, col_c3 = st.columns([1.2, 1, 1])
        with col_c1:
            cat_index = ISSUE_CATEGORIES.index(st.session_state.report_cat) if st.session_state.report_cat in ISSUE_CATEGORIES else 0
            form_cat = st.selectbox("Category *", ISSUE_CATEGORIES, index=cat_index)
        with col_c2:
            urgency_options = ["Let AI Recommend"] + URGENCY_LEVELS
            cur_urg_idx = urgency_options.index(st.session_state.report_user_urgency) if st.session_state.report_user_urgency in urgency_options else 0
            form_user_urgency = st.selectbox("Your Assessed Urgency (Optional)", urgency_options, index=cur_urg_idx)
        with col_c3:
            form_date = st.date_input("Date Observed", value=st.session_state.report_date)

        form_location = st.text_input(
            "Location / Locality / Landmark *",
            value=st.session_state.report_loc,
            placeholder="e.g. North Campus Gate 2, Ring Road Intersection",
            help="Be specific to guide municipal triage and avoid duplicate investigations."
        )

        form_desc = st.text_area(
            "Detailed Description of the Problem *",
            value=st.session_state.report_desc,
            height=140,
            placeholder="Provide factual details: physical dimensions, duration, hazards to pedestrians/drivers, weather impacts, and recent incidents...",
            help="At least 20 characters of detail."
        )

        uploaded_photo = st.file_uploader(
            "Optional Evidence Photo (Preserved locally in uploads/)",
            type=["png", "jpg", "jpeg"],
            help="Images are stored locally as evidence attachments for your formal complaint dossier."
        )

        form_submit = st.form_submit_button("⚡ Analyze Issue with NVIDIA Nemotron", use_container_width=True)

    # Form Submission Logic
    if form_submit:
        errors = []
        if len(form_title.strip()) < 5:
            errors.append("Title must be at least 5 characters.")
        if len(form_desc.strip()) < 20:
            errors.append("Description must contain at least 20 characters of factual detail.")
        if len(form_location.strip()) < 3:
            errors.append("Location must be at least 3 characters.")

        if errors:
            for err in errors:
                st.error(f"⚠️ {err}")
        else:
            # Check for existing open duplicate report
            dup_case = check_duplicate_case(form_title, form_location)
            if dup_case:
                st.warning(f"⚠️ **Potential Duplicate:** An active case with this exact title and location is already registered: **Case #{dup_case.case_number}** (Status: {dup_case.status}).")

            # Handle photo save
            saved_photo_path = None
            if uploaded_photo is not None:
                photo_ext = Path(uploaded_photo.name).suffix
                timestamp_str = datetime.now().strftime("%Y%m%d_%H%M%S")
                target_filename = f"evidence_{timestamp_str}{photo_ext}"
                target_path = UPLOADS_DIR / target_filename
                with open(target_path, "wb") as f:
                    f.write(uploaded_photo.getbuffer())
                saved_photo_path = str(target_path)

            case_input = CaseInput(
                title=form_title,
                description=form_desc,
                location=form_location,
                category=form_cat,
                photo_path=saved_photo_path,
                observed_date=str(form_date),
                user_urgency=form_user_urgency if form_user_urgency in URGENCY_LEVELS else None,
            )

            # Check if key is available
            active_key = get_effective_key()
            if not has_configured_key():
                st.error("❌ **Nebius Token Factory API Key Not Configured**")
                st.info("You can either configure your key in Settings, or save this complaint directly without AI analysis below.")
                st.session_state.pending_report = {
                    "case_input": case_input,
                    "ai_analysis": None,
                    "model_used": "Manual Direct Submission",
                    "requires_fallback": True,
                }
            else:
                with st.spinner("🤖 Sending prompt to Nebius Token Factory (`nvidia/Llama-3.1-Nemotron-70B-Instruct`)..."):
                    try:
                        result = analyze_civic_case(case_input, api_key=active_key)
                        st.session_state.pending_report = {
                            "case_input": case_input,
                            "ai_analysis": result["analysis"],
                            "model_used": result["model_used"],
                            "requires_fallback": False,
                        }
                        st.session_state.connection_status = "CONNECTED"
                        st.session_state.connection_message = "Active & verified with Nebius Token Factory."
                        st.success("✅ Analysis completed! Please review the findings below and confirm case creation.")
                    except NebiusMissingCredentialsError as nmce:
                        st.error(f"🔑 Credential Error: {str(nmce)}")
                        st.session_state.pending_report = {
                            "case_input": case_input,
                            "ai_analysis": None,
                            "model_used": "Manual Direct Submission",
                            "requires_fallback": True,
                        }
                    except NebiusClientError as nce:
                        st.error(f"🚨 Nebius API Error: {str(nce)}")
                        st.session_state.connection_status = "ERROR"
                        st.session_state.connection_message = str(nce)[:100]
                        st.session_state.pending_report = {
                            "case_input": case_input,
                            "ai_analysis": None,
                            "model_used": "Manual Direct Submission",
                            "requires_fallback": True,
                        }
                    except Exception as ex:
                        st.error(f"Unexpected Error: {str(ex)}")

    # ---------------------------------------------------------
    # HUMAN CONFIRMATION STAGE (Phase 3 Requirement)
    # ---------------------------------------------------------
    if st.session_state.pending_report:
        prep = st.session_state.pending_report
        c_in = prep["case_input"]
        ai_res = prep["ai_analysis"]
        is_fallback = prep["requires_fallback"]

        st.markdown("---")
        st.markdown("### 📋 Review AI Analysis & Human Confirmation")
        st.caption("Verify the AI-suggested category and urgency before registering the official case record.")

        if is_fallback or ai_res is None:
            st.warning("⚠️ **Live AI Analysis Unavailable:** You can proceed to save this report directly without AI analysis. It will be recorded with status 'Open' for municipal inspection.")
            suggested_urg = c_in.user_urgency or "Medium"
            suggested_cat = c_in.category
            fallback_analysis = create_unavailable_analysis(suggested_cat, suggested_urg)
            active_analysis = fallback_analysis
        else:
            active_analysis = ai_res
            suggested_urg = ai_res.urgency
            suggested_cat = ai_res.category if ai_res.category in ISSUE_CATEGORIES else c_in.category

            urg_cls = f"urgency-{ai_res.urgency.lower()}"
            st.markdown(f"""
            <div class="civic-card">
                <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.6rem;">
                    <span class="urgency-badge {urg_cls}">{ai_res.urgency} Urgency Recommendation</span>
                    <span style="font-size: 0.85rem; color: #94a3b8;">Inference Model: {prep['model_used']}</span>
                </div>
                <h3 style="color: #ffffff !important; margin: 0.3rem 0;">{ai_res.summary}</h3>
                <p style="color: #cbd5e1 !important; margin-bottom: 0.3rem;">
                    <b style="color: #ffffff !important;">Responsible Department Type:</b> {ai_res.responsible_authority_type}
                </p>
                <p style="color: #cbd5e1 !important; margin-bottom: 0.6rem;">
                    <b style="color: #ffffff !important;">Urgency Reasoning:</b> {ai_res.urgency_reasoning}
                </p>
                <div class="notice-box">
                    <b style="color: #ffffff !important;">Advisory Notice & Confidence:</b> {ai_res.confidence_assessment}
                </div>
            </div>
            """, unsafe_allow_html=True)

            t1, t2, t3 = st.tabs(["🔍 Facts vs Assumptions", "✉️ Formal Complaint Letter Draft", "✅ Action Checklists"])
            with t1:
                col_f1, col_f2 = st.columns(2)
                with col_f1:
                    st.markdown("##### 📌 Citizen Stated Facts")
                    for fact in ai_res.distinguished_facts:
                        st.markdown(f"- {fact}")
                with col_f2:
                    st.markdown("##### 💡 Inferred Impact & Context Risks")
                    for asmp in ai_res.assumptions_made:
                        st.markdown(f"- {asmp}")
                if ai_res.missing_information:
                    st.markdown("##### ❓ Missing Details to Gather")
                    for mis in ai_res.missing_information:
                        st.markdown(f"- [ ] {mis}")

            with t2:
                st.caption("Official draft formatted for submission to the municipal grievance portal.")
                st.code(ai_res.complaint_letter, language="text")

            with t3:
                col_k1, col_k2 = st.columns(2)
                with col_k1:
                    st.markdown("##### 📸 Evidence Collection")
                    for ev in ai_res.evidence_checklist:
                        st.markdown(f"- [ ] {ev}")
                with col_k2:
                    st.markdown("##### 🗓️ Follow-up Protocol")
                    for fol in ai_res.follow_up_checklist:
                        st.markdown(f"- [ ] {fol}")

        # Human Confirmation Form
        st.markdown("<div class='confirmation-card'>", unsafe_allow_html=True)
        st.markdown("#### 👤 Citizen Confirmation & Acceptance")
        st.markdown("You may adjust the final category and urgency before saving to the official registry:")

        conf_c1, conf_c2 = st.columns(2)
        with conf_c1:
            conf_cat_idx = ISSUE_CATEGORIES.index(suggested_cat) if suggested_cat in ISSUE_CATEGORIES else 0
            final_cat = st.selectbox("Confirmed Category", ISSUE_CATEGORIES, index=conf_cat_idx, key="conf_cat_select")
        with conf_c2:
            conf_urg_idx = URGENCY_LEVELS.index(suggested_urg) if suggested_urg in URGENCY_LEVELS else 1
            final_urg = st.selectbox("Confirmed Urgency Level", URGENCY_LEVELS, index=conf_urg_idx, key="conf_urg_select")

        # Create updated analysis object with human confirmation
        final_analysis = active_analysis.model_copy(update={"category": final_cat, "urgency": final_urg})

        conf_btn_c1, conf_btn_c2 = st.columns([1.5, 1])
        with conf_btn_c1:
            if st.button("✅ Confirm & Create Official Case Record", type="primary", use_container_width=True, key="save_confirmed_case"):
                new_case = create_case(
                    title=c_in.title,
                    description=c_in.description,
                    location=c_in.location,
                    category=final_cat,
                    ai_analysis=final_analysis,
                    model_used=prep["model_used"],
                    photo_path=c_in.photo_path,
                    observed_date=c_in.observed_date,
                    status="Open",
                    add_initial_note=True,
                    is_demo=False,
                )
                st.session_state.selected_case_id = new_case.id
                st.session_state.pending_report = None
                st.success(f"🎉 **Case Created Successfully!** Case Reference: `{new_case.case_number}`")
                st.balloons()

                nav_btn_c1, nav_btn_c2 = st.columns(2)
                with nav_btn_c1:
                    if st.button("📁 Open Case in Case Management", key="nav_to_cm", use_container_width=True):
                        st.session_state.active_tab = "Case Management"
                        st.rerun()
                with nav_btn_c2:
                    if st.button("📊 View on Dashboard", key="nav_to_dash", use_container_width=True):
                        st.session_state.active_tab = "Dashboard"
                        st.rerun()

        with conf_btn_c2:
            if st.button("🔄 Discard & Start Over", key="discard_pending_btn", use_container_width=True):
                st.session_state.pending_report = None
                st.rerun()

        st.markdown("</div>", unsafe_allow_html=True)

# -------------------------------------------------------------
# PAGE 3: CASE MANAGEMENT (Phase 5)
# -------------------------------------------------------------
elif current_tab == "Case Management":
    st.subheader("📁 Case Management System")
    st.caption("Filter, search, track status changes, inspect chronological audit histories, and export case plans.")

    # Filter controls
    f1, f2, f3, f4 = st.columns([1.4, 1.2, 1.2, 2])
    with f1:
        sel_cat = st.selectbox("Category Filter", ["All"] + ISSUE_CATEGORIES)
    with f2:
        sel_urg = st.selectbox("Urgency Filter", ["All"] + URGENCY_LEVELS)
    with f3:
        sel_status = st.selectbox("Status Filter", ["All"] + CASE_STATUSES)
    with f4:
        search_kw = st.text_input("🔍 Search Keyword / Case #", placeholder="e.g. pothole, CP-2026...")

    cases = get_all_cases(
        category_filter=sel_cat,
        urgency_filter=sel_urg,
        status_filter=sel_status,
        search_query=search_kw,
    )

    st.markdown(f"**Found {len(cases)} matching cases**")

    # Resolve active selected case
    active_case = None
    if st.session_state.selected_case_id:
        active_case = get_case_by_id(st.session_state.selected_case_id)
    if active_case is None and cases:
        active_case = cases[0]

    case_list_col, detail_col = st.columns([1, 1.85])

    with case_list_col:
        st.markdown("##### Cases List")
        if not cases:
            st.info("No cases match your filters.")
        for cs in cases:
            is_active = (active_case and cs.id == active_case.id)
            border_style = "border: 2px solid #0d9488;" if is_active else "border: 1px solid #334155;"
            tag = " [Demo]" if cs.is_demo else " [Resident]"
            urg_cls = f"urgency-{cs.urgency.lower()}"
            status_cls = f"status-{cs.status.lower().replace(' ', '-')}"

            st.markdown(f"""
            <div style="background: #1e293b; {border_style} border-radius: 10px; padding: 0.85rem; margin-bottom: 0.6rem;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <b style="color: #2dd4bf;">{cs.case_number}{tag}</b>
                    <div>
                        <span class="status-badge {status_cls}">{cs.status}</span>
                        <span class="urgency-badge {urg_cls}">{cs.urgency}</span>
                    </div>
                </div>
                <div style="font-weight: 600; color: #f8fafc; margin: 0.3rem 0;">{cs.title[:45]}...</div>
                <div style="font-size: 0.8rem; color: #94a3b8;">📍 {cs.location[:30]}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Select Case", key=f"sel_btn_{cs.id}", use_container_width=True):
                st.session_state.selected_case_id = cs.id
                st.rerun()

    with detail_col:
        if active_case:
            st.markdown(f"### Case Record: `{active_case.case_number}`")
            if active_case.is_demo:
                st.info("ℹ️ **Demo Reference Record** — Created as a baseline scenario.")

            # Status Update & Audit Log Row
            st.markdown("##### 🔄 Update Case Status & Record Activity")
            sc1, sc2, sc3 = st.columns([1.2, 1.2, 1])
            with sc1:
                cur_status_idx = CASE_STATUSES.index(active_case.status) if active_case.status in CASE_STATUSES else 0
                new_st = st.selectbox("Target Status", CASE_STATUSES, index=cur_status_idx, key=f"st_sel_{active_case.id}")
            with sc2:
                role_opts = ["Resident", "Municipal Worker", "Community Lead", "Case Officer", "Admin"]
                actor_role = st.selectbox("Your Role", role_opts, key=f"role_sel_{active_case.id}")
            with sc3:
                st.write("")
                st.write("")
                update_status_btn = st.button("Save Status Update", key=f"savest_{active_case.id}", use_container_width=True)

            status_note = st.text_input("Status Update Reason / Note (Optional)", placeholder="e.g. Dispatched asphalt repair crew to North Campus", key=f"st_note_{active_case.id}")

            if update_status_btn:
                if new_st != active_case.status or status_note.strip():
                    update_case_status(
                        active_case.id,
                        new_st,
                        author=actor_role,
                        activity_note=status_note if status_note.strip() else None,
                    )
                    st.success(f"Status updated to '{new_st}' and recorded in activity log.")
                    st.rerun()
                else:
                    st.info("Status is already set to this value.")

            # Case details
            st.markdown(f"""
            <div class="civic-card">
                <h3 style="color: #ffffff !important; margin-bottom: 0.5rem;">{active_case.title}</h3>
                <p style="color: #cbd5e1 !important; margin-bottom: 0.3rem;">
                    <b style="color: #ffffff !important;">Category:</b> {active_case.category} &nbsp;|&nbsp; 
                    <b style="color: #ffffff !important;">Location:</b> {active_case.location}
                </p>
                <p style="color: #94a3b8 !important; margin-bottom: 0.8rem;">
                    <b style="color: #cbd5e1 !important;">Observed:</b> {active_case.observed_date or 'N/A'} &nbsp;|&nbsp; 
                    <b style="color: #cbd5e1 !important;">Logged:</b> {active_case.created_at} &nbsp;|&nbsp;
                    <b style="color: #cbd5e1 !important;">Inference Engine:</b> {active_case.model_used}
                </p>
                <div style="font-size: 0.95rem; color: #f1f5f9 !important; line-height: 1.6; border-top: 1px solid #334155; padding-top: 0.8rem;">
                    <b style="color: #ffffff !important;">Full Description:</b><br>{active_case.description}
                </div>
            </div>
            """, unsafe_allow_html=True)

            if active_case.photo_path and Path(active_case.photo_path).exists():
                st.image(active_case.photo_path, caption="Attached Evidence Photo", use_column_width=True)

            # AI Analysis Details
            ai = active_case.ai_analysis
            with st.expander("🤖 AI Case Analysis & Complaint Draft", expanded=True):
                st.markdown(f"**Target Authority:** {ai.responsible_authority_type}")
                st.markdown(f"**Urgency Reasoning:** {ai.urgency_reasoning}")
                st.markdown("**Official Complaint Letter:**")
                st.code(ai.complaint_letter, language="text")

                st.markdown("**Recommended Next Steps:**")
                for s in ai.recommended_next_steps:
                    st.markdown(f"1. {s}")

            # Chronological Activity History & Case Log
            st.markdown("##### 📜 Chronological Activity History & Follow-Up Notes")
            notes = active_case.notes
            if notes:
                for n in notes:
                    st.markdown(f"""
                    <div style="background: #0f172a; border-left: 3px solid #0d9488; padding: 0.5rem 0.8rem; border-radius: 4px; margin-bottom: 0.4rem; font-size: 0.88rem;">
                        <span style="color: #94a3b8; font-weight: 600;">[{n.timestamp}]</span>
                        <b style="color: #2dd4bf;">{n.author}:</b>
                        <span style="color: #e2e8f0;">{n.content}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("No notes or activity recorded yet.")

            # Add Follow-up Note Form
            with st.form(f"note_form_{active_case.id}"):
                note_author = st.text_input("Author / Role", value="Resident", key=f"author_{active_case.id}")
                note_content = st.text_area("Add Case Note / Field Inspection Update", placeholder="e.g. Registered grievance on city portal, tracking ref #12345", key=f"content_{active_case.id}")
                submit_note = st.form_submit_button("Add Note to Case History")
                if submit_note and note_content.strip():
                    add_case_note(active_case.id, note_author, note_content)
                    st.success("Note recorded in case history!")
                    st.rerun()

            # Actions: Export & Delete
            act1, act2 = st.columns([1, 1])
            with act1:
                md_text = export_case_to_markdown(active_case)
                st.download_button(
                    label="⬇️ Export Case Dossier (.md)",
                    data=md_text,
                    file_name=f"Case_{active_case.case_number}.md",
                    mime="text/markdown",
                    use_container_width=True,
                )
            with act2:
                with st.popover("🗑️ Delete Case", use_container_width=True):
                    st.warning(f"Are you sure you want to permanently delete case **{active_case.case_number}**?")
                    confirm_del = st.checkbox("Confirm permanent deletion", key=f"del_chk_{active_case.id}")
                    if st.button("Delete Permanently", key=f"del_btn_{active_case.id}", disabled=not confirm_del):
                        delete_case(active_case.id)
                        st.session_state.selected_case_id = None
                        st.success("Case deleted.")
                        st.rerun()
        else:
            st.info("Select a case on the left to view complete details.")

# -------------------------------------------------------------
# PAGE 4: COMMUNITY INSIGHTS (Phase 6)
# -------------------------------------------------------------
elif current_tab == "Community Insights":
    st.subheader("📈 Community Infrastructure Insights")
    st.caption("Real-world aggregated metrics, recurring issue themes, and hotspot areas derived from stored cases.")

    insights = get_community_insights()

    st.markdown(
        f"""
        <div class="notice-box">
            <b>Data Provenance Disclosure:</b> All analytics below are computed directly from actual local SQLite database storage.
            Currently analyzing <b>{insights['total_cases']}</b> registered civic records.
            No simulated external government statistics or fabricated distributions are generated.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if insights["total_cases"] > 0:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Issues by Category")
            df_cat = pd.DataFrame(insights["category_distribution"])
            if not df_cat.empty:
                chart_cat = alt.Chart(df_cat).mark_bar(cornerRadius=6, color="#0d9488").encode(
                    x=alt.X("count:Q", title="Total Cases"),
                    y=alt.Y("category:N", sort="-x", title="Category"),
                    tooltip=["category", "count"]
                ).properties(height=260)
                st.altair_chart(chart_cat, use_container_width=True)

        with c2:
            st.markdown("##### Resolution Lifecycle Status")
            df_st = pd.DataFrame(insights["status_distribution"])
            if not df_st.empty:
                chart_st = alt.Chart(df_st).mark_arc(innerRadius=50).encode(
                    theta=alt.Theta(field="count", type="quantitative"),
                    color=alt.Color(field="status", type="nominal", scale=alt.Scale(
                        domain=["Open", "In Progress", "Resolved", "Closed"],
                        range=["#f59e0b", "#3b82f6", "#10b981", "#64748b"]
                    )),
                    tooltip=["status", "count"]
                ).properties(height=260)
                st.altair_chart(chart_st, use_container_width=True)

        st.markdown("---")
        col_t1, col_t2 = st.columns(2)

        with col_t1:
            st.markdown("##### 🏷️ Recurring Problem Themes")
            st.caption("Derived from keyword frequency analysis across case descriptions.")
            themes = insights["common_themes"]
            if themes:
                df_th = pd.DataFrame(themes)
                chart_th = alt.Chart(df_th).mark_bar(cornerRadius=4, color="#0284c7").encode(
                    x=alt.X("mentions:Q", title="Keyword Mentions"),
                    y=alt.Y("theme:N", sort="-x", title="Theme"),
                    tooltip=["theme", "mentions"]
                ).properties(height=240)
                st.altair_chart(chart_th, use_container_width=True)
            else:
                st.caption("No recurring themes identified yet.")

        with col_t2:
            st.markdown("##### 📍 Infrastructure Hotspots")
            st.caption("Localities and landmarks with repeated civic complaints.")
            hotspots = insights["hotspot_areas"]
            if hotspots:
                for h in hotspots:
                    st.markdown(f"- **{h['location']}**: `{h['count']} case{'s' if h['count'] > 1 else ''}`")
            else:
                st.caption("Insufficient location data for hotspot clustering.")
    else:
        st.info("No cases available for analysis yet. Submit an issue or load a demo scenario to see community insights.")

# -------------------------------------------------------------
# PAGE 5: SETTINGS & API STATUS (Phase 4)
# -------------------------------------------------------------
elif current_tab == "Settings & API Status":
    st.subheader("⚙️ Nebius Token Factory & NVIDIA Integration Settings")
    st.caption("Configure credentials, test live backend connectivity, and verify model availability.")

    active_k = get_effective_key()
    has_k = has_configured_key()

    st.markdown("##### 🔑 API Key Configuration")
    if has_k:
        masked = f"{active_k[:4]}...{active_k[-4:]}" if len(active_k) > 8 else "Active"
        st.success(f"🟢 **API Key Configured:** `{masked}`")
    else:
        st.warning("🟡 **API Key Not Configured:** Enter your Nebius Token Factory API key below.")

    with st.container():
        new_key_input = st.text_input(
            "Nebius Token Factory API Key",
            type="password",
            placeholder="nbf-... from tokenfactory.nebius.com",
            help="Your key is kept safe and never logged.",
            key="settings_key_input",
        )

        save_to_file = st.checkbox("Save permanently to local .env file", value=True, key="settings_save_env")

        btn_c1, btn_c2 = st.columns([1, 1])
        with btn_c1:
            if st.button("💾 Save & Apply Key", key="save_key_btn", use_container_width=True):
                if new_key_input.strip():
                    st.session_state.nebius_api_key = new_key_input.strip()
                    if save_to_file:
                        update_env_file("NEBIUS_API_KEY", new_key_input.strip())
                    st.session_state.connection_status = "UNVERIFIED"
                    st.session_state.connection_message = "Key updated. Run verification test."
                    st.success("API Key successfully applied!")
                    st.rerun()
                else:
                    st.warning("Please enter an API key.")

        with btn_c2:
            test_target_key = new_key_input.strip() if new_key_input.strip() else active_k
            if st.button("⚡ Test AI Connection Now", key="test_conn_btn", use_container_width=True):
                with st.spinner("Connecting to Nebius Token Factory API endpoint..."):
                    res = verify_nebius_connection(api_key=test_target_key)
                    st.session_state.api_test_result = res
                    if res["success"]:
                        st.session_state.connection_status = "CONNECTED"
                        st.session_state.connection_message = res["message"]
                    else:
                        st.session_state.connection_status = "ERROR"
                        st.session_state.connection_message = res["message"]

    # Show Test Results
    if st.session_state.api_test_result:
        res = st.session_state.api_test_result
        if res["success"]:
            st.success(f"✅ {res['message']}")
            st.markdown(f"- **Configured Model (`{NEBIUS_MODEL}`):** {'✅ Available in account' if res.get('model_present') else '⚠️ Not listed in account models'}")
            st.markdown(f"- **Endpoint Verified:** `{res.get('endpoint')}`")
            with st.expander("📋 View Available Models on Nebius"):
                for m in res.get("available_models", []):
                    st.markdown(f"- `{m}`")
        else:
            st.error(f"❌ {res['message']}")
            st.markdown(
                """
                **How to obtain a valid Nebius Token Factory key:**
                1. Sign up or log into [Nebius Token Factory](https://tokenfactory.nebius.com/).
                2. Navigate to **API Keys** and generate a new key.
                3. Paste the key above and click **Save & Apply Key**.
                """
            )

    st.markdown("---")
    st.markdown("##### 📡 Runtime Environment & Deployment Configuration")
    st.markdown(f"- **Nebius Base URL:** `{NEBIUS_BASE_URL}`")
    st.markdown(f"- **Target Model:** `{NEBIUS_MODEL}`")
    st.markdown(f"- **Database Path:** `{DATABASE_PATH}`")

    st.markdown("---")
    st.markdown("##### 🔒 Privacy, Security & Data Boundaries")
    st.markdown(
        """
        - **Local SQLite Database:** All cases, notes, timestamps, and evidence reside securely on the host machine in `civicpulse.db`.
        - **Zero Secret Exposure:** API keys are never rendered in HTML, frontend source code, or exported markdown files.
        - **Model Inference Boundaries:** Transmitted prompts contain civic issue details (title, category, location, description). Personal passwords, national IDs, and financial information are strictly prohibited.
        - **Advisory Algorithmic Guidance:** All AI urgency triage rankings and jurisdictional assignments are advisory suggestions designed to empower citizen advocacy, not binding governmental decisions.
        """
    )
