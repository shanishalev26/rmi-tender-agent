import requests
import json
import os

BASE = "https://apps.land.gov.il/MichrazimSite"
SEARCH_URL = f"{BASE}/api/SearchApi/Search"

#הסינון ששלח האתר: מכרזים פעיליםב
payload = {
    "Uchlusiya": [],
    "QuickResultsInMonth": False,
    "QuickResultsIWeek": False,
    "FromCloseDate": None,
    "ToCloseDate": None,
    "ActiveQuickSearch": False,
    "ActiveMichraz": True,
}

# כותרות שגורמות לבקשה להיראות כמו דפדפן אמיתי
headers = {
    "Content-Type": "application/json",
    "Accept": "application/json, text/plain, */*",
    "Origin": BASE,
    "Referer": BASE + "/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15",
}

session = requests.Session()
session.get(BASE + "/", headers=headers, timeout=30)  # חימום - אוסף cookies


resp = session.post(SEARCH_URL, json=payload, headers=headers, timeout=30)
print("Status:", resp.status_code)

tenders = resp.json()

# שמירה לקובץ מסודר, במקום הדפסה לטרמינל שהופך עברית
os.makedirs("data", exist_ok=True)
with open("data/tenders.json", "w", encoding="utf-8") as f:
    json.dump(tenders, f, ensure_ascii=False, indent=2)

print("saved", len(tenders), "tenders -> data/tenders.json")