"""Unit and integration test suite for Doctor CRUD, validation, and SQLite persistence."""
import unittest
from database.connection import get_db_connection
from services.doctor_service import (
    archive_doctor,
    create_doctor,
    delete_doctor,
    get_doctor_appointment_count,
    get_doctor_by_id,
    get_next_doctor_code,
    update_doctor,
)
from services.validation import validate_doctor_data


class TestDoctorCRUD(unittest.TestCase):
    """Test suite verifying Doctor CRUD operations with temporary test records."""

    @classmethod
    def setUpClass(cls):
        """Record baseline state of doctors table."""
        with get_db_connection() as conn:
            cls.baseline_count = conn.execute("SELECT COUNT(*) as c FROM doctors;").fetchone()["c"]

    def test_01_validation_rejects_invalid_inputs(self):
        """Verify validation engine catches missing or malformed doctor fields."""
        # 1. Missing First Name
        val, msg = validate_doctor_data({"first_name": "", "last_name": "Sharma", "doctor_code": "DOC-9999", "specialization": "Cardiology", "phone": "9876543210", "email": "doc@test.demo", "consultation_fee": 500.0, "room_number": "101"})
        self.assertFalse(val)
        self.assertIn("First Name", msg)

        # 2. Invalid Doctor Code format
        val, msg = validate_doctor_data({"first_name": "Dr. Arun", "last_name": "Sharma", "doctor_code": "INVALID-123", "specialization": "Cardiology", "phone": "9876543210", "email": "doc@test.demo", "consultation_fee": 500.0, "room_number": "101"})
        self.assertFalse(val)
        self.assertIn("DOC-", msg)

        # 3. Duplicate Doctor Code (DOC-2001 exists in seed)
        val, msg = validate_doctor_data({"first_name": "Dr. Arun", "last_name": "Sharma", "doctor_code": "DOC-2001", "specialization": "Cardiology", "phone": "9876543210", "email": "doc@test.demo", "consultation_fee": 500.0, "room_number": "101"})
        self.assertFalse(val)
        self.assertIn("already assigned", msg)

        # 4. Invalid Phone (<10 digits)
        val, msg = validate_doctor_data({"first_name": "Dr. Arun", "last_name": "Sharma", "doctor_code": "DOC-9999", "specialization": "Cardiology", "phone": "12345", "email": "doc@test.demo", "consultation_fee": 500.0, "room_number": "101"})
        self.assertFalse(val)
        self.assertIn("Phone Number", msg)

        # 5. Invalid Email
        val, msg = validate_doctor_data({"first_name": "Dr. Arun", "last_name": "Sharma", "doctor_code": "DOC-9999", "specialization": "Cardiology", "phone": "9876543210", "email": "invalid_email_format", "consultation_fee": 500.0, "room_number": "101"})
        self.assertFalse(val)
        self.assertIn("email", msg.lower())

        # 6. Negative Consultation Fee
        val, msg = validate_doctor_data({"first_name": "Dr. Arun", "last_name": "Sharma", "doctor_code": "DOC-9999", "specialization": "Cardiology", "phone": "9876543210", "email": "doc@test.demo", "consultation_fee": -100.0, "room_number": "101"})
        self.assertFalse(val)
        self.assertIn("Fee", msg)

        # 7. Missing Room Number
        val, msg = validate_doctor_data({"first_name": "Dr. Arun", "last_name": "Sharma", "doctor_code": "DOC-9999", "specialization": "Cardiology", "phone": "9876543210", "email": "doc@test.demo", "consultation_fee": 500.0, "room_number": ""})
        self.assertFalse(val)
        self.assertIn("Room", msg)

    def test_02_create_read_update_archive_delete_lifecycle(self):
        """Execute full CRUD lifecycle on a temporary doctor record and verify persistence."""
        test_code = "DOC-TEMP-8888"
        test_data = {
            "doctor_code": test_code,
            "first_name": "Dr. Sandeep",
            "last_name": "Aggarwal",
            "specialization": "Neurology",
            "phone": "+91 98888 11111",
            "email": "sandeep.a@hospital.demo",
            "consultation_fee": 850.0,
            "room_number": "Neuro-305",
            "status": "Available",
        }

        # 1. CREATE
        success, msg, doctor_id = create_doctor(test_data)
        self.assertTrue(success, f"Failed to create doctor: {msg}")
        self.assertIsNotNone(doctor_id)

        try:
            # 2. READ & PERSISTENCE CHECK
            saved = get_doctor_by_id(doctor_id)
            self.assertIsNotNone(saved)
            self.assertEqual(saved["doctor_code"], test_code)
            self.assertEqual(saved["first_name"], "Dr. Sandeep")
            self.assertEqual(saved["specialization"], "Neurology")
            self.assertEqual(saved["consultation_fee"], 850.0)
            self.assertEqual(saved["room_number"], "Neuro-305")
            self.assertEqual(saved["status"], "Available")

            # 3. UPDATE
            updated_data = test_data.copy()
            updated_data["consultation_fee"] = 950.0
            updated_data["room_number"] = "Neuro-310"
            updated_data["status"] = "In Consultation"

            upd_success, upd_msg = update_doctor(doctor_id, updated_data)
            self.assertTrue(upd_success, f"Failed to update doctor: {upd_msg}")

            # Verify in SQLite
            updated_record = get_doctor_by_id(doctor_id)
            self.assertEqual(updated_record["consultation_fee"], 950.0)
            self.assertEqual(updated_record["room_number"], "Neuro-310")
            self.assertEqual(updated_record["status"], "In Consultation")

            # 4. ARCHIVE (Set status to 'On Leave')
            arc_success, arc_msg = archive_doctor(doctor_id)
            self.assertTrue(arc_success, f"Failed to archive doctor: {arc_msg}")

            archived_record = get_doctor_by_id(doctor_id)
            self.assertEqual(archived_record["status"], "On Leave")

        finally:
            # 5. DELETE (Cleanup temporary record)
            del_success, del_msg = delete_doctor(doctor_id)
            self.assertTrue(del_success, f"Failed to delete temporary doctor: {del_msg}")

            # Verify deleted from SQLite
            deleted_check = get_doctor_by_id(doctor_id)
            self.assertIsNone(deleted_check, "Doctor record was not removed from SQLite!")

    def test_03_foreign_key_safety_blocks_deleting_busy_doctor(self):
        """Verify that doctors with existing patient bookings cannot be permanently deleted."""
        with get_db_connection() as conn:
            # DOC-2001 has active appointments in demo seed data
            doc_row = conn.execute("SELECT id, doctor_code FROM doctors WHERE doctor_code = 'DOC-2001';").fetchone()
            self.assertIsNotNone(doc_row)
            doc_id = doc_row["id"]

            appt_count = get_doctor_appointment_count(doc_id)
            self.assertGreater(appt_count, 0, "DOC-2001 should have appointments in demo dataset.")

            # Attempt delete: should be safely rejected
            success, msg = delete_doctor(doc_id)
            self.assertFalse(success, "Deleting a doctor with active appointments should fail!")
            self.assertIn("linked appointment", msg)

    def test_04_baseline_doctors_integrity_preserved(self):
        """Ensure all 10 original demo doctors remain untouched and intact."""
        with get_db_connection() as conn:
            current_count = conn.execute("SELECT COUNT(*) as c FROM doctors;").fetchone()["c"]
            self.assertEqual(
                current_count,
                self.baseline_count,
                f"Baseline doctor count altered! Expected {self.baseline_count}, found {current_count}",
            )


if __name__ == "__main__":
    unittest.main()
