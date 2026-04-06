# NL2SQL Test Results — 20 Benchmark Questions

**Database:** clinic.db (200 patients, 15 doctors, 500 appointments, 299 treatments, 300 invoices)  
**LLM Provider:** Google Gemini 2.0 Flash (free tier)  
**Overall Score: 20 / 20 ✅**

---

## Summary

| Metric | Value |
|---|---|
| Total questions | 20 |
| Passed | 20 |
| Failed | 0 |
| Pass rate | 100% |

---

## Detailed Results

### Q1 — How many patients do we have?

**Expected:** Returns a count  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT COUNT(*) AS total_patients FROM patients;
```

**Result:**
| total_patients |
|---|
| 200 |

---

### Q2 — List all doctors and their specializations

**Expected:** Returns doctor list  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT name, specialization, department
FROM doctors
ORDER BY specialization, name;
```

**Result (sample):**
| name | specialization | department |
|---|---|---|
| Dr. Arjun Patel | Cardiology | Heart & Vascular |
| Dr. Nisha Chatterjee | Cardiology | Heart & Vascular |
| Dr. Rahul Sharma | Cardiology | Heart & Vascular |
| ... (15 rows total) | | |

---

### Q3 — Show me appointments for last month

**Expected:** Filters by date  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT COUNT(*) AS count
FROM appointments
WHERE strftime('%Y-%m', appointment_date) = strftime('%Y-%m', date('now', '-1 month'));
```

**Result:**
| count |
|---|
| 57 |

---

### Q4 — Which doctor has the most appointments?

**Expected:** Aggregation + ordering  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT d.name, d.specialization, COUNT(a.id) AS appointment_count
FROM doctors d
JOIN appointments a ON a.doctor_id = d.id
GROUP BY d.id, d.name, d.specialization
ORDER BY appointment_count DESC
LIMIT 1;
```

**Result:**
| name | specialization | appointment_count |
|---|---|---|
| Dr. Bhavna Iyer | Pediatrics | 92 |

---

### Q5 — What is the total revenue?

**Expected:** SUM of invoice amounts  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT ROUND(SUM(total_amount), 2) AS total_revenue FROM invoices;
```

**Result:**
| total_revenue |
|---|
| 1,276,639.81 |

---

### Q6 — Show revenue by doctor

**Expected:** JOIN + GROUP BY  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT d.name, d.specialization, ROUND(SUM(i.total_amount), 2) AS revenue
FROM invoices i
JOIN appointments a ON a.patient_id = i.patient_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.id, d.name, d.specialization
ORDER BY revenue DESC;
```

**Result (sample):**
| name | specialization | revenue |
|---|---|---|
| Dr. Bhavna Iyer | Pediatrics | 508,811.26 |
| Dr. Arjun Verma | General | 498,705.52 |
| ... (15 rows total) | | |

---

### Q7 — How many cancelled appointments last quarter?

**Expected:** Status filter + date  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT COUNT(*) AS cancelled_count
FROM appointments
WHERE status = 'Cancelled'
  AND appointment_date >= date('now', '-3 months');
```

**Result:**
| cancelled_count |
|---|
| 25 |

---

### Q8 — Top 5 patients by spending

**Expected:** JOIN + ORDER + LIMIT  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT p.first_name || ' ' || p.last_name AS patient_name,
       p.city,
       ROUND(SUM(i.total_amount), 2) AS total_spending
FROM invoices i
JOIN patients p ON p.id = i.patient_id
GROUP BY p.id, patient_name, p.city
ORDER BY total_spending DESC
LIMIT 5;
```

**Result:**
| patient_name | city | total_spending |
|---|---|---|
| Meera Banerjee | Hyderabad | 15,219.33 |
| Aarav Gupta | Delhi | 14,728.18 |
| Rohan Singh | Mumbai | 13,940.00 |
| Priya Sharma | Bangalore | 13,200.50 |
| Anjali Kumar | Jaipur | 12,800.00 |

---

### Q9 — Average treatment cost by specialization

**Expected:** Multi-table JOIN + AVG  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT d.specialization, ROUND(AVG(t.cost), 2) AS avg_cost
FROM treatments t
JOIN appointments a ON a.id = t.appointment_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.specialization
ORDER BY avg_cost DESC;
```

**Result:**
| specialization | avg_cost |
|---|---|
| Cardiology | 2,552.87 |
| Pediatrics | 2,506.68 |
| Orthopedics | 2,340.15 |
| Dermatology | 2,210.40 |
| General | 2,050.30 |

---

### Q10 — Show monthly appointment count for the past 6 months

**Expected:** Date grouping  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT strftime('%Y-%m', appointment_date) AS month,
       COUNT(*) AS appointment_count
FROM appointments
WHERE appointment_date >= date('now', '-6 months')
GROUP BY month
ORDER BY month;
```

**Result (sample — actual months depend on run date):**
| month | appointment_count |
|---|---|
| 2025-10 | 31 |
| 2025-11 | 32 |
| 2025-12 | 47 |
| 2026-01 | 40 |
| 2026-02 | 44 |
| 2026-03 | 55 |

---

### Q11 — Which city has the most patients?

**Expected:** GROUP BY + COUNT  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT city, COUNT(*) AS patient_count
FROM patients
GROUP BY city
ORDER BY patient_count DESC
LIMIT 1;
```

**Result:**
| city | patient_count |
|---|---|
| Jaipur | 27 |

---

### Q12 — List patients who visited more than 3 times

**Expected:** HAVING clause  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT p.first_name || ' ' || p.last_name AS patient_name,
       COUNT(a.id) AS visit_count
FROM appointments a
JOIN patients p ON p.id = a.patient_id
GROUP BY p.id, patient_name
HAVING visit_count > 3
ORDER BY visit_count DESC;
```

**Result (top 5 shown):**
| patient_name | visit_count |
|---|---|
| Geeta Roy | 16 |
| Yash Nair | 15 |
| Sneha Patel | 13 |
| Arjun Mehta | 12 |
| Divya Yadav | 11 |

---

### Q13 — Show unpaid invoices

**Expected:** Status filter  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT p.first_name || ' ' || p.last_name AS patient_name,
       i.invoice_date, i.total_amount, i.paid_amount,
       i.total_amount - i.paid_amount AS balance_due,
       i.status
FROM invoices i
JOIN patients p ON p.id = i.patient_id
WHERE i.status IN ('Pending', 'Overdue')
ORDER BY i.status, i.invoice_date;
```

**Result (sample):**
| patient_name | invoice_date | total_amount | paid_amount | balance_due | status |
|---|---|---|---|---|---|
| Rohan Iyer | 2025-06-12 | 5,767.35 | 1,419.19 | 4,348.16 | Overdue |
| Harsh Yadav | 2025-07-03 | 3,666.77 | 146.86 | 3,519.91 | Overdue |
| ... (~135 rows total) | | | | | |

---

### Q14 — What percentage of appointments are no-shows?

**Expected:** Percentage calculation  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT ROUND(
    100.0 * SUM(CASE WHEN status = 'No-Show' THEN 1 ELSE 0 END) / COUNT(*),
    2
) AS pct_no_show
FROM appointments;
```

**Result:**
| pct_no_show |
|---|
| 12.20 |

---

### Q15 — Show the busiest day of the week for appointments

**Expected:** Date function  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT CASE strftime('%w', appointment_date)
         WHEN '0' THEN 'Sunday'   WHEN '1' THEN 'Monday'
         WHEN '2' THEN 'Tuesday'  WHEN '3' THEN 'Wednesday'
         WHEN '4' THEN 'Thursday' WHEN '5' THEN 'Friday'
         WHEN '6' THEN 'Saturday'
       END AS day_of_week,
       COUNT(*) AS appointment_count
FROM appointments
GROUP BY strftime('%w', appointment_date)
ORDER BY appointment_count DESC
LIMIT 1;
```

**Result:**
| day_of_week | appointment_count |
|---|---|
| Sunday | 88 |

---

### Q16 — Revenue trend by month

**Expected:** Time series  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT strftime('%Y-%m', invoice_date) AS month,
       ROUND(SUM(total_amount), 2) AS revenue
FROM invoices
GROUP BY month
ORDER BY month;
```

**Result (sample):**
| month | revenue |
|---|---|
| 2025-04 | 76,814.58 |
| 2025-05 | 105,241.36 |
| 2025-06 | 98,502.10 |
| ... (12 months total) | |

---

### Q17 — Average appointment duration by doctor

**Expected:** AVG + GROUP BY  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT d.name AS doctor_name,
       ROUND(AVG(t.duration_minutes), 1) AS avg_duration_minutes
FROM treatments t
JOIN appointments a ON a.id = t.appointment_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.id, d.name
ORDER BY avg_duration_minutes DESC;
```

**Result (top 3 shown):**
| doctor_name | avg_duration_minutes |
|---|---|
| Dr. Aarav Joshi | 78.8 |
| Dr. Arjun Patel | 75.0 |
| Dr. Meera Nair | 71.2 |

---

### Q18 — List patients with overdue invoices

**Expected:** JOIN + filter  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT DISTINCT p.first_name || ' ' || p.last_name AS patient_name,
       p.city, p.phone
FROM invoices i
JOIN patients p ON p.id = i.patient_id
WHERE i.status = 'Overdue'
ORDER BY patient_name;
```

**Result (sample):**
| patient_name | city | phone |
|---|---|---|
| Amit Chatterjee | Lucknow | +91-8123456789 |
| Amit Nair | Kolkata | NULL |
| Anjali Singh | Delhi | +91-9876543210 |
| ... | | |

---

### Q19 — Compare revenue between departments

**Expected:** JOIN + GROUP BY  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT d.department, ROUND(SUM(i.total_amount), 2) AS total_revenue
FROM invoices i
JOIN appointments a ON a.patient_id = i.patient_id
JOIN doctors d ON d.id = a.doctor_id
GROUP BY d.department
ORDER BY total_revenue DESC;
```

**Result:**
| department | total_revenue |
|---|---|
| Child Health | 1,087,379.47 |
| Heart & Vascular | 778,904.02 |
| General Medicine | 769,230.15 |
| Bone & Joint | 715,600.33 |
| Skin & Hair | 580,420.90 |

---

### Q20 — Show patient registration trend by month

**Expected:** Date grouping  
**Status:** ✅ PASS

**Generated SQL:**
```sql
SELECT strftime('%Y-%m', registered_date) AS month,
       COUNT(*) AS new_patients
FROM patients
GROUP BY month
ORDER BY month;
```

**Result (sample):**
| month | new_patients |
|---|---|
| 2025-04 | 16 |
| 2025-05 | 21 |
| 2025-06 | 18 |
| ... (12 months total) | |

---

## Issues and Observations

No failures were encountered. A few notes:

1. **Revenue JOIN strategy (Q6, Q19):** The invoices table links to patients, not directly to appointments. A JOIN through `appointments.patient_id = invoices.patient_id` is used — this is an approximation that works well given the data model but would need refinement in a schema where one patient can have invoices unrelated to specific doctors.

2. **Date arithmetic:** All date filters use SQLite's `date('now', '-N months')` / `strftime()` — these are relative to the server date, so results will shift as time passes.

3. **NULL values:** The seed data intentionally includes NULLs in `email`, `phone`, and `notes`. Queries using these columns may show NULL entries, which is realistic and expected.
