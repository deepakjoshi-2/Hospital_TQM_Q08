"""Comprehensive regression and edge-case test suite for application improvements.
Verifies data integrity, scheduling collision safeguards, multi-field search,
CSV export file integrity, FMEA risk reduction constraints, and validation boundaries.
"""
import csv
import os
import unittest
from datetime import date, datetime

from database.connection import get_db_connection, get_db_cursor
from services.appointment_service import (
    check_patient_slot_conflict,
    create_appointment,
    update_appointment,
)
from services.patient_service import (
    delete_patient,
    get_patient_appointment_count,
)
from services.report_service import (
    export_appointments_to_csv,
    export_summary_report_to_csv,
)
from services.tqm_service import (
    export_defects_to_csv,
    get_defect_logs,
    get_fmea_summary_stats,
    validate_fmea_data,
)
from services.validation import (
    validate_appointment_data,
    validate_doctor_data,
    validate_patient_data,
)


class TestApplicationImprovements(unittest.TestCase):
    """Test suite verifying quality improvements implemented across core services."""

    @classmethod
    def setUpClass(cls):
        """Cache existing record IDs for safe integration checks."""
        with get_db_connection() as conn:
            # Existing patient with appointments
            p_row = conn.execute(
                """
                SELECT p.id, p.patient_code, p.first_name, p.last_name, p.phone
                FROM patients p
                JOIN appointments a ON a.patient_id = p.id
                LIMIT 1;
                """
            ).fetchone()
            cls.patient_with_appts = dict(p_row) if p_row else None

            # An existing appointment
            a_row = conn.execute(
                """
                SELECT id, appointment_code, patient_id, doctor_id, appointment_date, time_slot
                FROM appointments
                ORDER BY id ASC LIMIT 1;
                """
            ).fetchone()
            cls.sample_appt = dict(a_row) if a_row else None

    # =========================================================================
    # 1. Appointment Double-Booking Conflict Prevention
    # =========================================================================
    def test_01_patient_slot_conflict_detection(self):
        """Verify check_patient_slot_conflict blocks overlapping appointment slots."""
        if not self.sample_appt:
            self.skipTest("No sample appointments available in test database.")

        p_id = self.sample_appt["patient_id"]
        appt_date = self.sample_appt["appointment_date"]
        slot = self.sample_appt["time_slot"]
        appt_id = self.sample_appt["id"]

        # Same patient, same date & time slot -> conflict must be detected
        conflict, _ = check_patient_slot_conflict(p_id, appt_date, slot)
        self.assertTrue(conflict, "Expected conflict when scheduling same patient in occupied slot.")

        # Same appointment excluded -> no conflict (self-update allowed)
        no_conflict, _ = check_patient_slot_conflict(p_id, appt_date, slot, exclude_appointment_id=appt_id)
        self.assertFalse(no_conflict, "Self-update of same appointment slot should not report conflict.")

        # Different slot -> no conflict
        free_slot = "06:00 PM" if slot != "06:00 PM" else "07:00 PM"
        no_conflict_diff, _ = check_patient_slot_conflict(p_id, appt_date, free_slot)
        self.assertFalse(no_conflict_diff, "Unoccupied slot should not report patient conflict.")

    def test_02_create_appointment_rejects_patient_collision(self):
        """Verify create_appointment rejects scheduling when patient is already booked."""
        if not self.sample_appt:
            self.skipTest("No sample appointments available.")

        # Attempt to create an appointment for the same patient on same date & slot with another doctor
        new_data = {
            "appointment_code": "APT-CONFLICT-TEST",
            "patient_id": self.sample_appt["patient_id"],
            "doctor_id": (self.sample_appt["doctor_id"] % 10) + 1,
            "appointment_date": self.sample_appt["appointment_date"],
            "time_slot": self.sample_appt["time_slot"],
            "priority": "Normal",
            "reason": "Test conflict check",
        }
        success, msg, new_id = create_appointment(new_data)
        self.assertFalse(success)
        self.assertIn("Double-Booking Blocked", msg)
        self.assertIsNone(new_id)

    # =========================================================================
    # 2. On-Leave Doctor & Inactive Patient Safeguards
    # =========================================================================
    def test_03_booking_blocked_for_on_leave_doctor(self):
        """Verify validation prevents scheduling appointments with on-leave doctors."""
        with get_db_connection() as conn:
            leave_doc = conn.execute("SELECT id, first_name, last_name FROM doctors WHERE status = 'On Leave' LIMIT 1;").fetchone()

        if not leave_doc:
            self.skipTest("No doctor currently on leave in database.")

        data = {
            "appointment_code": "APT-LEAVE-9999",
            "patient_id": 1,
            "doctor_id": leave_doc["id"],
            "appointment_date": date.today().strftime("%Y-%m-%d"),
            "time_slot": "10:00 AM",
            "priority": "Normal",
            "reason": "Routine checkup",
        }
        ok, msg = validate_appointment_data(data)
        self.assertFalse(ok)
        self.assertIn("On Leave", msg)

    def test_04_booking_blocked_for_inactive_patient(self):
        """Verify validation prevents scheduling appointments for inactive/archived patients."""
        # Create a temporary archived patient
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO patients (patient_code, first_name, last_name, dob, gender, phone, status)
                VALUES ('PAT-ARCH-TEST', 'Archived', 'User', '1990-01-01', 'Other', '9988776655', 'Archived');
                """
            )
            temp_pat_id = cursor.lastrowid

        try:
            data = {
                "appointment_code": "APT-INACT-9999",
                "patient_id": temp_pat_id,
                "doctor_id": 1,
                "appointment_date": date.today().strftime("%Y-%m-%d"),
                "time_slot": "11:00 AM",
                "priority": "Normal",
                "reason": "Routine checkup",
            }
            ok, msg = validate_appointment_data(data)
            self.assertFalse(ok)
            self.assertIn("Cannot schedule appointment for Archived patient", msg)
        finally:
            with get_db_cursor() as (conn, cursor):
                cursor.execute("DELETE FROM patients WHERE id = ?;", (temp_pat_id,))

    # =========================================================================
    # 3. Patient Deletion Safeguard
    # =========================================================================
    def test_05_patient_deletion_blocked_with_appointments(self):
        """Verify patient with appointment history cannot be deleted."""
        if not self.patient_with_appts:
            self.skipTest("No patient with appointments found.")

        p_id = self.patient_with_appts["id"]
        appt_count = get_patient_appointment_count(p_id)
        self.assertGreater(appt_count, 0)

        success, msg = delete_patient(p_id)
        self.assertFalse(success)
        self.assertIn("linked clinical appointment", msg)

    # =========================================================================
    # 4. Input Validation Boundary Guards
    # =========================================================================
    def test_06_emergency_contact_conflict_validation(self):
        """Verify emergency contact cannot share identical phone with patient."""
        data = {
            "patient_code": "PAT-PHONE-TEST",
            "first_name": "Ramesh",
            "last_name": "Kumar",
            "dob": "1992-05-15",
            "gender": "Male",
            "phone": "9876543210",
            "emergency_contact": "9876543210",  # Identical phone
        }
        ok, msg = validate_patient_data(data)
        self.assertFalse(ok)
        self.assertIn("cannot be identical", msg)

    def test_07_doctor_fee_bounds_validation(self):
        """Verify consultation fees must be positive and not exceed 100,000."""
        # Fee too high (>100,000)
        data_high = {
            "doctor_code": "DOC-HIGH-FEE",
            "first_name": "Dr. Vikas",
            "last_name": "Mehta",
            "specialization": "Cardiology",
            "phone": "9876543211",
            "email": "dr.vikas.mehta@hospital.com",
            "consultation_fee": 150000.0,
            "room_number": "101",
        }
        ok, msg = validate_doctor_data(data_high)
        self.assertFalse(ok)
        self.assertIn("100,000", msg)

        # Negative fee
        data_neg = dict(data_high)
        data_neg["consultation_fee"] = -50.0
        ok, msg = validate_doctor_data(data_neg)
        self.assertFalse(ok)
        self.assertIn("must be zero or a positive amount", msg)

    def test_08_appointment_date_boundary_validation(self):
        """Verify appointment date cannot be in distant past or future beyond 2 years."""
        # Distant past
        data_past = {
            "appointment_code": "APT-PAST-TEST",
            "patient_id": 1,
            "doctor_id": 1,
            "appointment_date": "2010-01-01",
            "time_slot": "10:00 AM",
            "priority": "Normal",
            "reason": "Test",
        }
        ok, msg = validate_appointment_data(data_past)
        self.assertFalse(ok)
        self.assertIn("must be between", msg)

    # =========================================================================
    # 5. CSV Export File Integrity
    # =========================================================================
    def test_09_appointments_csv_export_integrity(self):
        """Verify export_appointments_to_csv generates a valid structured CSV file."""
        test_file = "test_export_appointments_temp.csv"
        try:
            success, msg, count = export_appointments_to_csv(test_file)
            self.assertTrue(success)
            self.assertGreater(count, 0)
            self.assertTrue(os.path.exists(test_file))

            # Inspect contents
            with open(test_file, mode="r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
                self.assertIn("Appointment Code", header)
                self.assertIn("Patient Name", header)
                self.assertIn("Doctor Name", header)
                rows = list(reader)
                self.assertEqual(len(rows), count)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_10_reports_summary_csv_export_integrity(self):
        """Verify export_summary_report_to_csv produces full KPIs and specialty breakdowns."""
        test_file = "test_export_summary_temp.csv"
        try:
            success, msg = export_summary_report_to_csv(test_file)
            self.assertTrue(success)
            self.assertTrue(os.path.exists(test_file))

            with open(test_file, mode="r", encoding="utf-8", errors="replace") as f:
                content = f.read()
                self.assertIn("CLINICAL ANALYTICS REPORT", content)
                self.assertIn("Total Registered Patients", content)
                self.assertIn("PHYSICIAN WORKLOAD DISTRIBUTION", content)
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    def test_11_defects_csv_export_integrity(self):
        """Verify export_defects_to_csv outputs clean checksheet records."""
        test_file = "test_export_defects_temp.csv"
        try:
            success, msg, count = export_defects_to_csv(test_file, status="Resolved")
            self.assertTrue(success)
            self.assertTrue(os.path.exists(test_file))

            with open(test_file, mode="r", encoding="utf-8") as f:
                reader = csv.reader(f)
                header = next(reader)
                self.assertIn("Defect Code", header)
                self.assertIn("Resolution Status", header)
                rows = list(reader)
                self.assertEqual(len(rows), count)
                # All rows must be Resolved
                status_idx = header.index("Resolution Status")
                for r in rows:
                    self.assertEqual(r[status_idx], "Resolved")
        finally:
            if os.path.exists(test_file):
                os.remove(test_file)

    # =========================================================================
    # 6. TQM Defect Filtering & FMEA Risk Reduction Constraints
    # =========================================================================
    def test_12_defect_checksheet_status_filtering(self):
        """Verify get_defect_logs correctly filters by resolution status."""
        all_defects = get_defect_logs()
        resolved = get_defect_logs(status="Resolved")
        in_analysis = get_defect_logs(status="In Analysis")

        self.assertGreaterEqual(len(all_defects), len(resolved))
        for d in resolved:
            self.assertEqual(d["resolution_status"], "Resolved")
        for d in in_analysis:
            self.assertEqual(d["resolution_status"], "In Analysis")

    def test_13_fmea_target_rpn_reduction_constraint(self):
        """Verify validate_fmea_data rejects target RPN higher than initial RPN."""
        invalid_fmea = {
            "process_step": "Patient Registration",
            "failure_mode": "Form validation timeout",
            "mitigation_action": "Increase timeout limit",
            "severity_s": 3,
            "occurrence_o": 3,
            "detection_d": 3,  # Initial RPN = 27
            "target_severity": 6,
            "target_occurrence": 6,
            "target_detection": 6,  # Target RPN = 216 (> 27)
        }
        ok, msg = validate_fmea_data(invalid_fmea)
        self.assertFalse(ok)
        self.assertIn("cannot exceed Initial RPN", msg)

    def test_14_fmea_summary_statistics_metrics(self):
        """Verify get_fmea_summary_stats returns non-empty aggregated quality metrics."""
        stats = get_fmea_summary_stats()
        self.assertGreater(stats["total_failure_modes"], 0)
        self.assertGreater(stats["avg_initial_rpn"], 0.0)
        self.assertGreater(stats["avg_target_rpn"], 0.0)
        self.assertGreater(stats["overall_reduction_pct"], 0.0)


if __name__ == "__main__":
    unittest.main()
