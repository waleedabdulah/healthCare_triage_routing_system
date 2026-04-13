"""
Wait time simulation tools.
Phase 1: Returns realistic simulated data with time-of-day variation.
Phase 3+: Replace with real hospital ERP integration.
"""
import random
from datetime import datetime, timedelta


# Baseline wait times by department (in minutes)
BASE_WAIT_TIMES = {
    "Emergency Room": 0,
    "Cardiology": 40,
    "Neurology": 55,
    "ENT": 30,
    "Dermatology": 90,
    "Gastroenterology": 45,
    "Pulmonology": 35,
    "Orthopedics": 50,
    "General Medicine": 25,
    "Pediatrics": 20,
}


def _time_multiplier() -> float:
    """Simulate busier periods: morning rush and afternoon peak."""
    hour = datetime.now().hour
    if 9 <= hour <= 11:
        return 1.5   # Morning rush
    if 14 <= hour <= 16:
        return 1.3   # Afternoon peak
    if hour < 7 or hour > 20:
        return 0.5   # Off hours
    return 1.0


def _next_slot_time(wait_minutes: int) -> str:
    next_time = datetime.now() + timedelta(minutes=wait_minutes)
    return next_time.strftime("%I:%M %p")


def get_er_wait_time() -> dict:
    """Returns current ER estimated wait time."""
    # ER always immediate for critical cases
    queue_depth = random.randint(2, 8)
    return {
        "wait_minutes": 0,
        "queue_depth": queue_depth,
        "status": "open",
    }


def get_opd_wait_time(department: str) -> dict:
    """Returns estimated OPD wait time for the given department."""
    base = BASE_WAIT_TIMES.get(department, 30)
    multiplier = _time_multiplier()
    jitter = random.randint(-5, 15)

    wait_minutes = max(5, int(base * multiplier) + jitter)
    is_accepting = True  # In production: check from ERP

    return {
        "department": department,
        "wait_minutes": wait_minutes,
        "next_slot": _next_slot_time(wait_minutes),
        "is_accepting": is_accepting,
    }
