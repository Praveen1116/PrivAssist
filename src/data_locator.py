import json
from pathlib import Path

DATA_DIR = Path("data")

def locate_user_records(user_id: str = "", email: str = "") -> dict:
    """Interrogates CRM, Billing, and Activity logs for a given user_id or email."""
    # 1. Search CRM
    crm_path = DATA_DIR / "crm_data.json"
    crm_records = []
    if crm_path.exists():
        with open(crm_path, "r", encoding="utf-8") as f:
            for item in json.load(f):
                if (user_id and item.get("user_id") == user_id) or (email and item.get("email") == email):
                    crm_records.append(item)
                    if not user_id:
                        user_id = item.get("user_id", "")

    # 2. Search Billing
    billing_path = DATA_DIR / "billing_data.json"
    billing_records = []
    if billing_path.exists() and user_id:
        with open(billing_path, "r", encoding="utf-8") as f:
            billing_records = [inv for inv in json.load(f) if inv.get("user_id") == user_id]

    # 3. Search Activity Logs
    logs_path = DATA_DIR / "activity_logs.json"
    log_records = []
    if logs_path.exists() and user_id:
        with open(logs_path, "r", encoding="utf-8") as f:
            log_records = [log for log in json.load(f) if log.get("user_id") == user_id]

    records_found = {
        "crm": crm_records,
        "billing": billing_records,
        "activity_logs": log_records
    }
    systems_with_data = [sys for sys, recs in records_found.items() if len(recs) > 0]

    return {
        "systems_searched": ["crm", "billing", "activity_logs"],
        "records_found": records_found,
        "systems_with_data": systems_with_data
    }

if __name__ == "__main__":
    print("Testing Data Locator Tool for user U001 (Rahul Sharma)...")
    result = locate_user_records(user_id="U001")
    print(f"Systems with data: {result['systems_with_data']}")
    print(f"CRM records: {len(result['records_found']['crm'])}")
    print(f"Billing records: {len(result['records_found']['billing'])}")
    print(f"Log records: {len(result['records_found']['activity_logs'])}")

