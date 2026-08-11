import json
import os
from pathlib import Path

PROFILE_PATH = Path("data/company_profile.json")

# These default values can be edited through the app
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
    """Validates the company profile structure and values"""
    if not isinstance(profile, dict):
        raise ValueError("Company profile must be an object")

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

    profile_name = profile["profile_name"]

    if (
        not isinstance(profile_name, str)
        or not profile_name.strip()
    ):
        raise ValueError("profile_name must be a non-empty string")

    for field in ("activity_areas", "project_types"):
        values = profile[field]

        if not isinstance(values, list):
            raise ValueError(f"{field} must be a list")

        if not all(
            isinstance(value, str) and value.strip()
            for value in values
        ):
            raise ValueError(
                f"{field} must contain only non-empty strings"
            )

    numeric_fields = (
        "min_housing_units",
        "max_housing_units",
        "max_development_costs",
        "min_days_until_submission",
    )

    for field in numeric_fields:
        value = profile[field]

        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
        ):
            raise ValueError(f"{field} must be a numeric value")

    if not isinstance(profile["requires_approved_plan"], bool):
        raise ValueError(
            "requires_approved_plan must be a boolean"
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
    """Validates and saves the company profile"""

    validate_profile(profile)

    PROFILE_PATH.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = Path(str(PROFILE_PATH) + ".tmp")

    with temporary_path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            profile,
            file,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(temporary_path, PROFILE_PATH)

    print(f"Profile saved -> {PROFILE_PATH}")


def load_profile():
    """Loads the saved company profile or creates the default profile."""

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
