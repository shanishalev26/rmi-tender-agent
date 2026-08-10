import json
import os
from pathlib import Path

ANALYSIS_DIR = Path("data/analysis")


def get_analysis_path(michraz_id):
    """Returns the analysis file path for one tender."""
    return ANALYSIS_DIR / f"{michraz_id}.json"


def load_analysis_record(michraz_id):
    """Loads an analysis record and returns it with its path."""
    path = get_analysis_path(michraz_id)

    if not path.exists():
        raise FileNotFoundError(
            f"Analysis file was not found: {path}"
        )

    with path.open("r", encoding="utf-8") as file:
        return json.load(file), path


def save_analysis_record(record, path):
    """Saves an analysis record without leaving a partial JSON file."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = Path(str(path) + ".tmp")

    with temporary_path.open("w", encoding="utf-8") as file:
        json.dump(
            record,
            file,
            ensure_ascii=False,
            indent=2,
        )

    os.replace(temporary_path, path)
