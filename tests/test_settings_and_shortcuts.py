"""Unit and integration test suite for User Profile Settings, Validation, Persistence, and Shortcut Safety."""
import tkinter as tk
import unittest
import customtkinter as ctk

from database.connection import get_db_connection
from services.profile_service import (
    ALLOWED_ROLES,
    ALLOWED_SCALING,
    ALLOWED_THEMES,
    ALLOWED_VIEWS,
    get_user_profile,
    update_user_profile,
    validate_profile_data,
)


class TestSettingsAndShortcuts(unittest.TestCase):
    """Test suite verifying User Profile Settings, validation engine, and shortcut safety."""

    @classmethod
    def setUpClass(cls):
        """Record baseline profile and entity record counts."""
        cls.initial_profile = get_user_profile("deepak_admin")
        with get_db_connection() as conn:
            cls.baseline_patients = conn.execute("SELECT COUNT(*) FROM patients;").fetchone()[0]
            cls.baseline_doctors = conn.execute("SELECT COUNT(*) FROM doctors;").fetchone()[0]
            cls.baseline_appointments = conn.execute("SELECT COUNT(*) FROM appointments;").fetchone()[0]

    def tearDown(self):
        """Restore initial user profile if modified during tests."""
        if self.initial_profile:
            update_user_profile("deepak_admin", self.initial_profile)

    def test_01_get_user_profile_returns_valid_record(self):
        """Verify profile retrieval loads expected schema attributes from SQLite."""
        prof = get_user_profile("deepak_admin")
        self.assertIsNotNone(prof)
        self.assertEqual(prof["username"], "deepak_admin")
        self.assertIn("full_name", prof)
        self.assertIn("role", prof)
        self.assertIn("email", prof)
        self.assertIn("phone", prof)
        self.assertIn("theme_preference", prof)
        self.assertIn("scaling_factor", prof)
        self.assertIn("default_view", prof)
        self.assertIn("notifications_enabled", prof)

    def test_02_validation_rejects_invalid_inputs(self):
        """Verify validation catches empty, malformed, or out-of-range fields."""
        valid_template = {
            "full_name": "Deepak Joshi",
            "role": "Hospital Administrator",
            "email": "deepak.joshi.tqm@hospital.demo",
            "phone": "+91 98765 43210",
            "theme_preference": "Dark",
            "scaling_factor": "100%",
            "default_view": "Dashboard",
            "notifications_enabled": 1,
        }

        # 1. Missing Full Name
        d = valid_template.copy()
        d["full_name"] = ""
        ok, msg = validate_profile_data(d)
        self.assertFalse(ok)
        self.assertIn("Full Name", msg)

        # 2. Too short Full Name
        d = valid_template.copy()
        d["full_name"] = "A"
        ok, msg = validate_profile_data(d)
        self.assertFalse(ok)
        self.assertIn("2 characters", msg)

        # 3. Invalid Role
        d = valid_template.copy()
        d["role"] = "Unauthorized Guest"
        ok, msg = validate_profile_data(d)
        self.assertFalse(ok)
        self.assertIn("Role must be one of", msg)

        # 4. Invalid Email
        d = valid_template.copy()
        d["email"] = "not-an-email"
        ok, msg = validate_profile_data(d)
        self.assertFalse(ok)
        self.assertIn("email", msg.lower())

        # 5. Invalid Phone (<10 digits)
        d = valid_template.copy()
        d["phone"] = "12345"
        ok, msg = validate_profile_data(d)
        self.assertFalse(ok)
        self.assertIn("Phone Number", msg)

        # 6. Invalid Theme
        d = valid_template.copy()
        d["theme_preference"] = "NeonCyberpunk"
        ok, msg = validate_profile_data(d)
        self.assertFalse(ok)
        self.assertIn("Theme", msg)

        # 7. Invalid Scaling Factor
        d = valid_template.copy()
        d["scaling_factor"] = "250%"
        ok, msg = validate_profile_data(d)
        self.assertFalse(ok)
        self.assertIn("Scaling", msg)

        # 8. Invalid Default View
        d = valid_template.copy()
        d["default_view"] = "NonExistentScreen"
        ok, msg = validate_profile_data(d)
        self.assertFalse(ok)
        self.assertIn("Default View", msg)

    def test_03_profile_update_and_sqlite_persistence(self):
        """Verify updating profile fields persists directly into SQLite database."""
        test_update = {
            "full_name": "Dr. Deepak Joshi",
            "role": "Chief Medical Officer",
            "email": "cmo.deepak@hospital.demo",
            "phone": "+91 91234 56789",
            "theme_preference": "Light",
            "scaling_factor": "110%",
            "default_view": "Reports",
            "notifications_enabled": 0,
        }

        success, msg = update_user_profile("deepak_admin", test_update)
        self.assertTrue(success, f"Profile update failed: {msg}")

        # Verify persisted values in SQLite
        updated_prof = get_user_profile("deepak_admin")
        self.assertEqual(updated_prof["full_name"], "Dr. Deepak Joshi")
        self.assertEqual(updated_prof["role"], "Chief Medical Officer")
        self.assertEqual(updated_prof["email"], "cmo.deepak@hospital.demo")
        self.assertEqual(updated_prof["phone"], "+91 91234 56789")
        self.assertEqual(updated_prof["theme_preference"], "Light")
        self.assertEqual(updated_prof["scaling_factor"], "110%")
        self.assertEqual(updated_prof["default_view"], "Reports")
        self.assertEqual(updated_prof["notifications_enabled"], 0)

    def test_04_text_input_conflict_detection_logic(self):
        """Verify helper identifies text entry widgets so shortcuts like Ctrl+A don't disrupt typing."""
        from ui.app import HospitalApp

        # Test with a mock / headless instance
        root = ctk.CTk()
        try:
            entry_widget = tk.Entry(root)
            text_widget = tk.Text(root)
            button_widget = tk.Button(root)
            frame_widget = tk.Frame(root)

            app = HospitalApp()
            try:
                # Text inputs must return True
                self.assertTrue(app._is_text_widget_focused(type("MockEvent", (), {"widget": entry_widget})()))
                self.assertTrue(app._is_text_widget_focused(type("MockEvent", (), {"widget": text_widget})()))

                # Buttons and frames must return False
                self.assertFalse(app._is_text_widget_focused(type("MockEvent", (), {"widget": button_widget})()))
                self.assertFalse(app._is_text_widget_focused(type("MockEvent", (), {"widget": frame_widget})()))
                self.assertFalse(app._is_text_widget_focused(type("MockEvent", (), {"widget": None})()))
            finally:
                app.destroy()
        finally:
            root.destroy()

    def test_05_database_integrity_preserved(self):
        """Ensure all original database records remain intact."""
        with get_db_connection() as conn:
            p_count = conn.execute("SELECT COUNT(*) FROM patients;").fetchone()[0]
            d_count = conn.execute("SELECT COUNT(*) FROM doctors;").fetchone()[0]
            a_count = conn.execute("SELECT COUNT(*) FROM appointments;").fetchone()[0]

            self.assertEqual(p_count, self.baseline_patients, "Patient count must remain untouched.")
            self.assertEqual(d_count, self.baseline_doctors, "Doctor count must remain untouched.")
            self.assertEqual(a_count, self.baseline_appointments, "Appointment count must remain untouched.")


if __name__ == "__main__":
    unittest.main()
