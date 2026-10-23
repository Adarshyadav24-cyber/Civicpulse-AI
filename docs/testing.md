# CivicPulse AI — Testing Guide & Verification Procedure

This guide details both automated test execution and the manual end-to-end verification procedure for the **Nebius Token Factory** and **NVIDIA Nemotron** integration.

---

## 1. Automated Unit & Integration Tests

The test suite validates input sanitization, database CRUD operations, filtering, markdown export generation, and mocked model responses without expending real API tokens during CI/CD.

### Running Automated Tests
Run pytest in your terminal:
```powershell
.\.venv\Scripts\pytest -v
```

### Test Coverage Areas
1. **Schema Validation (`tests/test_schemas.py`)**:
   - Rejection of short titles (< 5 characters) and short descriptions (< 20 characters).
   - Rejection of invalid urgency values (must strictly be `Low`, `Medium`, `High`, or `Critical`).
   - Rejection of missing required fields in AI output.
2. **Database Persistence (`tests/test_database.py`)**:
   - SQLite table initialization and index creation.
   - Case creation and verification of `CP-2026-XXXX` format.
   - Status transitions (`Open` -> `In Progress` -> `Resolved`).
   - Appending timestamped follow-up notes.
   - Category, urgency, status, and full-text keyword search.
   - Permanent deletion with note cleanup.
   - Markdown case export verification.
3. **AI Services & Error Handling (`tests/test_ai_service.py`)**:
   - Extraction of JSON from Markdown code blocks (`_clean_json_response`).
   - Mocked successful inference response from NVIDIA Nemotron.
   - Handling of missing credentials (`NebiusMissingCredentialsError`).
   - Handling of malformed JSON strings (`NebiusClientError`).
   - Safe verification of `/v1/models` without leaking secrets.

---

## 2. Manual Verification Procedure (Real Nebius Token Factory Request)

Follow these steps to perform genuine inference with **NVIDIA Nemotron** on Nebius Token Factory:

### Step 1: Obtain a Nebius Token Factory API Key
1. Sign in to your account at [Nebius Token Factory](https://tokenfactory.nebius.com/).
2. Navigate to **API Keys** and generate a new key.
3. Copy the key.

### Step 2: Configure Local Credentials
Open `.env` (or create it from `.env.example`) and add your key:
```ini
NEBIUS_API_KEY=your_actual_nebius_api_key_here
NEBIUS_BASE_URL=https://api.tokenfactory.us-central1.nebius.com/v1/
NEBIUS_MODEL=nvidia/Llama-3.1-Nemotron-70B-Instruct
```

### Step 3: Launch the Application
```powershell
.\.venv\Scripts\streamlit run app.py
```
Open `http://localhost:8501` in your browser.

### Step 4: Verify Live Connectivity
1. In the sidebar, select **⚙️ Settings & API Status**.
2. Click **⚡ Test Nebius API Connection Now**.
3. Verify that the response returns `Successfully connected to Nebius Token Factory` and confirms that the configured NVIDIA model is available.

### Step 5: Test Real AI Case Plan Generation
1. Navigate to **📝 Report an Issue**.
2. Click **🚧 Campus Gate Pothole** to populate the form with realistic data.
3. Click **⚡ Run Real AI Analysis with NVIDIA Nemotron**.
4. Observe the spinner indicating real inference.
5. Review the generated output:
   - Check the **Urgency Recommendation** and **Urgency Reasoning**.
   - Review the **Verified Facts** vs. **Inferred Assumptions** section.
   - Review the **Formal Complaint Draft** tailored to the municipal department.
   - Check off items in the **Evidence Checklist**.
6. Switch to **📁 Case Management** to confirm the case was persisted in SQLite.
7. Click **⬇️ Export Case (.md)** to download the case report.
