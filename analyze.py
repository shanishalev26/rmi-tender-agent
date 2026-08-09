import argparse
import json
import os
from datetime import datetime, timezone

from get_booklet import (
    get_session,
    get_tender_detail,
    extract_api_facts,
    get_tender_lookups,
    get_locality_lookup,
    download_booklet,
)
from extract import extract_from_pdf


def refresh_rmi_data(michraz_id):
    output_path = (
        f"data/analysis/{michraz_id}.json"
    )

    if not os.path.exists(output_path):
        raise FileNotFoundError(
            f"Analysis record was not found: "
            f"{output_path}"
        )

    with open(
        output_path,
        "r",
        encoding="utf-8",
    ) as file:
        record = json.load(file)

    session = get_session()
    detail = get_tender_detail(
        session,
        michraz_id,
    )

    (
        tender_type_lookup,
        tender_designation_lookup,
    ) = get_tender_lookups(session)

    locality_lookup = get_locality_lookup(session)

    api_facts = extract_api_facts(
        detail,
        michraz_id,
        tender_type_lookup=tender_type_lookup,
        locality_lookup=locality_lookup,
        tender_designation_lookup=(
            tender_designation_lookup
        ),
    )

    record.setdefault("sources", {})
    record["sources"]["rmi_api"] = {
        "status": "success",
        "refreshed_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "data": api_facts,
    }

    temporary_path = output_path + ".tmp"

    with open(
        temporary_path,
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            record,
            file,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(
        temporary_path,
        output_path,
    )

    return record


def analyze(michraz_id):
    print(f"\n=== Analyzing tender {michraz_id} ===")

    session = get_session()

    # 1. קבלת פרטי המכרז מה-API של רמ"י
    detail = get_tender_detail(session, michraz_id)
    (
        tender_type_lookup,
        tender_designation_lookup,
    ) = get_tender_lookups(session)
    locality_lookup = get_locality_lookup(session)
    api_facts = extract_api_facts(
        detail,
        michraz_id,
        tender_type_lookup=tender_type_lookup,
        locality_lookup=locality_lookup,
        tender_designation_lookup=(
            tender_designation_lookup
        ),
    )

    # 2. הורדת חוברת המכרז
    pdf_path, document_metadata = download_booklet(
        session,
        detail,
        michraz_id,
    )

    # 3. חילוץ שדות מהחוברת באמצעות AI
    ai_fields = None
    ai_status = "not_started"
    ai_error = None

    if pdf_path:
        try:
            raw_ai_output = extract_from_pdf(pdf_path)
            ai_fields = json.loads(raw_ai_output)
            ai_status = "success"

        except json.JSONDecodeError as error:
            ai_status = "invalid_json"
            ai_error = str(error)

        except Exception as error:
            ai_status = "failed"
            ai_error = str(error)

    else:
        ai_status = "booklet_not_found"

    # מעדכנים את סטטוס העיבוד של המסמך
    if ai_status == "success":
        document_metadata["processing_status"] = "processed"

    elif ai_status in {"failed", "invalid_json"}:
        document_metadata["processing_status"] = "processing_failed"

    elif ai_status == "booklet_not_found":
        document_metadata["processing_status"] = "not_found"


    output_directory = "data/analysis"
    output_path = f"{output_directory}/{michraz_id}.json"

    os.makedirs(output_directory, exist_ok=True)

    existing_sources = {}

    if os.path.exists(output_path):
        try:
            with open(output_path, "r", encoding="utf-8") as file:
                existing_record = json.load(file)

            existing_sources = existing_record.get("sources", {})

        except (json.JSONDecodeError, OSError):
            existing_sources = {}

    # 4. יצירת רשומה מאוחדת, תוך הפרדה ברורה בין המקורות
    record = {
        "michraz_id": michraz_id,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),

        "documents": [
            document_metadata
        ],

        "sources": {
            # שומר מקורות שכבר נוספו, למשל planning_api
            **existing_sources,

            # מעדכן מחדש את נתוני רמ"י
            "rmi_api": {
                "status": "success",
                "data": api_facts,
            },

            # מעדכן מחדש את חילוץ ה-AI
            "tender_booklet_ai": {
                "status": ai_status,
                "document_path": pdf_path,
                "error": ai_error,
                "data": ai_fields,
            },
        },
    }

    # 5. שמירת הרשומה
    output_directory = "data/analysis"
    output_path = f"{output_directory}/{michraz_id}.json"

    os.makedirs(output_directory, exist_ok=True)

    with open(output_path, "w", encoding="utf-8") as file:
        json.dump(
            record,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"OK -> {output_path}")
    print(f"AI extraction status: {ai_status}")

    return record


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze one RMI tender"
    )

    parser.add_argument(
        "michraz_id",
        type=int,
        nargs="?",
        default=20260639,
        help="RMI tender ID",
    )

    args = parser.parse_args()
    analyze(args.michraz_id)
