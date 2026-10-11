"""Unit and integration test suite for TQM Quality Toolkit (BBAT104 Course Project).
Verifies RPN calculations, FMEA matrix integrity, Defect logging, Pareto distributions,
SIPOC mapping, CTQ trees, and database safety.
"""
import unittest
from database.connection import get_db_connection, get_db_cursor
from services.tqm_service import (
    add_fmea_record,
    calculate_rpn,
    get_ctq_tree_data,
    get_defect_logs,
    get_defect_pareto_data,
    get_fishbone_data,
    get_fmea_records,
    get_next_defect_code,
    get_pdca_cycles_data,
    get_sipoc_data,
    log_defect,
    update_defect_status,
    validate_defect_data,
    validate_fmea_data,
)


class TestTQMToolkit(unittest.TestCase):
    """Test suite verifying TQM analytical calculations, validation, and persistence."""

    @classmethod
    def setUpClass(cls):
        """Record baseline record counts."""
        with get_db_connection() as conn:
            cls.baseline_patients = conn.execute("SELECT COUNT(*) FROM patients;").fetchone()[0]
            cls.baseline_doctors = conn.execute("SELECT COUNT(*) FROM doctors;").fetchone()[0]
            cls.baseline_appointments = conn.execute("SELECT COUNT(*) FROM appointments;").fetchone()[0]
            cls.baseline_defects = conn.execute("SELECT COUNT(*) FROM tqm_defect_logs;").fetchone()[0]

    def test_01_rpn_calculation_formula(self):
        """Verify RPN = Severity x Occurrence x Detection with boundary checks."""
        # Standard clinical risk calculations from seed data
        self.assertEqual(calculate_rpn(8, 8, 6), 384)  # Double-booking race condition
        self.assertEqual(calculate_rpn(6, 7, 5), 210)  # Manual entry typo
        self.assertEqual(calculate_rpn(9, 6, 5), 270)  # Scheduling doctor on leave
        self.assertEqual(calculate_rpn(8, 5, 7), 280)  # Silent submission failure

        # Extreme valid boundaries (1 to 10 scale)
        self.assertEqual(calculate_rpn(1, 1, 1), 1)
        self.assertEqual(calculate_rpn(10, 10, 10), 1000)

        # Invalid ratings must raise ValueError
        with self.assertRaises(ValueError):
            calculate_rpn(0, 5, 5)
        with self.assertRaises(ValueError):
            calculate_rpn(5, 11, 5)
        with self.assertRaises(ValueError):
            calculate_rpn(5, 5, -1)
        with self.assertRaises(ValueError):
            calculate_rpn("high", 5, 5)

    def test_02_fmea_database_records_integrity(self):
        """Verify all FMEA records adhere to RPN formula and have lower target RPN."""
        fmea_records = get_fmea_records()
        self.assertGreaterEqual(len(fmea_records), 8, "Expected at least 8 distinct FMEA failure modes.")

        for r in fmea_records:
            # Check pre-mitigation RPN calculation
            calculated_initial = calculate_rpn(r["severity_s"], r["occurrence_o"], r["detection_d"])
            self.assertEqual(r["rpn"], calculated_initial, f"RPN mismatch for {r['failure_mode']}")

            # Check post-mitigation Target RPN calculation
            calculated_target = calculate_rpn(r["target_severity"], r["target_occurrence"], r["target_detection"])
            self.assertEqual(r["target_rpn"], calculated_target, f"Target RPN mismatch for {r['failure_mode']}")

            # Target risk must be strictly lower than pre-mitigation risk
            self.assertLess(r["target_rpn"], r["rpn"], f"Target RPN should be lower than initial RPN for {r['failure_mode']}")

            # Risk reduction percentage must be positive
            self.assertGreater(r["reduction_pct"], 0.0)

    def test_03_fmea_validation_and_creation(self):
        """Verify FMEA validation rules and temporary record creation."""
        # 1. Missing Process Step
        ok, msg = validate_fmea_data({"process_step": "", "failure_mode": "Crash", "mitigation_action": "Fix", "severity_s": 5, "occurrence_o": 5, "detection_d": 5, "target_severity": 2, "target_occurrence": 2, "target_detection": 2})
        self.assertFalse(ok)
        self.assertIn("Process Step", msg)

        # 2. Out of bounds rating (>10)
        ok, msg = validate_fmea_data({"process_step": "Triage", "failure_mode": "Crash", "mitigation_action": "Fix", "severity_s": 15, "occurrence_o": 5, "detection_d": 5, "target_severity": 2, "target_occurrence": 2, "target_detection": 2})
        self.assertFalse(ok)
        self.assertIn("Severity", msg)

        # 3. Create temporary FMEA entry
        temp_data = {
            "process_step": "Unit Test Step",
            "failure_mode": "Temporary test failure mode",
            "failure_effect": "Test impact",
            "potential_cause": "Unit test harness",
            "severity_s": 7,
            "occurrence_o": 6,
            "detection_d": 5,
            "mitigation_action": "Automated test suite verification",
            "target_severity": 7,
            "target_occurrence": 1,
            "target_detection": 1,
        }
        success, msg, new_id = add_fmea_record(temp_data)
        self.assertTrue(success, f"Failed to add FMEA record: {msg}")
        self.assertIsNotNone(new_id)

        try:
            with get_db_connection() as conn:
                row = conn.execute("SELECT * FROM tqm_fmea_records WHERE id = ?;", (new_id,)).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["rpn"], 210)  # 7 * 6 * 5
                self.assertEqual(row["target_rpn"], 7)  # 7 * 1 * 1
        finally:
            with get_db_cursor() as (conn, cursor):
                cursor.execute("DELETE FROM tqm_fmea_records WHERE id = ?;", (new_id,))

    def test_04_defect_validation_and_logging_lifecycle(self):
        """Verify defect checksheet validation, insertion, and resolution status update."""
        # 1. Validation catches missing description
        ok, msg = validate_defect_data({"category": "UI Lag / Latency", "severity": "Major", "description": "", "reported_by": "Nurse"})
        self.assertFalse(ok)
        self.assertIn("Description", msg)

        # 2. Validation catches invalid severity
        ok, msg = validate_defect_data({"category": "UI Lag / Latency", "severity": "Catastrophic", "description": "System freeze", "reported_by": "Nurse"})
        self.assertFalse(ok)
        self.assertIn("Severity", msg)

        # 3. Log temporary defect record
        temp_defect = {
            "defect_code": "DEF-TEST-9999",
            "category": "Appointment Booking Error",
            "severity": "Critical",
            "description": "Temporary collision defect for automated verification",
            "reported_by": "Test Suite Operator",
            "resolution_status": "Logged",
        }
        success, msg, def_id = log_defect(temp_defect)
        self.assertTrue(success, f"Failed to log defect: {msg}")
        self.assertIsNotNone(def_id)

        try:
            # Verify in SQLite
            with get_db_connection() as conn:
                row = conn.execute("SELECT * FROM tqm_defect_logs WHERE id = ?;", (def_id,)).fetchone()
                self.assertIsNotNone(row)
                self.assertEqual(row["defect_code"], "DEF-TEST-9999")
                self.assertEqual(row["resolution_status"], "Logged")

            # Update status to Resolved
            upd_ok, upd_msg = update_defect_status(def_id, "Resolved")
            self.assertTrue(upd_ok)

            with get_db_connection() as conn:
                updated_row = conn.execute("SELECT * FROM tqm_defect_logs WHERE id = ?;", (def_id,)).fetchone()
                self.assertEqual(updated_row["resolution_status"], "Resolved")
                self.assertIsNotNone(updated_row["resolved_at"])
        finally:
            with get_db_cursor() as (conn, cursor):
                cursor.execute("DELETE FROM tqm_defect_logs WHERE id = ?;", (def_id,))

    def test_05_pareto_analysis_calculation(self):
        """Verify Pareto analysis 80/20 distribution metrics and descending ordering."""
        pareto = get_defect_pareto_data()
        self.assertIsInstance(pareto, dict)
        self.assertGreaterEqual(pareto["total_defects"], self.baseline_defects)

        counts = pareto["counts"]
        cum_pct = pareto["cumulative_pct"]

        # Counts must be in strictly descending order
        for i in range(len(counts) - 1):
            self.assertGreaterEqual(counts[i], counts[i + 1], "Pareto counts must be sorted descending.")

        # Cumulative percentage must reach 100%
        self.assertAlmostEqual(cum_pct[-1], 100.0, delta=0.5)

        # Vital few categories must be identified
        self.assertGreater(len(pareto["vital_few"]), 0)
        self.assertIn("Appointment Booking Error", pareto["vital_few"])

    def test_06_sipoc_and_ctq_framework_integrity(self):
        """Verify SIPOC 5 pillars and CTQ Tree nodes are fully populated."""
        sipoc = get_sipoc_data()
        for pillar in ["Suppliers", "Inputs", "Process", "Outputs", "Customers"]:
            self.assertIn(pillar, sipoc)
            self.assertGreaterEqual(len(sipoc[pillar]), 4, f"SIPOC pillar '{pillar}' must have items.")

        ctq_tree = get_ctq_tree_data()
        self.assertGreaterEqual(len(ctq_tree), 5, "Expected at least 5 CTQ quality requirements.")
        for item in ctq_tree:
            self.assertIn("need", item)
            self.assertIn("driver", item)
            self.assertIn("ctq", item)
            self.assertIn("target", item)
            self.assertIn("status", item)

        fishbone = get_fishbone_data()
        self.assertIn("problem", fishbone)
        self.assertIn("branches", fishbone)
        self.assertGreaterEqual(len(fishbone["branches"]), 4)

        pdca = get_pdca_cycles_data()
        self.assertEqual(len(pdca), 4, "PDCA must have exactly 4 stages (Plan, Do, Check, Act).")

    def test_07_baseline_data_integrity_preserved(self):
        """Ensure all original database records remain intact."""
        with get_db_connection() as conn:
            p_count = conn.execute("SELECT COUNT(*) FROM patients;").fetchone()[0]
            d_count = conn.execute("SELECT COUNT(*) FROM doctors;").fetchone()[0]
            a_count = conn.execute("SELECT COUNT(*) FROM appointments;").fetchone()[0]

            self.assertEqual(p_count, self.baseline_patients, "Patients count must remain intact.")
            self.assertEqual(d_count, self.baseline_doctors, "Doctors count must remain intact.")
            self.assertEqual(a_count, self.baseline_appointments, "Appointments count must remain intact.")


if __name__ == "__main__":
    unittest.main()
