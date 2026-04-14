"""
Simulated doctor roster per department.
In production: replace with ERP / HIS database queries.
"""
import random
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Doctor roster
# ---------------------------------------------------------------------------

DOCTOR_ROSTER: dict[str, list[dict]] = {
    "Emergency Room": [
        {"id": "er-1", "name": "Dr. Hassan Riaz",   "specialization": "Emergency Medicine"},
        {"id": "er-2", "name": "Dr. Sana Tariq",    "specialization": "Emergency Medicine"},
    ],
    "Cardiology": [
        {"id": "card-1", "name": "Dr. Imran Qureshi", "specialization": "Interventional Cardiology"},
        {"id": "card-2", "name": "Dr. Ayesha Baig",   "specialization": "General Cardiology"},
    ],
    "Neurology": [
        {"id": "neuro-1", "name": "Dr. Zafar Khan",    "specialization": "Clinical Neurology"},
        {"id": "neuro-2", "name": "Dr. Maryam Iqbal",  "specialization": "Neurological Disorders"},
    ],
    "ENT": [
        {"id": "ent-1", "name": "Dr. Usman Farooq", "specialization": "Head & Neck Surgery"},
        {"id": "ent-2", "name": "Dr. Nadia Shah",   "specialization": "Rhinology & Sinusology"},
    ],
    "Dermatology": [
        {"id": "derm-1", "name": "Dr. Khalid Mehmood", "specialization": "Clinical Dermatology"},
        {"id": "derm-2", "name": "Dr. Rabia Hassan",   "specialization": "Cosmetic Dermatology"},
    ],
    "Gastroenterology": [
        {"id": "gastro-1", "name": "Dr. Ali Raza",    "specialization": "Gastroenterology & Hepatology"},
        {"id": "gastro-2", "name": "Dr. Saima Jamil", "specialization": "Endoscopy & GI"},
    ],
    "Pulmonology": [
        {"id": "pulm-1", "name": "Dr. Tariq Aziz",  "specialization": "Respiratory Medicine"},
        {"id": "pulm-2", "name": "Dr. Huma Zafar",  "specialization": "Sleep & Lung Disorders"},
    ],
    "Orthopedics": [
        {"id": "ortho-1", "name": "Dr. Bilal Ahmed",     "specialization": "Bone & Joint Surgery"},
        {"id": "ortho-2", "name": "Dr. Rukhsana Pervez", "specialization": "Sports Medicine"},
    ],
    "Ophthalmology": [
        {"id": "ophthal-1", "name": "Dr. Naeem Siddiqui", "specialization": "Cataract & Refractive Surgery"},
        {"id": "ophthal-2", "name": "Dr. Farah Anwar",    "specialization": "Retina & Vitreous"},
    ],
    "Gynecology": [
        {"id": "gyn-1", "name": "Dr. Asma Butt",  "specialization": "Obstetrics & Gynecology"},
        {"id": "gyn-2", "name": "Dr. Zobia Mir",  "specialization": "Reproductive Medicine"},
    ],
    "Urology": [
        {"id": "urol-1", "name": "Dr. Naveed Chaudhry",  "specialization": "Urological Surgery"},
        {"id": "urol-2", "name": "Dr. Shahid Maqbool",   "specialization": "Kidney & Urinary Tract"},
    ],
    "Psychiatry": [
        {"id": "psych-1", "name": "Dr. Amina Sohail",  "specialization": "Clinical Psychiatry"},
        {"id": "psych-2", "name": "Dr. Faisal Rehman", "specialization": "Cognitive Behavioural Therapy"},
    ],
    "Pediatrics": [
        {"id": "ped-1", "name": "Dr. Shamim Akhtar", "specialization": "General Pediatrics"},
        {"id": "ped-2", "name": "Dr. Lubna Waheed",  "specialization": "Neonatal & Child Health"},
    ],
    "General Medicine": [
        {"id": "gm-1", "name": "Dr. Wasim Akram",   "specialization": "Internal Medicine"},
        {"id": "gm-2", "name": "Dr. Nosheen Ali",   "specialization": "Family Medicine"},
        {"id": "gm-3", "name": "Dr. Pervaiz Alam",  "specialization": "General Practice"},
    ],
}


# ---------------------------------------------------------------------------
# Slot generation
# ---------------------------------------------------------------------------

def get_available_slots(doctor_id: str, days_ahead: int = 7) -> list[dict]:
    """
    Generate simulated available appointment slots for a doctor.
    Produces morning (09:00–12:00) and afternoon (14:00–17:00) slots
    in 30-minute increments over the next `days_ahead` working days.

    Slots are deterministic per doctor per calendar date so refreshing
    the page does not shuffle them — uses doctor_id + today's date as seed.
    """
    rng = random.Random(doctor_id + str(datetime.now().date()))

    slots: list[dict] = []
    candidate = datetime.now()
    days_found = 0

    while days_found < days_ahead:
        candidate += timedelta(days=1)
        if candidate.weekday() >= 5:          # skip weekends
            continue

        date_str = candidate.strftime("%Y-%m-%d")
        date_label = candidate.strftime("%a, %b %d")

        for hour, minute in [
            (9, 0), (9, 30), (10, 0), (10, 30), (11, 0), (11, 30),
            (14, 0), (14, 30), (15, 0), (15, 30), (16, 0), (16, 30),
        ]:
            if rng.random() > 0.45:           # ~55 % availability
                dt = candidate.replace(hour=hour, minute=minute, second=0, microsecond=0)
                time_12 = dt.strftime("%I:%M %p").lstrip("0")
                slots.append({
                    "id": f"{doctor_id}_{date_str}_{hour:02d}{minute:02d}",
                    "date": date_str,
                    "time": time_12,
                    "label": f"{date_label} at {time_12}",
                })

        days_found += 1

    return slots


def get_doctors_for_department(department: str, booked_slot_ids: set[str] | None = None) -> list[dict]:
    """Return doctors for a department, each with their available (unbooked) slots."""
    doctors = DOCTOR_ROSTER.get(department, DOCTOR_ROSTER["General Medicine"])
    blocked = booked_slot_ids or set()
    result = []
    for doc in doctors:
        slots = [s for s in get_available_slots(doc["id"]) if s["id"] not in blocked]
        result.append({**doc, "slots": slots})
    return result
