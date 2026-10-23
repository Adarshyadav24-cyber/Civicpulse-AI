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
4. **Instant Formal Complaint Drafting:** Generates an authoritative, respectful administrative letter ready to copy and paste directly into government portals.
5. **Tangible Checklists:** Outlines evidence collection steps (measurements, photo angles, geo-tags) and an actionable 7-day follow-up protocol.
6. **Local Case Lifecycle Management:** Saves all cases into SQLite, enabling tracking (`Open`, `In Progress`, `Resolved`), field notes, and one-click Markdown export.

### 🛠️ How We Built It
- **AI Backbone:** We integrated **Nebius Token Factory** (`https://api.tokenfactory.us-central1.nebius.com/v1/`) using the official OpenAI-compatible client pattern to access **NVIDIA Nemotron** (`nvidia/Llama-3.1-Nemotron-70B-Instruct`).
- **Prompt Architecture:** A structured system prompt guides Nemotron to act as a Senior Civic Infrastructure & Public Policy Analyst, enforcing strict JSON output conforming to a Pydantic schema.
- **Frontend & UX:** Built with Streamlit, enriched with a custom civic-tech design system (dark navy typography, teal and lime accents, responsive cards, and accessible status badges).
- **Persistence & Privacy:** SQLite database with indexing for search and category filtering. Uploaded evidence photos and case data stay securely stored locally.

### 🧗 Challenges We Overcame
1. **Model Output Predictability:** Ensuring frontier 70B models return strictly structured JSON without conversational filler or Markdown framing. We addressed this through robust regex boundary sanitization and Pydantic validation.
2. **Responsible AI Guardrails:** Preventing the model from inventing fictional civil servant names or misleading citizens into thinking an automated triage is an official government declaration. We enforced strict advisory disclosures and authority-type mappings.
3. **Responsive Civic-Tech Aesthetic:** Overcoming default UI styling to provide a polished SaaS interface with clear visual hierarchy, dynamic metric cards, and 1-click demo scenarios.

### 🏆 Accomplishments That We're Proud Of
- A truly useful, full-stack application that solves real-world citizen headaches rather than functioning as a toy chatbot.
- Real-time, high-speed inference powered by **NVIDIA Nemotron** on **Nebius Token Factory**.
- Zero fabricated data: every statistic on the dashboard is derived from verifiable SQLite storage.
- 100% automated test coverage across schemas, database CRUD, and AI error handling.

### 📖 What We Learned
- How to harness NVIDIA Nemotron’s exceptional reasoning for administrative document generation and legal triage.
- The simplicity and speed of Nebius Token Factory’s OpenAI-compatible endpoints.
- Best practices for local-first civic application architecture.

### 🔮 What's Next for CivicPulse AI
- Multimodal damage assessment using NVIDIA vision-language models to measure pothole dimensions directly from photos.
- Direct integration with open government API grievance systems and RTI (Right to Information) portals.
- Localized language translation support for regional municipal languages.

---

## 3. Video Demonstration Script (< 3 Minutes)

**Total Duration:** 2 minutes 45 seconds  
**Visuals:** Screen recording with voiceover (no background music)

### [0:00 - 0:30] Hook & Problem
- **Voiceover:** *"Every day, thousands of students and residents walk past dangerous hazards like this 3-foot pothole outside a college gate. But filing a municipal complaint is intimidating. Citizens don't know who is responsible, how to write a formal letter, or how to follow up. Meet CivicPulse AI — an intelligent civic action platform powered by NVIDIA Nemotron on Nebius Token Factory."*
- **Action:** Show the CivicPulse AI Dashboard with metric cards and category breakdown.

### [0:30 - 1:15] Real Report Submission & Nebius/Nemotron Inference
- **Voiceover:** *"Let's report an incident. We'll use our fast-fill demo scenario: a severe pothole causing student motorcycle accidents. Notice our location, category, and detailed description. Now, let's trigger a real inference request to Nebius Token Factory."*
- **Action:** Click '🚧 Campus Gate Pothole'. Point to form fields. Click '⚡ Run Real AI Analysis with NVIDIA Nemotron'. Show the real-time spinner.

### [1:15 - 2:00] Generated Case Plan & Actionable Triage
- **Voiceover:** *"In seconds, NVIDIA Nemotron analyzes the hazard. Notice how it classifies the urgency as High with factual reasoning. Crucially, it separates what the citizen stated from inferred risk assumptions. Here is the formal complaint draft addressed to the Municipal Road Maintenance division, ready to copy and paste. And below, a concrete evidence checklist and a 7-day follow-up timeline."*
- **Action:** Scroll through the analysis tabs: Facts vs Assumptions, Complaint Letter, and Evidence Checklist.

### [2:00 - 2:30] Case Management & Technical Architecture
- **Voiceover:** *"Under Case Management, every report is tracked in a local SQLite database. We can filter by urgency, update the status from Open to In Progress, append field notes from local officials, and export the entire dossier as a clean Markdown report. In the Settings tab, we can verify our live connectivity to the Nebius Token Factory endpoint and inspect available models."*
- **Action:** Switch to 'Case Management'. Update status to 'In Progress'. Add a quick note. Switch to 'Settings & API Status' and show verified Nebius connection.

### [2:30 - 2:45] Conclusion & Hackathon Track
- **Voiceover:** *"CivicPulse AI turns citizen frustration into structured, accountable civic action using state-of-the-art NVIDIA Nemotron models hosted on Nebius high-performance infrastructure. Thank you!"*
- **Action:** Return to Dashboard with updated resolved/in-progress counts.
