"""
setup_database.py
Creates the clinic SQLite database schema and populates it with realistic dummy data.
Run: python setup_database.py
"""

import sqlite3
import random
from datetime import datetime, timedelta, date

DB_PATH = "clinic.db"

# ---------------------------------------------------------------------------
# Seed data pools
# ---------------------------------------------------------------------------
FIRST_NAMES_M = [
    "Aarav", "Aditya", "Arjun", "Karan", "Rahul", "Vikram", "Suresh", "Rajesh",
    "Amit", "Ravi", "Sanjay", "Deepak", "Nikhil", "Rohan", "Harsh", "Yash",
    "Pranav", "Vivek", "Manish", "Gaurav",
]
FIRST_NAMES_F = [
    "Priya", "Anjali", "Sneha", "Pooja", "Kavita", "Meera", "Asha", "Nisha",
    "Divya", "Sunita", "Rekha", "Usha", "Swati", "Rani", "Geeta", "Lata",
    "Radha", "Anita", "Smita", "Bhavna",
]
LAST_NAMES = [
    "Sharma", "Verma", "Gupta", "Singh", "Kumar", "Yadav", "Patel", "Mehta",
    "Joshi", "Nair", "Reddy", "Iyer", "Pillai", "Menon", "Chatterjee",
    "Banerjee", "Das", "Bose", "Sen", "Roy",
]
CITIES = [
    "Mumbai", "Delhi", "Hyderabad", "Bangalore", "Chennai",
    "Pune", "Kolkata", "Ahmedabad", "Jaipur", "Lucknow",
]
SPECIALIZATIONS = [
    "Dermatology", "Cardiology", "Orthopedics", "General", "Pediatrics",
]
DEPARTMENTS = {
    "Dermatology": "Skin & Hair",
    "Cardiology": "Heart & Vascular",
    "Orthopedics": "Bone & Joint",
    "General": "General Medicine",
    "Pediatrics": "Child Health",
}
TREATMENT_NAMES = {
    "Dermatology": ["Acne Treatment", "Skin Biopsy", "Laser Therapy", "Patch Test"],
    "Cardiology": ["ECG", "Echo", "Stress Test", "Angiography", "Holter Monitor"],
    "Orthopedics": ["X-Ray", "Physiotherapy", "Joint Injection", "Fracture Setting"],
    "General": ["Blood Test", "Urine Test", "Vaccination", "BP Monitoring", "Diabetes Screening"],
    "Pediatrics": ["Vaccination", "Growth Assessment", "Nebulisation", "Vision Test"],
}
STATUSES = ["Scheduled", "Completed", "Cancelled", "No-Show"]
INVOICE_STATUSES = ["Paid", "Pending", "Overdue"]


def random_date(start: date, end: date) -> date:
    delta = (end - start).days
    return start + timedelta(days=random.randint(0, delta))


def random_datetime(start: date, end: date) -> datetime:
    d = random_date(start, end)
    hour = random.randint(8, 17)
    minute = random.choice([0, 15, 30, 45])
    return datetime(d.year, d.month, d.day, hour, minute)


def maybe_null(value, probability=0.15):
    """Return None with given probability to simulate realistic NULLs."""
    return None if random.random() < probability else value


# ---------------------------------------------------------------------------
# Schema
# ---------------------------------------------------------------------------
SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS patients (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    first_name      TEXT    NOT NULL,
    last_name       TEXT    NOT NULL,
    email           TEXT,
    phone           TEXT,
    date_of_birth   DATE,
    gender          TEXT,
    city            TEXT,
    registered_date DATE
);

CREATE TABLE IF NOT EXISTS doctors (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT    NOT NULL,
    specialization  TEXT,
    department      TEXT,
    phone           TEXT
);

CREATE TABLE IF NOT EXISTS appointments (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id       INTEGER,
    doctor_id        INTEGER,
    appointment_date DATETIME,
    status           TEXT,
    notes            TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id),
    FOREIGN KEY (doctor_id)  REFERENCES doctors(id)
);

CREATE TABLE IF NOT EXISTS treatments (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_id     INTEGER,
    treatment_name     TEXT,
    cost               REAL,
    duration_minutes   INTEGER,
    FOREIGN KEY (appointment_id) REFERENCES appointments(id)
);

CREATE TABLE IF NOT EXISTS invoices (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id    INTEGER,
    invoice_date  DATE,
    total_amount  REAL,
    paid_amount   REAL,
    status        TEXT,
    FOREIGN KEY (patient_id) REFERENCES patients(id)
);
"""


# ---------------------------------------------------------------------------
# Data insertion
# ---------------------------------------------------------------------------

def insert_doctors(cur):
    doctors = []
    # 3 per specialization = 15 doctors
    for spec in SPECIALIZATIONS:
        for i in range(3):
            gender = random.choice(["M", "F"])
            if gender == "M":
                fname = random.choice(FIRST_NAMES_M)
            else:
                fname = random.choice(FIRST_NAMES_F)
            lname = random.choice(LAST_NAMES)
            name = f"Dr. {fname} {lname}"
            dept = DEPARTMENTS[spec]
            phone = f"+91-{random.randint(7000000000, 9999999999)}"
            doctors.append((name, spec, dept, phone))

    cur.executemany(
        "INSERT INTO doctors (name, specialization, department, phone) VALUES (?,?,?,?)",
        doctors,
    )
    return len(doctors)


def insert_patients(cur, count=200):
    today = date.today()
    twelve_months_ago = today - timedelta(days=365)
    patients = []
    for _ in range(count):
        gender = random.choice(["M", "F"])
        if gender == "M":
            fname = random.choice(FIRST_NAMES_M)
        else:
            fname = random.choice(FIRST_NAMES_F)
        lname = random.choice(LAST_NAMES)
        email = maybe_null(f"{fname.lower()}.{lname.lower()}{random.randint(1,99)}@email.com")
        phone = maybe_null(f"+91-{random.randint(7000000000, 9999999999)}")
        dob = random_date(date(1950, 1, 1), date(2010, 12, 31))
        city = random.choice(CITIES)
        reg_date = random_date(twelve_months_ago, today)
        patients.append((fname, lname, email, phone, dob, gender, city, reg_date))

    cur.executemany(
        "INSERT INTO patients (first_name, last_name, email, phone, date_of_birth, gender, city, registered_date) "
        "VALUES (?,?,?,?,?,?,?,?)",
        patients,
    )
    return count


def insert_appointments(cur, num_patients, num_doctors, count=500):
    today = date.today()
    start = today - timedelta(days=365)

    # Weight patients so some have many appointments
    patient_weights = []
    for i in range(1, num_patients + 1):
        w = 5 if random.random() < 0.15 else 1   # 15% of patients are frequent visitors
        patient_weights.append((i, w))
    total_weight = sum(w for _, w in patient_weights)
    patients_pool = []
    for pid, w in patient_weights:
        patients_pool.extend([pid] * w)

    # Weight doctors so some are busier
    doctor_weights = []
    for i in range(1, num_doctors + 1):
        w = 4 if random.random() < 0.2 else 1
        doctor_weights.append((i, w))
    doctors_pool = []
    for did, w in doctor_weights:
        doctors_pool.extend([did] * w)

    appointments = []
    for _ in range(count):
        pid = random.choice(patients_pool)
        did = random.choice(doctors_pool)
        appt_dt = random_datetime(start, today)
        status = random.choices(
            STATUSES, weights=[10, 60, 15, 15], k=1
        )[0]
        notes = maybe_null(random.choice([
            "Follow-up required", "First visit", "Referred by GP",
            "Routine check", "Post-surgery", "Emergency walk-in",
        ]), probability=0.3)
        appointments.append((pid, did, appt_dt, status, notes))

    cur.executemany(
        "INSERT INTO appointments (patient_id, doctor_id, appointment_date, status, notes) VALUES (?,?,?,?,?)",
        appointments,
    )
    return count


def insert_treatments(cur, completed_appt_ids, num_doctors_by_appt):
    """Insert ~350 treatments for completed appointments."""
    # Get specialization per appointment via doctor
    cur.execute(
        "SELECT a.id, d.specialization FROM appointments a "
        "JOIN doctors d ON d.id = a.doctor_id WHERE a.status = 'Completed'"
    )
    rows = cur.fetchall()
    # Randomly pick ~350 of them
    random.shuffle(rows)
    selected = rows[:350]

    treatments = []
    for appt_id, spec in selected:
        names = TREATMENT_NAMES.get(spec, TREATMENT_NAMES["General"])
        treatment_name = random.choice(names)
        cost = round(random.uniform(50, 5000), 2)
        duration = random.randint(10, 120)
        treatments.append((appt_id, treatment_name, cost, duration))

    cur.executemany(
        "INSERT INTO treatments (appointment_id, treatment_name, cost, duration_minutes) VALUES (?,?,?,?)",
        treatments,
    )
    return len(treatments)


def insert_invoices(cur, num_patients, count=300):
    today = date.today()
    start = today - timedelta(days=365)
    invoices = []
    patient_ids = list(range(1, num_patients + 1))
    random.shuffle(patient_ids)

    for i in range(count):
        pid = patient_ids[i % num_patients]
        inv_date = random_date(start, today)
        total = round(random.uniform(100, 8000), 2)
        status = random.choices(
            INVOICE_STATUSES, weights=[55, 25, 20], k=1
        )[0]
        if status == "Paid":
            paid = total
        elif status == "Pending":
            paid = round(random.uniform(0, total * 0.5), 2)
        else:  # Overdue
            paid = round(random.uniform(0, total * 0.3), 2)
        invoices.append((pid, inv_date, total, paid, status))

    cur.executemany(
        "INSERT INTO invoices (patient_id, invoice_date, total_amount, paid_amount, status) VALUES (?,?,?,?,?)",
        invoices,
    )
    return count


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    import os
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
        print(f"Removed existing {DB_PATH}")

    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()
    cur.executescript(SCHEMA_SQL)
    con.commit()

    n_doctors = insert_doctors(cur)
    con.commit()

    n_patients = insert_patients(cur, 200)
    con.commit()

    n_appointments = insert_appointments(cur, n_patients, n_doctors, 500)
    con.commit()

    n_treatments = insert_treatments(cur, [], {})
    con.commit()

    n_invoices = insert_invoices(cur, n_patients, 300)
    con.commit()

    con.close()

    print(
        f"\n✅ Database created: {DB_PATH}\n"
        f"   Created {n_patients} patients\n"
        f"   Created {n_doctors} doctors\n"
        f"   Created {n_appointments} appointments\n"
        f"   Created {n_treatments} treatments\n"
        f"   Created {n_invoices} invoices\n"
    )


if __name__ == "__main__":
    random.seed(42)
    main()
