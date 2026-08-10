import argparse
import json
from datetime import datetime, timezone

from analysis_store import (
    get_analysis_path,
    load_analysis_record,
    save_analysis_record,
)
from rmi_client import get_session
from get_booklet import (
    get_rmi_tender_data,
    download_booklet,
)
from extract import extract_from_pdf


def refresh_rmi_data(michraz_id):
    """Refreshes only the RMI source in an existing analysis record."""
    output_path = get_analysis_path(michraz_id)

    if not output_path.exists():
        raise FileNotFoundError(
            f"Analysis record was not found: "
            f"{output_path}"
        )

    record, output_path = load_analysis_record(michraz_id)

    session = get_session()
    _, api_facts = get_rmi_tender_data(
        session,
        michraz_id,
    )

    record.setdefault("sources", {})
    record["sources"]["rmi_api"] = {
        "status": "success",
        "refreshed_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "data": api_facts,
    }

    save_analysis_record(record, output_path)

    return record


def analyze(michraz_id):
    """Analyzes one tender and saves its unified analysis record."""
    print(f"\n=== Analyzing tender {michraz_id} ===")

    # Step 1: Fetch and normalize RMI tender data.
    session = get_session()
    detail, api_facts = get_rmi_tender_data(
        session,
        michraz_id,
    )

    # Step 2: Download the tender booklet.
    pdf_path, document_metadata = download_booklet(
        session,
        detail,
        michraz_id,
    )

    # Step 3: Extract structured facts from the booklet with Claude.
    ai_fields = None
    ai_error = None

    if pdf_path:
        try:
            ai_fields = extract_from_pdf(pdf_path)
            ai_status = "success"

        except json.JSONDecodeError as error:
            ai_status = "invalid_json"
            ai_error = str(error)

        except Exception as error:
            ai_status = "failed"
            ai_error = str(error)

    else:
        ai_status = "booklet_not_found"

    # Step 4: Align document metadata with the extraction result.
    if ai_status == "success":
        document_metadata["processing_status"] = "processed"

    elif ai_status in {"failed", "invalid_json"}:
        document_metadata["processing_status"] = "processing_failed"

    elif ai_status == "booklet_not_found":
        document_metadata["processing_status"] = "not_found"


    # Step 5: Build and save the unified analysis record.
    record = {
        "michraz_id": michraz_id,
        "analyzed_at": datetime.now(timezone.utc).isoformat(),

        "documents": [
            document_metadata
        ],

        "sources": {
            "rmi_api": {
                "status": "success",
                "data": api_facts,
            },

            "tender_booklet_ai": {
                "status": ai_status,
                "document_path": pdf_path,
                "error": ai_error,
                "data": ai_fields,
            },
        },
    }

    output_path = get_analysis_path(michraz_id)

    save_analysis_record(record, output_path)

    print(f"OK -> {output_path}")
    print(f"AI extraction status: {ai_status}")

    return record

# Run the analysis directly for one tender from the command line
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Analyze one RMI tender"
    )

    parser.add_argument(
        "michraz_id",
        type=int,
        help="RMI tender ID",
    )

    args = parser.parse_args()
    analyze(args.michraz_id)
