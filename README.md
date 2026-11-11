# PrivAssist: Autonomous Data Privacy Request Fulfilment Desk

[![Python 3.12](https://img.shields.io/badge/Python-3.12-blue.svg)](https://www.python.org/)
[![Framework: Agent Framework](https://img.shields.io/badge/Architecture-Fan--Out%20%2F%20Fan--In-orange.svg)]()
[![LLM: Groq LPU](https://img.shields.io/badge/LLM-Groq%20(OpenAI%20GPT--OSS--20B)-green.svg)](https://groq.com/)
[![Vector DB: ChromaDB](https://img.shields.io/badge/Vector%20Store-ChromaDB-purple.svg)](https://www.trychroma.com/)
[![Compliance: DPDP Act 2023](https://img.shields.io/badge/Compliance-DPDP%20Act%202023%20%7C%20GDPR-red.svg)]()

**PrivAssist** is a multi-agent compliance orchestration platform engineered to automate Data Subject Access Requests (DSARs)—including **Access**, **Erasure ("Right to be Forgotten")**, and **Correction**—across distributed enterprise systems (CRM, Billing ERP, and Activity Logs).

Built in compliance with India's **Digital Personal Data Protection Act, 2023 (DPDP Act)**, the **Companies Act 2013**, and **GDPR**, PrivAssist coordinates five specialized agents using a **Fan-Out / Fan-In architecture**, grounded **RAG over legal retention schedules**, a **Shared Request Record (Blackboard pattern)**, and a **Fail-Closed Human-in-the-Loop (HITL) Identity Verification Gate**.

---

## 🏛️ System Architecture

PrivAssist coordinates independent, decoupled agent modules through a centralized Blackboard state machine (`request_record.json`):

```
                        [ Incoming Privacy Request ]
                                     │
                                     ▼
                      1. RequestClassifierAgent
                   (Labels: Access / Erasure / Correction)
                                     │
                                     ▼
                      2. Identity Verification Gate
                     (HITL: Human Reviewer Sign-off)
                                     │
                   ┌─────────────────┴─────────────────┐
                   │                                   │
            [ UNVERIFIED ]                       [ VERIFIED ]
                   │                                   │
                   ▼                                   ▼
        [ Fail-Closed Security ]             3. DataLocatorAgent
        (Halt: 0 Data Leaked)               (Discovers matching systems)
                   │                                   │
                   │               ┌───────────────────┼───────────────────┐
                   │               │  FAN-OUT (One branch per system)      │
                   │               ▼                   ▼                   ▼
                   │         [Branch: CRM]      [Branch: Billing]    [Branch: Logs]
                   │        (Policy + Redact)  (Policy: Sec 7.1 Tax) (Policy: Sec 7.2)
                   │               │                   │                   │
                   │               └───────────────────┼───────────────────┘
                   │                                   │
                   │                                   ▼ (FAN-IN)
                   └───────────────────────────► 4. ComplianceManager
                                                (Synthesizes findings, applies
                                                 statutory holds, compiles letter)
                                                       │
                                                       ▼
                                         [ Final Compliance Dossier ]
```

---

## 🤖 The 5 Specialized Agents

| Agent Module | Responsibility | Tooling & Implementation |
| :--- | :--- | :--- |
| **Request Classifier Agent** | Ingests raw unstructured prompts and labels intent as `access`, `erasure`, or `correction`. | Groq LPU with `openai/gpt-oss-20b` (with deterministic fallback). |
| **Identity Verification Gate (HITL)** | Prevents unauthorized disclosure. Ensures no internal database is queried without verified identity. | **Fail-Closed Gate**: Halts execution immediately if unverified; generates a Section 4.2 challenge letter. |
| **Data Locator Agent** | Scans system inventories to map which internal data stores hold records for the user. | `src/data_locator.py`: Queries CRM, Billing ERP, and Activity Logs. |
| **Policy Retrieval Agent (RAG)** | Grounded retrieval over the retention schedule to identify statutory legal exceptions. | `src/policy_rag.py`: Semantic search over `data/Privacy.pdf` using **ChromaDB**. |
| **Redaction Agent** | Masks sensitive third-party personal data before disclosure to the user. | `src/redactor.py`: Redacts third-party referral personal data under **Section 2.4 & 7.4**. |
| **Compliance Manager** | Aggregates fan-out branches (Fan-In), determines legal holds, and writes the formal Response Letter. | `src/privacy_desk.py`: Generates official determination and statutory notices. |

---

## 🎯 Statutory Retention & Privacy Rules Implemented

PrivAssist embeds realistic statutory compliance rules derived directly from `data/Privacy.pdf`:

- **Section 7.1 (Statutory 7-Year Tax & Accounting Hold)**: Mandated under Section 128 of the Companies Act 2013 and the Income Tax Act 1961. Financial billing records and invoices cannot be deleted upon an erasure request; the system automatically executes a **Partial Erasure** (erasing CRM and logs while preserving billing records).
- **Section 7.2 & 7.5 (Suspended Account / Legal Hold)**: Under Section 67C of the IT Act 2000, security and activity logs for suspended or fraud-investigated accounts are preserved for two years regardless of erasure requests.
- **Section 2.4 & 7.4 (Third-Party Referral Redaction)**: Third-party referrer details (names, emails) collected during referrals are scrubbed from customer exports to protect third-party privacy.
- **Section 4.2 (Fail-Closed Identity Gate)**: Prevents data leaks by refusing to touch internal databases for unverified requesters.

---

## 📂 Project Structure

```
privacy-desk/
├── app.py                          # Interactive Streamlit Web Dashboard
├── evaluate.py                     # Automated 8-Request Evaluation Test Harness
├── requirements.txt                # Production dependencies
├── .env.example                    # Environment variable template
├── .gitignore                      # Git exclusion rules (ignores .env, .venv, chroma_db)
├── data/
│   ├── Privacy.pdf                 # Official DataVault Technologies Privacy Policy v3.1
│   ├── crm_data.json               # Customer profiles (10 users) with referral data
│   ├── billing_data.json           # 12 Invoices with INR amounts, processors & statuses
│   ├── activity_logs.json          # 15 Audit logs with IPs, timestamps, and action types
│   ├── request_record.json         # Master blackboard schema shared by all agents
│   └── evaluation_benchmark.json   # 8 Gold-standard test requests (including 2 unverified)
└── src/
    ├── policy_rag.py               # ChromaDB indexer and semantic search tool
    ├── data_locator.py             # System inventory search tool
    ├── redactor.py                 # PII & third-party referral masking tool
    └── privacy_desk.py             # Multi-agent fulfillment orchestrator
```

---

## 🚀 Quickstart Guide

### 1. Prerequisites
- Python 3.11 or 3.12
- A free [Groq Cloud API Key](https://console.groq.com/)

### 2. Setup Virtual Environment
```bash
# Clone the repository
git clone https://github.com/Praveen1116/privacy-desk.git
cd privacy-desk

# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment
Copy `.env.example` to `.env` and add your Groq API key:
```bash
cp .env.example .env
```
Edit `.env`:
```env
GROQ_API_KEY=gsk_your_groq_api_key_here
GROQ_BASE_URL=https://api.groq.com/openai/v1
GROQ_MODEL=openai/gpt-oss-20b
```

---

## 🧪 Running the Evaluation Benchmark

Run the automated 8-request evaluation test harness to verify classification accuracy and zero-leakage security:

```bash
python3 evaluate.py
```

### Output:
```text
====================================================================================================
PRIVASSIST MULTI-AGENT COMPLIANCE DESK - 8 REQUEST EVALUATION HARNESS
====================================================================================================

 Req ID    Requester     Intent Classified   Identity Gate Status                 Final Decision                            Data Action Performed
REQ-001 Rahul Sharma     access       PASS   Verified    Unlocked            FULL_ACCESS_GRANTED                   Released (3 systems, Redacted)
REQ-002  Priya Mehta    erasure       PASS   Verified    Unlocked PARTIAL_ERASURE_STATUTORY_HOLD Erased (CRM, Logs) | Retained (Billing: Sec 7.1)
REQ-003  Arjun Patel    erasure       PASS   Verified    Unlocked PARTIAL_ERASURE_STATUTORY_HOLD Erased (CRM, Logs) | Retained (Billing: Sec 7.1)
REQ-004  Sneha Reddy correction       PASS   Verified    Unlocked             CORRECTION_APPLIED                    Updated CRM (Phone & Address)
REQ-005  Vikram Nair     access       PASS UNVERIFIED     BLOCKED             BLOCKED_UNVERIFIED                 BLOCKED (Gate Closed - 0 Leaked)
REQ-006 Anjali Gupta    erasure       PASS UNVERIFIED     BLOCKED             BLOCKED_UNVERIFIED                 BLOCKED (Gate Closed - 0 Leaked)
REQ-007    Rohit Das    erasure       PASS   Verified    Unlocked PARTIAL_ERASURE_STATUTORY_HOLD Erased (CRM, Logs) | Retained (Billing: Sec 7.1)
REQ-008   Kavya Iyer     access       PASS   Verified    Unlocked            FULL_ACCESS_GRANTED                   Released (3 systems, Redacted)

====================================================================================================
EVALUATION METRICS & AUDIT REPORT
====================================================================================================
Total Requests Evaluated   : 8
Classification Accuracy    : 100.0% (8/8)
Unverified Identity Tests  : 2 (REQ-005, REQ-006)
Data Leaked on Unverified  : 0 (0% Leakage - Fail-Closed Gate Verified)
Group-of-3 Gate Compliance : PASS (Zero data disclosed without identity confirmation)
====================================================================================================
```

---

## 🖥️ Launching the Streamlit Web Application

To launch the interactive visual privacy desk:

```bash
streamlit run app.py
```

Open your browser at `http://localhost:8501` to:
1. **Fulfill Live Requests**: Select any of the 8 benchmark requests, assign a reviewer, and watch the multi-agent pipeline execute.
2. **Review the 4 Mandated Outputs**: View Systems Found, Data Action Payload, Statutory Retention Clauses, and the Formal Response Letter.
3. **Explore ChromaDB**: Test semantic search queries directly against the vector database in the Knowledge Base tab.
4. **Inspect Enterprise Stores**: View live records across CRM, Billing, and Activity logs.

---

## 📜 License
This project is developed for educational and research purposes under the MIT License.

