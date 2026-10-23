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
)
from models.schemas import CaseInput, AIAnalysisResult
from database.repository import (
    init_db,
    create_case,
    get_all_cases,
    get_case_by_id,
    update_case_status,
    add_case_note,
    delete_case,
    get_case_statistics,
    export_case_to_markdown,
)
from services.nebius_client import verify_nebius_connection, NebiusMissingCredentialsError, NebiusClientError
from services.case_analyzer import analyze_civic_case

# Set page configuration
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

# Load CSS
css_file = BASE_DIR / "assets" / "style.css"
if css_file.exists():
    with open(css_file, "r") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# Seed demo cases on first run if empty
def seed_demo_cases():
    stats = get_case_statistics()
    if stats["total"] == 0:
        # Pre-seed with realistic analysis for offline / first-time review
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
            is_demo=True,
        )

seed_demo_cases()

# Session State Initialization
if "active_tab" not in st.session_state:
    st.session_state.active_tab = "Dashboard"
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
if "report_date" not in st.session_state:
    st.session_state.report_date = date.today()
if "last_analysis_result" not in st.session_state:
    st.session_state.last_analysis_result = None
if "api_test_result" not in st.session_state:
    st.session_state.api_test_result = None

# Sidebar Navigation & Diagnostics
with st.sidebar:
    st.markdown("### 🏛️ CivicPulse AI")
    st.caption("Nebius × NVIDIA Global AI Hackathon 2026")

    # API Status Pill
    has_key = is_nebius_configured()
    if has_key:
        st.success(f"🟢 **Nebius Configured**\n\nModel: `{NEBIUS_MODEL}`")
    else:
        st.warning("🟡 **API Key Not Set**\n\nConfigure in Settings or `.env`")

    st.markdown("---")
    nav_selection = st.radio(
        "Navigation",
        [
            "📊 Dashboard",
            "📝 Report an Issue",
            "📁 Case Management",
            "📈 Community Insights",
            "⚙️ Settings & API Status",
        ],
        index=[
            "📊 Dashboard",
            "📝 Report an Issue",
            "📁 Case Management",
            "📈 Community Insights",
            "⚙️ Settings & API Status",
        ].index(f"📊 {st.session_state.active_tab}" if not any(x in st.session_state.active_tab for x in ["📊", "📝", "📁", "📈", "⚙️"]) else st.session_state.active_tab)
        if any(st.session_state.active_tab in x for x in ["Dashboard", "Report an Issue", "Case Management", "Community Insights", "Settings & API Status"])
        else 0,
    )
    # Strip icon for routing
    current_tab = nav_selection.split(" ", 1)[1]
    st.session_state.active_tab = current_tab

    st.markdown("---")
    st.markdown(
        """
        <div style="font-size: 0.8rem; color: #64748b; line-height: 1.4;">
        <b>Privacy Notice:</b> CivicPulse AI processes issue descriptions and stores case records locally in SQLite. Never submit passwords, banking, or sensitive national ID documents.
        </div>
        """,
        unsafe_allow_html=True,
    )

# Header Banner
st.markdown(
    f"""
    <div class="civic-hero">
        <h1>CivicPulse AI</h1>
        <p>Turning grassroots civic infrastructure & community grievances into structured, accountable case plans powered by NVIDIA Nemotron on Nebius Token Factory.</p>
        <div class="civic-badge-container">
            <span class="civic-badge badge-teal">⚡ Nebius Token Factory</span>
            <span class="civic-badge badge-lime">🤖 NVIDIA Nemotron</span>
            <span class="civic-badge">🏆 Best Apps & Agents Track</span>
            <span class="civic-badge">🛡️ Advisory Citizen Triage</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# -------------------------------------------------------------
# PAGE 1: DASHBOARD
# -------------------------------------------------------------
if current_tab == "Dashboard":
    stats = get_case_statistics()

    if stats["is_all_demo"]:
        st.info("ℹ️ **Notice:** The statistics shown currently include initial demo scenarios. As you submit reports in 'Report an Issue', real community records will appear here.")
    elif stats["total"] == 0:
        st.info("ℹ️ No cases currently in database. Submit an issue or load a demo scenario to begin.")
    else:
        st.success(f"📊 Tracking **{stats['total']}** total cases (**{stats['user_count']}** resident-submitted, **{stats['demo_count']}** demo baseline).")

    # Metric Cards
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
            <div class="stat-label" style="color: #2563eb;">In Progress</div>
            <div class="stat-value" style="color: #2563eb;">{stats['in_progress']}</div>
        </div>
        """, unsafe_allow_html=True)
    with c4:
        st.markdown(f"""
        <div class="stat-card">
            <div class="stat-label" style="color: #16a34a;">Resolved</div>
            <div class="stat-value" style="color: #16a34a;">{stats['resolved']}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Visualizations
    col_left, col_right = st.columns(2)

    with col_left:
        st.subheader("Urgency Breakdown")
        urgency_data = stats["urgency_counts"]
        if urgency_data:
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
            st.caption("No urgency data available.")

    with col_right:
        st.subheader("Category Distribution")
        cat_data = stats["category_counts"]
        if cat_data:
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
            st.caption("No category data available.")

    st.markdown("---")
    st.subheader("Recent Case Records")
    recent_cases = get_all_cases()[:5]
    if recent_cases:
        for c in recent_cases:
            urg_class = f"urgency-{c.urgency.lower()}"
            status_class = f"status-{c.status.lower().replace(' ', '-')}"
            tag = " [Demo]" if c.is_demo else ""

            with st.container():
                st.markdown(f"""
                <div class="civic-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.5rem;">
                        <span style="font-weight: 700; color: #0d9488;">{c.case_number}{tag}</span>
                        <div>
                            <span class="status-badge {status_class}">{c.status}</span>
                            <span class="urgency-badge {urg_class}">{c.urgency} Urgency</span>
                        </div>
                    </div>
                    <div style="font-size: 1.15rem; font-weight: 700; color: #0f172a; margin-bottom: 0.3rem;">{c.title}</div>
                    <div style="font-size: 0.9rem; color: #64748b; margin-bottom: 0.5rem;">📍 {c.location} &nbsp;|&nbsp; 🏷️ {c.category} &nbsp;|&nbsp; 📅 {c.created_at}</div>
                    <div style="font-size: 0.95rem; color: #334155;">{c.ai_analysis.summary}</div>
                </div>
                """, unsafe_allow_html=True)
                btn_col1, _ = st.columns([1, 4])
                with btn_col1:
                    if st.button(f"View Full Case Plan #{c.case_number}", key=f"rec_{c.id}"):
                        st.session_state.selected_case_id = c.id
                        st.session_state.active_tab = "Case Management"
                        st.rerun()
    else:
        st.info("No cases logged yet.")

# -------------------------------------------------------------
# PAGE 2: REPORT AN ISSUE
# -------------------------------------------------------------
elif current_tab == "Report an Issue":
    st.subheader("📝 Submit a Community Infrastructure Report")
    st.caption("Provide details of the problem. Our NVIDIA Nemotron AI agent will validate the report, triage urgency, and build an actionable case plan.")

    # 1-Click Demo Scenarios
    st.markdown("##### 🚀 Fast-Fill 1-Click Demo Scenarios")
    d_col1, d_col2, d_col3 = st.columns(3)

    with d_col1:
        if st.button("🚧 Campus Gate Pothole", use_container_width=True):
            pothole = DEMO_SCENARIOS["Pothole Near College Gate"]
            st.session_state.report_title = pothole["title"]
            st.session_state.report_desc = pothole["description"]
            st.session_state.report_loc = pothole["location"]
            st.session_state.report_cat = pothole["category"]
            st.session_state.report_date = datetime.strptime(pothole["observed_date"], "%Y-%m-%d").date()
            st.rerun()

    with d_col2:
        if st.button("🗑️ Overflowing Dumpster", use_container_width=True):
            dumpster = DEMO_SCENARIOS["Overflowing Public Garbage Bin"]
            st.session_state.report_title = dumpster["title"]
            st.session_state.report_desc = dumpster["description"]
            st.session_state.report_loc = dumpster["location"]
            st.session_state.report_cat = dumpster["category"]
            st.session_state.report_date = datetime.strptime(dumpster["observed_date"], "%Y-%m-%d").date()
            st.rerun()

    with d_col3:
        if st.button("💡 Unlit Pedestrian Walkway", use_container_width=True):
            lights = DEMO_SCENARIOS["Dark Streetlights on Pedestrian Walkway"]
            st.session_state.report_title = lights["title"]
            st.session_state.report_desc = lights["description"]
            st.session_state.report_loc = lights["location"]
            st.session_state.report_cat = lights["category"]
            st.session_state.report_date = datetime.strptime(lights["observed_date"], "%Y-%m-%d").date()
            st.rerun()

    st.markdown("<br>", unsafe_allow_html=True)

    # Input Form
    with st.form("civic_report_form"):
        form_title = st.text_input(
            "Report Title *",
            value=st.session_state.report_title,
            placeholder="e.g. Broken water pipeline causing road cave-in",
            help="At least 5 characters summarizing the problem."
        )

        col_c1, col_c2 = st.columns([1, 1])
        with col_c1:
            cat_index = ISSUE_CATEGORIES.index(st.session_state.report_cat) if st.session_state.report_cat in ISSUE_CATEGORIES else 0
            form_cat = st.selectbox("Issue Category *", ISSUE_CATEGORIES, index=cat_index)
        with col_c2:
            form_date = st.date_input("Date Observed", value=st.session_state.report_date)

        form_location = st.text_input(
            "Location / Address / Landmark *",
            value=st.session_state.report_loc,
            placeholder="e.g. Opposite Central Library Gate, Sector 4",
            help="Be as specific as possible to guide municipal triage."
        )

        form_desc = st.text_area(
            "Detailed Description of the Issue *",
            value=st.session_state.report_desc,
            height=150,
            placeholder="Describe what is broken, physical size, immediate risks to public health or traffic, and how long it has been occurring...",
            help="Minimum 20 characters of detail."
        )

        uploaded_photo = st.file_uploader(
            "Optional Evidence Photo (Stored locally as case attachment)",
            type=["png", "jpg", "jpeg"],
            help="Image is preserved in local case storage as tangible evidence for your complaint package."
        )

        st.caption("ℹ️ *Note: The text description is analyzed by NVIDIA Nemotron to generate structured triage, missing evidence checklists, and formal complaint drafts.*")

        submit_btn = st.form_submit_button("⚡ Run Real AI Analysis with NVIDIA Nemotron", use_container_width=True)

    if submit_btn:
        # Validate inputs
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
            )

            # Check API Key status
            if not is_nebius_configured():
                st.error(
                    "❌ **Nebius Token Factory API Key Not Configured**\n\n"
                    "CivicPulse AI requires genuine inference with NVIDIA Nemotron on Nebius Token Factory. "
                    "Please configure your `NEBIUS_API_KEY` in the `.env` file or test it in the **Settings & API Status** tab."
                )
            else:
                with st.spinner("🤖 Sending request to Nebius Token Factory (`nvidia/Llama-3.1-Nemotron-70B-Instruct`)..."):
                    try:
                        result = analyze_civic_case(case_input)
                        ai_analysis = result["analysis"]
                        model_used = result["model_used"]

                        # Save to database
                        new_case = create_case(
                            title=form_title,
                            description=form_desc,
                            location=form_location,
                            category=form_cat,
                            ai_analysis=ai_analysis,
                            model_used=model_used,
                            photo_path=saved_photo_path,
                            observed_date=str(form_date),
                            is_demo=False,
                        )

                        st.session_state.last_analysis_result = new_case
                        st.session_state.selected_case_id = new_case.id
                        st.success(f"✅ Case generated & saved successfully! Assigned Case #{new_case.case_number}")
                        st.balloons()
                    except NebiusMissingCredentialsError as nmce:
                        st.error(f"🔑 Credential Error: {str(nmce)}")
                    except NebiusClientError as nce:
                        st.error(f"🚨 Nebius API Error: {str(nce)}")
                    except Exception as ex:
                        st.error(f"Unexpected Error during analysis: {str(ex)}")

    # Display Last Analysis Result if Available
    if st.session_state.last_analysis_result:
        res_case = st.session_state.last_analysis_result
        ai = res_case.ai_analysis
        st.markdown("---")
        st.markdown(f"### 📋 Generated Action Plan: {res_case.case_number}")

        # Urgency & Jurisdictional Banner
        urg_cls = f"urgency-{ai.urgency.lower()}"
        st.markdown(f"""
        <div class="civic-card">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <span class="urgency-badge {urg_cls}">{ai.urgency} Urgency Recommendation</span>
                <span style="font-size: 0.85rem; color: #64748b;">Model: {res_case.model_used}</span>
            </div>
            <h3 style="margin-top: 0.8rem;">{ai.summary}</h3>
            <p><b>Target Jurisdiction:</b> {ai.responsible_authority_type}</p>
            <p style="color: #475569;"><b>Urgency Reasoning:</b> {ai.urgency_reasoning}</p>
            <div class="notice-box">
                <b>Confidence & Advisory Notice:</b> {ai.confidence_assessment}
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Tabs for details
        t1, t2, t3, t4 = st.tabs([
            "🔍 Facts vs Assumptions",
            "✉️ Official Complaint Letter",
            "✅ Action Checklists",
            "📥 Export Package"
        ])

        with t1:
            f_col1, f_col2 = st.columns(2)
            with f_col1:
                st.markdown("##### 📌 Verified Facts Stated by Citizen")
                for f in ai.distinguished_facts:
                    st.markdown(f"- {f}")
            with f_col2:
                st.markdown("##### 💡 Inferred Assumptions & Impact Risks")
                for a in ai.assumptions_made:
                    st.markdown(f"- {a}")

            st.markdown("##### ❓ Missing Details to Gather")
            for m in ai.missing_information:
                st.markdown(f"- [ ] {m}")

        with t2:
            st.markdown("##### Formal Complaint Draft")
            st.caption("Copy this draft into your municipal grievance portal or print for submission.")
            st.code(ai.complaint_letter, language="text")

        with t3:
            c_col1, c_col2 = st.columns(2)
            with c_col1:
                st.markdown("##### 📸 Evidence Checklist")
                for e in ai.evidence_checklist:
                    st.checkbox(e, key=f"ev_chk_{hash(e)}")
            with c_col2:
                st.markdown("##### 🗓️ Follow-Up Timeline & Escalation")
                for f in ai.follow_up_checklist:
                    st.checkbox(f, key=f"fol_chk_{hash(f)}")

        with t4:
            md_export = export_case_to_markdown(res_case)
            st.download_button(
                label=f"⬇️ Download Case Plan #{res_case.case_number} (.md)",
                data=md_export,
                file_name=f"CivicPulse_Case_{res_case.case_number}.md",
                mime="text/markdown",
                use_container_width=True,
            )

# -------------------------------------------------------------
# PAGE 3: CASE MANAGEMENT
# -------------------------------------------------------------
elif current_tab == "Case Management":
    st.subheader("📁 Case Management System")
    st.caption("Track, filter, update status, and manage the full lifecycle of community infrastructure cases.")

    # Filter controls
    f1, f2, f3, f4 = st.columns([1.5, 1.2, 1.2, 2])
    with f1:
        sel_cat = st.selectbox("Filter Category", ["All"] + ISSUE_CATEGORIES)
    with f2:
        sel_urg = st.selectbox("Filter Urgency", ["All"] + URGENCY_LEVELS)
    with f3:
        sel_status = st.selectbox("Filter Status", ["All"] + CASE_STATUSES)
    with f4:
        search_kw = st.text_input("🔍 Search Keyword / Case #", placeholder="e.g. pothole, CP-2026...")

    cases = get_all_cases(
        category_filter=sel_cat,
        urgency_filter=sel_urg,
        status_filter=sel_status,
        search_query=search_kw,
    )

    st.markdown(f"**Found {len(cases)} matching cases**")

    # If case selected, show detail view
    if st.session_state.selected_case_id:
        active_case = get_case_by_id(st.session_state.selected_case_id)
    else:
        active_case = cases[0] if cases else None

    case_list_col, detail_col = st.columns([1, 1.8])

    with case_list_col:
        st.markdown("##### All Cases")
        if not cases:
            st.info("No cases match your filters.")
        for cs in cases:
            is_active = (active_case and cs.id == active_case.id)
            border_style = "border: 2px solid #0d9488;" if is_active else "border: 1px solid #e2e8f0;"
            tag = " [Demo]" if cs.is_demo else ""

            st.markdown(f"""
            <div style="background: #ffffff; {border_style} border-radius: 10px; padding: 0.9rem; margin-bottom: 0.6rem;">
                <div style="display: flex; justify-content: space-between;">
                    <b style="color: #0d9488;">{cs.case_number}{tag}</b>
                    <span style="font-size: 0.75rem; font-weight: 700;">{cs.urgency} | {cs.status}</span>
                </div>
                <div style="font-weight: 600; color: #0f172a; margin: 0.2rem 0;">{cs.title[:45]}...</div>
                <div style="font-size: 0.8rem; color: #64748b;">📍 {cs.location[:30]}</div>
            </div>
            """, unsafe_allow_html=True)
            if st.button("Select Case", key=f"sel_btn_{cs.id}", use_container_width=True):
                st.session_state.selected_case_id = cs.id
                st.rerun()

    with detail_col:
        if active_case:
            st.markdown(f"### Case Record: `{active_case.case_number}`")
            if active_case.is_demo:
                st.info("ℹ️ **Demo Scenario Record** — Created as an architectural and training reference.")

            # Status Update Row
            sc1, sc2 = st.columns([1.5, 1])
            with sc1:
                cur_status_idx = CASE_STATUSES.index(active_case.status) if active_case.status in CASE_STATUSES else 0
                new_st = st.selectbox("Update Case Status", CASE_STATUSES, index=cur_status_idx, key=f"st_sel_{active_case.id}")
            with sc2:
                st.write("")
                st.write("")
                if st.button("Save Status Update", key=f"savest_{active_case.id}"):
                    update_case_status(active_case.id, new_st)
                    st.success(f"Status updated to '{new_st}'")
                    st.rerun()

            # Case details
            st.markdown(f"""
            <div class="civic-card">
                <h4>{active_case.title}</h4>
                <p><b>Category:</b> {active_case.category} &nbsp;|&nbsp; <b>Location:</b> {active_case.location}</p>
                <p><b>Observed:</b> {active_case.observed_date or 'N/A'} &nbsp;|&nbsp; <b>Logged:</b> {active_case.created_at}</p>
                <p><b>Description:</b><br>{active_case.description}</p>
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

                st.markdown("**Next Steps:**")
                for s in ai.recommended_next_steps:
                    st.markdown(f"1. {s}")

            # Case Notes Section
            st.markdown("##### 📝 Case Log & Follow-Up Notes")
            notes = active_case.notes
            if notes:
                for n in notes:
                    st.markdown(f"**[{n.timestamp}] {n.author}:** {n.content}")
            else:
                st.caption("No follow-up notes logged yet.")

            with st.form(f"note_form_{active_case.id}"):
                note_author = st.text_input("Your Name / Role", value="Resident", key=f"author_{active_case.id}")
                note_content = st.text_area("Note / Action Update", placeholder="e.g. Filed complaint on portal, tracking ref #54321", key=f"content_{active_case.id}")
                submit_note = st.form_submit_button("Add Note")
                if submit_note and note_content.strip():
                    add_case_note(active_case.id, note_author, note_content)
                    st.success("Note added!")
                    st.rerun()

            # Actions: Export & Delete
            act1, act2 = st.columns([1, 1])
            with act1:
                md_text = export_case_to_markdown(active_case)
                st.download_button(
                    label="⬇️ Export Case (.md)",
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
            st.info("Select a case on the left to view details.")

# -------------------------------------------------------------
# PAGE 4: COMMUNITY INSIGHTS
# -------------------------------------------------------------
elif current_tab == "Community Insights":
    st.subheader("📈 Community Infrastructure Insights")
    st.caption("Aggregated trends and public infrastructure health metrics derived from saved cases.")

    stats = get_case_statistics()

    st.markdown(
        f"""
        <div class="notice-box">
            <b>Data Provenance Disclosure:</b> All metrics below are calculated directly from local SQLite database storage.
            Currently tracking <b>{stats['total']}</b> cases (<b>{stats['demo_count']}</b> initial demo baselines and <b>{stats['user_count']}</b> verified resident reports).
            No simulated external government statistics are fabricated.
        </div>
        """,
        unsafe_allow_html=True,
    )

    if stats["total"] > 0:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("##### Issues by Category")
            df_cat = pd.DataFrame([
                {"Category": k, "Cases": v} for k, v in stats["category_counts"].items()
            ])
            chart_cat = alt.Chart(df_cat).mark_bar(cornerRadius=6, color="#0d9488").encode(
                x=alt.X("Cases:Q"),
                y=alt.Y("Category:N", sort="-x"),
                tooltip=["Category", "Cases"]
            ).properties(height=280)
            st.altair_chart(chart_cat, use_container_width=True)

        with c2:
            st.markdown("##### Resolution Status")
            status_df = pd.DataFrame([
                {"Status": "Open", "Count": stats["open"], "Color": "#f59e0b"},
                {"Status": "In Progress", "Count": stats["in_progress"], "Color": "#3b82f6"},
                {"Status": "Resolved", "Count": stats["resolved"], "Color": "#10b981"},
            ])
            chart_st = alt.Chart(status_df).mark_arc(innerRadius=50).encode(
                theta=alt.Theta(field="Count", type="quantitative"),
                color=alt.Color(field="Status", type="nominal", scale=alt.Scale(
                    domain=["Open", "In Progress", "Resolved"],
                    range=["#f59e0b", "#3b82f6", "#10b981"]
                )),
                tooltip=["Status", "Count"]
            ).properties(height=280)
            st.altair_chart(chart_st, use_container_width=True)
    else:
        st.info("No cases available for aggregation.")

# -------------------------------------------------------------
# PAGE 5: SETTINGS & API STATUS
# -------------------------------------------------------------
elif current_tab == "Settings & API Status":
    st.subheader("⚙️ Nebius Token Factory & NVIDIA Integration Settings")
    st.caption("Verify API credentials, live endpoint connectivity, and model availability.")

    st.markdown("##### Current Runtime Configuration")
    st.markdown(f"- **Endpoint Base URL:** `{NEBIUS_BASE_URL}`")
    st.markdown(f"- **Configured Model:** `{NEBIUS_MODEL}`")
    masked_key = f"{NEBIUS_API_KEY[:4]}...{NEBIUS_API_KEY[-4:]}" if len(NEBIUS_API_KEY) > 8 else ("Configured" if NEBIUS_API_KEY else "Not Configured")
    st.markdown(f"- **API Key Status:** `{masked_key}`")

    st.markdown("---")
    st.markdown("##### 🔌 Test Live Nebius Token Factory Connectivity")
    st.caption("Perform a genuine call to `/v1/models` on Nebius Token Factory to verify credentials.")

    test_key_input = st.text_input(
        "Override Nebius API Key for this session (optional)",
        type="password",
        placeholder="Paste your Nebius Token Factory API key here if not set in .env",
    )

    effective_key = test_key_input.strip() if test_key_input.strip() else NEBIUS_API_KEY

    if st.button("⚡ Test Nebius API Connection Now", use_container_width=True):
        with st.spinner("Connecting to Nebius Token Factory API..."):
            res = verify_nebius_connection(api_key=effective_key)
            st.session_state.api_test_result = res

    if st.session_state.api_test_result:
        res = st.session_state.api_test_result
        if res["success"]:
            st.success(f"✅ {res['message']}")
            st.markdown(f"- **Configured Model Present:** {'✅ Yes' if res.get('model_present') else '⚠️ Not found in account model list, check model ID'}")
            with st.expander("View Available Models on Nebius"):
                for m in res.get("available_models", []):
                    st.markdown(f"- `{m}`")
        else:
            st.error(f"❌ {res['message']}")
            st.markdown(
                """
                **How to fix:**
                1. Sign up / log into [Nebius Token Factory](https://tokenfactory.nebius.com/).
                2. Generate an API Key under API Keys.
                3. Add the key to your `.env` file as `NEBIUS_API_KEY=your_key` or paste it above.
                4. Ensure your account has access to NVIDIA Nemotron models.
                """
            )

    st.markdown("---")
    st.markdown("##### 🔒 Privacy & Local Storage Audit")
    st.markdown(
        """
        - **Local SQLite Database:** Stored at `civicpulse.db`. All cases, notes, and timestamps reside on your local machine.
        - **No Third-Party Analytics:** CivicPulse AI does not use telemetry trackers or third-party behavioral analytics.
        - **Model Inference:** Reports are transmitted securely over TLS to Nebius Token Factory for analysis by NVIDIA Nemotron.
        """
    )
