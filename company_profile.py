import json
from pathlib import Path

PROFILE_PATH = Path("data/company_profile.json")

# ערכי דוגמה בלבד.
# בהמשך המשתמש יוכל לשנות אותם דרך הטופס בממשק.
DEFAULT_PROFILE = {
    "profile_name": "חברת נדל״ן לדוגמה",

    "activity_areas": [
        "תל אביב יפו",
        "רמת גן",
        "גבעתיים"
    ],

    "project_types": [
        "מגורים",
        "התחדשות עירונית"
    ],

    "min_housing_units": 10,
    "max_housing_units": 250,
    "max_development_costs": 20000000,
    "requires_approved_plan": True,
    "min_days_until_submission": 14
}

def validate_profile(profile):
    """
    בדיקה שהפרופיל מכיל ערכים תקינים.
    """

    required_fields = [
        "profile_name",
        "activity_areas",
        "project_types",
        "min_housing_units",
        "max_housing_units",
        "max_development_costs",
        "requires_approved_plan",
        "min_days_until_submission",
    ]

    missing_fields = [
        field
        for field in required_fields
        if field not in profile
    ]

    if missing_fields:
        raise ValueError(
            f"חסרים שדות בפרופיל: {missing_fields}"
        )

    if not isinstance(profile["activity_areas"], list):
        raise ValueError(
            "activity_areas חייב להיות מערך"
        )

    if not isinstance(profile["project_types"], list):
        raise ValueError(
            "project_types חייב להיות מערך"
        )

    minimum_units = profile["min_housing_units"]
    maximum_units = profile["max_housing_units"]

    if minimum_units < 0 or maximum_units < 0:
        raise ValueError(
            "מספר יחידות הדיור לא יכול להיות שלילי"
        )

    if minimum_units > maximum_units:
        raise ValueError(
            "מספר היחידות המינימלי לא יכול להיות "
            "גדול ממספר היחידות המקסימלי"
        )

    if profile["max_development_costs"] < 0:
        raise ValueError(
            "הוצאות הפיתוח המקסימליות לא יכולות להיות שליליות"
        )

    if profile["min_days_until_submission"] < 0:
        raise ValueError(
            "מספר הימים המינימלי לא יכול להיות שלילי"
        )
    

def save_profile(profile):
    """
    שומר את פרופיל החברה בקובץ JSON.
    """

    validate_profile(profile)

    PROFILE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with PROFILE_PATH.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            profile,
            file,
            ensure_ascii=False,
            indent=2,
        )

    print(f"Profile saved -> {PROFILE_PATH}")


def load_profile():
    """
    טוען את פרופיל החברה.

    אם עדיין לא קיים קובץ,
    נוצר פרופיל ברירת המחדל.
    """

    if not PROFILE_PATH.exists():
        print("Company profile does not exist.")
        print("Creating default profile...")

        save_profile(DEFAULT_PROFILE)

        return DEFAULT_PROFILE

    with PROFILE_PATH.open(
        "r",
        encoding="utf-8",
    ) as file:
        profile = json.load(file)

    validate_profile(profile)

    return profile


if __name__ == "__main__":
    company_profile = load_profile()

    print("\nCurrent company profile:")
    print(
        json.dumps(
            company_profile,
            ensure_ascii=False,
            indent=2,
        )
    )