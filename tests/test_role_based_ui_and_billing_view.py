"""Unit and UI integration test suite for Role-Based Navigation, LoginView, BillingView, and Confirmation modals."""
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
from database.seed_data import seed_database
from services.auth_service import authenticate_user, login, logout, set_current_user
from services.appointment_service import create_appointment
from services.billing_service import create_bill_for_appointment, record_payment
from ui.app import HospitalApp
from ui.components.appointment_modals import AppointmentConfirmationModal
from ui.components.billing_modals import RecordPaymentModal, ReceiptViewModal
from ui.components.notification_modal import NotificationCenterModal
from ui.views.billing_view import BillingView
from ui.views.login_view import LoginView
from ui.views.user_management_view import UserManagementView


class TestRoleBasedUIAndBillingView(unittest.TestCase):
    """Test suite verifying role-based navigation menus, LoginView, BillingView, and Modals."""

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
        self.test_db_path = os.path.join(self.temp_dir.name, "test_ui_rbac.db")
        os.environ["HOSPITAL_DB_PATH"] = self.test_db_path
        seed_database(self.test_db_path)
        logout()

    def tearDown(self):
        logout()
        os.environ.pop("HOSPITAL_DB_PATH", None)
        self.temp_dir.cleanup()

    def test_01_role_based_sidebar_menus(self):
        """Verify sidebar navigation buttons adapt dynamically to the logged-in role."""
        app = HospitalApp()
        self.root.update()

        # 1. Administrator Menu Check (9 buttons)
        admin_keys = set(app.nav_buttons.keys())
        expected_admin = {"Dashboard", "Patients", "Doctors", "Appointments", "Reports", "Billing", "TQM", "Users", "Settings"}
        self.assertEqual(admin_keys, expected_admin)

        # 2. Staff Menu Check (6 buttons)
        _, staff_u, _ = login("staff_reception", "Staff@123")
        app.on_login_success(staff_u)
        self.root.update()
        staff_keys = set(app.nav_buttons.keys())
        expected_staff = {"Dashboard", "Patients", "Doctors", "Appointments", "Billing", "Settings"}
        self.assertEqual(staff_keys, expected_staff)

        # 3. Doctor Menu Check (5 buttons)
        _, doc_u, _ = login("dr_arun", "Doctor@123")
        app.on_login_success(doc_u)
        self.root.update()
        doc_keys = set(app.nav_buttons.keys())
        expected_doctor = {"Appointments", "Patients", "Reports", "Billing", "Settings"}
        self.assertEqual(doc_keys, expected_doctor)

        # 4. Patient Menu Check (4 buttons)
        _, pat_u, _ = login("patient_aarav", "Patient@123")
        app.on_login_success(pat_u)
        self.root.update()
        pat_keys = set(app.nav_buttons.keys())
        expected_patient = {"Appointments", "Doctors", "Billing", "Settings"}
        self.assertEqual(pat_keys, expected_patient)

        app.destroy()
        self.root.update()

    def test_02_billing_view_kpis_and_filtering(self):
        """Verify BillingView renders metric cards, table rows, and filters correctly."""
        login("admin", "Admin@123")
        bv = BillingView(self.root)
        self.root.update()

        # Check KPI cards exist and are formatted
        self.assertTrue(bv.card_invoiced.cget("text").startswith("Rs."))
        self.assertTrue(bv.card_collected.cget("text").startswith("Rs."))
        self.assertTrue(bv.card_outstanding.cget("text").startswith("Rs."))

        # Filter by Paid status
        bv.status_filter_menu.set("Paid")
        bv._on_filter_changed()
        self.root.update()

        # Filter by Unpaid status
        bv.status_filter_menu.set("Unpaid")
        bv._on_filter_changed()
        self.root.update()

        bv.destroy()
        self.root.update()

    def test_03_login_view_authentication(self):
        """Verify LoginView credentials submission and error banner."""
        logged_in_user = [None]

        def on_success(user):
            logged_in_user[0] = user

        lv = LoginView(self.root, on_login_success=on_success)
        self.root.update()

        # Fill invalid credentials
        lv._fill_and_login("admin", "WrongPassword")
        self.root.update()
        self.assertIn("Invalid", lv.error_lbl.cget("text"))
        self.assertIsNone(logged_in_user[0])

        # Fill valid credentials via quick demo switcher
        lv._fill_and_login("admin", "Admin@123")
        self.root.update()
        self.assertIsNotNone(logged_in_user[0])
        self.assertEqual(logged_in_user[0]["username"], "admin")

        lv.destroy()
        self.root.update()

    def test_04_user_management_view(self):
        """Verify UserManagementView loads users list and handles status toggles."""
        login("admin", "Admin@123")
        uv = UserManagementView(self.root)
        self.root.update()

        # Verify scroll rows contain children
        row_count = len(uv.rows_scroll.winfo_children())
        self.assertGreaterEqual(row_count, 4, "Expected at least 4 seeded role accounts.")

        uv.destroy()
        self.root.update()

    def test_05_modals_instantiation(self):
        """Verify modals can be instantiated and dismissed without errors."""
        login("admin", "Admin@123")

        # 1. Appointment Confirmation Modal
        conf_modal = AppointmentConfirmationModal(self.root, appointment_id=1)
        self.root.update()
        self.assertTrue(conf_modal.winfo_exists())
        conf_modal.destroy()
        self.root.update()

        # 2. Notification Center Modal
        notif_modal = NotificationCenterModal(self.root, user_id=1)
        self.root.update()
        self.assertTrue(notif_modal.winfo_exists())
        notif_modal.destroy()
        self.root.update()


if __name__ == "__main__":
    unittest.main()
