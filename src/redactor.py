import copy

def redact_records(records_found: dict) -> dict:
    """Masks third-party referral personal data under Policy Section 2.4 & 7.4."""
    redacted = copy.deepcopy(records_found)

    # Redact CRM records (mask third-party referral details)
    if "crm" in redacted:
        for record in redacted["crm"]:
            if "third_party_referral" in record and record["third_party_referral"]:
                record["third_party_referral"] = "[REDACTED_THIRD_PARTY_REFERRAL]"

    # Billing records don't contain third-party customer PII, but keep structure
    if "billing" not in redacted:
        redacted["billing"] = []

    # Activity logs keep user's own logs, but can mask internal staff notes if present
    if "activity_logs" not in redacted:
        redacted["activity_logs"] = []

    return redacted

if __name__ == "__main__":
    sample_crm = [{
        "user_id": "U001",
        "name": "Rahul Sharma",
        "email": "rahul.sharma@gmail.com",
        "third_party_referral": "Amit Verma (amit.verma@gmail.com)"
    }]
    print("Testing Redaction Tool on CRM record...")
    print("Before Redaction:", sample_crm[0]["third_party_referral"])
    res = redact_records({"crm": sample_crm})
    print("After Redaction: ", res["crm"][0]["third_party_referral"])

