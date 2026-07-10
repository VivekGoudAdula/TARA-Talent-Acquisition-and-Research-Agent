"""One-shot demo patch: set Krishna contact on all internal + external leads."""

from datetime import datetime

from app.db.mongo import get_database

EMAIL = "krishnajai008@gmail.com"
PHONE = "+918897371942"
NOW = datetime.utcnow()

PATCH = {"phone_number": PHONE, "email": EMAIL, "updated_at": NOW}


def main() -> None:
    db = get_database()
    internal = db["customers"].update_many({}, {"$set": PATCH})
    external = db["external_leads"].update_many({}, {"$set": PATCH})
    print(f"customers: matched={internal.matched_count} modified={internal.modified_count}")
    print(f"external_leads: matched={external.matched_count} modified={external.modified_count}")


if __name__ == "__main__":
    main()
