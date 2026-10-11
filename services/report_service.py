"""Reporting and analytics service for Hospital Management System — Q08.
Fetches and aggregates actual SQLite records for appointment statuses,
chronological trends, physician workload, and patient satisfaction (CSAT).
"""
from typing import Any, Dict, List, Optional
from database.connection import get_db_connection


def get_appointments_by_status() -> Dict[str, Any]:
    """Query distribution of appointments grouped by status.
    
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


def get_appointments_over_time() -> List[Dict[str, Any]]:
    """Query daily appointment volumes ordered chronologically by appointment_date.
    
    Returns:
        list of dicts: [{'date': 'YYYY-MM-DD', 'count': N}, ...]
    """
    results = []
    try:
        with get_db_connection() as conn:
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


def get_patient_satisfaction_data() -> Dict[str, Any]:
    """Query patient satisfaction (CSAT) ratings from appointments.
    
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


def get_reports_summary_stats() -> Dict[str, Any]:
    """Fetch high-level overview metrics for the reports header."""
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
            d_row = conn.execute("SELECT COUNT(*) as c FROM doctors;").fetchone()
            summary["total_doctors"] = d_row["c"] if d_row else 0

            # Patients count
            p_row = conn.execute("SELECT COUNT(*) as c FROM patients;").fetchone()
            summary["total_patients"] = p_row["c"] if p_row else 0

            # CSAT score
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
