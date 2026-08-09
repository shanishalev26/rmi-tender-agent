import argparse
import json
from pathlib import Path

from analyze import analyze
from planning import find_plans_for_tender
from matching import calculate_match_for_file, load_json
from company_profile import load_profile

TENDERS_PATH = Path("data/tenders.json")
ANALYSIS_DIR = Path("data/analysis")


from datetime import datetime, timezone

def pick_michraz_ids(count):
    """בוחר את המכרזים שנסגרים הכי בקרוב מבין אלה שעוד פתוחים."""
    tenders = json.loads(TENDERS_PATH.read_text(encoding="utf-8"))
    now = datetime.now(timezone.utc)

    def closing_date(t):
        raw = t.get("SgiraDate")
        if not raw:
            return None
        try:
            return datetime.fromisoformat(raw)
        except ValueError:
            return None

    # רק מכרזים שמועד הסגירה שלהם עדיין בעתיד
    still_open = [
        t for t in tenders
        if closing_date(t) and closing_date(t) > now
    ]

    # מיון מהמועד הקרוב ביותר להגשה ואילך
    still_open.sort(key=closing_date)

    return [t["MichrazID"] for t in still_open[:count]]


def build(count, refresh):
    profile = load_profile()
    michraz_ids = pick_michraz_ids(count)

    print(f"Building dataset for {len(michraz_ids)} tenders "
          f"(refresh={refresh})\n")

    for michraz_id in michraz_ids:
        analysis_path = ANALYSIS_DIR / f"{michraz_id}.json"

        # דילוג על מכרז שכבר נותח, אלא אם ביקשו רענון
        if analysis_path.exists() and not refresh:
            print(f"SKIP {michraz_id} (already analyzed)")
            continue

        print(f"--- {michraz_id} ---")
        try:
            analyze(michraz_id)                 # פרטים + חוברת + חילוץ AI
            find_plans_for_tender(michraz_id)   # חיפוש תב"ע
            record = load_json(analysis_path)    # התאמה לפרופיל
            calculate_match_for_file(analysis_path, profile)
        except Exception as error:
            print(f"FAILED {michraz_id}: {error}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Build the analysis dataset for several tenders"
    )
    parser.add_argument("--count", type=int, default=7,
                        help="how many tenders to process")
    parser.add_argument("--refresh", action="store_true",
                        help="re-analyze tenders that already exist")
    args = parser.parse_args()

    build(args.count, args.refresh)