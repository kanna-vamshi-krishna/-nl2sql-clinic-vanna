"""
seed_memory.py
Pre-seeds the Vanna 2.0 DemoAgentMemory with 15 known-good question→SQL pairs
so the agent has a head start when answering clinic queries.

Run AFTER setup_database.py:
    python seed_memory.py
"""

import asyncio
from vanna.core.user import RequestContext

# Import the shared agent and memory from vanna_setup.py
from vanna_setup import agent, memory

# ---------------------------------------------------------------------------
# 15 question → SQL pairs covering all required categories
# ---------------------------------------------------------------------------

QA_PAIRS = [
    # ── Patient queries ──────────────────────────────────────────────────────
    {
        "question": "How many patients do we have?",
        "sql": "SELECT COUNT(*) AS total_patients FROM patients;",
    },
    {
        "question": "List all patients",
        "sql": (
            "SELECT id, first_name, last_name, email, phone, city, gender "
            "FROM patients ORDER BY last_name, first_name;"
        ),
    },
    {
        "question": "How many patients are from each city?",
        "sql": (
            "SELECT city, COUNT(*) AS patient_count "
            "FROM patients "
            "GROUP BY city "
            "ORDER BY patient_count DESC;"
        ),
    },
    {
        "question": "Which city has the most patients?",
        "sql": (
            "SELECT city, COUNT(*) AS patient_count "
            "FROM patients "
            "GROUP BY city "
            "ORDER BY patient_count DESC "
            "LIMIT 1;"
        ),
    },
    {
        "question": "Show all female patients",
        "sql": (
            "SELECT id, first_name, last_name, city, date_of_birth "
            "FROM patients "
            "WHERE gender = 'F' "
            "ORDER BY last_name;"
        ),
    },
    # ── Doctor queries ───────────────────────────────────────────────────────
    {
        "question": "List all doctors and their specializations",
        "sql": (
            "SELECT name, specialization, department, phone "
            "FROM doctors "
            "ORDER BY specialization, name;"
        ),
    },
    {
        "question": "Which doctor has the most appointments?",
        "sql": (
            "SELECT d.name, d.specialization, COUNT(a.id) AS appointment_count "
            "FROM doctors d "
            "JOIN appointments a ON a.doctor_id = d.id "
            "GROUP BY d.id, d.name, d.specialization "
            "ORDER BY appointment_count DESC "
            "LIMIT 1;"
        ),
    },
    # ── Appointment queries ──────────────────────────────────────────────────
    {
        "question": "How many appointments are there by status?",
        "sql": (
            "SELECT status, COUNT(*) AS count "
            "FROM appointments "
            "GROUP BY status "
            "ORDER BY count DESC;"
        ),
    },
    {
        "question": "Show appointments for last month",
        "sql": (
            "SELECT a.id, p.first_name || ' ' || p.last_name AS patient_name, "
            "d.name AS doctor_name, a.appointment_date, a.status "
            "FROM appointments a "
            "JOIN patients p ON p.id = a.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "WHERE strftime('%Y-%m', a.appointment_date) = "
            "    strftime('%Y-%m', date('now', '-1 month')) "
            "ORDER BY a.appointment_date;"
        ),
    },
    {
        "question": "Show monthly appointment count for the past 6 months",
        "sql": (
            "SELECT strftime('%Y-%m', appointment_date) AS month, "
            "COUNT(*) AS appointment_count "
            "FROM appointments "
            "WHERE appointment_date >= date('now', '-6 months') "
            "GROUP BY month "
            "ORDER BY month;"
        ),
    },
    # ── Financial queries ────────────────────────────────────────────────────
    {
        "question": "What is the total revenue?",
        "sql": "SELECT SUM(total_amount) AS total_revenue FROM invoices;",
    },
    {
        "question": "Show revenue by doctor",
        "sql": (
            "SELECT d.name AS doctor_name, d.specialization, "
            "SUM(i.total_amount) AS total_revenue "
            "FROM invoices i "
            "JOIN appointments a ON a.patient_id = i.patient_id "
            "JOIN doctors d ON d.id = a.doctor_id "
            "GROUP BY d.id, d.name, d.specialization "
            "ORDER BY total_revenue DESC;"
        ),
    },
    {
        "question": "Show unpaid invoices",
        "sql": (
            "SELECT i.id, p.first_name || ' ' || p.last_name AS patient_name, "
            "i.invoice_date, i.total_amount, i.paid_amount, "
            "i.total_amount - i.paid_amount AS balance_due, i.status "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "WHERE i.status IN ('Pending', 'Overdue') "
            "ORDER BY i.status, i.invoice_date;"
        ),
    },
    # ── Time-based queries ───────────────────────────────────────────────────
    {
        "question": "How many cancelled appointments last quarter?",
        "sql": (
            "SELECT COUNT(*) AS cancelled_count "
            "FROM appointments "
            "WHERE status = 'Cancelled' "
            "AND appointment_date >= date('now', '-3 months');"
        ),
    },
    {
        "question": "Top 5 patients by spending",
        "sql": (
            "SELECT p.first_name || ' ' || p.last_name AS patient_name, "
            "p.city, SUM(i.total_amount) AS total_spending "
            "FROM invoices i "
            "JOIN patients p ON p.id = i.patient_id "
            "GROUP BY p.id, patient_name, p.city "
            "ORDER BY total_spending DESC "
            "LIMIT 5;"
        ),
    },
]


# ---------------------------------------------------------------------------
# Seeding helper
# ---------------------------------------------------------------------------

async def seed():
    """Insert all Q&A pairs into DemoAgentMemory."""

    # A dummy context is fine for seeding — memory doesn't enforce auth
    ctx = RequestContext()

    print(f"Seeding {len(QA_PAIRS)} Q&A pairs into agent memory...\n")

    for i, pair in enumerate(QA_PAIRS, 1):
        await memory.save_tool_usage(
            question=pair["question"],
            tool_name="run_sql",
            args={"sql": pair["sql"]},
            context=ctx,
            success=True,
            metadata={"source": "seed_memory.py", "category": "clinic_qa"},
        )
        print(f"  [{i:02d}/{len(QA_PAIRS)}] Seeded: {pair['question'][:70]}")

    # Verify
    recent = await memory.get_recent_memories(context=ctx, limit=len(QA_PAIRS))
    print(f"\n✅ Agent memory now contains {len(recent)} seeded entries.")
    print("   Run 'uvicorn main:app --port 8000' to start the API server.\n")


if __name__ == "__main__":
    asyncio.run(seed())
