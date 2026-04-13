import json
from pathlib import Path

_DEPT_DATA = None


def _load_dept_data() -> dict:
    global _DEPT_DATA
    if _DEPT_DATA is None:
        dept_file = Path("data/raw/department_symptom_map.json")
        if dept_file.exists():
            with open(dept_file, encoding="utf-8") as f:
                _DEPT_DATA = json.load(f).get("departments", {})
        else:
            _DEPT_DATA = {}
    return _DEPT_DATA


def get_department_info(department: str) -> dict:
    """Returns location and contact info for a department."""
    data = _load_dept_data()
    if department in data:
        dept = data[department]
        return {
            "department": department,
            "location": dept.get("location", "Please ask at reception"),
            "floor": dept.get("floor", "Ground"),
            "contact": dept.get("contact", "Ext: 0"),
            "accepts_walkins": dept.get("accepts_walkins", True),
        }
    return {
        "department": department,
        "location": "Please ask at reception",
        "floor": "Unknown",
        "contact": "Ext: 0",
        "accepts_walkins": True,
    }
