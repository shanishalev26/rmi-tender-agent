import requests, json, os
from datetime import datetime, timezone

BASE = "https://apps.land.gov.il/MichrazimSite"
DETAIL_URL = f"{BASE}/api/MichrazDetailsApi/Get"
FILE_URL = f"{BASE}/api/MichrazDetailsApi/GetFileContent"
GENERAL_TABLES_URL = f"{BASE}/api/GeneralTablesApi"
YESHUVIM_URL = f"{BASE}/api/YeshuvimApi/Get"

# Verified against RMI's official GeneralTablesApi:
# TableID 215 is "סוג מכרז".
TENDER_TYPE_TABLE_ID = 215

# Verified against RMI's official GeneralTablesApi and frontend:
# TableID -1 resolves KodYeudMichraz for displayed tenders.
TENDER_DESIGNATION_TABLE_ID = -1

HEADERS = {
    "Accept": "application/json, text/plain, */*",
    "Origin": BASE,
    "Referer": BASE + "/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17 Safari/605.1.15",
}


def get_session():
    """פותח session ומבצע בקשת חימום כדי לאסוף cookies."""
    s = requests.Session()
    s.get(BASE + "/", headers=HEADERS, timeout=30)
    return s


def get_tender_detail(session, michraz_id):
    """מביא את כל פרטי המכרז מה-API ושומר את ה-JSON הגולמי המלא."""
    response = session.get(
        DETAIL_URL,
        params={"michrazID": michraz_id},
        headers=HEADERS,
        timeout=30,
    )
    response.raise_for_status()
    detail = response.json()

    os.makedirs("data/details", exist_ok=True)

    with open(f"data/details/{michraz_id}.json", "w", encoding="utf-8") as f:
        json.dump(detail, f, ensure_ascii=False, indent=2)

    return detail


def get_document_source_url(document):
    if (
        document.get("PirsumType") == 1
        and document.get("Url")
    ):
        return document["Url"]

    params = {
        "michrazId": document.get("MichrazID"),
        "rowId": document.get("RowID"),
        "size": document.get("Size"),
        "typePirsum": document.get("PirsumType"),
        "fileName": document.get("DocName"),
        "teur": document.get("Teur"),
        "fileType": document.get("FileType"),
    }

    return requests.Request(
        "GET",
        FILE_URL,
        params=params,
    ).prepare().url


def get_tender_documents(detail):
    documents = []

    full_document = detail.get(
        "MichrazFullDocument"
    )

    source_documents = []

    if full_document:
        source_documents.append(
            ("full_tender_document", full_document)
        )

    for document in detail.get(
        "MichrazDocList",
        [],
    ):
        role = "tender_attachment"

        if document.get("Teur") == "חוברת המכרז":
            role = "tender_booklet"

        source_documents.append((role, document))

    for role, document in source_documents:
        documents.append({
            "role": role,
            "name": document.get("DocName"),
            "description": document.get("Teur"),
            "source_url": get_document_source_url(
                document
            ),
            "source_document_id": document.get(
                "RowID"
            ),
            "publication_type": document.get(
                "PirsumType"
            ),
            "file_type": document.get("FileType"),
            "file_size_bytes": document.get("Size"),
            "source_updated_at": document.get(
                "UpdateDate"
            ),
        })

    return documents


def get_tender_lookups(session):
    """
    Return RMI's official tender type and designation mappings.

    Failure to load this optional enrichment does not prevent the
    tender's raw codes and other facts from being preserved.
    """
    try:
        response = session.get(
            GENERAL_TABLES_URL,
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        rows = response.json()

    except (requests.RequestException, ValueError):
        return {}, {}

    tender_type_lookup = {
        row["Code"]: str(row["Value"]).strip()
        for row in rows
        if (
            row.get("TableID") == TENDER_TYPE_TABLE_ID
            and row.get("Code") is not None
            and row.get("Value")
        )
    }

    tender_designation_lookup = {
        row["Code"]: str(row["Value"]).strip()
        for row in rows
        if (
            row.get("TableID")
            == TENDER_DESIGNATION_TABLE_ID
            and row.get("Code") is not None
            and row.get("Value")
        )
    }

    return (
        tender_type_lookup,
        tender_designation_lookup,
    )


def get_locality_lookup(session):
    """
    Return RMI's official KodYeshuv-to-locality mapping.

    Failure to load this optional enrichment does not prevent
    the tender's raw code and other facts from being preserved.
    """
    try:
        response = session.get(
            YESHUVIM_URL,
            headers=HEADERS,
            timeout=30,
        )
        response.raise_for_status()
        rows = response.json()

    except (requests.RequestException, ValueError):
        return {}

    return {
        row["mtysvSemelYishuv"]: str(
            row["mtysvShemYishuv"]
        ).strip()
        for row in rows
        if (
            row.get("mtysvSemelYishuv") is not None
            and row.get("mtysvShemYishuv")
        )
    }


def extract_api_facts(
    detail,
    michraz_id,
    tender_type_lookup=None,
    locality_lookup=None,
    tender_designation_lookup=None,
):
    """שולף מה-JSON הגולמי רק את השדות שהמטלה מבקשת (השאר נשמר בקובץ)."""
    tender_type_lookup = tender_type_lookup or {}
    locality_lookup = locality_lookup or {}
    tender_designation_lookup = (
        tender_designation_lookup or {}
    )

    gush_helka = []
    structured_block_parcels = []
    structured_plan_references = []
    migrashim = []
    shetach = None
    hotzaot = None

    for tik in detail.get("Tik", []):
        if tik.get("MitchamName"):
            migrashim.append(tik["MitchamName"])

        if tik.get("Shetach") is not None:
            shetach = tik["Shetach"]

        if tik.get("HotzaotPituach") is not None:
            hotzaot = tik["HotzaotPituach"]

        for gh in tik.get("GushHelka", []):
            gush_helka.append(f'גוש {gh["Gush"]} חלקה {gh["Helka"]}')

            pair = {
                "gush": str(gh["Gush"]).strip(),
                "chelka": str(gh["Helka"]).strip(),
            }

            if pair not in structured_block_parcels:
                structured_block_parcels.append(pair)

        for plan_lot in tik.get("TochnitMigrash", []):
            plan_number = str(
                plan_lot.get("Tochnit") or ""
            ).strip()

            if not plan_number:
                continue

            lot_name = str(
                plan_lot.get("MigrashName") or ""
            ).strip()

            reference = {
                "plan_number": plan_number,
                "lot_name": lot_name or None,
                "tik_id": tik.get("TikID"),
                "source_field": "Tik.TochnitMigrash",
            }

            if reference not in structured_plan_references:
                structured_plan_references.append(reference)

    structured_plan_numbers = []

    for reference in structured_plan_references:
        plan_number = reference["plan_number"]

        if plan_number not in structured_plan_numbers:
            structured_plan_numbers.append(plan_number)

    tender_type_code = detail.get("KodSugMichraz")
    locality_code = detail.get("KodYeshuv")
    tender_designation_code = detail.get(
        "KodYeudMichraz"
    )

    facts = {
        "מספר מכרז": detail.get("MichrazName"),
        "קוד יישוב": locality_code,
        "קוד ייעוד": tender_designation_code,
        "קוד סוג מכרז": tender_type_code,
        "שכונה": detail.get("Shchuna"),
        "מגרשים": migrashim,
        "שטח": shetach,
        "יחידות דיור": detail.get("YechidotDiur"),
        "מחיר מינימום": detail.get("MechirSafMichraz"),
        "הוצאות פיתוח": hotzaot,
        "סכום ערבות": detail.get("SchumArvut"),
        "תוקף ערבות": detail.get("TokefArvut"),
        "גוש/חלקה": gush_helka,
        "גושים/חלקות מובנים": structured_block_parcels,
        "מספרי תכנית מובנים": structured_plan_numbers,
        "תכניות/מגרשים מובנים": (
            structured_plan_references
        ),
        "תאריך פרסום": detail.get("PirsumDate"),
        "מועד אחרון": detail.get("SgiraDate"),
        "קישור למקור": f"{BASE}/#/michraz/{michraz_id}",
        "קישור למסמכי המכרז": (
            f"{BASE}/#/michraz/"
            f"{michraz_id}/PirsumDocs"
        ),
        "מסמכים": [d["DocName"] for d in detail.get("MichrazDocList", [])],
        "מסמכי מכרז מובנים": get_tender_documents(
            detail
        ),
    }

    tender_type = tender_type_lookup.get(tender_type_code)

    if tender_type:
        facts["סוג מכרז"] = tender_type

    locality = locality_lookup.get(locality_code)

    if locality:
        facts["יישוב"] = locality

    tender_designation = (
        tender_designation_lookup.get(
            tender_designation_code
        )
    )

    if tender_designation:
        facts["ייעוד מכרז"] = tender_designation

    return facts


def download_booklet(session, detail, michraz_id):
    """מאתר את חוברת המכרז, מוריד אותה ומחזיר גם metadata."""

    booklet = next(
        (
            document
            for document in detail.get("MichrazDocList", [])
            if document.get("Teur") == "חוברת המכרז"
        ),
        None,
    )

    if booklet is None:
        print("  אין חוברת מכרז למכרז הזה.")

        document_metadata = {
            "role": "tender_booklet",
            "name": None,
            "source_url": None,
            "download_endpoint": FILE_URL,
            "file_type": None,
            "downloaded_at": None,
            "local_path": None,
            "processing_status": "not_found",
        }

        return None, document_metadata

    form = {
        key: "" if value is None else value
        for key, value in booklet.items()
    }

    response = session.post(
        FILE_URL,
        data=form,
        headers=HEADERS,
        timeout=60,
    )
    response.raise_for_status()

    os.makedirs("data/booklets", exist_ok=True)

    path = f"data/booklets/{michraz_id}.pdf"

    with open(path, "wb") as file:
        file.write(response.content)

    document_metadata = {
        "role": "tender_booklet",
        "name": booklet.get("DocName"),
        "description": booklet.get("Teur"),
        "source_url": get_document_source_url(
            booklet
        ),
        "download_endpoint": FILE_URL,
        "source_document_id": booklet.get("RowID"),
        "file_type": (
            booklet.get("FileType")
            or response.headers.get("Content-Type")
            or "application/pdf"
        ),
        "downloaded_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "local_path": path,
        "file_size_bytes": len(response.content),
        "processing_status": "downloaded",
    }

    print(
        f"  נשמרה חוברת: {path} "
        f"({len(response.content):,} bytes)"
    )

    return path, document_metadata


def analyze_tender(session, michraz_id):
    """התהליך המלא עבור מכרז אחד - הפונקציה שנקרא לה לכל מכרז."""
    print(f"\n=== מכרז {michraz_id} ===")
    detail = get_tender_detail(session, michraz_id)
    (
        tender_type_lookup,
        tender_designation_lookup,
    ) = get_tender_lookups(session)
    locality_lookup = get_locality_lookup(session)
    facts = extract_api_facts(
        detail,
        michraz_id,
        tender_type_lookup=tender_type_lookup,
        locality_lookup=locality_lookup,
        tender_designation_lookup=(
            tender_designation_lookup
        ),
    )
    for k, v in facts.items():
        print(f"  {k}: {v}")
    download_booklet(session, detail, michraz_id)
    return facts


if __name__ == "__main__":
    session = get_session()

    # עכשיו זה עובד לכל מכרז - רק מחליפים או מוסיפים מספרים:
    analyze_tender(session, 20260639)
    # analyze_tender(session, 20260638)
