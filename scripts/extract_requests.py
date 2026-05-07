from unmet_demand.db import connect, init_db
from unmet_demand.extract.extractor import extract_requests


if __name__ == "__main__":
    init_db()
    with connect() as conn:
        count = extract_requests(conn)
    print(f"Extracted {count} requests.")
