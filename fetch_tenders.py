import json
import os

from rmi_client import BASE, HEADERS, get_session

SEARCH_URL = f"{BASE}/api/SearchApi/Search"

# Match the RMI frontend search payload. ActiveMichraz selects active tenders.
SEARCH_PAYLOAD = {
    "Uchlusiya": [],
    "QuickResultsInMonth": False,
    "QuickResultsIWeek": False,
    "FromCloseDate": None,
    "ToCloseDate": None,
    "ActiveQuickSearch": False,
    "ActiveMichraz": True,
}


def fetch_active_tenders(session):
    """Fetches active tenders from the RMI search API and returns them as a list."""
    response = session.post(
        SEARCH_URL,
        json=SEARCH_PAYLOAD,
        headers=HEADERS,
        timeout=30,
    )

    # Do not parse or save an HTTP error response as tender data
    response.raise_for_status()
    tenders = response.json()

    if not isinstance(tenders, list):
        raise ValueError(
            "RMI SearchApi returned an unexpected response format"
        )

    return tenders


def save_tenders(tenders):
    """Saves the current tender list to data/tenders.json."""
    # This file is a current snapshot, so each refresh replaces the old list.
    os.makedirs("data", exist_ok=True)

    with open("data/tenders.json", "w", encoding="utf-8") as file:
        json.dump(tenders, file, ensure_ascii=False, indent=2)


def main():
    """Fetches and saves the current active tenders"""
    session = get_session()
    tenders = fetch_active_tenders(session)
    save_tenders(tenders)
    print(f"saved {len(tenders)} tenders -> data/tenders.json")


if __name__ == "__main__":
    main()
