import requests

BASE = "https://apps.land.gov.il/MichrazimSite"

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": BASE,
    "Referer": BASE + "/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15",
}


def get_session():
    """Creates and initializes a session for RMI API requests."""
    session = requests.Session()

    # Keep cookies between requests. First access the RMI website,
    # then reuse the same session for API calls.
    session.get(BASE + "/", headers=HEADERS, timeout=30)
    return session
