import json
from datetime import datetime, timezone
from pathlib import Path


PROFILE_PATH = Path("data/company_profile.json")
ANALYSIS_DIR = Path("data/analysis")


# המשקלים מסתכמים ל-100
WEIGHTS = {
    "activity_area": 20,
    "project_type": 20,
    "housing_units": 20,
    "development_costs": 15,
    "approved_plan": 15,
    "submission_days": 10,
}


def load_json(path):
    if not path.exists():
        raise FileNotFoundError(
            f"File was not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file)


def normalize_text(value):
    """
    מנרמל טקסט לצורך השוואה פשוטה.
    """

    if value is None:
        return ""

    return (
        str(value)
        .replace("-", " ")
        .replace("–", " ")
        .replace("־", " ")
        .replace('"', "")
        .replace("״", "")
        .strip()
        .lower()
    )


def values_match(actual_value, expected_values):
    """
    בדיקה האם הערך בפועל תואם לאחד מערכי הפרופיל.
    """

    actual = normalize_text(actual_value)

    if not actual:
        return False

    for expected_value in expected_values:
        expected = normalize_text(expected_value)

        if expected and (
            expected in actual
            or actual in expected
        ):
            return True

    return False


def get_rmi_data(record):
    return (
        record
        .get("sources", {})
        .get("rmi_api", {})
        .get("data", {})
    )


def get_selected_plan(record):
    return (
        record
        .get("sources", {})
        .get("planning_api", {})
        .get("data", {})
        .get("selected_plan")
    )


def calculate_days_until_submission(deadline_value):
    if not deadline_value:
        return None

    try:
        deadline = datetime.fromisoformat(deadline_value)

        if deadline.tzinfo is None:
            deadline = deadline.replace(
                tzinfo=timezone.utc
            )

        now = datetime.now(deadline.tzinfo)

        seconds_remaining = (
            deadline - now
        ).total_seconds()

        return int(seconds_remaining // 86400)

    except (TypeError, ValueError):
        return None


def is_meaningful_designation(value):
    return bool(
        value
        and normalize_text(value) != "אחר"
    )


def get_project_designation(
    rmi_data,
    selected_plan,
):
    tender_designation = rmi_data.get(
        "ייעוד מכרז"
    )

    if is_meaningful_designation(
        tender_designation
    ):
        return (
            tender_designation,
            f"ייעוד המכרז ברמ״י הוא "
            f"{tender_designation}",
        )

    plan_designation = None

    if selected_plan:
        plan_designation = selected_plan.get(
            "main_designation"
        )

    if is_meaningful_designation(
        plan_designation
    ):
        return (
            plan_designation,
            f"ייעוד התכנית שנבחרה הוא "
            f"{plan_designation}",
        )

    housing_units = rmi_data.get(
        "יחידות דיור"
    )

    if (
        isinstance(housing_units, (int, float))
        and housing_units > 0
    ):
        return (
            "מגורים",
            "מספר יחידות הדיור במכרז גדול מאפס, "
            "ולכן סוג הפרויקט סווג כמגורים",
        )

    if tender_designation:
        return (
            tender_designation,
            f"ייעוד המכרז ברמ״י הוא "
            f"{tender_designation}",
        )

    if plan_designation:
        return (
            plan_designation,
            f"ייעוד התכנית שנבחרה הוא "
            f"{plan_designation}",
        )

    return None, None


def normalize_project_type(designation):
    if not designation:
        return None

    normalized = normalize_text(designation)

    if (
        "מגורים" in normalized
        or "בנייה רוויה" in normalized
        or "בניה רוויה" in normalized
        or "בנייה נמוכה" in normalized
        or "בניה נמוכה" in normalized
        or "צמודת קרקע" in normalized
    ):
        return "מגורים"

    if normalized == "אחר":
        return None

    return designation


def add_criterion(
    criteria,
    key,
    title,
    weight,
    actual,
    expected,
    status,
    explanation,
):
    points = weight if status == "matched" else 0

    criteria.append({
        "key": key,
        "title": title,
        "weight": weight,
        "status": status,
        "actual": actual,
        "expected": expected,
        "points_awarded": points,
        "explanation": explanation,
    })


def calculate_company_match(record, profile):
    rmi_data = get_rmi_data(record)
    selected_plan = get_selected_plan(record)

    criteria = []

    # 1. אזור פעילות
    city = None

    if selected_plan:
        city = selected_plan.get("city")

    if city is None:
        add_criterion(
            criteria=criteria,
            key="activity_area",
            title="אזור פעילות",
            weight=WEIGHTS["activity_area"],
            actual=None,
            expected=profile["activity_areas"],
            status="needs_clarification",
            explanation=(
                "לא נמצא שם יישוב שניתן להשוות "
                "לאזורי הפעילות של החברה."
            ),
        )

    elif values_match(
        city,
        profile["activity_areas"],
    ):
        add_criterion(
            criteria=criteria,
            key="activity_area",
            title="אזור פעילות",
            weight=WEIGHTS["activity_area"],
            actual=city,
            expected=profile["activity_areas"],
            status="matched",
            explanation=(
                f"היישוב {city} נמצא באזורי "
                "הפעילות של החברה."
            ),
        )

    else:
        add_criterion(
            criteria=criteria,
            key="activity_area",
            title="אזור פעילות",
            weight=WEIGHTS["activity_area"],
            actual=city,
            expected=profile["activity_areas"],
            status="not_matched",
            explanation=(
                f"היישוב {city} אינו נמצא באזורי "
                "הפעילות שהוגדרו."
            ),
        )

    # 2. סוג פרויקט
    (
        project_designation,
        project_source,
    ) = get_project_designation(
        rmi_data,
        selected_plan,
    )

    project_type = normalize_project_type(
        project_designation
    )

    project_explanation = project_source

    if (
        project_type
        and project_type != project_designation
    ):
        project_explanation = (
            f"{project_source}, ולכן סוג הפרויקט "
            f"סווג כ{project_type}"
        )

    if project_type is None:
        add_criterion(
            criteria=criteria,
            key="project_type",
            title="סוג פרויקט",
            weight=WEIGHTS["project_type"],
            actual=project_designation,
            expected=profile["project_types"],
            status="needs_clarification",
            explanation=(
                (
                    f"{project_source}, אך לא ניתן "
                    "לקבוע ממנו את סוג הפרויקט."
                )
                if project_source
                else (
                    "לא ניתן לקבוע בוודאות את סוג "
                    "הפרויקט מהנתונים הקיימים."
                )
            ),
        )

    elif values_match(
        project_type,
        profile["project_types"],
    ):
        add_criterion(
            criteria=criteria,
            key="project_type",
            title="סוג פרויקט",
            weight=WEIGHTS["project_type"],
            actual=project_designation,
            expected=profile["project_types"],
            status="matched",
            explanation=(
                f"{project_explanation}, והוא מתאים "
                "לפרופיל החברה."
            ),
        )

    else:
        add_criterion(
            criteria=criteria,
            key="project_type",
            title="סוג פרויקט",
            weight=WEIGHTS["project_type"],
            actual=project_designation,
            expected=profile["project_types"],
            status="not_matched",
            explanation=(
                f"{project_explanation}, והוא אינו "
                "מתאים לסוגי הפרויקטים שהוגדרו."
            ),
        )

    # 3. מספר יחידות דיור
    housing_units = rmi_data.get("יחידות דיור")

    if (
        not isinstance(housing_units, (int, float))
        or housing_units == 0
    ):
        add_criterion(
            criteria=criteria,
            key="housing_units",
            title="מספר יחידות דיור",
            weight=WEIGHTS["housing_units"],
            actual=None,
            expected={
                "minimum": profile["min_housing_units"],
                "maximum": profile["max_housing_units"],
            },
            status="needs_clarification",
            explanation=(
                "מספר יחידות הדיור אינו זמין או שאינו "
                "רלוונטי לסוג המכרז, ונדרש בירור."
            ),
        )

    elif (
        profile["min_housing_units"]
        <= housing_units
        <= profile["max_housing_units"]
    ):
        add_criterion(
            criteria=criteria,
            key="housing_units",
            title="מספר יחידות דיור",
            weight=WEIGHTS["housing_units"],
            actual=housing_units,
            expected={
                "minimum": profile["min_housing_units"],
                "maximum": profile["max_housing_units"],
            },
            status="matched",
            explanation=(
                f"{housing_units} יחידות נמצאות "
                "בטווח שהוגדר."
            ),
        )

    else:
        add_criterion(
            criteria=criteria,
            key="housing_units",
            title="מספר יחידות דיור",
            weight=WEIGHTS["housing_units"],
            actual=housing_units,
            expected={
                "minimum": profile["min_housing_units"],
                "maximum": profile["max_housing_units"],
            },
            status="not_matched",
            explanation=(
                f"{housing_units} יחידות אינן בטווח "
                "שהגדירה החברה."
            ),
        )

    # 4. הוצאות פיתוח
    development_costs = rmi_data.get(
        "הוצאות פיתוח"
    )

    if (
        not isinstance(development_costs, (int, float))
        or development_costs == 0
    ):
        add_criterion(
            criteria=criteria,
            key="development_costs",
            title="הוצאות פיתוח",
            weight=WEIGHTS["development_costs"],
            actual=None,
            expected=profile[
                "max_development_costs"
            ],
            status="needs_clarification",
            explanation=(
                "הוצאות הפיתוח אינן זמינות או שאינן "
                "רלוונטיות לסוג המכרז, ונדרש בירור."
            ),
        )

    elif (
        development_costs
        <= profile["max_development_costs"]
    ):
        add_criterion(
            criteria=criteria,
            key="development_costs",
            title="הוצאות פיתוח",
            weight=WEIGHTS["development_costs"],
            actual=development_costs,
            expected=profile[
                "max_development_costs"
            ],
            status="matched",
            explanation=(
                "הוצאות הפיתוח אינן חורגות "
                "מהמקסימום שהוגדר."
            ),
        )

    else:
        add_criterion(
            criteria=criteria,
            key="development_costs",
            title="הוצאות פיתוח",
            weight=WEIGHTS["development_costs"],
            actual=development_costs,
            expected=profile[
                "max_development_costs"
            ],
            status="not_matched",
            explanation=(
                "הוצאות הפיתוח חורגות מהמקסימום "
                "שהוגדר."
            ),
        )

    # 5. תכנית מאושרת
    plan_status = None

    if selected_plan:
        plan_status = selected_plan.get("status")

    if not profile["requires_approved_plan"]:
        add_criterion(
            criteria=criteria,
            key="approved_plan",
            title="סטטוס תכנוני",
            weight=WEIGHTS["approved_plan"],
            actual=plan_status,
            expected="אין דרישה לתכנית מאושרת",
            status="matched",
            explanation=(
                "החברה אינה דורשת תכנית מאושרת."
            ),
        )

    elif not plan_status:
        add_criterion(
            criteria=criteria,
            key="approved_plan",
            title="סטטוס תכנוני",
            weight=WEIGHTS["approved_plan"],
            actual=None,
            expected="תכנית מאושרת",
            status="needs_clarification",
            explanation=(
                "לא נמצא סטטוס תכנוני ברור."
            ),
        )

    elif (
        "תוקף" in plan_status
        or "מאושר" in plan_status
        or "אישור" in plan_status
    ):
        add_criterion(
            criteria=criteria,
            key="approved_plan",
            title="סטטוס תכנוני",
            weight=WEIGHTS["approved_plan"],
            actual=plan_status,
            expected="תכנית מאושרת",
            status="matched",
            explanation=(
                f"סטטוס התכנית הוא: {plan_status}."
            ),
        )

    else:
        add_criterion(
            criteria=criteria,
            key="approved_plan",
            title="סטטוס תכנוני",
            weight=WEIGHTS["approved_plan"],
            actual=plan_status,
            expected="תכנית מאושרת",
            status="not_matched",
            explanation=(
                f"סטטוס התכנית אינו מעיד בבירור "
                f"על תכנית מאושרת: {plan_status}."
            ),
        )

    # 6. מספר ימים עד ההגשה
    submission_deadline = rmi_data.get(
        "מועד אחרון"
    )

    days_remaining = calculate_days_until_submission(
        submission_deadline
    )

    if days_remaining is None:
        add_criterion(
            criteria=criteria,
            key="submission_days",
            title="זמן עד להגשה",
            weight=WEIGHTS["submission_days"],
            actual=None,
            expected=profile[
                "min_days_until_submission"
            ],
            status="needs_clarification",
            explanation=(
                "לא ניתן לחשב את הזמן שנותר להגשה."
            ),
        )

    elif (
        days_remaining
        >= profile["min_days_until_submission"]
    ):
        add_criterion(
            criteria=criteria,
            key="submission_days",
            title="זמן עד להגשה",
            weight=WEIGHTS["submission_days"],
            actual=days_remaining,
            expected=profile[
                "min_days_until_submission"
            ],
            status="matched",
            explanation=(
                f"נותרו {days_remaining} ימים, "
                "מספיק לפי פרופיל החברה."
            ),
        )

    else:
        add_criterion(
            criteria=criteria,
            key="submission_days",
            title="זמן עד להגשה",
            weight=WEIGHTS["submission_days"],
            actual=days_remaining,
            expected=profile[
                "min_days_until_submission"
            ],
            status="not_matched",
            explanation=(
                f"נותרו רק {days_remaining} ימים "
                "עד למועד ההגשה."
            ),
        )

    known_criteria = [
        criterion
        for criterion in criteria
        if criterion["status"]
        != "needs_clarification"
    ]

    known_weight = sum(
        criterion["weight"]
        for criterion in known_criteria
    )

    earned_points = sum(
        criterion["points_awarded"]
        for criterion in criteria
    )

    if known_weight:
        score = round(
            earned_points / known_weight * 100
        )
    else:
        score = 0

    data_coverage = known_weight

    matched_criteria = [
        criterion["title"]
        for criterion in criteria
        if criterion["status"] == "matched"
    ]

    criteria_requiring_clarification = [
        criterion["title"]
        for criterion in criteria
        if criterion["status"]
        == "needs_clarification"
    ]

    missing_information = [
        criterion["explanation"]
        for criterion in criteria
        if criterion["status"]
        == "needs_clarification"
    ]

    if data_coverage < 70:
        recommendation = "דורש בירור"

    elif score >= 80:
        recommendation = "התאמה גבוהה"

    elif score >= 60:
        recommendation = "מתאים לבדיקה"

    elif score >= 40:
        recommendation = "דורש בירור"

    else:
        recommendation = "התאמה נמוכה"

    return {
        "profile_name": profile["profile_name"],
        "calculated_at": datetime.now(
            timezone.utc
        ).isoformat(),
        "score": score,
        "data_coverage": data_coverage,
        "recommendation": recommendation,
        "matched_criteria": matched_criteria,
        "criteria_requiring_clarification": (
            criteria_requiring_clarification
        ),
        "missing_information": missing_information,
        "criteria": criteria,
        "scoring_method": {
            "weights": WEIGHTS,
            "explanation": (
                "הציון מחושב מתוך הקריטריונים "
                "שעבורם קיים מידע. data_coverage מציג "
                "כמה מתוך 100 נקודות המשקל נבדקו."
            ),
        },
    }


def calculate_match_for_file(analysis_path, profile):
    record = load_json(analysis_path)

    company_match = calculate_company_match(
        record,
        profile,
    )

    record.setdefault("derived_analysis", {})

    record["derived_analysis"][
        "company_match"
    ] = company_match

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
        f"{analysis_path.name}: "
        f"score={company_match['score']}, "
        f"recommendation="
        f"{company_match['recommendation']}"
    )


def main():
    profile = load_json(PROFILE_PATH)

    analysis_files = sorted(
        ANALYSIS_DIR.glob("*.json")
    )

    if not analysis_files:
        print(
            "No files were found in data/analysis."
        )
        return

    print(
        f"Calculating match for "
        f"{len(analysis_files)} tender(s)..."
    )

    for analysis_path in analysis_files:
        try:
            calculate_match_for_file(
                analysis_path,
                profile,
            )

        except Exception as error:
            print(
                f"FAILED {analysis_path.name}: "
                f"{error}"
            )


if __name__ == "__main__":
    main()
