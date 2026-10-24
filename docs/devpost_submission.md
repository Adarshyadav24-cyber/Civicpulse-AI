# CivicPulse AI — Devpost Submission & Demo Video Script
> **Hackathon:** Nebius × NVIDIA Global AI Hackathon 2026
> **Track:** Best Apps and Agents
> **Submission Deadline:** October 30, 2026, 10:30 PM IST

---

## 1. Quick Metadata & Submission Links

- **Project Title:** CivicPulse AI
- **Tagline:** Empowering communities by turning infrastructure hazards into structured, prioritized case plans and formal complaint packages via NVIDIA Nemotron on Nebius Token Factory.
- **Track:** Best Apps and Agents
- **GitHub Repository URL:** `[Your Public GitHub Repository URL]`
- **Live Public Demo URL:** `[Your Live Public Demo URL - e.g. Streamlit Cloud / Render]`
- **Demo Video URL (YouTube, < 3 Minutes):** `[Your Public YouTube Video URL]`
- **Built With:**
  - Nebius Token Factory (High-throughput GPU inference)
  - NVIDIA Nemotron (`nvidia/Llama-3.1-Nemotron-70B-Instruct`)
  - OpenAI Python SDK
  - Streamlit & Custom Civic-Tech CSS Design System
  - Python 3.11 & Pydantic v2
  - SQLite3
  - Altair & Pandas

---

## 2. Devpost Submission Description

### 🌟 Inspiration
Across colleges, urban neighborhoods, and semi-rural communities, everyday infrastructure hazards—such as open manholes, sunken road craters, leaking water mains, and unlit pedestrian pathways—often go unaddressed for months. 

When citizens attempt to report these problems, the process is intimidating and opaque. Reports submitted to municipal portals are often vague, misclassified, or sent to the wrong jurisdictional authority. More importantly, citizens lack the administrative knowledge to draft formal grievance letters, collect legally compelling evidence, or follow up effectively. We built **CivicPulse AI** to bridge this power imbalance and provide every citizen with an expert AI civic case analyst in their pocket.

### 💡 What It Does
CivicPulse AI converts raw, unstructured community reports into comprehensive, prioritized case plans:
1. **Intelligent Triage & Urgency Assessment:** Analyzes reports and assigns an advisory urgency level (`Low`, `Medium`, `High`, `Critical`) supported by factual risk reasoning.
2. **Epistemic Fact vs. Assumption Separation:** Clearly delineates user-provided observations from inferred consequences, ensuring credibility.
3. **Jurisdictional Mapping:** Identifies the precise authority type (e.g. Municipal Road Maintenance, Public Health, Electricity Board) without inventing fictional personnel.
4. **Human Review & Confirmation:** Provides citizens with an interactive preview to accept, adjust, or override AI suggestions before creating the official record.
5. **Instant Formal Complaint Drafting:** Generates an authoritative, respectful administrative letter ready to copy and paste directly into government portals.
6. **Tangible Checklists:** Outlines evidence collection steps (measurements, photo angles, geo-tags) and an actionable follow-up protocol.
7. **Local Case Lifecycle Management:** Saves all cases into SQLite, enabling tracking (`Open`, `In Progress`, `Resolved`, `Closed`), chronological activity audit logging, field notes, and one-click Markdown export.
8. **Community Insights:** Derives aggregate statistics, recurring problem themes, and infrastructure hotspot clustering directly from authentic database records without simulated data.

### 🛠️ How We Built It
- **AI Backbone:** We integrated **Nebius Token Factory** (`https://api.tokenfactory.us-central1.nebius.com/v1/`) using the official OpenAI-compatible client pattern to access **NVIDIA Nemotron** (`nvidia/Llama-3.1-Nemotron-70B-Instruct`).
- **Prompt Architecture:** A structured system prompt guides Nemotron to act as a Senior Civic Infrastructure & Public Policy Analyst, enforcing strict JSON output conforming to a Pydantic schema.
- **Frontend & UX:** Built with Streamlit, enriched with a custom civic-tech design system (dark navy typography, teal and lime accents, responsive cards, and accessible status badges).
- **Persistence & Privacy:** Local SQLite database (`civicpulse.db`) with indexing for search, category filtering, and status audit tracking. Uploaded evidence photos and case data stay securely stored locally.

### 🧗 Challenges We Overcame
1. **Model Output Predictability:** Ensuring frontier 70B models return strictly structured JSON without conversational filler or Markdown framing. We addressed this through robust regex boundary sanitization and Pydantic validation.
2. **Responsible AI Guardrails & Human-in-the-Loop:** Preventing the model from inventing fictional civil servant names or misleading citizens into thinking an automated triage is an official government declaration. We enforced strict advisory disclosures, emergency helpline notices, and an explicit human confirmation step before case registration.
3. **Transparent Connection Verification:** Ensuring the UI displays honest connection telemetry (never falsely claiming "Connected" unless a verified backend health check succeeds) and providing offline direct logging if the AI service is unavailable.

### 🏆 Accomplishments That We're Proud Of
- A truly useful, full-stack application that solves real-world citizen headaches rather than functioning as a toy chatbot.
- Real-time, high-speed inference powered by **NVIDIA Nemotron** on **Nebius Token Factory**.
- Zero fabricated data: every statistic on the dashboard and community insights page is derived from verifiable SQLite storage.
- 100% automated test coverage across schemas, database CRUD, activity history logging, and AI error handling.

---

## 3. Video Demonstration Script (< 3 Minutes)

**Total Duration:** 2 minutes 45 seconds  
**Visuals:** Screen recording with voiceover (no background music)

### [0:00 - 0:25] Step 1: Open CivicPulse AI & Homepage Overview
- **Voiceover:** *"Welcome to CivicPulse AI — AI-powered community issue reporting and accountable case management for the Nebius × NVIDIA Global AI Hackathon 2026. On our dashboard, citizens and neighborhood leads see real-time metrics: Total Cases, Open Cases, High-Priority issues, and Resolved cases, alongside live AI provider status."*
- **Action:** Show the Homepage. Point out the summary cards and the prominent 'Report an Issue Now' button.

### [0:25 - 0:55] Step 2: Submit a Realistic Community Infrastructure Report
- **Voiceover:** *"Let's report an incident. We'll use a realistic 1-click scenario: a severe 3-foot pothole near a college campus entrance causing motorbike slips. Notice our location, category, date, and detailed description. Now, let's trigger real-time inference with NVIDIA Nemotron on Nebius Token Factory."*
- **Action:** Click 'Report an Issue'. Click '🚧 Campus Gate Pothole'. Click '⚡ Analyze Issue with NVIDIA Nemotron'. Show the real-time spinner.

### [0:55 - 1:30] Step 3: Inspect Nemotron Analysis & Human Confirmation
- **Voiceover:** *"In seconds, NVIDIA Nemotron analyzes the hazard. It recommends High Urgency with factual reasoning and maps the target jurisdiction to the Municipal Road Maintenance division. Crucially, it separates citizen facts from inferred risks, flags missing details, and writes an authoritative formal complaint letter ready for the grievance portal. Before saving, our human confirmation step allows the citizen to review and adjust the final classification."*
- **Action:** Scroll through the analysis tabs. Highlight Fact vs Assumption separation and Complaint Letter. Click '✅ Confirm & Create Official Case Record'. Show the success balloon and assigned Case Number.

### [1:30 - 2:05] Steps 4-6: Case Management, Status Transitions & Activity History
- **Voiceover:** *"Under Case Management, every case is stored in our local SQLite database. We can search by keyword or filter by category, urgency, and status. Let's select our new case. When a municipal crew responds, we update the status from Open to In Progress with an inspection note. Notice how every status update is permanently recorded in our chronological activity history."*
- **Action:** Switch to 'Case Management'. Select the newly created case. Change status to 'In Progress', type note 'Repair team dispatched', and click 'Save Status Update'. Point to the activity history audit box. Show the '⬇️ Export Case Dossier (.md)' download button.

### [2:05 - 2:25] Step 7: Return to Dashboard (Updated Metrics)
- **Voiceover:** *"Returning to the Dashboard, our counts have updated immediately from SQLite: our Open and High-Priority numbers reflect the latest state."*
- **Action:** Switch to 'Dashboard'. Show the updated metric cards.

### [2:25 - 2:40] Step 8: Community Insights from Real Records
- **Voiceover:** *"In Community Insights, we aggregate authentic trends across all stored cases: category distributions, lifecycle resolution charts, recurring problem themes, and infrastructure hotspots."*
- **Action:** Switch to 'Community Insights'. Show the category chart, status donut chart, themes, and location hotspots.

### [2:40 - 2:45] Step 9: Settings & Real Connection Verification
- **Voiceover:** *"Finally, in Settings, we can verify our live connection to Nebius Token Factory and inspect available models with zero secret leakage. Thank you!"*
- **Action:** Switch to 'Settings & API Status'. Click '⚡ Test AI Connection Now' and show the verified status message.
