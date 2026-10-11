"""Unit and integration test suite for Patient CRUD, validation, and SQLite persistence."""
import unittest
from database.connection import get_db_connection
from services.patient_service import (
    archive_patient,
    create_patient,
    delete_patient,
    get_next_patient_code,
    get_patient_appointment_count,
    get_patient_by_id,
    update_patient,
)
from services.validation import validate_patient_data


class TestPatientCRUD(unittest.TestCase):
    """Test suite verifying Patient CRUD operations with temporary test records."""

    @classmethod
    def setUpClass(cls):
        """Record baseline state of patients table."""
        with get_db_connection() as conn:
            cls.baseline_count = conn.execute("SELECT COUNT(*) as c FROM patients;").fetchone()["c"]

    def test_01_validation_rejects_invalid_inputs(self):
        """Verify validation engine catches missing or malformed fields."""
        # 1. Missing First Name
        val, msg = validate_patient_data({"first_name": "", "last_name": "Sharma", "patient_code": "PAT-9999", "dob": "1990-01-01", "gender": "Male", "phone": "9876543210"})
        self.assertFalse(val)
        self.assertIn("First Name", msg)

        # 2. Invalid Patient Code format
        val, msg = validate_patient_data({"first_name": "Test", "last_name": "User", "patient_code": "INVALID-123", "dob": "1990-01-01", "gender": "Male", "phone": "9876543210"})
        self.assertFalse(val)
        self.assertIn("PAT-", msg)

        # 3. Invalid Phone (<10 digits)
        val, msg = validate_patient_data({"first_name": "Test", "last_name": "User", "patient_code": "PAT-9999", "dob": "1990-01-01", "gender": "Male", "phone": "12345"})
        self.assertFalse(val)
        self.assertIn("Phone Number", msg)

        # 4. Invalid DOB format
        val, msg = validate_patient_data({"first_name": "Test", "last_name": "User", "patient_code": "PAT-9999", "dob": "31-12-1990", "gender": "Male", "phone": "9876543210"})
        self.assertFalse(val)
        self.assertIn("Date of Birth", msg)

        # 5. Duplicate Patient Code (PAT-1001 already exists in demo seed)
        val, msg = validate_patient_data({"first_name": "Test", "last_name": "User", "patient_code": "PAT-1001", "dob": "1990-01-01", "gender": "Male", "phone": "9876543210"})
        self.assertFalse(val)
        self.assertIn("already assigned", msg)

    def test_02_create_read_update_archive_delete_lifecycle(self):
        """Execute full CRUD lifecycle on a temporary demo record and verify persistence."""
        test_code = "PAT-TEMP-8888"
        test_data = {
            "patient_code": test_code,
            "first_name": "Harish",
            "last_name": "Chandra",
            "dob": "1988-06-20",
            "gender": "Male",
            "phone": "+91 98888 77777",
            "email": "harish.c@test.demo",
            "blood_group": "O+",
            "emergency_contact": "+91 98888 00000",
            "address": "404 Test Avenue, Sector 5",
            "status": "Active",
        }

        # 1. CREATE
        success, msg, patient_id = create_patient(test_data)
        self.assertTrue(success, f"Failed to create patient: {msg}")
        self.assertIsNotNone(patient_id)

        try:
            # 2. READ & PERSISTENCE CHECK
            saved = get_patient_by_id(patient_id)
            self.assertIsNotNone(saved)
            self.assertEqual(saved["patient_code"], test_code)
            self.assertEqual(saved["first_name"], "Harish")
            self.assertEqual(saved["blood_group"], "O+")
            self.assertEqual(saved["status"], "Active")

            # 3. UPDATE
            updated_data = test_data.copy()
            updated_data["phone"] = "+91 99999 44444"
            updated_data["address"] = "505 Updated Road, Green Valley"
            updated_data["status"] = "Discharged"

            upd_success, upd_msg = update_patient(patient_id, updated_data)
            self.assertTrue(upd_success, f"Failed to update patient: {upd_msg}")

            # Verify update persisted in SQLite
            updated_record = get_patient_by_id(patient_id)
            self.assertEqual(updated_record["phone"], "+91 99999 44444")
            self.assertEqual(updated_record["address"], "505 Updated Road, Green Valley")
            self.assertEqual(updated_record["status"], "Discharged")

            # 4. ARCHIVE
            arc_success, arc_msg = archive_patient(patient_id)
            self.assertTrue(arc_success, f"Failed to archive patient: {arc_msg}")

            archived_record = get_patient_by_id(patient_id)
            self.assertEqual(archived_record["status"], "Archived")

        finally:
            # 5. DELETE (Cleanup temporary record)
            del_success, del_msg = delete_patient(patient_id)
            self.assertTrue(del_success, f"Failed to delete temporary patient: {del_msg}")

            # Verify deleted from SQLite
            deleted_check = get_patient_by_id(patient_id)
            self.assertIsNone(deleted_check, "Patient record was not removed from SQLite!")

    def test_03_baseline_patients_integrity_preserved(self):
        """Ensure all 25 original demo patients remain untouched and intact."""
        with get_db_connection() as conn:
            current_count = conn.execute("SELECT COUNT(*) as c FROM patients;").fetchone()["c"]
            self.assertEqual(
                current_count,
                self.baseline_count,
                f"Baseline patient count altered! Expected {self.baseline_count}, found {current_count}",
            )


if __name__ == "__main__":
    unittest.main()
