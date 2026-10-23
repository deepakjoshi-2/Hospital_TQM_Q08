"""Authentication, session management, and Role-Based Access Control (RBAC) service.
Implements cryptographically secure PBKDF2 password hashing with salt,
session state tracking, permission verification, and user management.
"""
import hashlib
import re
import secrets
from typing import Dict, List, Optional, Tuple

from config.constants import (
    ROLE_ADMIN,
    ROLE_DOCTOR,
    ROLE_PATIENT,
    ROLE_STAFF,
    USER_ROLES,
)
from database.connection import get_db_connection, get_db_cursor

# In-memory active session state
_current_user: Optional[Dict] = None


# ==============================================================================
# 1. Cryptographic Password Hashing & Verification
# ==============================================================================

def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Generate salted PBKDF2-HMAC-SHA256 password hash with 100,000 iterations.
    
    Returns:
        (hex_hash, salt_hex)
    """
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return key.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify raw password against stored PBKDF2 hash using timing-safe comparison."""
    if not password or not stored_hash or not salt:
        return False
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, stored_hash)


# ==============================================================================
# 2. Authentication & Session State Management
# ==============================================================================

def authenticate_user(username: str, password: str) -> Tuple[bool, Optional[Dict], str]:
    """Authenticate user credentials against SQLite users table.
    
    Returns:
        (success, user_dict, status_message)
    """
    uname = str(username or "").strip()
    pwd = str(password or "")

    if not uname or not pwd:
        return False, None, "Please enter both username and password."

    try:
        with get_db_connection() as conn:
            query = """
                SELECT u.id, u.username, u.email, u.password_hash, u.salt, u.role, u.full_name,
                       u.linked_patient_id, u.linked_doctor_id, u.is_active,
                       p.patient_code, p.first_name AS pat_first_name, p.last_name AS pat_last_name,
                       d.doctor_code, d.first_name AS doc_first_name, d.last_name AS doc_last_name, d.specialization
                FROM users u
                LEFT JOIN patients p ON u.linked_patient_id = p.id
                LEFT JOIN doctors d ON u.linked_doctor_id = d.id
                WHERE LOWER(u.username) = LOWER(?);
            """
            row = conn.execute(query, (uname,)).fetchone()
            if not row:
                return False, None, "Invalid username or password."

            user = dict(row)

            if not user.get("is_active"):
                return False, None, "Account is disabled. Please contact Hospital Administrator."

            if not verify_password(pwd, user["password_hash"], user["salt"]):
                return False, None, "Invalid username or password."

            # Don't keep hash and salt in session user dictionary
            user_safe = {k: v for k, v in user.items() if k not in ("password_hash", "salt")}
            return True, user_safe, f"Welcome back, {user['full_name']}!"

    except Exception as e:
        return False, None, f"Authentication error: {e}"


def get_current_user() -> Optional[Dict]:
    """Retrieve current logged-in user session."""
    global _current_user
    return _current_user


def set_current_user(user: Optional[Dict]) -> None:
    """Set active user session."""
    global _current_user
    _current_user = user


def login(username: str, password: str) -> Tuple[bool, Optional[Dict], str]:
    """Perform login and record active user session upon success."""
    success, user, message = authenticate_user(username, password)
    if success and user:
        set_current_user(user)
    return success, user, message


def logout() -> None:
    """Clear active user session."""
    global _current_user
    _current_user = None


# ==============================================================================
# 3. Role-Based Permissions & Access Evaluation
# ==============================================================================

# Permission Matrix definition
ROLE_PERMISSIONS = {
    ROLE_ADMIN: {
        "view_dashboard": True,
        "view_patients": True,
        "manage_patients": True,
        "view_doctors": True,
        "manage_doctors": True,
        "view_appointments": True,
        "manage_appointments": True,
        "view_reports": True,
        "view_billing": True,
        "manage_billing": True,
        "record_payments": True,
        "issue_receipts": True,
        "view_tqm": True,
        "manage_tqm": True,
        "view_users": True,
        "manage_users": True,
        "view_settings": True,
        "all_appointments_access": True,
    },
    ROLE_STAFF: {
        "view_dashboard": True,
        "view_patients": True,
        "manage_patients": True,
        "view_doctors": True,
        "manage_doctors": False,
        "view_appointments": True,
        "manage_appointments": True,
        "view_reports": False,
        "view_billing": True,
        "manage_billing": True,
        "record_payments": True,
        "issue_receipts": True,
        "view_tqm": False,
        "manage_tqm": False,
        "view_users": False,
        "manage_users": False,
        "view_settings": True,
        "all_appointments_access": True,
    },
    ROLE_DOCTOR: {
        "view_dashboard": False,
        "view_patients": True,
        "manage_patients": False,
        "view_doctors": False,
        "manage_doctors": False,
        "view_appointments": True,
        "manage_appointments": True,  # For status updates (Complete consultation)
        "view_reports": True,
        "view_billing": True,         # View consultation fee/billing status
        "manage_billing": False,
        "record_payments": False,
        "issue_receipts": False,
        "view_tqm": False,
        "manage_tqm": False,
        "view_users": False,
        "manage_users": False,
        "view_settings": True,
        "all_appointments_access": False,  # Restricted to linked doctor ID
    },
    ROLE_PATIENT: {
        "view_dashboard": False,
        "view_patients": False,
        "manage_patients": False,
        "view_doctors": True,         # Can view physicians roster to choose doctor
        "manage_doctors": False,
        "view_appointments": True,    # Only own appointments
        "manage_appointments": True,  # Can book self or cancel self
        "view_reports": False,
        "view_billing": True,         # Can view own invoices & receipts
        "manage_billing": False,
        "record_payments": False,
        "issue_receipts": False,
        "view_tqm": False,
        "manage_tqm": False,
        "view_users": False,
        "manage_users": False,
        "view_settings": True,
        "all_appointments_access": False,  # Restricted to linked patient ID
    },
}


def get_user_role(user: Optional[Dict] = None) -> str:
    """Return role string for given user or current active user."""
    u = user or get_current_user()
    if not u:
        return ROLE_STAFF  # Fallback
    return u.get("role", ROLE_STAFF)


def has_permission(permission: str, user: Optional[Dict] = None) -> bool:
    """Verify if user has given permission flag."""
    role = get_user_role(user)
    role_perms = ROLE_PERMISSIONS.get(role, {})
    return bool(role_perms.get(permission, False))


def is_admin(user: Optional[Dict] = None) -> bool:
    return get_user_role(user) == ROLE_ADMIN


def is_staff(user: Optional[Dict] = None) -> bool:
    return get_user_role(user) == ROLE_STAFF


def is_doctor(user: Optional[Dict] = None) -> bool:
    return get_user_role(user) == ROLE_DOCTOR


def is_patient(user: Optional[Dict] = None) -> bool:
    return get_user_role(user) == ROLE_PATIENT


# ==============================================================================
# 4. User CRUD & Management Operations (Admin Service)
# ==============================================================================

def get_all_users() -> List[Dict]:
    """Retrieve all user accounts with linked entity labels."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT u.id, u.username, u.email, u.role, u.full_name,
                       u.linked_patient_id, u.linked_doctor_id, u.is_active,
                       u.created_at, u.updated_at,
                       p.patient_code, p.first_name AS pat_first_name, p.last_name AS pat_last_name,
                       d.doctor_code, d.first_name AS doc_first_name, d.last_name AS doc_last_name, d.specialization
                FROM users u
                LEFT JOIN patients p ON u.linked_patient_id = p.id
                LEFT JOIN doctors d ON u.linked_doctor_id = d.id
                ORDER BY u.id ASC;
            """)
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching users: {e}")
        return []


def get_user_by_id(user_id: int) -> Optional[Dict]:
    """Retrieve single user account by ID."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT u.id, u.username, u.email, u.role, u.full_name,
                       u.linked_patient_id, u.linked_doctor_id, u.is_active,
                       u.created_at, u.updated_at,
                       p.patient_code, p.first_name AS pat_first_name, p.last_name AS pat_last_name,
                       d.doctor_code, d.first_name AS doc_first_name, d.last_name AS doc_last_name
                FROM users u
                LEFT JOIN patients p ON u.linked_patient_id = p.id
                LEFT JOIN doctors d ON u.linked_doctor_id = d.id
                WHERE u.id = ?;
            """, (user_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error fetching user by ID {user_id}: {e}")
        return None


def get_user_by_username(username: str) -> Optional[Dict]:
    """Retrieve single user account by username."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT * FROM users WHERE LOWER(username) = LOWER(?);", (username.strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error fetching user by username {username}: {e}")
        return None


def create_user(data: Dict) -> Tuple[bool, str, Optional[int]]:
    """Create a new user account with validated fields and salted PBKDF2 hash.
    
    Returns:
        (success, message, new_user_id)
    """
    username = str(data.get("username", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    raw_password = str(data.get("password", "")).strip()
    role = str(data.get("role", "")).strip()
    full_name = str(data.get("full_name", "")).strip()
    linked_patient_id = data.get("linked_patient_id")
    linked_doctor_id = data.get("linked_doctor_id")

    # Validation
    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters long.", None
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", username):
        return False, "Username can only contain alphanumeric characters, hyphens, and underscores.", None

    if not full_name or len(full_name) < 2:
        return False, "Full Name is required.", None

    if not email or "@" not in email:
        return False, "A valid email address is required.", None

    if not raw_password or len(raw_password) < 6:
        return False, "Password must be at least 6 characters long.", None

    if role not in USER_ROLES:
        return False, f"Invalid role. Must be one of: {', '.join(USER_ROLES)}", None

    # Check username / email uniqueness
    try:
        with get_db_connection() as conn:
            row = conn.execute("SELECT id FROM users WHERE LOWER(username) = LOWER(?);", (username,)).fetchone()
            if row:
                return False, f"Username '{username}' is already taken.", None
            row_email = conn.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?);", (email,)).fetchone()
            if row_email:
                return False, f"Email '{email}' is already registered.", None

        # Hash password
        pwd_hash, salt = hash_password(raw_password)

        with get_db_cursor() as (conn, cursor):
            cursor.execute("""
                INSERT INTO users (username, email, password_hash, salt, role, full_name, linked_patient_id, linked_doctor_id, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1);
            """, (
                username,
                email,
                pwd_hash,
                salt,
                role,
                full_name,
                int(linked_patient_id) if linked_patient_id else None,
                int(linked_doctor_id) if linked_doctor_id else None,
            ))
            new_id = cursor.lastrowid
            return True, f"User account '{username}' created successfully.", new_id

    except Exception as e:
        return False, f"Database error creating user: {e}", None


def update_user(user_id: int, data: Dict) -> Tuple[bool, str]:
    """Update user account details (full_name, email, role, linked entities)."""
    full_name = str(data.get("full_name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    role = str(data.get("role", "")).strip()
    linked_patient_id = data.get("linked_patient_id")
    linked_doctor_id = data.get("linked_doctor_id")

    if not full_name:
        return False, "Full Name is required."
    if not email or "@" not in email:
        return False, "Valid email is required."
    if role not in USER_ROLES:
        return False, f"Invalid role. Must be one of: {', '.join(USER_ROLES)}"

    try:
        with get_db_connection() as conn:
            row = conn.execute("SELECT id FROM users WHERE LOWER(email) = LOWER(?) AND id != ?;", (email, user_id)).fetchone()
            if row:
                return False, f"Email '{email}' is already used by another account."

        with get_db_cursor() as (conn, cursor):
            cursor.execute("""
                UPDATE users SET
                    full_name = ?,
                    email = ?,
                    role = ?,
                    linked_patient_id = ?,
                    linked_doctor_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
            """, (
                full_name,
                email,
                role,
                int(linked_patient_id) if linked_patient_id else None,
                int(linked_doctor_id) if linked_doctor_id else None,
                user_id,
            ))
            return True, "User account updated successfully."
    except Exception as e:
        return False, f"Database error updating user: {e}"


def toggle_user_status(user_id: int) -> Tuple[bool, str]:
    """Toggle user active status (enable/disable account)."""
    try:
        current_u = get_current_user()
        if current_u and current_u.get("id") == user_id:
            return False, "You cannot deactivate your own active session account."

        with get_db_cursor() as (conn, cursor):
            cursor.execute("SELECT is_active FROM users WHERE id = ?;", (user_id,))
            row = cursor.fetchone()
            if not row:
                return False, "User not found."
            new_status = 0 if row["is_active"] == 1 else 1
            cursor.execute("UPDATE users SET is_active = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;", (new_status, user_id))
            status_label = "activated" if new_status == 1 else "deactivated"
            return True, f"User account successfully {status_label}."
    except Exception as e:
        return False, f"Error toggling user status: {e}"


def delete_user(user_id: int) -> Tuple[bool, str]:
    """Permanently delete user account."""
    try:
        current_u = get_current_user()
        if current_u and current_u.get("id") == user_id:
            return False, "You cannot delete your own active session account."

        with get_db_cursor() as (conn, cursor):
            cursor.execute("SELECT role FROM users WHERE id = ?;", (user_id,))
            row = cursor.fetchone()
            if not row:
                return False, "User not found."
            if row["role"] == ROLE_ADMIN:
                cursor.execute("SELECT COUNT(*) AS c FROM users WHERE role = ?;", (ROLE_ADMIN,))
                admin_count = cursor.fetchone()["c"]
                if admin_count <= 1:
                    return False, "Cannot delete the sole Administrator account."

            cursor.execute("DELETE FROM users WHERE id = ?;", (user_id,))
            return True, "User account deleted permanently."
    except Exception as e:
        return False, f"Error deleting user: {e}"


def reset_user_password(user_id: int, new_password: str) -> Tuple[bool, str]:
    """Reset user password directly (Admin operation)."""
    if not new_password or len(new_password) < 6:
        return False, "Password must be at least 6 characters long."
    pwd_hash, salt = hash_password(new_password)
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("""
                UPDATE users SET password_hash = ?, salt = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?;
            """, (pwd_hash, salt, user_id))
            return True, "Password reset successfully."
    except Exception as e:
        return False, f"Error resetting password: {e}"
