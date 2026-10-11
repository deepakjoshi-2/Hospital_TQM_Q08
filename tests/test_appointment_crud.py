"""Unit and integration test suite for Appointment CRUD, validation, double-booking prevention, and persistence."""
import unittest
from database.connection import get_db_connection
from services.appointment_service import (
    cancel_appointment,
    check_slot_conflict,
    create_appointment,
    delete_appointment,
    get_appointment_by_id,
    get_doctor_dropdown_options,
    get_next_appointment_code,
    get_patient_dropdown_options,
    update_appointment,
)
from services.validation import validate_appointment_data


class TestAppointmentCRUD(unittest.TestCase):
    """Test suite verifying Appointment CRUD operations and slot conflict safety."""

    @classmethod
    def setUpClass(cls):
        """Record baseline state of appointments table."""
        with get_db_connection() as conn:
            cls.baseline_count = conn.execute("SELECT COUNT(*) as c FROM appointments;").fetchone()["c"]
            # Fetch valid patient and doctor IDs for testing
            p_row = conn.execute("SELECT id FROM patients LIMIT 1;").fetchone()
            d_row = conn.execute("SELECT id FROM doctors LIMIT 1;").fetchone()
            cls.valid_patient_id = p_row["id"]
            cls.valid_doctor_id = d_row["id"]

    def test_01_validation_rejects_invalid_inputs(self):
        """Verify validation engine catches missing or malformed appointment fields."""
        # 1. Non-existent Patient ID
        val, msg = validate_appointment_data({
            "appointment_code": "APT-9999",
            "patient_id": 999999,
            "doctor_id": self.valid_doctor_id,
            "appointment_date": "2026-11-15",
            "time_slot": "09:00 AM",
        })
        self.assertFalse(val)
        self.assertIn("Patient", msg)

        # 2. Non-existent Doctor ID
        val, msg = validate_appointment_data({
            "appointment_code": "APT-9999",
            "patient_id": self.valid_patient_id,
            "doctor_id": 999999,
            "appointment_date": "2026-11-15",
            "time_slot": "09:00 AM",
        })
        self.assertFalse(val)
        self.assertIn("Doctor", msg)

        # 3. Invalid Appointment Code format
        val, msg = validate_appointment_data({
            "appointment_code": "INVALID-101",
            "patient_id": self.valid_patient_id,
            "doctor_id": self.valid_doctor_id,
            "appointment_date": "2026-11-15",
            "time_slot": "09:00 AM",
        })
        self.assertFalse(val)
        self.assertIn("APT-", msg)

        # 4. Duplicate Appointment Code (APT-3001 exists in seed data)
        val, msg = validate_appointment_data({
            "appointment_code": "APT-3001",
            "patient_id": self.valid_patient_id,
            "doctor_id": self.valid_doctor_id,
            "appointment_date": "2026-11-15",
            "time_slot": "09:00 AM",
            "reason": "Routine test for duplicate checking",
        })
        self.assertFalse(val)
        self.assertIn("already assigned", msg)

        # 5. Invalid Date format
        val, msg = validate_appointment_data({
            "appointment_code": "APT-9999",
            "patient_id": self.valid_patient_id,
            "doctor_id": self.valid_doctor_id,
            "appointment_date": "15-11-2026",
            "time_slot": "09:00 AM",
            "reason": "Invalid date test",
        })
        self.assertFalse(val)
        self.assertIn("YYYY-MM-DD", msg)

        # 6. Invalid Time Slot
        val, msg = validate_appointment_data({
            "appointment_code": "APT-9999",
            "patient_id": self.valid_patient_id,
            "doctor_id": self.valid_doctor_id,
            "appointment_date": "2026-11-15",
            "time_slot": "08:15 AM",
            "reason": "Invalid time slot test",
        })
        self.assertFalse(val)
        self.assertIn("time slot", msg.lower())

        # 7. Invalid Satisfaction Rating (> 5)
        val, msg = validate_appointment_data({
            "appointment_code": "APT-9999",
            "patient_id": self.valid_patient_id,
            "doctor_id": self.valid_doctor_id,
            "appointment_date": "2026-11-15",
            "time_slot": "09:00 AM",
            "reason": "Invalid rating test",
            "satisfaction_rating": 7,
        })
        self.assertFalse(val)
        self.assertIn("Rating", msg)

    def test_02_double_booking_conflict_prevention(self):
        """Verify that booking overlapping appointments for the same doctor and time slot is blocked."""
        # Find an existing scheduled consultation
        with get_db_connection() as conn:
            existing = conn.execute(
                "SELECT * FROM appointments WHERE status != 'Cancelled' LIMIT 1;"
            ).fetchone()

        self.assertIsNotNone(existing, "Seed data must contain active appointments.")
        doc_id = existing["doctor_id"]
        appt_date = existing["appointment_date"]
        slot = existing["time_slot"]

        # Conflict check should return True for this doctor/date/slot
        has_conflict, conf_code = check_slot_conflict(doc_id, appt_date, slot)
        self.assertTrue(has_conflict, "Conflict check should detect active booking.")
        self.assertIsNotNone(conf_code)

        # If we exclude this appointment's ID (e.g. when updating itself), no conflict
        has_conflict_self, _ = check_slot_conflict(doc_id, appt_date, slot, exclude_appointment_id=existing["id"])
        self.assertFalse(
            has_conflict_self,
            "Editing same appointment in its own slot should not trigger conflict."
        )


        # Attempt to create a NEW appointment in the same slot
        conflict_data = {
            "appointment_code": "APT-COLLISION-TEST",
            "patient_id": self.valid_patient_id,
            "doctor_id": doc_id,
            "appointment_date": appt_date,
            "time_slot": slot,
            "reason": "Collision prevention test",
            "priority": "Normal",
            "status": "Scheduled",
        }
        success, msg, new_id = create_appointment(conflict_data)
        self.assertFalse(success, "Double booking same doctor in same slot must be blocked!")
        self.assertIn("Double-Booking Blocked", msg)
        self.assertIsNone(new_id)


    def test_03_create_read_update_cancel_delete_lifecycle(self):
        """Execute full CRUD lifecycle on a temporary appointment and verify SQLite persistence."""
        test_code = "APT-TEST-8888"
        test_date = "2028-12-25"
        test_slot = "10:30 AM"

        test_data = {
            "appointment_code": test_code,
            "patient_id": self.valid_patient_id,
            "doctor_id": self.valid_doctor_id,
            "appointment_date": test_date,
            "time_slot": test_slot,
            "reason": "Temporary test consultation for TQM verification",
            "priority": "Normal",
            "status": "Scheduled",
            "satisfaction_rating": None,
        }

        # 1. CREATE
        success, msg, appt_id = create_appointment(test_data)
        self.assertTrue(success, f"Failed to create appointment: {msg}")
        self.assertIsNotNone(appt_id)

        try:
            # 2. READ & PERSISTENCE CHECK
            saved = get_appointment_by_id(appt_id)
            self.assertIsNotNone(saved)
            self.assertEqual(saved["appointment_code"], test_code)
            self.assertEqual(saved["patient_id"], self.valid_patient_id)
            self.assertEqual(saved["doctor_id"], self.valid_doctor_id)
            self.assertEqual(saved["appointment_date"], test_date)
            self.assertEqual(saved["time_slot"], test_slot)
            self.assertEqual(saved["status"], "Scheduled")

            # 3. UPDATE
            updated_data = test_data.copy()
            updated_data["time_slot"] = "11:00 AM"
            updated_data["priority"] = "Urgent"
            updated_data["reason"] = "Updated reason for follow-up review"
            updated_data["satisfaction_rating"] = 5

            upd_success, upd_msg = update_appointment(appt_id, updated_data)
            self.assertTrue(upd_success, f"Failed to update appointment: {upd_msg}")

            # Verify update in SQLite
            updated_record = get_appointment_by_id(appt_id)
            self.assertEqual(updated_record["time_slot"], "11:00 AM")
            self.assertEqual(updated_record["priority"], "Urgent")
            self.assertEqual(updated_record["reason"], "Updated reason for follow-up review")
            self.assertEqual(updated_record["satisfaction_rating"], 5)

            # 4. CANCEL APPOINTMENT (Sets status to 'Cancelled' and frees slot)
            cancel_success, cancel_msg = cancel_appointment(appt_id)
            self.assertTrue(cancel_success, f"Failed to cancel appointment: {cancel_msg}")

            cancelled_record = get_appointment_by_id(appt_id)
            self.assertEqual(cancelled_record["status"], "Cancelled")

            # Verifying slot is now free: booking another appointment in slot 11:00 AM should succeed
            free_slot_data = {
                "appointment_code": "APT-TEST-8889",
                "patient_id": self.valid_patient_id,
                "doctor_id": self.valid_doctor_id,
                "appointment_date": test_date,
                "time_slot": "11:00 AM",
                "reason": "Slot re-booking after cancellation",
                "priority": "Normal",
                "status": "Scheduled",
            }
            sub_success, sub_msg, sub_id = create_appointment(free_slot_data)
            self.assertTrue(sub_success, f"Slot should be available after cancellation: {sub_msg}")
            if sub_id:
                delete_appointment(sub_id)

        finally:
            # 5. PERMANENT DELETE (Cleanup temporary record)
            del_success, del_msg = delete_appointment(appt_id)
            self.assertTrue(del_success, f"Failed to delete temporary appointment: {del_msg}")

            # Verify deleted from SQLite
            deleted_check = get_appointment_by_id(appt_id)
            self.assertIsNone(deleted_check, "Appointment record was not deleted from SQLite!")

    def test_04_dropdown_helpers_return_populated_options(self):
        """Verify that dynamic patient and doctor dropdown loaders return populated data from SQLite."""
        pat_options = get_patient_dropdown_options()
        doc_options = get_doctor_dropdown_options()

        self.assertGreaterEqual(len(pat_options), 25, "Must load all 25+ patients from SQLite.")
        self.assertGreaterEqual(len(doc_options), 10, "Must load all 10+ doctors from SQLite.")

        # Check tuple structure: (id, label)
        self.assertIsInstance(pat_options[0], tuple)
        self.assertEqual(len(pat_options[0]), 2)
        self.assertIsInstance(doc_options[0], tuple)
        self.assertEqual(len(doc_options[0]), 2)

    def test_05_baseline_appointments_integrity_preserved(self):
        """Ensure all 42 original demo appointments remain untouched and intact."""
        with get_db_connection() as conn:
            current_count = conn.execute("SELECT COUNT(*) as c FROM appointments;").fetchone()["c"]
            self.assertEqual(
                current_count,
                self.baseline_count,
                f"Baseline appointment count altered! Expected {self.baseline_count}, found {current_count}",
            )


if __name__ == "__main__":
    unittest.main()
