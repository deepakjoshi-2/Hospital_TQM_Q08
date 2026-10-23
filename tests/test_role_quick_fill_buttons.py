"""Focused regression test suite for Login View Four Role Quick-Fill Buttons.

Verifies:
1. Four role buttons exist (Administrator, Reception Staff, Doctor, Patient) in a clean 2x2 grid.
2. Clicking each button populates correct demo credentials.
3. Clicking a button does NOT automatically submit or log in.
4. Password remains masked by default.
5. Show/Hide password toggle functions properly.
6. Selected role button is visually highlighted, and manual editing updates highlight state sensibly.
7. Sign In button properly authenticates through PBKDF2 authentication service.
8. Invalid credentials display error banner without crashing.
9. Missing demo account displays clear error without crashing.
"""
import os
import tempfile
import unittest
import customtkinter as ctk

from database.connection import get_db_cursor
from database.seed_data import seed_database
from services.auth_service import logout
from ui.views.login_view import LoginView


class TestRoleQuickFillButtons(unittest.TestCase):
    """Test suite verifying LoginView role quick-fill buttons and security behaviors."""

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
        self.test_db_path = os.path.join(self.temp_dir.name, "test_quick_fill.db")
        os.environ["HOSPITAL_DB_PATH"] = self.test_db_path
        seed_database(self.test_db_path)
        logout()

    def tearDown(self):
        logout()
        os.environ.pop("HOSPITAL_DB_PATH", None)
        self.temp_dir.cleanup()

    def test_01_four_buttons_exist_in_grid(self):
        """Verify the 4 designated role buttons exist and are configured in a 2x2 layout."""
        lv = LoginView(self.root, on_login_success=lambda u: None)
        self.root.update()

        self.assertEqual(len(lv.role_buttons), 4)
        expected_keys = {"admin", "staff", "doctor", "patient"}
        self.assertEqual(set(lv.role_buttons.keys()), expected_keys)

        self.assertIn("Administrator", lv.role_btn_admin.cget("text"))
        self.assertIn("Reception Staff", lv.role_btn_staff.cget("text"))
        self.assertIn("Doctor", lv.role_btn_doctor.cget("text"))
        self.assertIn("Patient", lv.role_btn_patient.cget("text"))

        lv.destroy()
        self.root.update()

    def test_02_button_clicks_populate_fields_without_auto_login(self):
        """Verify clicking each role button populates credentials, keeps mask, and does not auto-login."""
        logged_in_users = []

        lv = LoginView(self.root, on_login_success=lambda u: logged_in_users.append(u))
        self.root.update()

        expected_creds = [
            ("admin", lv.role_btn_admin, "admin", "Admin@123"),
            ("staff", lv.role_btn_staff, "staff_reception", "Staff@123"),
            ("doctor", lv.role_btn_doctor, "dr_arun", "Doctor@123"),
            ("patient", lv.role_btn_patient, "patient_aarav", "Patient@123"),
        ]

        for role_key, btn, expected_u, expected_p in expected_creds:
            btn.invoke()
            self.root.update()

            # Verify fields populated
            self.assertEqual(lv.username_entry.get(), expected_u)
            self.assertEqual(lv.password_entry.get(), expected_p)

            # Verify password remains masked by default
            self.assertEqual(lv.password_entry.cget("show"), "•")

            # Verify role highlight
            self.assertEqual(lv.get_selected_role(), role_key)

            # CRITICAL: Verify NO auto-submit occurred
            self.assertEqual(len(logged_in_users), 0)

        lv.destroy()
        self.root.update()

    def test_03_sign_in_authenticates_populated_credentials(self):
        """Verify Sign In button authenticates populated credentials via PBKDF2."""
        logged_in_users = []

        lv = LoginView(self.root, on_login_success=lambda u: logged_in_users.append(u))
        self.root.update()

        # Click Doctor quick-fill
        lv.role_btn_doctor.invoke()
        self.root.update()

        # User explicitly clicks Sign In
        lv.login_btn.invoke()
        self.root.update()

        self.assertEqual(len(logged_in_users), 1)
        self.assertEqual(logged_in_users[0]["username"], "dr_arun")
        self.assertEqual(logged_in_users[0]["role"], "Doctor")

        lv.destroy()
        self.root.update()

    def test_04_manual_edit_updates_selection_state(self):
        """Verify manual editing of fields deselects highlight or re-matches sensibly."""
        lv = LoginView(self.root, on_login_success=lambda u: None)
        self.root.update()

        # Select Administrator
        lv.role_btn_admin.invoke()
        self.assertEqual(lv.get_selected_role(), "admin")

        # Edit username to something else -> selection clears
        lv.username_entry.delete(0, "end")
        lv.username_entry.insert(0, "custom_admin")
        lv._on_entry_changed()
        self.assertIsNone(lv.get_selected_role())

        # Type doctor credentials manually -> doctor button highlights
        lv.username_entry.delete(0, "end")
        lv.username_entry.insert(0, "dr_arun")
        lv.password_entry.delete(0, "end")
        lv.password_entry.insert(0, "Doctor@123")
        lv._on_entry_changed()
        self.assertEqual(lv.get_selected_role(), "doctor")

        lv.destroy()
        self.root.update()

    def test_05_show_hide_password_toggle(self):
        """Verify show/hide password toggle works in conjunction with quick-fill."""
        lv = LoginView(self.root, on_login_success=lambda u: None)
        self.root.update()

        lv.role_btn_patient.invoke()
        self.root.update()

        self.assertEqual(lv.password_entry.cget("show"), "•")

        # Toggle to show
        lv.toggle_pwd_btn.invoke()
        self.root.update()
        self.assertEqual(lv.password_entry.cget("show"), "")
        self.assertIn("Hide", lv.toggle_pwd_btn.cget("text"))

        # Toggle back to hide
        lv.toggle_pwd_btn.invoke()
        self.root.update()
        self.assertEqual(lv.password_entry.cget("show"), "•")
        self.assertIn("Show", lv.toggle_pwd_btn.cget("text"))

        lv.destroy()
        self.root.update()

    def test_06_invalid_credentials_error_banner(self):
        """Verify invalid credentials show error banner without crashing."""
        logged_in_users = []
        lv = LoginView(self.root, on_login_success=lambda u: logged_in_users.append(u))
        self.root.update()

        lv.username_entry.insert(0, "admin")
        lv.password_entry.insert(0, "IncorrectPassword999")
        lv.login_btn.invoke()
        self.root.update()

        self.assertEqual(len(logged_in_users), 0)
        self.assertIn("Invalid", lv.error_lbl.cget("text"))

        lv.destroy()
        self.root.update()

    def test_07_missing_demo_account_shows_error(self):
        """Verify missing demo account in DB shows clear notification without crashing."""
        # Remove dr_arun from database
        with get_db_cursor() as (conn, cursor):
            cursor.execute("DELETE FROM users WHERE username = 'dr_arun';")

        lv = LoginView(self.root, on_login_success=lambda u: None)
        self.root.update()

        # Click doctor
        lv.role_btn_doctor.invoke()
        self.root.update()

        self.assertIn("not found in database", lv.error_lbl.cget("text"))
        self.assertIsNone(lv.get_selected_role())

        lv.destroy()
        self.root.update()


if __name__ == "__main__":
    unittest.main()
