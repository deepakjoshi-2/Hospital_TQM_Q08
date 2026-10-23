"""Reporting and analytics service for Hospital Management System — Q08.
Fetches and aggregates actual SQLite records for appointment statuses,
chronological trends, physician workload, and patient satisfaction (CSAT).
"""
import csv
from typing import Any, Dict, List, Optional, Tuple
from database.connection import get_db_connection


def get_appointments_by_status(doctor_id: Optional[int] = None) -> Dict[str, Any]:
    """Query distribution of appointments grouped by status, optionally scoped by physician.
    
    Returns:
        dict containing:
            - 'counts': dict mapping each status name to integer count
            - 'total': total count of appointments
            - 'is_empty': bool indicating whether table has zero appointments
    """
    standard_statuses = ["Scheduled", "Completed", "Cancelled", "No-Show"]
    counts = {s: 0 for s in standard_statuses}
    total = 0

    try:
        with get_db_connection() as conn:
            if doctor_id:
                rows = conn.execute(
                    "SELECT status, COUNT(*) as c FROM appointments WHERE doctor_id = ? GROUP BY status;",
                    (doctor_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT status, COUNT(*) as c FROM appointments GROUP BY status;"
                ).fetchall()
            for r in rows:
                status_name = r["status"]
                c = r["c"]
                counts[status_name] = c
                total += c
    except Exception as e:
        print(f"Error querying appointments by status: {e}")

    return {
        "counts": counts,
        "total": total,
        "is_empty": total == 0,
    }


def get_appointments_over_time(doctor_id: Optional[int] = None) -> List[Dict[str, Any]]:
    """Query daily appointment volumes ordered chronologically, optionally scoped by doctor.
    
    Returns:
        list of dicts: [{'date': 'YYYY-MM-DD', 'count': N}, ...]
    """
    results = []
    try:
        with get_db_connection() as conn:
            if doctor_id:
                rows = conn.execute(
                    """
                    SELECT appointment_date, COUNT(*) as c
                    FROM appointments
                    WHERE doctor_id = ?
                    GROUP BY appointment_date
                    ORDER BY appointment_date ASC;
                    """,
                    (doctor_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT appointment_date, COUNT(*) as c
                    FROM appointments
                    GROUP BY appointment_date
                    ORDER BY appointment_date ASC;
                    """
                ).fetchall()
            results = [{"date": r["appointment_date"], "count": r["c"]} for r in rows]
    except Exception as e:
        print(f"Error querying appointments over time: {e}")

    return results


def get_doctor_workload() -> List[Dict[str, Any]]:
    """Query appointment workload counts per doctor (including doctors with 0 consultations).
    
    Returns:
        list of dicts ordered by appointment count descending:
        [{'doctor_id': id, 'doctor_code': code, 'doctor_name': name, 'specialization': spec, 'count': N}, ...]
    """
    results = []
    try:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT d.id, d.doctor_code, 
                       d.first_name || ' ' || d.last_name AS doctor_name,
                       d.specialization,
                       COUNT(a.id) as appointment_count
                FROM doctors d
                LEFT JOIN appointments a ON d.id = a.doctor_id
                GROUP BY d.id
                ORDER BY appointment_count DESC, d.first_name ASC;
                """
            ).fetchall()
            results = [
                {
                    "doctor_id": r["id"],
                    "doctor_code": r["doctor_code"],
                    "doctor_name": r["doctor_name"],
                    "specialization": r["specialization"],
                    "count": r["appointment_count"],
                }
                for r in rows
            ]
    except Exception as e:
        print(f"Error querying doctor workload: {e}")

    return results


def get_patient_satisfaction_data(doctor_id: Optional[int] = None) -> Dict[str, Any]:
    """Query patient satisfaction (CSAT) ratings from appointments, optionally scoped by doctor.
    
    Returns:
        dict containing:
            - 'has_feedback': bool (True only if >= 1 non-null rating exists)
            - 'total_rated': total appointments with non-null satisfaction rating
            - 'average_rating': float rounded to 2 decimal places (or 0.0)
            - 'breakdown': dict mapping star rating (1 to 5) to integer count
            - 'positive_rate_pct': percentage of ratings that are 4 or 5 stars
    """
    breakdown = {1: 0, 2: 0, 3: 0, 4: 0, 5: 0}
    total_rated = 0
    total_score = 0

    try:
        with get_db_connection() as conn:
            if doctor_id:
                rows = conn.execute(
                    """
                    SELECT satisfaction_rating, COUNT(*) as c
                    FROM appointments
                    WHERE satisfaction_rating IS NOT NULL AND doctor_id = ?
                    GROUP BY satisfaction_rating
                    ORDER BY satisfaction_rating ASC;
                    """,
                    (doctor_id,),
                ).fetchall()
            else:
                rows = conn.execute(
                    """
                    SELECT satisfaction_rating, COUNT(*) as c
                    FROM appointments
                    WHERE satisfaction_rating IS NOT NULL
                    GROUP BY satisfaction_rating
                    ORDER BY satisfaction_rating ASC;
                    """
                ).fetchall()
            for r in rows:
                rating = r["satisfaction_rating"]
                c = r["c"]
                if rating in breakdown:
                    breakdown[rating] = c
                    total_rated += c
                    total_score += rating * c
    except Exception as e:
        print(f"Error querying satisfaction data: {e}")

    avg_rating = round(total_score / total_rated, 2) if total_rated > 0 else 0.0
    positive_count = breakdown[4] + breakdown[5]
    pos_pct = round((positive_count / total_rated) * 100, 1) if total_rated > 0 else 0.0

    return {
        "has_feedback": total_rated > 0,
        "total_rated": total_rated,
        "average_rating": avg_rating,
        "breakdown": breakdown,
        "positive_rate_pct": pos_pct,
    }


def get_reports_summary_stats(doctor_id: Optional[int] = None) -> Dict[str, Any]:
    """Fetch high-level overview metrics for reports header, optionally scoped by physician."""
    summary = {
        "total_appointments": 0,
        "completed_count": 0,
        "scheduled_count": 0,
        "cancelled_count": 0,
        "no_show_count": 0,
        "completion_rate_pct": 0.0,
        "total_doctors": 0,
        "total_patients": 0,
        "average_csat": 0.0,
        "has_feedback": False,
        "total_feedbacks": 0,
    }
    try:
        with get_db_connection() as conn:
            # Appointments breakdown
            if doctor_id:
                a_rows = conn.execute(
                    "SELECT status, COUNT(*) as c FROM appointments WHERE doctor_id = ? GROUP BY status;",
                    (doctor_id,),
                ).fetchall()
            else:
                a_rows = conn.execute("SELECT status, COUNT(*) as c FROM appointments GROUP BY status;").fetchall()

            total_a = 0
            for r in a_rows:
                cnt = r["c"]
                total_a += cnt
                st = r["status"]
                if st == "Completed":
                    summary["completed_count"] = cnt
                elif st == "Scheduled":
                    summary["scheduled_count"] = cnt
                elif st == "Cancelled":
                    summary["cancelled_count"] = cnt
                elif st == "No-Show":
                    summary["no_show_count"] = cnt
            summary["total_appointments"] = total_a
            if total_a > 0:
                summary["completion_rate_pct"] = round((summary["completed_count"] / total_a) * 100, 1)

            # Doctors count
            if doctor_id:
                summary["total_doctors"] = 1
            else:
                d_row = conn.execute("SELECT COUNT(*) as c FROM doctors;").fetchone()
                summary["total_doctors"] = d_row["c"] if d_row else 0

            # Patients count
            if doctor_id:
                p_row = conn.execute(
                    "SELECT COUNT(DISTINCT patient_id) as c FROM appointments WHERE doctor_id = ?;",
                    (doctor_id,),
                ).fetchone()
                summary["total_patients"] = p_row["c"] if p_row else 0
            else:
                p_row = conn.execute("SELECT COUNT(*) as c FROM patients;").fetchone()
                summary["total_patients"] = p_row["c"] if p_row else 0

            # CSAT score
            if doctor_id:
                sat = conn.execute(
                    "SELECT AVG(satisfaction_rating) as avg_r, COUNT(satisfaction_rating) as total_r "
                    "FROM appointments WHERE satisfaction_rating IS NOT NULL AND doctor_id = ?;",
                    (doctor_id,),
                ).fetchone()
            else:
                sat = conn.execute(
                    "SELECT AVG(satisfaction_rating) as avg_r, COUNT(satisfaction_rating) as total_r "
                    "FROM appointments WHERE satisfaction_rating IS NOT NULL;"
                ).fetchone()

            if sat and sat["total_r"] and sat["total_r"] > 0:
                summary["average_csat"] = round(sat["avg_r"], 2)
                summary["has_feedback"] = True
                summary["total_feedbacks"] = sat["total_r"]
    except Exception as e:
        print(f"Error querying reports summary stats: {e}")

    return summary


def export_appointments_to_csv(
    filepath: str,
    status_filter: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> Tuple[bool, str, int]:
    """Export appointment records from SQLite database to a structured CSV file.
    
    Returns:
        (success, message, record_count)
    """
    try:
        with get_db_connection() as conn:
            sql = """
                SELECT a.appointment_code, a.appointment_date, a.time_slot,
                       p.patient_code, p.first_name || ' ' || p.last_name AS patient_name, p.phone AS patient_phone,
                       d.doctor_code, d.first_name || ' ' || d.last_name AS doctor_name, d.specialization,
                       a.priority, a.status,
                       COALESCE(CAST(a.satisfaction_rating AS TEXT), 'Unrated') AS satisfaction_rating,
                       a.reason, COALESCE(a.notes, '') AS notes, a.created_at
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                JOIN doctors d ON a.doctor_id = d.id
                WHERE 1=1
            """
            params = []
            if status_filter and status_filter != "All Statuses":
                sql += " AND a.status = ?"
                params.append(status_filter)
            if date_from:
                sql += " AND a.appointment_date >= ?"
                params.append(date_from)
            if date_to:
                sql += " AND a.appointment_date <= ?"
                params.append(date_to)

            sql += " ORDER BY a.appointment_date DESC, a.time_slot ASC;"
            rows = conn.execute(sql, tuple(params)).fetchall()

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            # Write Header
            writer.writerow([
                "Appointment Code",
                "Appointment Date",
                "Time Slot",
                "Patient Code",
                "Patient Name",
                "Patient Phone",
                "Doctor Code",
                "Doctor Name",
                "Specialization",
                "Priority",
                "Status",
                "Satisfaction Rating (1-5)",
                "Reason for Visit",
                "Clinical Notes",
                "Created At",
            ])
            for r in rows:
                writer.writerow([
                    r["appointment_code"],
                    r["appointment_date"],
                    r["time_slot"],
                    r["patient_code"],
                    r["patient_name"],
                    r["patient_phone"],
                    r["doctor_code"],
                    r["doctor_name"],
                    r["specialization"],
                    r["priority"],
                    r["status"],
                    r["satisfaction_rating"],
                    r["reason"],
                    r["notes"],
                    r["created_at"],
                ])

        return True, f"Successfully exported {len(rows)} appointment record(s) to CSV.", len(rows)
    except Exception as e:
        return False, f"Failed to export appointments to CSV: {e}", 0


def export_summary_report_to_csv(filepath: str) -> Tuple[bool, str]:
    """Export high-level clinical quality metrics and KPI summaries to CSV."""
    try:
        summary = get_reports_summary_stats()
        status_data = get_appointments_by_status()
        workload = get_doctor_workload()
        csat = get_patient_satisfaction_data()

        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)

            writer.writerow(["=== HOSPITAL MANAGEMENT SYSTEM — Q08 CLINICAL ANALYTICS REPORT ==="])
            writer.writerow([])
            writer.writerow(["Metric", "Value"])
            writer.writerow(["Total Registered Patients", summary["total_patients"]])
            writer.writerow(["Active Specialists / Doctors", summary["total_doctors"]])
            writer.writerow(["Total Outpatient Appointments", summary["total_appointments"]])
            writer.writerow(["Completed Appointments", summary["completed_count"]])
            writer.writerow(["Scheduled Future Appointments", summary["scheduled_count"]])
            writer.writerow(["Cancelled Consultations", summary["cancelled_count"]])
            writer.writerow(["No-Show Appointments", summary["no_show_count"]])
            writer.writerow(["Completion Rate", f"{summary['completion_rate_pct']}%"])
            writer.writerow(["Average CSAT Rating", f"{summary['average_csat']} / 5.00 ⭐"])
            writer.writerow(["Total Rated Consultations", summary["total_feedbacks"]])
            writer.writerow([])

            writer.writerow(["=== APPOINTMENTS BY STATUS BREAKDOWN ==="])
            writer.writerow(["Status", "Count", "Percentage of Total"])
            tot = status_data["total"]
            for st, cnt in status_data["counts"].items():
                pct = round((cnt / tot) * 100, 1) if tot > 0 else 0.0
                writer.writerow([st, cnt, f"{pct}%"])
            writer.writerow([])

            writer.writerow(["=== PHYSICIAN WORKLOAD DISTRIBUTION ==="])
            writer.writerow(["Doctor Code", "Doctor Name", "Specialization", "Total Appointments Handled"])
            for doc in workload:
                writer.writerow([doc["doctor_code"], doc["doctor_name"], doc["specialization"], doc["count"]])
            writer.writerow([])

            writer.writerow(["=== PATIENT SATISFACTION (CSAT) STAR BREAKDOWN ==="])
            writer.writerow(["Rating", "Count", "Percentage of Rated"])
            tot_rated = csat["total_rated"]
            for star in range(1, 6):
                c = csat["breakdown"].get(star, 0)
                pct = round((c / tot_rated) * 100, 1) if tot_rated > 0 else 0.0
                writer.writerow([f"{star} Star", c, f"{pct}%"])
            writer.writerow(["Positive Rating (4-5 Stars) Rate", f"{csat['positive_rate_pct']}%"])

        return True, "Summary report successfully exported to CSV."
    except Exception as e:
        return False, f"Failed to export summary report to CSV: {e}"
