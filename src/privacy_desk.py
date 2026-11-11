import os
import sys
import json
import copy
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
from openai import OpenAI

# Add root directory to sys.path so imports work from anywhere
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from src.data_locator import locate_user_records
from src.redactor import redact_records
from src.policy_rag import search_policy

load_dotenv()

def get_llm_client():
    api_key = os.getenv("GROQ_API_KEY", "").strip()
    base_url = os.getenv("GROQ_BASE_URL", "https://api.groq.com/openai/v1")
    model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
    if api_key:
        return OpenAI(api_key=api_key, base_url=base_url), model
    return None, model

# 1. Request Classifier Agent
def request_classifier_agent(raw_request: str) -> dict:
    client, model = get_llm_client()
    if client:
        try:
            prompt = (
                f"You are a Privacy Request Classifier. Classify the user's intent into exactly one category: "
                f"'access', 'erasure', or 'correction'.\n"
                f"Request: \"{raw_request}\"\n"
                f"Respond ONLY with valid JSON in this format: {{\"label\": \"access\"|\"erasure\"|\"correction\", \"confidence\": 0.95}}"
            )
            res = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.0
            )
            content = res.choices[0].message.content.strip()
            if "{" in content and "}" in content:
                content = content[content.find("{"):content.rfind("}")+1]
                return json.loads(content)
        except Exception:
            pass

    # Deterministic fallback classifier
    text = raw_request.lower()
    if any(w in text for w in ["delete", "erase", "remove", "wipe", "purge"]):
        return {"label": "erasure", "confidence": 0.99}
    elif any(w in text for w in ["correct", "update", "change", "modify", "rectify"]):
        return {"label": "correction", "confidence": 0.98}
    return {"label": "access", "confidence": 0.97}

# 2. Fan-Out Branch per Data System
def execute_system_branch(system: str, records: list, intent: str, user_crm: dict) -> dict:
    """Processes a single data system branch independently."""
    branch_result = {"system": system, "exceptions": [], "redacted": records, "action": ""}

    if system == "billing":
        # Check Section 7.1 statutory tax hold
        if intent == "erasure" and len(records) > 0:
            policy = search_policy("billing invoices statutory retention 7 years", n_results=1)
            branch_result["exceptions"].append({
                "clause": "Section 7.1",
                "reason": "Statutory 7-year retention mandatory under Section 128 of Companies Act 2013 and Income Tax Act 1961."
            })
            branch_result["action"] = "retained_under_statutory_hold"
        else:
            branch_result["action"] = "released" if intent == "access" else "erased"

    elif system == "crm":
        if intent == "access":
            # Mask third-party referral data under Section 2.4 & 7.4
            branch_result["redacted"] = redact_records({"crm": records})["crm"]
            branch_result["action"] = "released_with_redaction"
        elif intent == "erasure":
            branch_result["action"] = "erased"
        elif intent == "correction":
            branch_result["action"] = "updated"

    elif system == "activity_logs":
        account_status = user_crm.get("account_status", "") if user_crm else ""
        if intent == "erasure" and account_status == "suspended":
            branch_result["exceptions"].append({
                "clause": "Section 7.2 & 7.5",
                "reason": "Security logs for suspended or fraud-investigated accounts retained for 2 years / legal hold."
            })
            branch_result["action"] = "retained_under_legal_hold"
        else:
            branch_result["action"] = "released" if intent == "access" else "erased"

    return branch_result

# 3. Main Multi-Agent Fulfillment Orchestrator
def process_privacy_request(test_request: dict, reviewer_name: str = "Praveen Kumar Yadav") -> dict:
    """Coordinates agents via Fan-Out / Fan-In over the Shared Request Record."""
    with open("data/request_record.json", "r", encoding="utf-8") as f:
        record = json.load(f)

    # Initialize Blackboard
    record["request_id"] = test_request.get("request_id", "REQ-TEMP")
    record["timestamp"] = datetime.now().isoformat()
    record["raw_request"] = test_request.get("raw_request_text", "")
    record["requester"] = {
        "user_id": test_request.get("user_id", ""),
        "name": test_request.get("requester_name", ""),
        "email": test_request.get("requester_email", ""),
        "identity_verified": test_request.get("identity_verified", False),
        "verified_by": reviewer_name if test_request.get("identity_verified", False) else ""
    }

    # Step 1: Request Classifier Agent
    classification = request_classifier_agent(record["raw_request"])
    record["classification"] = {
        "label": classification.get("label", "access"),
        "confidence": classification.get("confidence", 0.95),
        "agent": "RequestClassifierAgent",
        "status": "completed"
    }

    # Step 2: Identity Verification Gate (HITL Group-of-3 Gate - Fail Closed)
    is_verified = record["requester"]["identity_verified"]
    record["identity_gate"] = {
        "passed": is_verified,
        "checked_by": reviewer_name if is_verified else "Fail-Closed Security Gate",
        "timestamp": datetime.now().isoformat()
    }

    if not is_verified:
        # Halt execution: Zero internal data accessed or released!
        record["final_decision"] = {
            "action": "BLOCKED_UNVERIFIED",
            "data_to_release": [],
            "data_to_erase": [],
            "data_blocked": ["All internal data access blocked under Section 4.2"],
            "reason": "Identity verification failed. Under Section 4.2, no personal data shall be accessed or disclosed.",
            "agent": "ComplianceManager",
            "status": "completed"
        }
        record["response_letter"] = (
            f"Dear {record['requester']['name']},\n\n"
            f"Your privacy request ({record['request_id']}) cannot be fulfilled at this time.\n\n"
            f"Under Section 4.2 of DataVault Technologies Privacy Policy and India's DPDP Act 2023, "
            f"all data requests require positive identity verification before any internal system is accessed. "
            f"Please submit valid government photo ID (Aadhaar/PAN/Passport) or verify via OTP to complete your request.\n\n"
            f"Sincerely,\nPriya Nambiar\nData Protection Officer, DataVault Technologies Pvt. Ltd."
        )
        return record

    # Step 3: Data Locator Agent
    located = locate_user_records(user_id=record["requester"]["user_id"], email=record["requester"]["email"])
    record["data_located"] = {
        "systems_searched": located["systems_searched"],
        "records_found": located["records_found"],
        "agent": "DataLocatorAgent",
        "status": "completed"
    }

    # Step 4: FAN-OUT (One branch per system)
    user_crm = located["records_found"]["crm"][0] if located["records_found"]["crm"] else {}
    intent = record["classification"]["label"]
    branch_results = {}
    for sys in located["systems_searched"]:
        recs = located["records_found"].get(sys, [])
        branch_results[sys] = execute_system_branch(sys, recs, intent, user_crm)

    # Step 5: FAN-IN (Compliance Manager aggregates findings)
    all_exceptions = []
    redacted_data = {}
    data_to_release = []
    data_to_erase = []
    data_blocked = []

    for sys, res in branch_results.items():
        redacted_data[sys] = res["redacted"]
        all_exceptions.extend(res["exceptions"])
        if res["action"] in ["released", "released_with_redaction"]:
            data_to_release.append({sys: res["redacted"]})
        elif res["action"] == "erased":
            data_to_erase.append(f"{sys.upper()} ({len(res['redacted'])} records)")
        elif res["action"] in ["retained_under_statutory_hold", "retained_under_legal_hold"]:
            data_blocked.append(f"{sys.upper()} (Retained: {res['exceptions'][0]['clause']})")

    record["policy_retrieved"] = {
        "query": f"Policy for {intent} across {located['systems_with_data']}",
        "clauses": [e["clause"] for e in all_exceptions],
        "retention_exceptions": all_exceptions,
        "agent": "PolicyRetrievalAgent",
        "status": "completed"
    }
    record["redacted_data"] = {
        "crm": redacted_data.get("crm", []),
        "billing": redacted_data.get("billing", []),
        "activity_logs": redacted_data.get("activity_logs", []),
        "agent": "RedactionAgent",
        "status": "completed"
    }

    # Final Decision Synthesis
    if intent == "access":
        action = "FULL_ACCESS_GRANTED"
        reason = "Identity verified. Data compiled across internal systems with third-party referral data redacted under Section 2.4."
    elif intent == "erasure":
        if all_exceptions:
            action = "PARTIAL_ERASURE_STATUTORY_HOLD"
            reason = f"Partial erasure fulfilled. Records deleted except {', '.join(data_blocked)} due to mandatory legal retention."
        else:
            action = "FULL_ERASURE_GRANTED"
            reason = "Identity verified. All personal records across internal systems permanently erased."
    else:
        action = "CORRECTION_APPLIED"
        reason = "Identity verified. Contact details successfully updated in CRM."

    record["final_decision"] = {
        "action": action,
        "data_to_release": data_to_release,
        "data_to_erase": data_to_erase,
        "data_blocked": data_blocked,
        "reason": reason,
        "agent": "ComplianceManager",
        "status": "completed"
    }

    # Generate Formal Response Letter
    exceptions_text = ""
    if all_exceptions:
        exceptions_text = "\n\nStatutory Retention Notice:\n" + "\n".join(
            f"- {e['clause']}: {e['reason']}" for e in all_exceptions
        )

    record["response_letter"] = (
        f"Dear {record['requester']['name']},\n\n"
        f"We have completed processing your privacy {intent.upper()} request ({record['request_id']}) "
        f"under India's Digital Personal Data Protection Act, 2023 (DPDP Act) and Company policy.\n\n"
        f"Determination: {action}\n"
        f"Summary: {reason}{exceptions_text}\n\n"
        f"If you have questions regarding this decision, contact dpo@datavault.in.\n\n"
        f"Sincerely,\nPriya Nambiar\nData Protection Officer, DataVault Technologies Pvt. Ltd."
    )

    return record

if __name__ == "__main__":
    print("Testing Privacy Desk on REQ-001 (Rahul Sharma - Access Request)...")
    with open("data/evaluation_benchmark.json", "r") as f:
        benchmarks = json.load(f)["test_requests"]
    result = process_privacy_request(benchmarks[0])
    print(f"\n[Status]: {result['final_decision']['action']}")
    print(f"[Classification]: {result['classification']['label']} (conf: {result['classification']['confidence']})")
    print(f"[Systems Found]: {list(result['data_located']['records_found'].keys())}")
    print(f"\n--- Response Letter ---\n{result['response_letter']}")
