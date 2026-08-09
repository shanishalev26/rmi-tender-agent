import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin

import requests

PLANNING_PAGE_URL = "https://apps.land.gov.il/TabaSearch/"
PLANNING_API_URL = (
    "https://apps.land.gov.il/"
    "TabaSearch/api/SerachPlans/GetPlans"
)
PLAN_DETAIL_API_URL = (
    "https://apps.land.gov.il/"
    "TabaSearch/api/Plan/GetPlanData"
)

def load_analysis(michraz_id):
    path = Path(f"data/analysis/{michraz_id}.json")

    if not path.exists():
        raise FileNotFoundError(
            f"Analysis file was not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file), path


def get_ai_plan_number(record):
    """
    Read the plan number extracted by the AI.
    Return None when the AI did not find one.
    """

    ai_source = (
        record
        .get("sources", {})
        .get("tender_booklet_ai", {})
    )

    ai_data = ai_source.get("data") or {}
    plan_field = ai_data.get("plan_number") or {}
    value = plan_field.get("value")

    if value is None:
        return None

    value = str(value).strip()
    return value or None


def get_structured_plan_numbers(api_data):
    results = []

    for value in api_data.get("מספרי תכנית מובנים", []):
        value = str(value or "").strip()

        if value and value not in results:
            results.append(value)

    return results


def get_api_data(record):
    return (
        record
        .get("sources", {})
        .get("rmi_api", {})
        .get("data", {})
    )


def extract_block_parcels(api_data):
    results = []

    for pair in api_data.get(
        "גושים/חלקות מובנים",
        [],
    ):
        gush = str(pair.get("gush") or "").strip()
        chelka = str(pair.get("chelka") or "").strip()

        if gush and chelka:
            normalized_pair = {
                "gush": gush,
                "chelka": chelka,
            }

            if normalized_pair not in results:
                results.append(normalized_pair)

    if results:
        return results

    # Backward compatibility for existing analysis JSON.
    for value in api_data.get("גוש/חלקה", []):
        if not isinstance(value, str):
            continue

        words = value.split()

        try:
            gush_index = words.index("גוש")
            chelka_index = words.index("חלקה")
            gush = words[gush_index + 1]
            chelka = words[chelka_index + 1]

        except (ValueError, IndexError):
            continue

        pair = {
            "gush": gush,
            "chelka": chelka,
        }

        if pair not in results:
            results.append(pair)

    return results


def get_address_keywords(api_data):
    address = str(api_data.get("שכונה") or "")

    for separator in "-/,().":
        address = address.replace(separator, " ")

    ignored_words = {
        "רחוב",
        "רח",
        "שכונה",
    }

    words = []

    for word in address.split():
        if (
            word.isalpha()
            and len(word) >= 3
            and word not in ignored_words
        ):
            words.append(word)

    return words


def get_known_non_plan_values(api_data, block_parcels):
    values = []

    for pair in block_parcels:
        for value in (
            pair["gush"],
            pair["chelka"],
        ):
            value = str(value).strip()

            if value and value not in values:
                values.append(value)

    for value in api_data.get("מגרשים", []):
        value = str(value or "").strip()

        if value and value not in values:
            values.append(value)

    return values


def get_usable_ai_plan_number(
    ai_plan_number,
    api_data,
    block_parcels,
):
    if not ai_plan_number:
        return None

    known_non_plan_values = get_known_non_plan_values(
        api_data,
        block_parcels,
    )

    if ai_plan_number in known_non_plan_values:
        return None

    return ai_plan_number


def create_session():
    """
    Open the public planning website first so that the server
    can create the required cookies automatically.

    Do not copy browser cookies into the code.
    """

    session = requests.Session()

    session.headers.update({
        "Accept": "application/json, text/plain, */*",
        "Content-Type": "application/json",
        "Origin": "https://apps.land.gov.il",
        "Referer": PLANNING_PAGE_URL,
        "User-Agent": (
            "Mozilla/5.0 "
            "(compatible; RMITenderAgent/1.0)"
        ),
    })

    landing_response = session.get(
        PLANNING_PAGE_URL,
        timeout=30,
    )
    landing_response.raise_for_status()

    return session


def search_plans(
    session,
    plan_number="",
    gush="",
    chelka="",
):
    payload = {
        "planNumber": plan_number or "",
        "gush": gush or "",
        "chelka": chelka or "",
        "statuses": [],
        "planTypes": [],
        "planTypesUsed": False,
        "fromStatusDate": "",
        "toStatusDate": "",
    }

    response = session.post(
        PLANNING_API_URL,
        json=payload,
        timeout=45,
    )
    response.raise_for_status()

    data = response.json()

    return data.get("plansSmall") or [], payload


def get_plan_detail(session, plan_id):
    response = session.get(
        PLAN_DETAIL_API_URL,
        params={"planID": plan_id},
        timeout=45,
    )
    response.raise_for_status()
    return response.json()


def derive_plan_housing_units(areas):
    positive_values = []

    for area in areas:
        units = area.get("units")

        if (
            isinstance(units, (int, float))
            and not isinstance(units, bool)
            and units > 0
        ):
            positive_values.append(units)

    if len(positive_values) != 1:
        return None

    return positive_values[0]


def make_url(path):
    if not path:
        return None

    path = str(path).replace("\\", "/")

    if path.startswith("http://") or path.startswith("https://"):
        return path

    return urljoin(
        "https://apps.land.gov.il",
        path,
    )


def normalize_document(document):
    if not document:
        return None

    return {
        "name": document.get("info"),
        "document_type_code": document.get("codeMismach"),
        "url": make_url(document.get("path")),
    }


def normalize_documents(documents_set):
    documents_set = documents_set or {}
    documents = []

    for group_name in ("nispachim", "tasritim"):
        for document in documents_set.get(group_name) or []:
            normalized = normalize_document(document)

            if normalized:
                normalized["group"] = group_name
                documents.append(normalized)

    special_documents = {}

    for key in ("takanon", "mmg", "map"):
        normalized = normalize_document(
            documents_set.get(key)
        )

        if normalized:
            special_documents[key] = normalized

    return {
        "documents": documents,
        "special_documents": special_documents,
    }


def calculate_candidate_score(
    plan,
    searched_plan_numbers,
    address_keywords,
):
    score = 0
    reasons = []

    plan_number = str(plan.get("planNumber") or "")
    description = str(plan.get("mahut") or "")
    combined_text = f"{plan_number} {description}"

    if plan_number in searched_plan_numbers:
        score += 100
        reasons.append(
            "מספר התכנית זהה למספר התכנית שנמצא במקור"
        )

    matched_address_words = [
        word
        for word in address_keywords
        if word in combined_text
    ]

    if matched_address_words:
        score += 30
        reasons.append(
            "שם התכנית תואם לכתובת המכרז: "
            + ", ".join(matched_address_words)
        )

    return score, reasons


def normalize_candidate(
    plan,
    searched_plan_numbers,
    address_keywords,
):
    score, reasons = calculate_candidate_score(
        plan,
        searched_plan_numbers,
        address_keywords,
    )

    normalized_documents = normalize_documents(
        plan.get("documentsSet")
    )

    return {
        "plan_number": plan.get("planNumber"),
        "plan_id": plan.get("planId"),
        "city": plan.get("cityText"),
        "plan_name": plan.get("mahut"),
        "status": plan.get("status"),
        "status_date": str(
            plan.get("statusDate") or ""
        ).strip() or None,
        "relation_type": plan.get("relationType"),

        # הנתונים האלו אינם מוחזרים בבקשה הנוכחית.
        "main_designation": None,
        "housing_units": None,

        "match_score": score,
        "match_reasons": reasons,

        "documents": normalized_documents["documents"],
        "special_documents": (
            normalized_documents["special_documents"]
        ),
    }


def remove_duplicate_plans(plans):
    unique_plans = {}

    for plan in plans:
        plan_id = plan.get("planId")

        if plan_id is None:
            plan_id = (
                plan.get("planNumber"),
                plan.get("mahut"),
            )

        unique_plans[plan_id] = plan

    return list(unique_plans.values())


def choose_plan(candidates):
    if not candidates:
        return None, (
            "לא נמצאו תכניות מתאימות במקור התכנוני."
        )

    sorted_candidates = sorted(
        candidates,
        key=lambda item: item["match_score"],
        reverse=True,
    )

    best = sorted_candidates[0]

    if best["match_score"] == 0:
        return None, (
            "נמצאו תכניות החלות על הגוש והחלקה, "
            "אך אין מספיק מידע לבחירת תכנית אחת."
        )

    if (
        len(sorted_candidates) > 1
        and sorted_candidates[0]["match_score"]
        == sorted_candidates[1]["match_score"]
    ):
        return None, (
            "נמצאו מספר תכניות בעלות ציון התאמה זהה, "
            "ולכן לא נבחרה תכנית אוטומטית."
        )

    reason = (
        "התכנית נבחרה משום ש"
        + " וכן ".join(best["match_reasons"])
        + "."
    )

    return best, reason


def find_plans_for_tender(michraz_id):
    record, analysis_path = load_analysis(michraz_id)

    api_data = get_api_data(record)
    block_parcels = extract_block_parcels(api_data)
    address_keywords = get_address_keywords(api_data)
    structured_plan_numbers = get_structured_plan_numbers(
        api_data
    )
    ai_plan_number = get_ai_plan_number(record)
    usable_ai_plan_number = get_usable_ai_plan_number(
        ai_plan_number,
        api_data,
        block_parcels,
    )

    if structured_plan_numbers:
        searched_plan_numbers = structured_plan_numbers
    elif usable_ai_plan_number:
        searched_plan_numbers = [usable_ai_plan_number]
    else:
        searched_plan_numbers = []

    session = create_session()

    collected_plans = []
    searches_performed = []

    for plan_number in searched_plan_numbers:
        plans, payload = search_plans(
            session,
            plan_number=plan_number,
        )

        collected_plans.extend(plans)

        searches_performed.append({
            "method": "plan_number",
            "payload": payload,
            "results_count": len(plans),
        })

    # Cadastral search always runs when cadastral data exists.
    for pair in block_parcels:
        plans, payload = search_plans(
            session,
            gush=pair["gush"],
            chelka=pair["chelka"],
        )

        collected_plans.extend(plans)

        searches_performed.append({
            "method": "block_and_parcel",
            "payload": payload,
            "results_count": len(plans),
        })

    collected_plans = remove_duplicate_plans(
        collected_plans
    )

    candidates = [
        normalize_candidate(
            plan=plan,
            searched_plan_numbers=searched_plan_numbers,
            address_keywords=address_keywords,
        )
        for plan in collected_plans
    ]

    candidates.sort(
        key=lambda item: item["match_score"],
        reverse=True,
    )

    selected_plan, selection_reason = choose_plan(
        candidates
    )

    plan_detail_error = None

    if selected_plan and selected_plan.get("plan_id") is not None:
        try:
            plan_detail = get_plan_detail(
                session,
                selected_plan["plan_id"],
            )
            general_info = (
                plan_detail.get("generalInfo") or {}
            )
            areas = plan_detail.get("areas") or []

            selected_plan["main_designation"] = (
                general_info.get("category")
            )
            selected_plan["general_info"] = general_info
            selected_plan["areas"] = areas
            selected_plan["housing_units"] = (
                derive_plan_housing_units(areas)
            )

        except (requests.RequestException, ValueError) as error:
            plan_detail_error = str(error)

    planning_status = (
        "success"
        if candidates
        else "not_found"
    )

    record.setdefault("sources", {})

    record["sources"]["planning_api"] = {
        "status": planning_status,
        "searched_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "source_name": (
            "רשות מקרקעי ישראל – מאגר תכניות בניין עיר"
        ),
        "source_page_url": PLANNING_PAGE_URL,
        "api_url": PLANNING_API_URL,
        "searches_performed": searches_performed,
        "data": {
            "ai_plan_number": ai_plan_number,
            "usable_ai_plan_number": usable_ai_plan_number,
            "structured_plan_numbers": (
                structured_plan_numbers
            ),
            "searched_plan_numbers": searched_plan_numbers,
            "block_parcels": block_parcels,
            "address_keywords": address_keywords,
            "candidates": candidates,
            "selected_plan": selected_plan,
            "selection_reason": selection_reason,
            "plan_detail_error": plan_detail_error,
            "requires_verification": (
                selected_plan is None
                or len(candidates) > 1
            ),
        },
    }

    with analysis_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            record,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(
        f"Found {len(candidates)} planning candidate(s)."
    )

    if selected_plan:
        print(
            "Selected plan:",
            selected_plan["plan_number"],
            "-",
            selected_plan["plan_name"],
        )
        print("Reason:", selection_reason)
    else:
        print("No plan was selected automatically.")
        print("Reason:", selection_reason)

    print(f"Updated -> {analysis_path}")

    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description=(
            "Find planning information for an analyzed tender"
        )
    )

    parser.add_argument(
        "michraz_id",
        type=int,
        nargs="?",
        default=20260639,
        help="RMI tender ID",
    )

    args = parser.parse_args()

    find_plans_for_tender(args.michraz_id)
