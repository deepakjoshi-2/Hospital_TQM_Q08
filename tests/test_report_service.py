"""Unit and integration test suite for Report Calculations, Analytics Aggregations, and Empty Data Handling."""
from contextlib import contextmanager
import sqlite3
import unittest

from database.connection import get_db_connection
from services.report_service import (
    get_appointments_by_status,
    get_appointments_over_time,
    get_doctor_workload,
    get_patient_satisfaction_data,
    get_reports_summary_stats,
)


class TestReportService(unittest.TestCase):
    """Test suite verifying live SQLite analytics calculations and empty data edge cases."""

    @classmethod
    def setUpClass(cls):
        """Record baseline record counts from production SQLite database."""
        with get_db_connection() as conn:
            cls.baseline_patients = conn.execute("SELECT COUNT(*) FROM patients;").fetchone()[0]
            cls.baseline_doctors = conn.execute("SELECT COUNT(*) FROM doctors;").fetchone()[0]
            cls.baseline_appointments = conn.execute("SELECT COUNT(*) FROM appointments;").fetchone()[0]

    def test_01_appointments_by_status_calculation(self):
        """Verify status aggregation returns accurate counts matching the database."""
        res = get_appointments_by_status()
        self.assertIsInstance(res, dict)
        self.assertFalse(res["is_empty"], "Baseline database should have active appointments.")
        self.assertEqual(res["total"], self.baseline_appointments)

        counts = res["counts"]
        # Standard clinical statuses must be present
        for st in ["Scheduled", "Completed", "Cancelled", "No-Show"]:
            self.assertIn(st, counts)
            self.assertGreaterEqual(counts[st], 0)

        # Compare directly against raw DB count per status
        with get_db_connection() as conn:
            for st in ["Scheduled", "Completed", "Cancelled", "No-Show"]:
                db_cnt = conn.execute("SELECT COUNT(*) FROM appointments WHERE status = ?;", (st,)).fetchone()[0]
                self.assertEqual(counts[st], db_cnt)

    def test_02_appointments_over_time_chronological_ordering(self):
        """Verify timeline volumes are returned in strictly ascending chronological order."""
        timeline = get_appointments_over_time()
        self.assertIsInstance(timeline, list)
        self.assertGreater(len(timeline), 0)

        total_volume = 0
        prev_date = ""
        for entry in timeline:
            self.assertIn("date", entry)
            self.assertIn("count", entry)
            self.assertGreater(entry["count"], 0)
            total_volume += entry["count"]

            if prev_date:
                self.assertLess(prev_date, entry["date"], "Dates must be strictly sorted chronologically.")
            prev_date = entry["date"]

        # Sum across all dates must equal total appointments
        self.assertEqual(total_volume, self.baseline_appointments)

    def test_03_doctor_workload_aggregation_and_ordering(self):
        """Verify doctor workload counts include all registered physicians in descending order."""
        workload = get_doctor_workload()
        self.assertIsInstance(workload, list)
        self.assertEqual(len(workload), self.baseline_doctors, "All doctors must be listed in workload analysis.")

        total_workload = 0
        prev_count = float("inf")
        for doc in workload:
            self.assertIn("doctor_code", doc)
            self.assertIn("doctor_name", doc)
            self.assertIn("specialization", doc)
            self.assertIn("count", doc)
            total_workload += doc["count"]

            # Must be ordered descending by appointment count
            self.assertLessEqual(doc["count"], prev_count, "Workload must be ordered descending by count.")
            prev_count = doc["count"]

        # Sum of doctor appointments must equal total appointments
        self.assertEqual(total_workload, self.baseline_appointments)

        # Ensure doctor on leave with 0 appointments is included
        doc_codes = [d["doctor_code"] for d in workload]
        self.assertIn("DOC-2007", doc_codes)
        doc_2007 = next(d for d in workload if d["doctor_code"] == "DOC-2007")
        self.assertEqual(doc_2007["count"], 0)

    def test_04_patient_satisfaction_metrics_calculation(self):
        """Verify CSAT metrics, average score calculation, and positive rating percentage."""
        sat_data = get_patient_satisfaction_data()
        self.assertIsInstance(sat_data, dict)
        self.assertTrue(sat_data["has_feedback"], "Demo seed data should contain rated appointments.")
        self.assertEqual(sat_data["total_rated"], 20, "Seed data has exactly 20 completed rated consultations.")

        # Average rating calculation: (3*1 + 4*9 + 5*10) / 20 = 89 / 20 = 4.45
        self.assertEqual(sat_data["average_rating"], 4.45)

        # Positive rate percentage (4 and 5 stars): (9 + 10) / 20 = 95.0%
        self.assertEqual(sat_data["positive_rate_pct"], 95.0)

        # Breakdown checks
        breakdown = sat_data["breakdown"]
        self.assertEqual(breakdown[1], 0)
        self.assertEqual(breakdown[2], 0)
        self.assertEqual(breakdown[3], 1)
        self.assertEqual(breakdown[4], 9)
        self.assertEqual(breakdown[5], 10)

    def test_05_reports_summary_stats(self):
        """Verify high-level summary KPI calculations for the reports header."""
        stats = get_reports_summary_stats()
        self.assertEqual(stats["total_appointments"], self.baseline_appointments)
        self.assertEqual(stats["total_doctors"], self.baseline_doctors)
        self.assertEqual(stats["total_patients"], self.baseline_patients)

        with get_db_connection() as conn:
            actual_comp = conn.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Completed';").fetchone()[0]
            actual_sched = conn.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Scheduled';").fetchone()[0]
            actual_canc = conn.execute("SELECT COUNT(*) FROM appointments WHERE status = 'Cancelled';").fetchone()[0]
            actual_noshow = conn.execute("SELECT COUNT(*) FROM appointments WHERE status = 'No-Show';").fetchone()[0]
            expected_rate = round((actual_comp / self.baseline_appointments) * 100, 1)

        self.assertEqual(stats["completed_count"], actual_comp)
        self.assertEqual(stats["scheduled_count"], actual_sched)
        self.assertEqual(stats["cancelled_count"], actual_canc)
        self.assertEqual(stats["no_show_count"], actual_noshow)
        self.assertEqual(stats["completion_rate_pct"], expected_rate)
        self.assertTrue(stats["has_feedback"])
        self.assertEqual(stats["average_csat"], 4.45)
        self.assertEqual(stats["total_feedbacks"], 20)


    def test_06_empty_data_edge_cases(self):
        """Verify report calculations handle empty database tables safely without crashing."""
        # Create an isolated temporary SQLite database with empty schema
        empty_conn = sqlite3.connect(":memory:")
        empty_conn.row_factory = sqlite3.Row
        with open("database/schema.sql", "r", encoding="utf-8") as f:
            empty_conn.executescript(f.read())

        @contextmanager
        def mock_empty_db():
            yield empty_conn

        # Test report calculations against empty database
        import services.report_service as rs
        original_get_db = rs.get_db_connection
        rs.get_db_connection = mock_empty_db

        try:
            # 1. Empty appointments by status
            status_res = rs.get_appointments_by_status()
            self.assertTrue(status_res["is_empty"])
            self.assertEqual(status_res["total"], 0)
            self.assertEqual(status_res["counts"]["Scheduled"], 0)
            self.assertEqual(status_res["counts"]["Completed"], 0)

            # 2. Empty appointments over time
            timeline_res = rs.get_appointments_over_time()
            self.assertEqual(timeline_res, [])

            # 3. Empty doctor workload
            workload_res = rs.get_doctor_workload()
            self.assertEqual(workload_res, [])

            # 4. Empty patient satisfaction
            sat_res = rs.get_patient_satisfaction_data()
            self.assertFalse(sat_res["has_feedback"])
            self.assertEqual(sat_res["total_rated"], 0)
            self.assertEqual(sat_res["average_rating"], 0.0)
            self.assertEqual(sat_res["positive_rate_pct"], 0.0)
            self.assertEqual(sat_res["breakdown"], {1: 0, 2: 0, 3: 0, 4: 0, 5: 0})

            # 5. Empty summary stats
            summary_res = rs.get_reports_summary_stats()
            self.assertEqual(summary_res["total_appointments"], 0)
            self.assertEqual(summary_res["total_doctors"], 0)
            self.assertEqual(summary_res["total_patients"], 0)
            self.assertEqual(summary_res["completion_rate_pct"], 0.0)
            self.assertFalse(summary_res["has_feedback"])
            self.assertEqual(summary_res["average_csat"], 0.0)

        finally:
            rs.get_db_connection = original_get_db
            empty_conn.close()

    def test_07_baseline_data_integrity_preserved(self):
        """Ensure all original database records remain intact after running reporting suite."""
        with get_db_connection() as conn:
            p_count = conn.execute("SELECT COUNT(*) FROM patients;").fetchone()[0]
            d_count = conn.execute("SELECT COUNT(*) FROM doctors;").fetchone()[0]
            a_count = conn.execute("SELECT COUNT(*) FROM appointments;").fetchone()[0]

            self.assertEqual(p_count, self.baseline_patients, "Patient count must remain exactly 25.")
            self.assertEqual(d_count, self.baseline_doctors, "Doctor count must remain exactly 10.")
            self.assertEqual(a_count, self.baseline_appointments, "Appointment count must remain exactly 42.")


if __name__ == "__main__":
    unittest.main()
