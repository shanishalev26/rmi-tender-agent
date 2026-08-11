import html
import json
from datetime import datetime, timezone

import streamlit as st

from analysis_store import ANALYSIS_DIR, save_analysis_record
from analyze import refresh_rmi_data
from company_profile import load_profile, save_profile
from matching import update_company_match

PAGE_TENDERS = "📋 רשימת מכרזים"
PAGE_TENDER_DETAILS = "📄 עמוד המכרז"
PAGE_COMPANY_PROFILE = "⚙️ הגדרות חברה"


st.set_page_config(
    page_title="סוכנת מכרזי רמ״י",
    page_icon="🏗️",
    layout="wide",
)

st.markdown(
    """
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;500;600;700&family=Rubik:wght@500;600;700&display=swap');

        :root {
            --page-bg: #FBF9FE;
            --surface: #FFFFFF;
            --surface-soft: #F7F3FC;
            --lavender: #E9E0F6;
            --lavender-strong: #CDBCE8;
            --purple: #7567A8;
            --purple-dark: #51476F;
            --mint: #DDF2EA;
            --mint-strong: #BFE3D5;
            --peach: #FBE7D8;
            --pink: #F7DFE8;
            --blue: #DFEAF8;
            --text: #403A49;
            --muted: #776F80;
            --border: #E6DFEA;
            --shadow: 0 10px 30px rgba(83, 67, 105, 0.08);
        }

        html,
        body,
        [class*="css"] {
            direction: rtl;
            text-align: right;
            font-family: "Heebo", Arial, sans-serif;
            color: var(--text);
        }

        [data-testid="stAppViewContainer"] {
            background:
                radial-gradient(circle at 8% 4%, rgba(233, 224, 246, 0.65), transparent 24%),
                radial-gradient(circle at 90% 8%, rgba(221, 242, 234, 0.55), transparent 22%),
                var(--page-bg);
        }

        [data-testid="stHeader"] {
            background: transparent;
        }

        [data-testid="stMainBlockContainer"] {
            padding-top: 2rem;
            padding-bottom: 4rem;
        }

        h1,
        h2,
        h3 {
            font-family: "Rubik", "Heebo", Arial, sans-serif;
            color: var(--purple-dark);
            letter-spacing: -0.02em;
        }

        h1 {
            font-weight: 700;
            margin-bottom: 0.35rem;
        }

        h2,
        h3 {
            font-weight: 600;
        }

        p,
        label,
        span,
        div {
            font-family: "Heebo", Arial, sans-serif;
        }

        [data-testid="stSidebar"] {
            direction: rtl;
            text-align: right;
            background: linear-gradient(180deg, #F2ECFA 0%, #F9F6FC 55%, #EEF8F4 100%);
            border-left: 1px solid var(--border);
        }

        [data-testid="stSidebar"] > div:first-child {
            padding-top: 1.4rem;
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3 {
            color: var(--purple-dark);
        }

        [data-testid="stSidebar"] [role="radiogroup"] {
            gap: 0.5rem;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label {
            padding: 0.8rem 0.9rem;
            margin-bottom: 0.25rem;
            border: 1px solid rgba(117, 103, 168, 0.14);
            border-radius: 14px;
            background: rgba(255, 255, 255, 0.72);
            box-shadow: 0 4px 14px rgba(83, 67, 105, 0.04);
            transition: all 0.18s ease;
        }

        [data-testid="stSidebar"] [role="radiogroup"] label:hover {
            background: #FFFFFF;
            border-color: var(--lavender-strong);
            transform: translateY(-1px);
        }

        [data-testid="stSidebar"] [role="radiogroup"] label:has(input:checked) {
            background: linear-gradient(135deg, #E8DFF6, #F2EBFA);
            border-color: var(--lavender-strong);
            color: var(--purple-dark);
            font-weight: 700;
        }

        [data-testid="stMetric"] {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid var(--border);
            border-radius: 18px;
            padding: 1rem 1.1rem;
            box-shadow: var(--shadow);
            min-height: 118px;
        }

        [data-testid="stMetricLabel"] {
            color: var(--muted);
            font-weight: 600;
        }

        [data-testid="stMetricValue"] {
            color: var(--purple-dark);
            font-family: "Rubik", "Heebo", Arial, sans-serif;
            font-weight: 700;
        }

        [data-testid="stTabs"] [role="tablist"] {
            gap: 1.2rem;
            background: rgba(255, 255, 255, 0.72);
            border: 1px solid var(--border);
            border-radius: 16px;
            padding: 0.45rem;
            box-shadow: 0 6px 22px rgba(83, 67, 105, 0.05);
        }

        [data-testid="stTabs"] button[role="tab"] {
            border-radius: 12px;
            padding: 0.55rem 0.8rem;
            color: var(--muted);
            font-weight: 600;
        }

        [data-testid="stTabs"] button[role="tab"][aria-selected="true"] {
            background: var(--lavender);
            color: var(--purple-dark);
        }

        [data-testid="stTabs"] [data-baseweb="tab-highlight"] {
            display: none;
        }

        .stButton > button,
        .stLinkButton > a {
            border-radius: 14px;
            min-height: 44px;
            font-weight: 700;
            font-family: "Heebo", Arial, sans-serif;
            border: 1px solid var(--lavender-strong);
            box-shadow: 0 5px 16px rgba(83, 67, 105, 0.08);
            transition: all 0.18s ease;
        }

        .stButton > button:hover,
        .stLinkButton > a:hover {
            transform: translateY(-1px);
            box-shadow: 0 8px 20px rgba(83, 67, 105, 0.12);
        }

        .stButton > button[kind="primary"] {
            background: linear-gradient(135deg, #8878BC, #6F63A1);
            color: white;
            border: none;
        }

        .stButton > button[kind="secondary"],
        .stLinkButton > a {
            background: #FFFFFF;
            color: var(--purple-dark);
        }

        [data-testid="stForm"] {
            background: rgba(255, 255, 255, 0.88);
            border: 1px solid var(--border);
            border-radius: 22px;
            padding: 1.4rem;
            box-shadow: var(--shadow);
        }

        [data-baseweb="input"] > div,
        [data-baseweb="select"] > div,
        [data-testid="stNumberInput"] input,
        [data-testid="stTextInput"] input {
            background: #FFFFFF;
            border-color: var(--border);
            border-radius: 12px;
        }

        [data-baseweb="input"] > div:focus-within,
        [data-baseweb="select"] > div:focus-within {
            border-color: var(--lavender-strong);
            box-shadow: 0 0 0 3px rgba(205, 188, 232, 0.28);
        }

        [data-testid="stExpander"] {
            background: rgba(255, 255, 255, 0.78);
            border: 1px solid var(--border);
            border-radius: 14px;
            overflow: hidden;
        }

        [data-testid="stAlert"] {
            border-radius: 14px;
            border-width: 1px;
        }

        [data-testid="stAlert"] p {
            color: var(--text);
        }

        hr {
            border-color: var(--border);
        }

        code {
            font-family: "SFMono-Regular", Consolas, monospace;
        }

        @media (max-width: 900px) {
            [data-testid="stMainBlockContainer"] {
                padding-left: 1rem;
                padding-right: 1rem;
            }
        }

        [data-testid="stMetricValue"] {
            font-size: 1.5rem;
            white-space: normal;
            overflow-wrap: anywhere;
        }

        [data-testid="stTabs"] button {
            padding: 0 14px;
        }

        [data-testid="stTabs"] [data-testid="stMarkdownContainer"] p {
            font-size: 0.95rem;
        }

        [data-testid="stAppViewContainer"],
        [data-testid="stMainBlockContainer"],
        [data-testid="stMain"],
        section.main {
            direction: rtl;
            text-align: right;
        }

        [class*="st-emotion-cache"] {
            direction: rtl;
            text-align: right;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def format_date(value, include_time=False):
    """Formats a date value for display."""
    if not value:
        return "לא זמין"

    try:
        parsed = datetime.fromisoformat(
            str(value).replace("Z", "+00:00")
        )
        if include_time:
            return parsed.strftime("%d/%m/%Y בשעה %H:%M")
        return parsed.strftime("%d/%m/%Y")
    except (TypeError, ValueError):
        return str(value)


def format_list(value):
    """Formats a list or value for display."""
    if not value:
        return "לא זמין"

    if isinstance(value, list):
        return ", ".join(str(item) for item in value)

    return str(value)


def format_money(value):
    """Formats a numeric value as an amount in shekels."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "לא זמין"

    return "{:,.0f} ₪".format(value)


def format_housing_units(value):
    """Formats the number of housing units for display."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return "לא זמין"

    return "{:,.0f}".format(value)


def format_score(value):
    """Formats a company match score out of 100."""
    if not isinstance(value, (int, float)):
        return "טרם חושב"

    return "{}/100".format(value)


def format_percentage(value):
    """Formats a numeric value as a percentage."""
    if not isinstance(value, (int, float)):
        return "לא חושב"

    return "{}%".format(value)


def format_value(value):
    """Formats a general value for display."""
    if value is None or value == "":
        return "לא זמין"

    if isinstance(value, list):
        return ", ".join(str(item) for item in value)

    return str(value)


def format_table_value(value):
    """Formats a value for display inside a table."""
    if value is None or value == "":
        return "לא זמין"

    if isinstance(value, list):
        return ", ".join(str(item) for item in value)

    if isinstance(value, dict):
        minimum = value.get("minimum")
        maximum = value.get("maximum")

        if minimum is not None and maximum is not None:
            return "{}–{}".format(minimum, maximum)

        return ", ".join(
            "{}: {}".format(key, item)
            for key, item in value.items()
        )

    return str(value)


def translate_status(status):
    """Returns the display label for a matching status."""
    translations = {
        "matched": "מתאים",
        "not_matched": "לא מתאים",
        "needs_clarification": "דורש בירור",
    }
    return translations.get(status, status or "לא זמין")


def load_analysis_records():
    """Loads all saved analysis records for the app."""
    records = []

    if not ANALYSIS_DIR.exists():
        return records

    for path in sorted(ANALYSIS_DIR.glob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as file:
                record = json.load(file)

            record["_file_path"] = str(path)
            records.append(record)

        except (json.JSONDecodeError, OSError) as error:
            st.warning(
                "לא ניתן לקרוא את הקובץ {}: {}".format(
                    path.name,
                    error,
                )
            )

    return records


def get_rmi_data(record):
    """Returns the RMI data from an analysis record."""
    return (
        record
        .get("sources", {})
        .get("rmi_api", {})
        .get("data", {})
        or {}
    )


def get_tender_deadline(record):
    """Returns the tender submission deadline."""
    raw = get_rmi_data(record).get("מועד אחרון")

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


def is_open_tender(record):
    """Checks whether the tender is still open for submission."""
    deadline = get_tender_deadline(record)

    return (
        deadline is not None
        and deadline > datetime.now(timezone.utc)
    )


def sort_by_deadline(records):
    """Sorts tenders by the nearest submission deadline."""
    return sorted(
        records,
        key=lambda record: (
            get_tender_deadline(record)
            or datetime.max.replace(tzinfo=timezone.utc)
        ),
    )

def get_ai_data(record):
    """Returns the AI extraction data from an analysis record."""
    return (
        record
        .get("sources", {})
        .get("tender_booklet_ai", {})
        .get("data", {})
        or {}
    )


def get_planning_data(record):
    """Returns the planning data from an analysis record."""
    return (
        record
        .get("sources", {})
        .get("planning_api", {})
        .get("data", {})
        or {}
    )


def get_selected_plan(record):
    """Returns the selected plan from an analysis record."""
    return get_planning_data(record).get("selected_plan") or {}


def get_company_match(record):
    """Returns the saved company match result."""
    return (
        record
        .get("derived_analysis", {})
        .get("company_match", {})
        or {}
    )


def get_record_by_id(records, michraz_id):
    """Returns the record with the requested tender ID."""
    for record in records:
        if record.get("michraz_id") == michraz_id:
            return record
    return None


def render_html_table(rows, columns, css_class, widths):
    """Displays rows as a styled HTML table."""
    if not rows:
        st.info("אין נתונים להצגה.")
        return

    headers = "".join(
        "<th>{}</th>".format(html.escape(str(column)))
        for column in columns
    )

    body_rows = []

    for row in rows:
        cells = []

        for column in columns:
            raw_value = row.get(column, "לא זמין")
            formatted_value = format_table_value(raw_value)
            escaped_value = html.escape(str(formatted_value))
            cells.append("<td>{}</td>".format(escaped_value))

        body_rows.append("<tr>{}</tr>".format("".join(cells)))

    width_rules = []

    for index, width in enumerate(widths, start=1):
        width_rules.append(
            """
            .{css_class} th:nth-child({index}),
            .{css_class} td:nth-child({index}) {{
                min-width: {width}px;
            }}
            """.format(
                css_class=css_class,
                index=index,
                width=width,
            )
        )

    table_html = """
    <style>
        .{css_class}-wrapper {{
            width: 100%;
            overflow-x: auto;
            margin: 1.15rem 0;
            border-radius: 18px;
            box-shadow: 0 10px 30px rgba(83, 67, 105, 0.08);
        }}

        .{css_class} {{
            width: 100%;
            border-collapse: separate;
            border-spacing: 0;
            background: rgba(255, 255, 255, 0.94);
            border-radius: 18px;
            overflow: hidden;
            direction: rtl;
            text-align: right;
            table-layout: auto;
        }}

        .{css_class} th,
        .{css_class} td {{
            border: 1px solid #E6DFEA;
            padding: 12px 10px;
            vertical-align: top;
            white-space: normal;
            overflow-wrap: break-word;
            word-break: normal;
            line-height: 1.55;
        }}

        .{css_class} th {{
            background: linear-gradient(135deg, #E9E0F6, #F4EEF9);
            color: #51476F;
            font-weight: 700;
        }}

        .{css_class} tbody tr:nth-child(even) {{
            background-color: #FCFAFE;
        }}

        .{css_class} tbody tr:hover {{
            background-color: #F4F0FA;
        }}

        .{css_class} th:first-child {{
            border-top-right-radius: 18px;
        }}

        .{css_class} th:last-child {{
            border-top-left-radius: 18px;
        }}

        {width_rules}
    </style>

    <div class="{css_class}-wrapper">
        <table class="{css_class}">
            <thead>
                <tr>{headers}</tr>
            </thead>
            <tbody>
                {body_rows}
            </tbody>
        </table>
    </div>
    """.format(
        css_class=css_class,
        width_rules="".join(width_rules),
        headers=headers,
        body_rows="".join(body_rows),
    )

    st.markdown(table_html, unsafe_allow_html=True)


def create_tender_summary(record):
    """Creates one row for the main tenders table."""
    rmi_data = get_rmi_data(record)
    selected_plan = get_selected_plan(record)
    company_match = get_company_match(record)

    city = rmi_data.get("יישוב") or "לא זמין"

    return {
        "מספר מכרז": rmi_data.get("מספר מכרז") or "לא זמין",
        "ציון התאמה": format_score(company_match.get("score")),
        "יישוב": city,
        "מספר יחידות": format_housing_units(
            rmi_data.get("יחידות דיור")
        ),
        "מועד הגשה": format_date(
            rmi_data.get("מועד אחרון"),
            include_time=True,
        ),
        "סטטוס התכנית": (
            selected_plan.get("status")
            or "לא אותרה"
        ),
    }


def render_tenders_table(records):
    """Displays the main tenders table."""
    rows = [create_tender_summary(record) for record in records]

    render_html_table(
        rows=rows,
        columns=[
            "מספר מכרז",
            "ציון התאמה",
            "יישוב",
            "מספר יחידות",
            "מועד הגשה",
            "סטטוס התכנית",
        ],
        css_class="tenders-table",
        widths=[110, 110, 130, 115, 180, 190],
    )


def render_match_table(criteria):
    """Displays the company matching criteria table."""
    rows = []

    for criterion in criteria:
        weight = criterion.get("weight", 0)
        points_awarded = criterion.get("points_awarded", 0)

        if (
            isinstance(points_awarded, float)
            and points_awarded.is_integer()
        ):
            points_awarded = int(points_awarded)

        rows.append({
            "קריטריון": criterion.get("title") or "לא זמין",
            "משקל": weight,
            "סטטוס": translate_status(criterion.get("status")),
            "ערך בפועל": format_table_value(
                criterion.get("actual")
            ),
            "ערך נדרש": format_table_value(
                criterion.get("expected")
            ),
            "נקודות": "{}/{}".format(points_awarded, weight),
            "הסבר": criterion.get("explanation") or "לא זמין",
        })

    render_html_table(
        rows=rows,
        columns=[
            "קריטריון",
            "משקל",
            "סטטוס",
            "ערך בפועל",
            "ערך נדרש",
            "נקודות",
            "הסבר",
        ],
        css_class="match-table",
        widths=[130, 80, 110, 140, 140, 80, 280],
    )


def save_match_to_record(record, profile):
    """Recalculates and saves company matching for one record."""
    file_path = record["_file_path"]

    clean_record = {
        key: value
        for key, value in record.items()
        if key != "_file_path"
    }

    update_company_match(clean_record, profile)
    save_analysis_record(clean_record, file_path)


def recalculate_all_matches(profile):
    """Recalculates company matching for all saved records."""
    for record in load_analysis_records():
        save_match_to_record(record, profile)


def open_tender_page(michraz_id):
    """Opens the details page for one tender."""
    st.session_state["selected_tender_id"] = michraz_id
    st.session_state.pop("details_tender_selection", None)
    st.session_state["requested_page"] = PAGE_TENDER_DETAILS


def go_to_tenders_page():
    """Returns the app to the main tenders page."""
    st.session_state["requested_page"] = PAGE_TENDERS


def tender_options(records):
    """Creates tender labels for the selection widget."""
    options = {}

    for record in records:
        rmi_data = get_rmi_data(record)
        tender_number = rmi_data.get("מספר מכרז") or "ללא מספר"
        locality = rmi_data.get("יישוב") or "לא זמין"

        label = "{} — {}".format(
            tender_number,
            locality,
        )

        options[label] = record

    return options


def render_tenders_page(records):
    """Displays the active tenders page."""
    st.title("📋 רשימת מכרזים")

    st.write(
        "המכרזים שנמשכו ונותחו, מדורגים בהתאם "
        "לפרופיל החברה שהוגדר."
    )

    open_records = [
        record
        for record in records
        if is_open_tender(record)
    ]

    if not open_records:
        st.info("אין מכרזים פתוחים להצגה.")
        return

    sorted_records = sort_by_deadline(open_records)
    render_tenders_table(sorted_records)

    options = tender_options(sorted_records)

    selected_label = st.selectbox(
        "בחרי מכרז לצפייה",
        list(options.keys()),
        key="tender_list_selection",
    )

    selected_record = options[selected_label]

    st.button(
        "פתיחת עמוד המכרז",
        type="primary",
        use_container_width=True,
        on_click=open_tender_page,
        args=(selected_record.get("michraz_id"),),
    )


def render_tender_details_page(records):
    """Displays the full details page for a selected tender."""
    st.title("📄 עמוד המכרז")

    options = tender_options(records)

    selected_record = get_record_by_id(
        records,
        st.session_state.get("selected_tender_id"),
    )

    if selected_record is None:
        selected_record = records[0]

    st.session_state["selected_tender_id"] = selected_record.get(
        "michraz_id"
    )

    labels = list(options.keys())
    current_label = labels[0]

    for label, record in options.items():
        if record.get("michraz_id") == selected_record.get("michraz_id"):
            current_label = label
            break

    selected_label = st.selectbox(
        "מעבר למכרז אחר",
        labels,
        index=labels.index(current_label),
        key="details_tender_selection",
    )

    selected_record = options[selected_label]
    st.session_state["selected_tender_id"] = selected_record.get(
        "michraz_id"
    )

    st.button(
        "חזרה לרשימת המכרזים",
        on_click=go_to_tenders_page,
    )

    refresh_message = st.session_state.pop(
        "rmi_refresh_message",
        None,
    )

    if refresh_message:
        st.success(refresh_message)

    if st.button("רענון הנתונים מרמ״י"):
        michraz_id = selected_record.get(
            "michraz_id"
        )

        try:
            with st.spinner(
                "הנתונים מתרעננים מרמ״י..."
            ):
                refreshed_record = refresh_rmi_data(
                    michraz_id
                )

                refreshed_record["_file_path"] = (
                    selected_record["_file_path"]
                )

                save_match_to_record(
                    refreshed_record,
                    load_profile(),
                )

            st.session_state[
                "rmi_refresh_message"
            ] = (
                "נתוני המכרז עודכנו בהצלחה מרמ״י."
            )

            st.rerun()

        except Exception as error:
            st.error(
                "רענון הנתונים מרמ״י נכשל. "
                "הנתונים הקודמים נשמרו. "
                "פרטי השגיאה: {}".format(error)
            )

    rmi_data = get_rmi_data(selected_record)
    ai_data = get_ai_data(selected_record)
    ai_source = (
        selected_record
        .get("sources", {})
        .get("tender_booklet_ai", {})
    )
    ai_status = ai_source.get("status")
    planning_data = get_planning_data(selected_record)
    selected_plan = get_selected_plan(selected_record)
    company_match = get_company_match(selected_record)

    tender_number = rmi_data.get("מספר מכרז") or ""
    st.header("מכרז {}".format(tender_number))

    metric_1, metric_2, metric_3 = st.columns(3)

    metric_1.metric(
        "מחיר מינימום",
        format_money(rmi_data.get("מחיר מינימום")),
    )

    metric_2.metric(
        "סכום ערבות",
        format_money(rmi_data.get("סכום ערבות")),
    )

    metric_3.metric(
        "ציון התאמה סופי",
        format_score(company_match.get("score")),
    )

    known_match_score = company_match.get("known_match_score")
    data_coverage = company_match.get("data_coverage")
    coverage_text = format_percentage(data_coverage)

    (
        details_tab,
        extraction_tab,
        planning_tab,
        match_tab,
        checks_tab,
        sources_tab,
    ) = st.tabs(
        [
            "פרטי המכרז",
            "נתונים שחולצו",
            "פרטי התכנית",
            "התאמה לפרופיל החברה",
            "מידע חסר ונקודות לבדיקה",
            "מקורות המידע",
        ]
    )

    with details_tab:
        left_column, right_column = st.columns(2)

        with left_column:
            st.subheader("פרטים כלליים")

            st.write(
                "**מספר מכרז:**",
                rmi_data.get("מספר מכרז")
                or "לא זמין",
            )

            st.write(
                "**סוג מכרז:**",
                rmi_data.get("סוג מכרז") or "לא זמין",
            )

            st.write(
                "**יישוב:**",
                rmi_data.get("יישוב") or "לא זמין",
            )

            st.write(
                "**מיקום / שכונה:**",
                rmi_data.get("שכונה") or "לא זמין",
            )

            st.write(
                "**ייעוד המכרז:**",
                rmi_data.get("ייעוד מכרז") or "טרם מופה",
            )

            st.write(
                "**מספרי תכנית לפי רמ״י:**",
                format_list(
                    rmi_data.get(
                        "מספרי תכנית מובנים"
                    )
                ),
            )

            st.write(
                "**יחידות דיור:**",
                format_housing_units(
                    rmi_data.get("יחידות דיור")
                ),
            )

            st.write(
                "**מגרשים:**",
                format_list(rmi_data.get("מגרשים")),
            )

            st.write(
                "**גוש וחלקה:**",
                format_list(rmi_data.get("גוש/חלקה")),
            )

        with right_column:
            st.subheader("מועדים ועלויות")

            st.write(
                "**תאריך פרסום:**",
                format_date(rmi_data.get("תאריך פרסום")),
            )

            st.write(
                "**מועד אחרון להגשה:**",
                format_date(
                    rmi_data.get("מועד אחרון"),
                    include_time=True,
                ),
            )

            st.write(
                "**מחיר מינימום:**",
                format_money(rmi_data.get("מחיר מינימום")),
            )

            st.write(
                "**סכום ערבות:**",
                format_money(rmi_data.get("סכום ערבות")),
            )

            st.write(
                "**הוצאות פיתוח:**",
                format_money(rmi_data.get("הוצאות פיתוח")),
            )

            st.write(
                "**תוקף ערבות:**",
                format_date(rmi_data.get("תוקף ערבות")),
            )

        source_url = rmi_data.get("קישור למקור")

        if source_url:
            st.link_button(
                "פתיחת עמוד המכרז הרשמי",
                source_url,
            )

    with extraction_tab:
        if ai_status == "booklet_not_found":
            st.info(
                "לא נמצאה חוברת מכרז או מסמך מרכזי, "
                "ולכן לא בוצע חילוץ AI מהחוברת."
            )

        elif ai_status in {"failed", "invalid_json"}:
            st.error(
                "נמצאה חוברת מכרז, אך חילוץ ה-AI "
                "מהחוברת נכשל."
            )

        elif ai_status == "success":
            plan_number = ai_data.get("plan_number", {})

            st.subheader("מספר תכנית שחולץ")
            st.write(
                "**ערך:**",
                format_value(plan_number.get("value")),
            )
            st.write(
                "**מסמך מקור:**",
                format_value(
                    plan_number.get("source_document")
                ),
            )
            st.write(
                "**עמוד:**",
                format_value(plan_number.get("page")),
            )
            st.write(
                "**רמת ביטחון:**",
                format_value(plan_number.get("confidence")),
            )

            if plan_number.get("excerpt"):
                st.info(plan_number["excerpt"])
            else:
                st.warning(
                    "מספר התכנית לא נמצא בבירור בחוברת."
                )

            st.subheader("תנאים מרכזיים")

            threshold_conditions = ai_data.get(
                "threshold_conditions",
                [],
            )

            if not threshold_conditions:
                st.info("לא נמצאו תנאים שחולצו.")

            for index, condition in enumerate(
                threshold_conditions,
                start=1,
            ):
                condition_value = (
                    condition.get("value") or ""
                )
                title = "תנאי {}: {}".format(
                    index,
                    condition_value,
                )

                with st.expander(title):
                    st.write(
                        "**מסמך מקור:**",
                        format_value(
                            condition.get(
                                "source_document"
                            )
                        ),
                    )
                    st.write(
                        "**עמוד:**",
                        format_value(
                            condition.get("page")
                        ),
                    )
                    st.write(
                        "**רמת ביטחון:**",
                        format_value(
                            condition.get("confidence")
                        ),
                    )
                    st.write(
                        "**ציטוט:**",
                        format_value(
                            condition.get("excerpt")
                        ),
                    )

        else:
            st.info("חילוץ AI מהחוברת טרם הושלם.")

    with planning_tab:
        if not planning_data:
            st.warning(
                "טרם בוצע חיפוש במאגר התכניות. "
                "יש להריץ את planning.py."
            )
        else:
            candidates = planning_data.get(
                "candidates", []
            )

            if selected_plan:
                st.subheader("התכנית שנבחרה")

                st.write(
                    "**מספר התכנית שנבחרה במאגר התכנון:**",
                    format_value(
                        selected_plan.get("plan_number")
                    ),
                )
                st.write(
                    "**שם התכנית במאגר התכנון:**",
                    format_value(
                        selected_plan.get("plan_name")
                    ),
                )
                st.write(
                    "**יישוב:**",
                    format_value(selected_plan.get("city")),
                )
                st.write(
                    "**סטטוס:**",
                    format_value(selected_plan.get("status")),
                )
                st.write(
                    "**תאריך סטטוס:**",
                    format_date(
                        selected_plan.get("status_date")
                    ),
                )
                st.write(
                    "**ייעוד מרכזי:**",
                    format_value(
                        selected_plan.get("main_designation")
                    ),
                )
                st.write(
                    "**יחידות דיור בתכנית:**",
                    format_value(
                        selected_plan.get("housing_units")
                    ),
                )

                plan_id = selected_plan.get("plan_id")

                if plan_id:
                    plan_page_url = (
                        "https://apps.land.gov.il/"
                        f"TabaSearch/#/Plans/Plan/{plan_id}"
                    )

                    st.link_button(
                        "פתיחת התכנית באתר רמ״י",
                        plan_page_url,
                    )

                st.info(
                    planning_data.get(
                        "selection_reason",
                        "לא נשמר הסבר לבחירה.",
                    )
                )

                if planning_data.get("requires_verification"):
                    st.warning(
                        "נמצאו מספר אפשרויות. "
                        "הבחירה דורשת אימות."
                    )
            else:
                st.subheader("איתור התכנית")

                searched_plan_numbers = planning_data.get(
                    "searched_plan_numbers",
                    [],
                )

                if candidates:
                    st.warning(
                        "נמצאו תכניות אפשריות, אך לא ניתן "
                        "היה לבחור תכנית אחת באופן אוטומטי."
                    )
                elif searched_plan_numbers:
                    st.warning(
                        "מספר התכנית במכרז ידוע, אך לא "
                        "נמצאה תכנית תואמת במאגר התכנון."
                    )
                    st.write(
                        "**מספרי התכנית הידועים מהמכרז:**",
                        format_list(searched_plan_numbers),
                    )
                else:
                    st.warning(
                        "אין מספיק מידע כדי לאתר תכנית "
                        "במאגר התכנון."
                    )

            st.subheader("אפשרויות התאמה")

            selected_plan_id = selected_plan.get("plan_id")

            for candidate in candidates:
                candidate_number = (
                    candidate.get("plan_number")
                    or "ללא מספר"
                )
                candidate_name = (
                    candidate.get("plan_name")
                    or "ללא שם"
                )
                candidate_label = "{} — {}".format(
                    candidate_number,
                    candidate_name,
                )

                expanded = (
                    candidate.get("plan_id")
                    == selected_plan_id
                )

                with st.expander(
                    candidate_label,
                    expanded=expanded,
                ):
                    st.write(
                        "**יישוב:**",
                        format_value(candidate.get("city")),
                    )
                    st.write(
                        "**סטטוס:**",
                        format_value(candidate.get("status")),
                    )

                    reasons = candidate.get(
                        "match_reasons",
                        [],
                    )

                    if reasons:
                        st.write("**סיבות להתאמה:**")
                        for reason in reasons:
                            st.write("• {}".format(reason))
                    else:
                        st.write("לא נשמרו סיבות להתאמה.")

            st.subheader("מסמכי התכנית")

            special_documents = selected_plan.get(
                "special_documents",
                {},
            )

            if not special_documents:
                st.info("לא נמצאו קישורים למסמכי התכנית.")

            for document_key, document in special_documents.items():
                document_name = (
                    document.get("name")
                    or document_key
                )
                document_url = document.get("url")

                if document_url:
                    st.markdown(
                        "- [{}]({})".format(
                            document_name,
                            document_url,
                        )
                    )

    with match_tab:
        if not company_match:
            st.warning(
                "טרם חושבה התאמה לפרופיל החברה. "
                "יש להריץ את matching.py."
            )
        else:
            (
                score_column,
                known_match_column,
                coverage_column,
            ) = st.columns(3)

            score_column.metric(
                "ציון התאמה סופי",
                format_score(company_match.get("score")),
            )

            known_match_column.metric(
                "התאמה לפי מידע ידוע",
                format_percentage(known_match_score),
            )

            coverage_column.metric(
                "כיסוי מידע",
                coverage_text,
            )

            st.subheader(
                company_match.get(
                    "recommendation",
                    "ללא המלצה",
                )
            )

            render_match_table(
                company_match.get("criteria", [])
            )

    with checks_tab:
        st.subheader("מידע חסר")

        missing_information = company_match.get(
            "missing_information",
            [],
        )

        if missing_information:
            for item in missing_information:
                st.warning(item)
        else:
            st.success(
                "לא זוהה מידע חסר לצורך חישוב ההתאמה."
            )

        st.subheader("נקודות משמעותיות לבדיקה")

        point_to_check = ai_data.get(
            "point_to_check",
            {},
        )

        if ai_status == "booklet_not_found":
            st.info(
                "לא נמצאה חוברת מכרז או מסמך מרכזי, "
                "ולכן לא בוצע חילוץ AI מהחוברת."
            )

        elif ai_status in {"failed", "invalid_json"}:
            st.error(
                "נמצאה חוברת מכרז, אך חילוץ ה-AI "
                "מהחוברת נכשל."
            )

        elif (
            ai_status == "success"
            and point_to_check.get("value")
        ):
            st.warning(point_to_check["value"])

            source_details = []

            source_document = point_to_check.get(
                "source_document"
            )
            page = point_to_check.get("page")
            confidence = point_to_check.get("confidence")

            if source_document:
                source_details.append(
                    "מסמך: {}".format(source_document)
                )

            if page:
                source_details.append(
                    "עמוד: {}".format(page)
                )

            if confidence:
                source_details.append(
                    "רמת ביטחון: {}".format(confidence)
                )

            if source_details:
                st.caption(" | ".join(source_details))

            if point_to_check.get("excerpt"):
                with st.expander("הצגת קטע המקור"):
                    st.write(point_to_check["excerpt"])
        elif ai_status == "success":
            st.info(
                "חילוץ ה-AI מהחוברת הושלם, אך לא "
                "נמצאה נקודה משמעותית לבדיקה."
            )

        else:
            st.info("חילוץ AI מהחוברת טרם הושלם.")

        clarification_criteria = company_match.get(
            "criteria_requiring_clarification",
            [],
        )

        if clarification_criteria:
            st.subheader("קריטריונים שדורשים בירור")

            for criterion in clarification_criteria:
                st.write("• {}".format(criterion))

    with sources_tab:
        source_url = rmi_data.get("קישור למקור")

        if source_url:
            st.link_button(
                "פתיחת עמוד המכרז הרשמי",
                source_url,
            )

        documents_page_url = rmi_data.get(
            "קישור למסמכי המכרז"
        )

        if documents_page_url:
            st.link_button(
                "פתיחת כלל מסמכי המכרז",
                documents_page_url,
            )

        rmi_documents = rmi_data.get(
            "מסמכי מכרז מובנים",
            [],
        )

        if rmi_documents:
            with st.expander(
                "הצגת קישורים למסמכי המכרז"
            ):
                for index, document in enumerate(
                    rmi_documents
                ):
                    document_name = (
                        document.get("name")
                        or "מסמך ללא שם"
                    )

                    if (
                        document.get("role")
                        == "tender_booklet"
                    ):
                        document_label = (
                            "חוברת המכרז: {}".format(
                                document_name
                            )
                        )
                    else:
                        document_label = document_name

                    document_url = document.get(
                        "source_url"
                    )

                    if document_url:
                        st.link_button(
                            document_label,
                            document_url,
                        )

        st.subheader("מסמכי המכרז")

        documents = selected_record.get("documents", [])

        if not documents:
            st.info("לא נשמרו מסמכים עבור המכרז.")

        for document in documents:
            document_name = (
                document.get("name")
                or "ללא שם"
            )

            st.write("**{}**".format(document_name))
            st.write(
                "**סוג קובץ:**",
                document.get("file_type") or "לא זמין",
            )
            st.write(
                "**מועד הורדה:**",
                format_date(
                    document.get("downloaded_at"),
                    include_time=True,
                ),
            )
            st.write(
                "**סטטוס עיבוד:**",
                document.get("processing_status")
                or "לא זמין",
            )

            st.divider()

        with st.expander("הצגת הרשומה המלאה"):
            clean_record = {
                key: value
                for key, value in selected_record.items()
                if key != "_file_path"
            }
            st.json(clean_record)


def render_company_profile_page():
    """Displays and updates the company profile form."""
    st.title("⚙️ הגדרות חברה")

    st.write(
        "הגדירי את הקריטריונים של החברה. "
        "לאחר השמירה יחושבו מחדש ציוני ההתאמה."
    )

    profile = load_profile()

    with st.form("company_profile_form"):
        profile_name = st.text_input(
            "שם הפרופיל",
            value=profile["profile_name"],
        )

        activity_areas_text = st.text_input(
            "אזורי פעילות — מופרדים בפסיקים",
            value=", ".join(profile["activity_areas"]),
        )

        project_types_text = st.text_input(
            "סוגי פרויקטים — מופרדים בפסיקים",
            value=", ".join(profile["project_types"]),
        )

        minimum_units_column, maximum_units_column = (
            st.columns(2)
        )

        with minimum_units_column:
            min_housing_units = st.number_input(
                "מינימום יחידות דיור",
                min_value=0,
                value=int(profile["min_housing_units"]),
            )

        with maximum_units_column:
            max_housing_units = st.number_input(
                "מקסימום יחידות דיור",
                min_value=0,
                value=int(profile["max_housing_units"]),
            )

        max_development_costs = st.number_input(
            "הוצאות פיתוח מקסימליות",
            min_value=0,
            value=int(profile["max_development_costs"]),
            step=100000,
        )

        requires_approved_plan = st.checkbox(
            "נדרשת תכנית מאושרת",
            value=profile["requires_approved_plan"],
        )

        min_days_until_submission = st.number_input(
            "מינימום ימים עד להגשה",
            min_value=0,
            value=int(profile["min_days_until_submission"]),
        )

        submitted = st.form_submit_button(
            "שמור וחשב מחדש",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        activity_areas = [
            item.strip()
            for item in activity_areas_text.split(",")
            if item.strip()
        ]

        project_types = [
            item.strip()
            for item in project_types_text.split(",")
            if item.strip()
        ]

        updated_profile = {
            "profile_name": profile_name,
            "activity_areas": activity_areas,
            "project_types": project_types,
            "min_housing_units": int(min_housing_units),
            "max_housing_units": int(max_housing_units),
            "max_development_costs": int(
                max_development_costs
            ),
            "requires_approved_plan": (
                requires_approved_plan
            ),
            "min_days_until_submission": int(
                min_days_until_submission
            ),
        }

        try:
            save_profile(updated_profile)
            recalculate_all_matches(updated_profile)

            st.success(
                "הפרופיל נשמר וההתאמות חושבו מחדש."
            )

            st.rerun()

        except ValueError as error:
            st.error(str(error))


records = load_analysis_records()

if "current_page" not in st.session_state:
    st.session_state["current_page"] = PAGE_TENDERS

if "requested_page" in st.session_state:
    st.session_state["current_page"] = (
        st.session_state.pop("requested_page")
    )

if "selected_tender_id" not in st.session_state and records:
    st.session_state["selected_tender_id"] = (
        records[0].get("michraz_id")
    )


st.sidebar.title("ניווט במערכת")

st.sidebar.radio(
    "בחרי אזור",
    [
        PAGE_TENDERS,
        PAGE_TENDER_DETAILS,
        PAGE_COMPANY_PROFILE,
    ],
    key="current_page",
    label_visibility="collapsed",
)

st.sidebar.divider()

st.sidebar.caption(
    "סוכנת AI לאיתור וניתוח ראשוני של מכרזי רמ״י"
)


current_page = st.session_state["current_page"]

if current_page == PAGE_TENDERS:
    if records:
        render_tenders_page(records)
    else:
        st.error(
            "לא נמצאו מכרזים בתיקייה data/analysis. "
            "יש להריץ תחילה את analyze.py."
        )

elif current_page == PAGE_TENDER_DETAILS:
    if records:
        render_tender_details_page(records)
    else:
        st.error(
            "לא נמצאו מכרזים בתיקייה data/analysis. "
            "יש להריץ תחילה את analyze.py."
        )

else:
    render_company_profile_page()
