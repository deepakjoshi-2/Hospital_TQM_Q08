"""Automated test suite verifying Fishbone diagram structure, FMEA duplicate prevention,
executive quality improvement trace, and zero-record-loss database safety.
"""
import unittest
from database.connection import get_db_connection, get_db_cursor
from services.tqm_service import (
    add_fmea_record,
    check_fmea_duplicate,
    get_fishbone_data,
    get_fmea_records,
    get_fmea_summary_stats,
    get_quality_improvement_trace,
)


class TestQualityTraceAndFishbone(unittest.TestCase):
    """Test suite verifying Ishikawa root-cause diagram data, FMEA deduplication, and quality traceability."""

    @classmethod
    def setUpClass(cls):
        """Record baseline database record counts to verify complete data preservation."""
        with get_db_connection() as conn:
            cls.baseline_patients = conn.execute("SELECT COUNT(*) FROM patients;").fetchone()[0]
            cls.baseline_doctors = conn.execute("SELECT COUNT(*) FROM doctors;").fetchone()[0]
            cls.baseline_appointments = conn.execute("SELECT COUNT(*) FROM appointments;").fetchone()[0]
            cls.baseline_defects = conn.execute("SELECT COUNT(*) FROM tqm_defect_logs;").fetchone()[0]
            cls.baseline_fmea = conn.execute("SELECT COUNT(*) FROM tqm_fmea_records;").fetchone()[0]

    def test_01_fmea_duplicate_prevention_and_case_insensitivity(self):
        """Verify check_fmea_duplicate detects existing modes and add_fmea_record rejects duplicates."""
        # 1. Existing mode must be detected
        self.assertTrue(
            check_fmea_duplicate("Slot Reservation", "Double booking same doctor slot"),
            "Expected existing FMEA mode to be detected as duplicate.",
        )

        # 2. Case-insensitive and whitespace-tolerant check
        self.assertTrue(
            check_fmea_duplicate("  slot reservation  ", "  DOUBLE BOOKING SAME DOCTOR SLOT  "),
            "Duplicate check must be case-insensitive and trim surrounding whitespace.",
        )

        # 3. add_fmea_record must reject insertion of existing failure mode
        duplicate_payload = {
            "process_step": "Slot Reservation",
            "failure_mode": "Double booking same doctor slot",
            "failure_effect": "Duplicate test",
            "potential_cause": "Race condition test",
            "severity_s": 8,
            "occurrence_o": 8,
            "detection_d": 6,
            "mitigation_action": "Unique partial index",
            "target_severity": 8,
            "target_occurrence": 1,
            "target_detection": 1,
        }
        success, msg, new_id = add_fmea_record(duplicate_payload)
        self.assertFalse(success, "add_fmea_record must not permit duplicate failure modes.")
        self.assertIn("already exists", msg)
        self.assertIsNone(new_id)

        # 4. Non-existent mode check
        self.assertFalse(
            check_fmea_duplicate("Nonexistent Step", "Nonexistent Mode"),
            "Unique mode must not be reported as duplicate.",
        )

    def test_02_fmea_summary_stats_distinct_aggregation(self):
        """Verify get_fmea_summary_stats computes authentic metrics over distinct modes."""
        stats = get_fmea_summary_stats()
        distinct_records = get_fmea_records()

        # Must report authentic distinct failure mode count (8), not raw duplicated batch count (232)
        self.assertEqual(stats["total_failure_modes"], len(distinct_records))
        self.assertEqual(stats["total_failure_modes"], 8)

        # High risk count (RPN >= 200) across distinct modes is 4
        self.assertEqual(stats["high_risk_count"], 4)

        # Average initial RPN and target RPN
        self.assertGreater(stats["avg_initial_rpn"], 200.0)
        self.assertLess(stats["avg_target_rpn"], 30.0)

        # Overall risk reduction must exceed 90%
        self.assertGreater(stats["overall_reduction_pct"], 90.0)

        # Database rows must remain intact at baseline count (232)
        with get_db_connection() as conn:
            current_fmea_count = conn.execute("SELECT COUNT(*) FROM tqm_fmea_records;").fetchone()[0]
        self.assertEqual(current_fmea_count, self.baseline_fmea, "Database rows must not be deleted or purged.")

    def test_03_fishbone_data_and_rib_structure(self):
        """Verify classical Ishikawa data structure contains 4 branches and 12 root causes."""
        fish_data = get_fishbone_data()

        self.assertIn("problem", fish_data)
        self.assertIn("branches", fish_data)
        self.assertIn("root_cause_summary", fish_data)

        # 4 Major classical Ishikawa branches
        expected_branches = [
            "People (Staff & Patients)",
            "Process (Workflow Methods)",
            "Technology & Tools (Software / DB)",
            "Measurement & Environment",
        ]
        for b in expected_branches:
            self.assertIn(b, fish_data["branches"], f"Missing fishbone branch: {b}")
            causes = fish_data["branches"][b]
            self.assertGreaterEqual(len(causes), 3, f"Branch {b} should have at least 3 causes.")

        # Total causes mapped must be at least 12
        total_causes = sum(len(c) for c in fish_data["branches"].values())
        self.assertGreaterEqual(total_causes, 12, "Ishikawa diagram must map at least 12 distinct causes.")

    def test_04_quality_improvement_trace_structure_and_provenance(self):
        """Verify get_quality_improvement_trace returns verified KPIs, provenance notes, and 7 matrix rows."""
        trace = get_quality_improvement_trace()

        self.assertIn("provenance_notes", trace)
        self.assertIn("kpi_summary", trace)
        self.assertIn("trace_matrix", trace)

        # Provenance notes
        prov = trace["provenance_notes"]
        self.assertIn("actual_measured", prov)
        self.assertIn("configured_targets", prov)
        self.assertIn("sample_benchmarks", prov)

        # KPI Summary verified against database
        kpis = trace["kpi_summary"]
        self.assertEqual(kpis["total_defects_logged"], 21)
        self.assertEqual(kpis["total_appointments"], 44)
        self.assertEqual(kpis["completed_appointments"], 20)
        self.assertEqual(kpis["csat_rated_count"], 20)
        self.assertAlmostEqual(kpis["measured_csat"], 4.45, places=2)
        self.assertTrue(kpis["has_collision_index"])

        # Trace matrix must contain all 7 defect categories
        matrix = trace["trace_matrix"]
        self.assertEqual(len(matrix), 7)

    def test_05_trace_matrix_factual_integrity_and_unverified_gap_labeling(self):
        """Verify factual link verification, RPN transitions, and explicit unverified labeling for Row 6."""
        trace = get_quality_improvement_trace()
        matrix = trace["trace_matrix"]

        row_by_category = {r["defect_category"]: r for r in matrix}

        # Check Category 1: Appointment Booking Error
        row1 = row_by_category.get("Appointment Booking Error")
        self.assertIsNotNone(row1)
        self.assertTrue(row1["is_verified_link"])
        self.assertEqual(row1["verification_status"], "Verified")
        self.assertEqual(row1["fmea_step"], "Slot Reservation")
        self.assertEqual(row1["initial_rpn"], 384)
        self.assertEqual(row1["target_rpn"], 8)
        self.assertIn("0.0%", row1["measured_outcome"])

        # Check Category 6: Search Filter Inaccuracy (Unmodeled 1:1 in baseline FMEA register)
        row6 = row_by_category.get("Search Filter Inaccuracy")
        self.assertIsNotNone(row6)
        self.assertFalse(row6["is_verified_link"], "Search Filter Inaccuracy must be flagged as unverified link.")
        self.assertEqual(row6["verification_status"], "Unverified Link")
        self.assertIsNone(row6["initial_rpn"])
        self.assertIsNone(row6["target_rpn"])
        self.assertIn("Unmodeled", row6["fmea_step"])

        # Check Category 7: Theme / Visual Fatigue
        row7 = row_by_category.get("Theme / Visual Fatigue")
        self.assertIsNotNone(row7)
        self.assertTrue(row7["is_verified_link"])
        self.assertEqual(row7["fmea_step"], "Night Operations")
        self.assertEqual(row7["initial_rpn"], 192)
        self.assertEqual(row7["target_rpn"], 24)

    def test_06_database_record_preservation(self):
        """Verify that running the test suite has not altered or deleted any baseline clinical records."""
        with get_db_connection() as conn:
            cur_patients = conn.execute("SELECT COUNT(*) FROM patients;").fetchone()[0]
            cur_doctors = conn.execute("SELECT COUNT(*) FROM doctors;").fetchone()[0]
            cur_appointments = conn.execute("SELECT COUNT(*) FROM appointments;").fetchone()[0]
            cur_defects = conn.execute("SELECT COUNT(*) FROM tqm_defect_logs;").fetchone()[0]
            cur_fmea = conn.execute("SELECT COUNT(*) FROM tqm_fmea_records;").fetchone()[0]

        self.assertEqual(cur_patients, self.baseline_patients, "Patient count altered!")
        self.assertEqual(cur_doctors, self.baseline_doctors, "Doctor count altered!")
        self.assertEqual(cur_appointments, self.baseline_appointments, "Appointment count altered!")
        self.assertEqual(cur_defects, self.baseline_defects, "Defect log count altered!")
        self.assertEqual(cur_fmea, self.baseline_fmea, "FMEA record count altered!")


if __name__ == "__main__":
    unittest.main()
