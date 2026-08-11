import requests, json, os
from datetime import datetime, timezone

from rmi_client import BASE, HEADERS

DETAIL_URL = f"{BASE}/api/MichrazDetailsApi/Get"
FILE_URL = f"{BASE}/api/MichrazDetailsApi/GetFileContent"
GENERAL_TABLES_URL = f"{BASE}/api/GeneralTablesApi"
YESHUVIM_URL = f"{BASE}/api/YeshuvimApi/Get"

# TableID 215 contains ׳סוג מכרז׳ values
TENDER_TYPE_TABLE_ID = 215

# The RMI API and frontend use TableID -1 to translate KodYeudMichraz ׳ייעוד מכרז׳
TENDER_DESIGNATION_TABLE_ID = -1

def get_tender_detail(session, michraz_id):
    """Fetches full tender details from RMI, saves the raw JSON, and returns it."""

    #DETAIL_URL is the API endpoint used to request tender details. The tender ID is sent separately as a query parameter
    response = session.get(
        DETAIL_URL,
        params={"michrazID": michraz_id},
        headers=HEADERS,
        timeout=30,
    )

    # Stop on HTTP errors instead of saving an error page as tender data
    response.raise_for_status()
    detail = response.json() #הופך את הג׳ייסון שקיבלנו לאובייקט פייתון (מילון)

    # Support both the first run and later refreshes
    os.makedirs("data/details", exist_ok=True)

    # שומר את הנתונים שהתקבלו מקומי כקובץ ג׳ייסון, כדי שנוכל להשתמש בהם בהמשך
    with open(f"data/details/{michraz_id}.json", "w", encoding="utf-8") as f:
        json.dump(detail, f, ensure_ascii=False, indent=2)

    return detail


def get_document_source_url(document):
    """Returns the RMI source URL for a tender document"""
    #סוג פרסום הוא 1 וגם רמ״י סיפקה כבר שדה כתובת אז פשוט מחזירים את הכתובת שהגיעה מ- api
    if (
        document.get("PirsumType") == 1
        and document.get("Url")
    ):
        return document["Url"]

    # אם אין כתובת מוכנה,מגיעים לחלק זה- בונים מילון של הפרמטרים שצריך לצרף לכתובת המסמך
    # Use .get() because some metadata fields are optional
    params = {
        "michrazId": document.get("MichrazID"),
        "rowId": document.get("RowID"),
        "size": document.get("Size"),
        "typePirsum": document.get("PirsumType"),
        "fileName": document.get("DocName"),
        "teur": document.get("Teur"),
        "fileType": document.get("FileType"),
    }

    #  בניית url מלא -query parametersעם כל ה־
    return requests.Request(
        "GET",
        FILE_URL,
        params=params,
    ).prepare().url #רק יוצרים אובייקט בקשה (ולא שולחים אותה בפועל)


def _is_tender_booklet(document):
    """Returns whether RMI describes the document as the tender booklet"""
    return document.get("Teur") == "חוברת המכרז"


def get_tender_documents(detail):
    """Combines the full tender document and attachments into one metadata list"""
    documents = []

    full_document = detail.get(
        "MichrazFullDocument"
    )

    source_documents = []

    # MichrazFullDocument is the complete publication document
    # MichrazDocList contains separate documents and attachments
    if full_document:
        source_documents.append(
            ("full_tender_document", full_document)
        )

    for document in detail.get(
        "MichrazDocList",
        [],
    ):
        role = "tender_attachment"

        if _is_tender_booklet(document):
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

#מחזירה שני מילונים: אחד-לסוג מכרז, השני-לייעוד מכרז
def get_tender_lookups(session):
    """Returns RMI Code-to-Value lookups for tender type and designation"""
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

    # GeneralTablesApi returns several tables, so filter rows by TableID
    # Each lookup maps a raw Code to its readable Value
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
    """Returns a lookup from RMI locality codes to readable locality names"""
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

    # YeshuvimApi only returns localities, so it does not need TableID filtering
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

#לוקחת את הג׳ייסון הגדול שמגיע מרמ״י והופכת אותו למערך עובדות מסודר שהמערכת יודעת לעבוד איתו
def extract_api_facts(
    detail,
    michraz_id,
    tender_type_lookup=None,
    locality_lookup=None,
    tender_designation_lookup=None,
):
    """Extracts readable and structured facts from RMI tender details"""
    # Lookups are optional. Raw codes and other facts remain available if they fail
    tender_type_lookup = tender_type_lookup or {}
    locality_lookup = locality_lookup or {}
    tender_designation_lookup = (
        tender_designation_lookup or {}
    )

    gush_helka = [] #גוש חלקה להצגה למשתמש
    structured_block_parcels = [] #גוש חלקה לעבודה של הקוד
    structured_plan_references = []
    mitchamim = []
    migrashim = []
    shetach = None
    shetach_bniya = None
    hotzaot = None

    # Tik contains tender areas. Each area may include block-parcel pairs
    # in GushHelka and plan-lot references in TochnitMigrash
    for tik in detail.get("Tik", []):
        if tik.get("MitchamName"):
            mitcham_name = str(tik["MitchamName"]).strip()

            if mitcham_name and mitcham_name not in mitchamim:
                mitchamim.append(mitcham_name)

        if tik.get("Shetach") is not None:
            shetach = tik["Shetach"]

        if tik.get("ShetachBniya") is not None:
            shetach_bniya = tik["ShetachBniya"]

        if tik.get("HotzaotPituach") is not None:
            hotzaot = tik["HotzaotPituach"]

        for gh in tik.get("GushHelka", []):
            # Both fields are required. Fail on incomplete API data instead of
            # silently creating a partial block-parcel pair
            pair = {
                "gush": str(gh["Gush"]).strip(),
                "chelka": str(gh["Helka"]).strip(),
            }

            # Keep the readable and structured versions in sync and deduplicated
            if pair not in structured_block_parcels:
                structured_block_parcels.append(pair)
                gush_helka.append(
                    f'גוש {gh["Gush"]} חלקה {gh["Helka"]}'
                )

        for plan_lot in tik.get("TochnitMigrash", []):
            lot_name = str(
                plan_lot.get("MigrashName") or ""
            ).strip()

            if lot_name and lot_name not in migrashim:
                migrashim.append(lot_name)

            plan_number = str(
                plan_lot.get("Tochnit") or ""
            ).strip()

            if not plan_number:
                continue

           # יוצרים אובייקט מסודר שמספר לנו מה מספר התכנית,מאיפה היא הגיעה ובאיזה טיק היא הופיעה 
            reference = {
                "plan_number": plan_number,
                "lot_name": lot_name or None,
                "tik_id": tik.get("TikID"),
                "source_field": "Tik.TochnitMigrash",
            }

            # שוב מניעת כפילויות- אם כבר קיים אובייקט כזה ברשימה, לא מוסיפים אותו שוב
            if reference not in structured_plan_references:
                structured_plan_references.append(reference)

    # Keep full references for context and unique plan numbers for later searches
    structured_plan_numbers = []

    for reference in structured_plan_references:
        plan_number = reference["plan_number"]

        if plan_number not in structured_plan_numbers:
            structured_plan_numbers.append(plan_number)

    tender_type_code = detail.get("KodSugMichraz")
    locality_code = detail.get("KodYeshuv")
    tender_designation_code = detail.get("KodYeudMichraz")

    # Keep raw tender type, locality, and designation codes even without lookups

    facts = {
        "מספר מכרז": detail.get("MichrazID"),
        "שם מכרז": detail.get("MichrazName"),
        "קוד יישוב": locality_code,
        "קוד ייעוד": tender_designation_code,
        "קוד סוג מכרז": tender_type_code,
        "שכונה": detail.get("Shchuna"),
        "מתחמים": mitchamim,
        "מגרשים": migrashim,
        "שטח": shetach,
        "שטח בנייה": shetach_bniya,
        "יחידות דיור": detail.get("YechidotDiur"),
        "מחיר מינימום": detail.get("MechirSafMichraz"),
        "הוצאות פיתוח": hotzaot,
        "סכום ערבות": detail.get("SchumArvut"),
        "תוקף ערבות": detail.get("TokefArvut"),
        "גוש/חלקה": gush_helka,
        "גושים/חלקות מובנים": structured_block_parcels,
        "מספרי תכנית מובנים": structured_plan_numbers,
        "תכניות/מגרשים מובנים": (structured_plan_references),
        "תאריך פרסום": detail.get("PirsumDate"),
        "מועד אחרון": detail.get("SgiraDate"),
        "קישור למקור": f"{BASE}/#/michraz/{michraz_id}",
        "קישור למסמכי המכרז": (
            f"{BASE}/#/michraz/"
            f"{michraz_id}/PirsumDocs"
        ),
        # Skip unnamed documents because this list is only used for display
        "מסמכים": [
            document.get("DocName")
            for document in detail.get("MichrazDocList", [])
            if document.get("DocName")
        ],
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

    tender_designation = (tender_designation_lookup.get(tender_designation_code))

    if tender_designation:
        facts["ייעוד מכרז"] = tender_designation

    return facts


def get_rmi_tender_data(session, michraz_id):
    """Fetches and normalizes RMI data for one tender"""
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

    return detail, api_facts


def download_booklet(session, detail, michraz_id):
    """Downloads the tender booklet and returns its path and metadata
    Returns None with not-found metadata when no booklet exists
    """

    # Only MichrazDocList is used to find the booklet
    booklet = next(
        (
            document
            for document in detail.get("MichrazDocList", [])
            if _is_tender_booklet(document)
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

    # GetFileContent expects the original document fields as form data
    # Use empty strings instead of sending None values
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

    # Do not save an HTTP error response as a PDF file
    response.raise_for_status()

    # Support both the first download and later downloads or refreshes
    os.makedirs("data/booklets", exist_ok=True)

    path = f"data/booklets/{michraz_id}.pdf"

    with open(path, "wb") as file: #pdf הוא קובץ הינארי ולא טקטסט לכן צריך wb
        file.write(response.content)

    # "downloaded" means the file is saved. analyze.py updates the status after AI processing
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
