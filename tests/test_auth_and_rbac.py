"""Unit tests for Authentication, PBKDF2 Password Hashing, Session Management, and RBAC."""
import os
import tempfile
import unittest

from config.constants import (
    ROLE_ADMIN,
    ROLE_DOCTOR,
    ROLE_PATIENT,
    ROLE_STAFF,
)
from database.connection import get_db_connection
from database.seed_data import seed_database
from services.auth_service import (
    authenticate_user,
    create_user,
    delete_user,
    get_all_users,
    get_current_user,
    get_user_by_id,
    get_user_by_username,
    has_permission,
    hash_password,
    is_admin,
    is_doctor,
    is_patient,
    is_staff,
    login,
    logout,
    reset_user_password,
    set_current_user,
    toggle_user_status,
    update_user,
    verify_password,
)


class TestAuthAndRBAC(unittest.TestCase):
    """Test suite verifying PBKDF2 cryptography, role permissions, and user management."""

    def setUp(self):
        """Set up an isolated database with seeded demo records for testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = os.path.join(self.temp_dir.name, "test_auth.db")
        os.environ["HOSPITAL_DB_PATH"] = self.test_db_path
        seed_database(self.test_db_path)
        logout()

    def tearDown(self):
        """Clean up active session and temporary test directory."""
        logout()
        os.environ.pop("HOSPITAL_DB_PATH", None)
        self.temp_dir.cleanup()

    def test_01_password_hashing_and_verification(self):
        """Verify PBKDF2-HMAC-SHA256 generates secure hashes and verifies correctly."""
        raw_pwd = "SecurePassword@2026"
        pwd_hash, salt = hash_password(raw_pwd)

        self.assertIsInstance(pwd_hash, str)
        self.assertEqual(len(pwd_hash), 64, "PBKDF2 SHA-256 hex digest must be 64 characters.")
        self.assertIsInstance(salt, str)
        self.assertEqual(len(salt), 32, "Salt must be 16 bytes (32 hex characters).")

        # Positive match
        self.assertTrue(verify_password(raw_pwd, pwd_hash, salt))

        # Negative matches
        self.assertFalse(verify_password("WrongPassword", pwd_hash, salt))
        self.assertFalse(verify_password("", pwd_hash, salt))
        self.assertFalse(verify_password(raw_pwd, pwd_hash, "different_salt_1234567890123456"))

        # Distinct salts generate different hashes for same password
        hash2, salt2 = hash_password(raw_pwd)
        self.assertNotEqual(salt, salt2)
        self.assertNotEqual(pwd_hash, hash2)

    def test_02_authenticate_seeded_accounts(self):
        """Verify authentication for all 4 seeded role accounts."""
        # 1. Administrator
        ok, user, msg = authenticate_user("admin", "Admin@123")
        self.assertTrue(ok)
        self.assertIsNotNone(user)
        self.assertEqual(user["role"], ROLE_ADMIN)
        self.assertNotIn("password_hash", user, "Password hash must not be exposed in session dictionary.")

        # 2. Staff
        ok, user, msg = authenticate_user("staff_reception", "Staff@123")
        self.assertTrue(ok)
        self.assertEqual(user["role"], ROLE_STAFF)

        # 3. Doctor
        ok, user, msg = authenticate_user("dr_arun", "Doctor@123")
        self.assertTrue(ok)
        self.assertEqual(user["role"], ROLE_DOCTOR)
        self.assertIsNotNone(user.get("linked_doctor_id"))

        # 4. Patient
        ok, user, msg = authenticate_user("patient_aarav", "Patient@123")
        self.assertTrue(ok)
        self.assertEqual(user["role"], ROLE_PATIENT)
        self.assertIsNotNone(user.get("linked_patient_id"))

    def test_03_authenticate_failures(self):
        """Verify authentication rejects wrong passwords and non-existent usernames."""
        # Wrong password
        ok, user, msg = authenticate_user("admin", "WrongPass123")
        self.assertFalse(ok)
        self.assertIsNone(user)
        self.assertIn("Invalid", msg)

        # Non-existent user
        ok, user, msg = authenticate_user("ghost_user", "AnyPassword")
        self.assertFalse(ok)
        self.assertIsNone(user)
        self.assertIn("Invalid", msg)

        # Empty credentials
        ok, user, msg = authenticate_user("", "")
        self.assertFalse(ok)
        self.assertIn("both", msg)

    def test_04_session_management(self):
        """Verify login, active session state, and logout workflow."""
        self.assertIsNone(get_current_user())

        # Successful login
        ok, user, msg = login("admin", "Admin@123")
        self.assertTrue(ok)
        self.assertEqual(get_current_user()["username"], "admin")
        self.assertTrue(is_admin())

        # Logout
        logout()
        self.assertIsNone(get_current_user())

    def test_05_role_permission_matrix(self):
        """Verify granular permission boundaries across all 4 roles."""
        admin_u = {"role": ROLE_ADMIN}
        staff_u = {"role": ROLE_STAFF}
        doc_u = {"role": ROLE_DOCTOR}
        pat_u = {"role": ROLE_PATIENT}

        # Administrator: has full access to everything
        self.assertTrue(has_permission("view_dashboard", admin_u))
        self.assertTrue(has_permission("manage_doctors", admin_u))
        self.assertTrue(has_permission("manage_users", admin_u))
        self.assertTrue(has_permission("manage_tqm", admin_u))
        self.assertTrue(is_admin(admin_u))

        # Staff: cannot manage doctors, tqm, or users; can manage patients & billing
        self.assertTrue(has_permission("view_dashboard", staff_u))
        self.assertTrue(has_permission("manage_patients", staff_u))
        self.assertTrue(has_permission("record_payments", staff_u))
        self.assertFalse(has_permission("manage_doctors", staff_u))
        self.assertFalse(has_permission("manage_users", staff_u))
        self.assertFalse(has_permission("view_tqm", staff_u))
        self.assertTrue(is_staff(staff_u))

        # Doctor: restricted to appointments and clinical reports; no admin or billing edit
        self.assertFalse(has_permission("view_dashboard", doc_u))
        self.assertTrue(has_permission("view_appointments", doc_u))
        self.assertTrue(has_permission("view_reports", doc_u))
        self.assertFalse(has_permission("manage_billing", doc_u))
        self.assertFalse(has_permission("record_payments", doc_u))
        self.assertFalse(has_permission("all_appointments_access", doc_u))
        self.assertTrue(is_doctor(doc_u))

        # Patient: restricted to view doctors, appointments, and bills; no dashboard or management
        self.assertFalse(has_permission("view_dashboard", pat_u))
        self.assertTrue(has_permission("view_doctors", pat_u))
        self.assertTrue(has_permission("view_appointments", pat_u))
        self.assertTrue(has_permission("view_billing", pat_u))
        self.assertFalse(has_permission("manage_patients", pat_u))
        self.assertFalse(has_permission("all_appointments_access", pat_u))
        self.assertTrue(is_patient(pat_u))

    def test_06_user_crud_operations(self):
        """Verify Administrator user creation, update, password reset, and status toggle."""
        # 1. Create new user
        new_user_data = {
            "username": "nurse_priya",
            "email": "priya.n@hospital.demo",
            "password": "NursePass@123",
            "role": ROLE_STAFF,
            "full_name": "Priya Nair",
        }
        ok, msg, new_id = create_user(new_user_data)
        self.assertTrue(ok, msg)
        self.assertIsNotNone(new_id)

        # Verify created in DB and can authenticate
        created = get_user_by_id(new_id)
        self.assertEqual(created["username"], "nurse_priya")
        self.assertEqual(created["role"], ROLE_STAFF)

        auth_ok, auth_user, _ = authenticate_user("nurse_priya", "NursePass@123")
        self.assertTrue(auth_ok)

        # 2. Duplicate username rejection
        ok, msg, _ = create_user(new_user_data)
        self.assertFalse(ok)
        self.assertIn("already taken", msg)

        # 3. Update user
        update_ok, update_msg = update_user(new_id, {
            "full_name": "Priya Nair (Senior Nurse)",
            "email": "priya.senior@hospital.demo",
            "role": ROLE_STAFF,
            "linked_patient_id": None,
            "linked_doctor_id": None,
        })
        self.assertTrue(update_ok, update_msg)
        updated = get_user_by_id(new_id)
        self.assertEqual(updated["full_name"], "Priya Nair (Senior Nurse)")
        self.assertEqual(updated["email"], "priya.senior@hospital.demo")

        # 4. Toggle Status (Deactivate / Reactivate)
        toggle_ok, toggle_msg = toggle_user_status(new_id)
        self.assertTrue(toggle_ok)
        self.assertIn("deactivated", toggle_msg)

        # Deactivated user cannot login
        auth_ok2, _, block_msg = authenticate_user("nurse_priya", "NursePass@123")
        self.assertFalse(auth_ok2)
        self.assertIn("disabled", block_msg)

        # Reactivate
        toggle_ok2, toggle_msg2 = toggle_user_status(new_id)
        self.assertTrue(toggle_ok2)
        self.assertIn("activated", toggle_msg2)

        # 5. Reset Password
        reset_ok, reset_msg = reset_user_password(new_id, "NewNursePass@456")
        self.assertTrue(reset_ok)
        auth_ok3, _, _ = authenticate_user("nurse_priya", "NewNursePass@456")
        self.assertTrue(auth_ok3)

        # 6. Delete user
        del_ok, del_msg = delete_user(new_id)
        self.assertTrue(del_ok)
        self.assertIsNone(get_user_by_id(new_id))

    def test_07_prevent_deleting_active_or_sole_admin(self):
        """Verify safeguards against self-deletion and sole admin account deletion."""
        admin_u = get_user_by_username("admin")
        self.assertIsNotNone(admin_u)

        # Attempt to delete while logged in as admin
        login("admin", "Admin@123")
        del_ok, del_msg = delete_user(admin_u["id"])
        self.assertFalse(del_ok)
        self.assertIn("cannot delete your own", del_msg)

        # Attempt to toggle status while logged in
        tog_ok, tog_msg = toggle_user_status(admin_u["id"])
        self.assertFalse(tog_ok)
        self.assertIn("cannot deactivate your own", tog_msg)

        # Logout and attempt to delete sole admin
        logout()
        del_ok2, del_msg2 = delete_user(admin_u["id"])
        self.assertFalse(del_ok2)
        self.assertIn("sole Administrator", del_msg2)


if __name__ == "__main__":
    unittest.main()
