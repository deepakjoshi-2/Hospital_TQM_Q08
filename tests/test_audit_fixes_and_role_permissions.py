"""Comprehensive Test Suite for Audit Fixes, Role Permissions, and Workflow Correction.

Validates all 11 critical audit areas:
1. Dedicated fullscreen login flow on fresh launch (start_login=True).
2. Clean authentication, logout, and session clearing.
3. Appointment booking without AttributeError (self.save_btn restored, rating_menu is None).
4. Validation rules: Reject inactive patients, on-leave doctors, and double booking.
5. Post-visit CSAT feedback restricted to 'Completed' visits with duplicate prevention.
6. Billing summary financial scoping by role (Admin hospital totals, Doctor fees, Patient balance).
7. Sync unbilled appointments transaction safety.
8. User Settings and Profile isolation without administrator data leakage.
9. Clinical reports doctor scoping.
10. TQM Toolkit role-based access control (Admin full 7 tabs, Staff defect checksheet only, Doctor/Patient restricted).
"""
import os
import tempfile
import unittest
import customtkinter as ctk

from config.constants import (
    ROLE_ADMIN,
    ROLE_DOCTOR,
    ROLE_PATIENT,
    ROLE_STAFF,
)
from database.connection import get_db_connection, get_db_cursor
from database.seed_data import seed_database
from services.appointment_service import (
    create_appointment,
    get_appointment_by_id,
    submit_visit_feedback,
    update_appointment,
)
from services.auth_service import (
    authenticate_user,
    get_current_user,
    login,
    logout,
    set_current_user,
)
from services.billing_service import (
    get_billing_summary_statistics,
    sync_unbilled_appointments,
)
from services.profile_service import get_user_profile
from services.report_service import (
    get_appointments_by_status,
    get_patient_satisfaction_data,
)
from ui.app import HospitalApp
from ui.components.appointment_modals import AppointmentFormModal, PostVisitFeedbackModal
from ui.views.tqm_view import TQMView


class TestAuditFixesAndRolePermissions(unittest.TestCase):
    """Test suite verifying all 11 audit defect fixes and role permissions."""

    @classmethod
    def setUpClass(cls):
        ctk.set_appearance_mode("Dark")
        cls.root = ctk.CTk()
        cls.root.geometry("1100x650")
        cls.root.withdraw()
        cls.root.update()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = os.path.join(self.temp_dir.name, "test_audit.db")
        os.environ["HOSPITAL_DB_PATH"] = self.test_db_path
        seed_database(self.test_db_path)
        logout()

    def tearDown(self):
        logout()
        os.environ.pop("HOSPITAL_DB_PATH", None)
        self.temp_dir.cleanup()

    # -------------------------------------------------------------------------
    # 1. Dedicated Startup & Clean Logout
    # -------------------------------------------------------------------------
    def test_01_fresh_launch_starts_with_login_view(self):
        """Verify launching with start_login=True opens dedicated fullscreen login screen."""
        app = HospitalApp(start_login=True)
        self.root.update()

        self.assertEqual(app.active_view_name, "Login")
        self.assertFalse(app.sidebar.winfo_ismapped())
        self.assertFalse(app.content_container.winfo_ismapped())

        # Test clean sign in
        _, user, _ = login("admin", "Admin@123")
        app.on_login_success(user)
        self.root.update()

        self.assertTrue(app.sidebar.winfo_ismapped())
        self.assertTrue(app.content_container.winfo_ismapped())

        # Now trigger logout_user()
        app.logout_user()
        self.root.update()

        self.assertEqual(app.active_view_name, "Login")
        self.assertFalse(app.sidebar.winfo_ismapped())
        self.assertFalse(app.content_container.winfo_ismapped())
        self.assertIsNone(get_current_user())

        app.destroy()
        self.root.update()

    def test_02_authentication_and_session_clearing(self):
        """Verify PBKDF2 authentication validates correct credentials and logout clears state."""
        # Invalid password
        ok, user, err = authenticate_user("admin", "WrongPassword")
        self.assertFalse(ok)
        self.assertIsNone(user)
        self.assertIn("Invalid", err)

        # Non-existent user
        ok, user, err = authenticate_user("unknown_user", "AnyPassword")
        self.assertFalse(ok)
        self.assertIsNone(user)

        # Valid login
        ok, user, msg = login("admin", "Admin@123")
        self.assertTrue(ok)
        self.assertIsNotNone(user)
        self.assertEqual(user["username"], "admin")
        self.assertEqual(get_current_user()["username"], "admin")

        # Clean logout
        logout()
        self.assertIsNone(get_current_user())

    # -------------------------------------------------------------------------
    # 2. Appointment Booking & Modal Inspection
    # -------------------------------------------------------------------------
    def test_03_appointment_modal_has_save_btn_and_no_csat_input(self):
        """Verify AppointmentFormModal has self.save_btn and omits CSAT rating."""
        modal = AppointmentFormModal(self.root)
        self.root.update()

        # Check self.save_btn exists and is not None
        self.assertTrue(hasattr(modal, "save_btn"))
        self.assertIsNotNone(modal.save_btn)
        self.assertIn("Confirm Booking", modal.save_btn.cget("text"))

        # Verify satisfaction rating field is omitted from initial booking modal
        self.assertIsNone(modal.rating_menu)

        modal.destroy()
        self.root.update()

    def test_04_appointment_booking_business_rules(self):
        """Verify booking rejects inactive patients, on-leave doctors, and double booking."""
        with get_db_cursor() as (conn, cursor):
            # Deactivate patient 2
            cursor.execute("UPDATE patients SET status = 'Archived' WHERE id = 2;")
            # Doctor 7 is On Leave in seed data (Dr. Farhan Qureshi)
            cursor.execute("UPDATE doctors SET status = 'On Leave' WHERE id = 7;")

        # 1. Reject inactive patient
        ok, msg, _ = create_appointment({
            "appointment_code": "APT-9101",
            "patient_id": 2,
            "doctor_id": 1,
            "appointment_date": "2026-11-15",
            "time_slot": "10:00 AM",
            "reason": "Checkup",
        })
        self.assertFalse(ok)
        self.assertIn("Archived", msg)

        # 2. Reject on-leave doctor
        ok, msg, _ = create_appointment({
            "appointment_code": "APT-9102",
            "patient_id": 1,
            "doctor_id": 7,
            "appointment_date": "2026-11-15",
            "time_slot": "10:00 AM",
            "reason": "Checkup",
        })
        self.assertFalse(ok)
        self.assertIn("On Leave", msg)

        # 3. Successful booking
        ok, msg, appt_id = create_appointment({
            "appointment_code": "APT-9103",
            "patient_id": 1,
            "doctor_id": 1,
            "appointment_date": "2026-11-15",
            "time_slot": "10:00 AM",
            "reason": "Checkup",
        })
        self.assertTrue(ok)
        appt = get_appointment_by_id(appt_id)
        self.assertIsNotNone(appt)
        self.assertIn(appt["status"], ["Scheduled", "Confirmed"])
        self.assertIsNone(appt["satisfaction_rating"])

        # 4. Reject double-booking same doctor at exact date and time
        ok, msg, _ = create_appointment({
            "appointment_code": "APT-9104",
            "patient_id": 3,
            "doctor_id": 1,
            "appointment_date": "2026-11-15",
            "time_slot": "10:00 AM",
            "reason": "Followup",
        })
        self.assertFalse(ok)
        self.assertIn("already", msg.lower())

    # -------------------------------------------------------------------------
    # 3. Post-Visit CSAT Feedback
    # -------------------------------------------------------------------------
    def test_05_post_visit_csat_feedback_rules(self):
        """Verify CSAT feedback is accepted only for Completed visits and prevents duplicates."""
        ok, _, appt_id = create_appointment({
            "appointment_code": "APT-9201",
            "patient_id": 1,
            "doctor_id": 1,
            "appointment_date": "2026-11-20",
            "time_slot": "11:30 AM",
            "reason": "Followup",
        })
        self.assertTrue(ok)

        # Attempting rating on Scheduled visit must fail
        ok, msg = submit_visit_feedback(appt_id, satisfaction_rating=5, feedback_notes="Great service")
        self.assertFalse(ok)
        self.assertIn("Completed", msg)

        # Mark appointment Completed via full record update
        record = get_appointment_by_id(appt_id)
        record["status"] = "Completed"
        update_ok, update_msg = update_appointment(appt_id, record)
        self.assertTrue(update_ok)

        # Submit valid CSAT feedback
        ok, msg = submit_visit_feedback(appt_id, satisfaction_rating=5, feedback_notes="Excellent doctor consultation")
        self.assertTrue(ok)

        appt = get_appointment_by_id(appt_id)
        self.assertEqual(appt["satisfaction_rating"], 5)
        self.assertIn("Excellent doctor consultation", appt["notes"])

        # Submitting duplicate feedback must be rejected
        ok, msg = submit_visit_feedback(appt_id, satisfaction_rating=4, feedback_notes="Second rating")
        self.assertFalse(ok)
        self.assertIn("already been recorded", msg)

    # -------------------------------------------------------------------------
    # 4. Billing Summary Financial Scoping & Sync
    # -------------------------------------------------------------------------
    def test_06_billing_summary_scoping_by_role(self):
        """Verify billing financial statistics are strictly scoped by user role."""
        # Create 2 appointments to generate invoices
        create_appointment({
            "appointment_code": "APT-9301",
            "patient_id": 1,
            "doctor_id": 1,
            "appointment_date": "2026-11-21",
            "time_slot": "10:00 AM",
            "reason": "Checkup 1",
        })
        create_appointment({
            "appointment_code": "APT-9302",
            "patient_id": 2,
            "doctor_id": 2,
            "appointment_date": "2026-11-22",
            "time_slot": "10:30 AM",
            "reason": "Checkup 2",
        })

        # 1. Admin gets total hospital statistics
        admin_stats = get_billing_summary_statistics()
        self.assertGreater(admin_stats["total_invoiced"], 0)

        # 2. Doctor stats: Only consultations assigned to doctor 1
        doc_stats = get_billing_summary_statistics(doctor_id=1)
        self.assertGreater(doc_stats["total_invoiced"], 0)
        self.assertLessEqual(doc_stats["total_invoiced"], admin_stats["total_invoiced"])

        # 3. Patient stats: Only bills for patient 1
        pat_stats = get_billing_summary_statistics(patient_id=1)
        self.assertGreater(pat_stats["total_invoiced"], 0)
        self.assertLessEqual(pat_stats["total_invoiced"], admin_stats["total_invoiced"])

    def test_07_sync_unbilled_appointments(self):
        """Verify unbilled completed appointments generate bills safely."""
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO appointments (appointment_code, patient_id, doctor_id, appointment_date, time_slot, status, reason, consultation_fee)
                VALUES ('APT-UNBILLED-01', 1, 1, '2026-10-20', '09:00 AM', 'Completed', 'Consultation for unbilled test', 800.0);
                """
            )
        # Run sync
        created_count = sync_unbilled_appointments()
        self.assertGreaterEqual(created_count, 1)

    # -------------------------------------------------------------------------
    # 5. User Settings & Profile Isolation
    # -------------------------------------------------------------------------
    def test_08_profile_isolation_no_admin_leakage(self):
        """Verify non-admin users load their own profile instead of hardcoded admin."""
        # Logged in as Doctor
        _, doc_user, _ = login("dr_arun", "Doctor@123")
        doc_profile = get_user_profile()
        self.assertIsNotNone(doc_profile)
        self.assertEqual(doc_profile["username"], "dr_arun")
        self.assertEqual(doc_profile["role"], "Doctor")
        self.assertIn("Rajesh Sharma", doc_profile["full_name"])

        # Logged in as Patient
        _, pat_user, _ = login("patient_aarav", "Patient@123")
        pat_profile = get_user_profile()
        self.assertIsNotNone(pat_profile)
        self.assertEqual(pat_profile["username"], "patient_aarav")
        self.assertEqual(pat_profile["role"], "Patient")
        self.assertIn("Aarav", pat_profile["full_name"])

        # Logged in as Admin
        _, admin_user, _ = login("admin", "Admin@123")
        admin_profile = get_user_profile()
        self.assertIsNotNone(admin_profile)
        self.assertIn(admin_profile["role"], ["Hospital Administrator", "Administrator"])

    # -------------------------------------------------------------------------
    # 6. Clinical Reports Doctor Scoping
    # -------------------------------------------------------------------------
    def test_09_clinical_reports_doctor_scoping(self):
        """Verify clinical reports filter by doctor_id when provided."""
        all_appts = get_appointments_by_status()
        doc_appts = get_appointments_by_status(doctor_id=1)

        total_all = all_appts.get("total", 0)
        total_doc = doc_appts.get("total", 0)
        self.assertLessEqual(total_doc, total_all)

        all_csat = get_patient_satisfaction_data()
        doc_csat = get_patient_satisfaction_data(doctor_id=1)
        self.assertLessEqual(len(doc_csat.get("labels", [])), len(all_csat.get("labels", [])))

    # -------------------------------------------------------------------------
    # 7. TQM Toolkit Role Access Control
    # -------------------------------------------------------------------------
    def test_10_tqm_toolkit_role_restrictions(self):
        """Verify TQM view gives 7 tabs to Admin, defect checksheet to Staff, restricted to others."""
        # 1. Admin access: All 7 tab buttons enabled
        login("admin", "Admin@123")
        admin_tqm = TQMView(self.root)
        self.root.update()
        self.assertIsNotNone(admin_tqm.tabview)
        self.assertEqual(len(admin_tqm.tab_buttons), 7)
        for btn in admin_tqm.tab_buttons.values():
            self.assertEqual(btn.cget("state"), "normal")
        admin_tqm.destroy()
        self.root.update()

        # 2. Staff access: Only Defect Checksheet button is normal, other 6 disabled
        login("staff_reception", "Staff@123")
        staff_tqm = TQMView(self.root)
        self.root.update()
        self.assertIsNotNone(staff_tqm.tabview)
        self.assertEqual(len(staff_tqm.tab_buttons), 7)
        self.assertEqual(staff_tqm.tab_buttons["4. Defect Checksheet Log"].cget("state"), "normal")
        for k, btn in staff_tqm.tab_buttons.items():
            if k != "4. Defect Checksheet Log":
                self.assertEqual(btn.cget("state"), "disabled")
        staff_tqm.destroy()
        self.root.update()

        # 3. Doctor restricted: no tabview
        login("dr_arun", "Doctor@123")
        doc_tqm = TQMView(self.root)
        self.root.update()
        self.assertIsNone(doc_tqm.tabview)
        doc_tqm.destroy()
        self.root.update()

        # 4. Patient restricted: no tabview
        login("patient_aarav", "Patient@123")
        pat_tqm = TQMView(self.root)
        self.root.update()
        self.assertIsNone(pat_tqm.tabview)
        pat_tqm.destroy()
        self.root.update()


if __name__ == "__main__":
    unittest.main()
