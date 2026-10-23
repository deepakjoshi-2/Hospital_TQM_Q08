"""Unit tests for Appointment Confirmation, Status Transitions, Fee Preservation, and Notifications."""
import os
import tempfile
import unittest

from config.constants import (
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_CONFIRMED,
    STATUS_NO_SHOW,
    STATUS_PENDING,
)
from database.connection import get_db_connection, get_db_cursor
from database.seed_data import seed_database
from services.appointment_service import (
    cancel_appointment,
    create_appointment,
    get_appointment_by_id,
    get_appointment_confirmation_details,
    get_filtered_appointments,
    update_appointment,
    validate_status_transition,
)
from services.notification_service import (
    get_notifications_for_patient,
    get_unread_notification_count,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)


class TestAppointmentConfirmationAndNotifications(unittest.TestCase):
    """Test suite verifying confirmation cards, status lifecycle, notifications, and fee preservation."""

    def setUp(self):
        """Set up clean isolated test database."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = os.path.join(self.temp_dir.name, "test_confirm.db")
        os.environ["HOSPITAL_DB_PATH"] = self.test_db_path
        seed_database(self.test_db_path)

        with get_db_connection(self.test_db_path) as conn:
            p_row = conn.execute("SELECT id FROM patients LIMIT 1;").fetchone()
            d_row = conn.execute("SELECT id, consultation_fee FROM doctors LIMIT 1;").fetchone()
            self.patient_id = p_row["id"]
            self.doctor_id = d_row["id"]
            self.original_doctor_fee = float(d_row["consultation_fee"])

    def tearDown(self):
        """Clean up environment and temporary database."""
        os.environ.pop("HOSPITAL_DB_PATH", None)
        self.temp_dir.cleanup()

    def test_01_status_transition_rules(self):
        """Verify strict clinical state machine transitions and terminal states."""
        # 1. Allowed transitions
        ok, _ = validate_status_transition(STATUS_PENDING, STATUS_CONFIRMED)
        self.assertTrue(ok)

        ok, _ = validate_status_transition(STATUS_PENDING, STATUS_CANCELLED)
        self.assertTrue(ok)

        ok, _ = validate_status_transition(STATUS_CONFIRMED, STATUS_COMPLETED)
        self.assertTrue(ok)

        ok, _ = validate_status_transition(STATUS_CONFIRMED, STATUS_CANCELLED)
        self.assertTrue(ok)

        ok, _ = validate_status_transition(STATUS_CONFIRMED, STATUS_NO_SHOW)
        self.assertTrue(ok)

        # 2. Terminal states cannot transition
        ok, msg = validate_status_transition(STATUS_COMPLETED, STATUS_CONFIRMED)
        self.assertFalse(ok)
        self.assertIn("Completed", msg)

        ok, msg = validate_status_transition(STATUS_CANCELLED, STATUS_CONFIRMED)
        self.assertFalse(ok)
        self.assertIn("Cancelled", msg)

        # 3. Invalid target status
        ok, msg = validate_status_transition(STATUS_PENDING, "NonExistentStatus")
        self.assertFalse(ok)
        self.assertIn("Invalid target status", msg)

    def test_02_fee_preservation_at_booking_time(self):
        """Verify doctor consultation fee is frozen at booking and immune to future doctor fee changes."""
        appt_data = {
            "appointment_code": "APT-9901",
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "appointment_date": "2026-11-20",
            "time_slot": "10:00 AM",
            "reason": "Cardiac checkup",
            "priority": "Normal",
            "status": STATUS_CONFIRMED,
        }
        ok, msg, appt_id = create_appointment(appt_data)
        self.assertTrue(ok, msg)

        # Verify fee frozen
        created_appt = get_appointment_by_id(appt_id)
        self.assertEqual(float(created_appt["consultation_fee"]), self.original_doctor_fee)

        # Update doctor's fee in doctors table
        new_doctor_fee = self.original_doctor_fee + 500.0
        with get_db_cursor(self.test_db_path) as (conn, cursor):
            cursor.execute("UPDATE doctors SET consultation_fee = ? WHERE id = ?;", (new_doctor_fee, self.doctor_id))

        # Existing appointment fee MUST remain unchanged!
        rechecked_appt = get_appointment_by_id(appt_id)
        self.assertEqual(float(rechecked_appt["consultation_fee"]), self.original_doctor_fee)
        self.assertNotEqual(float(rechecked_appt["consultation_fee"]), new_doctor_fee)

    def test_03_in_app_notification_generation_and_reading(self):
        """Verify automatic notification generation on appointment booking and status change."""
        initial_count = get_unread_notification_count(patient_id=self.patient_id)

        # 1. Book appointment triggers confirmation notification
        appt_data = {
            "appointment_code": "APT-9902",
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "appointment_date": "2026-11-21",
            "time_slot": "11:00 AM",
            "reason": "Follow up consultation",
            "priority": "Normal",
            "status": STATUS_CONFIRMED,
        }
        ok, msg, appt_id = create_appointment(appt_data)
        self.assertTrue(ok)

        new_count = get_unread_notification_count(patient_id=self.patient_id)
        self.assertGreater(new_count, initial_count)

        notifs = get_notifications_for_patient(self.patient_id)
        latest = notifs[0]
        self.assertEqual(latest["title"], "Appointment Confirmed")
        self.assertIn("APT-9902", latest["message"])
        self.assertEqual(latest["is_read"], 0)

        # 2. Mark single notification as read
        read_ok = mark_notification_as_read(latest["id"])
        self.assertTrue(read_ok)

        # 3. Cancel appointment triggers cancellation notification
        cancel_ok, cancel_msg = cancel_appointment(appt_id)
        self.assertTrue(cancel_ok)

        updated_notifs = get_notifications_for_patient(self.patient_id)
        latest_cancel = updated_notifs[0]
        self.assertEqual(latest_cancel["title"], "Appointment Cancelled")
        self.assertIn("APT-9902", latest_cancel["message"])

        # 4. Mark all as read
        marked = mark_all_notifications_as_read(patient_id=self.patient_id)
        self.assertGreater(marked, 0)
        self.assertEqual(get_unread_notification_count(patient_id=self.patient_id), 0)

    def test_04_confirmation_details_card_builder(self):
        """Verify confirmation details slip contains all required clinical guidelines and doctor info."""
        appt_data = {
            "appointment_code": "APT-9903",
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "appointment_date": "2026-11-22",
            "time_slot": "02:00 PM",
            "reason": "Orthopedic consultation",
            "priority": "Urgent",
            "status": STATUS_CONFIRMED,
        }
        ok, _, appt_id = create_appointment(appt_data)
        self.assertTrue(ok)

        details = get_appointment_confirmation_details(appt_id)
        self.assertIsNotNone(details)
        self.assertEqual(details["appointment_code"], "APT-9903")
        self.assertIn("Dr.", details["doctor_name"])
        self.assertIsNotNone(details["specialization"])
        self.assertIsNotNone(details["room_number"])
        self.assertEqual(details["time_slot"], "02:00 PM")
        self.assertIsInstance(details["instructions"], list)
        self.assertGreaterEqual(len(details["instructions"]), 3)

    def test_05_role_based_appointment_scoping(self):
        """Verify role filtering: Patients only see their own appointments, Doctors see assigned appointments."""
        # Query with patient scoping
        pat_user = {"role": "Patient", "linked_patient_id": self.patient_id}
        pat_appts = get_filtered_appointments(user=pat_user)
        for a in pat_appts:
            self.assertEqual(a["patient_id"], self.patient_id)

        # Query with doctor scoping
        doc_user = {"role": "Doctor", "linked_doctor_id": self.doctor_id}
        doc_appts = get_filtered_appointments(user=doc_user)
        for a in doc_appts:
            self.assertEqual(a["doctor_id"], self.doctor_id)


if __name__ == "__main__":
    unittest.main()
