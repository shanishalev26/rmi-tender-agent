import argparse
from datetime import datetime, timezone

from analysis_store import get_analysis_path
from analyze import analyze
from company_profile import load_profile
from fetch_tenders import fetch_active_tenders, save_tenders
from matching import calculate_match_for_file
from planning import find_plans_for_tender
from rmi_client import get_session


def get_closing_date(tender):
    """Returns a tender closing date, or None when it is invalid"""
    raw = tender.get("SgiraDate")

    if not raw:
        return None

    try:
        parsed = datetime.fromisoformat(
            str(raw).replace("Z", "+00:00")
        )

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)

        return parsed

    except (TypeError, ValueError):
        return None


def pick_michraz_ids(tenders, count):
    """Returns the nearest open tender IDs from a fresh RMI list"""
    if count <= 0:
        raise ValueError("count must be a positive integer")

    now = datetime.now(timezone.utc)
    open_tenders = []

    for tender in tenders:
        deadline = get_closing_date(tender)

        if deadline is not None and deadline > now:
            open_tenders.append((deadline, tender))

    open_tenders.sort(key=lambda item: item[0])

    selected_ids = []

    for deadline, tender in open_tenders[:count]:
        selected_ids.append(tender["MichrazID"])

    return selected_ids


def build(count, refresh):
    """Fetches active tenders and runs the analysis pipeline"""
    if count <= 0:
        raise ValueError("count must be a positive integer")

    session = get_session()
    tenders = fetch_active_tenders(session)
    save_tenders(tenders)

    profile = load_profile()
    michraz_ids = pick_michraz_ids(tenders, count)

    print(f"Building dataset for {len(michraz_ids)} tenders "
          f"(refresh={refresh})\n")

    for michraz_id in michraz_ids:
        analysis_path = get_analysis_path(michraz_id)

        # דילוג על מכרז שכבר נותח, אלא אם ביקשו רענון
        if analysis_path.exists() and not refresh:
            print(f"SKIP {michraz_id} (already analyzed)")
            continue

        print(f"--- {michraz_id} ---")
        try:
            analyze(michraz_id)
            find_plans_for_tender(michraz_id)
            calculate_match_for_file(analysis_path, profile)
        except Exception as error:
            print(f"FAILED {michraz_id}: {error}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--count", type=int, default=7)
    parser.add_argument("--refresh", action="store_true")

    args = parser.parse_args()
    build(args.count, args.refresh)


if __name__ == "__main__":
    main()
