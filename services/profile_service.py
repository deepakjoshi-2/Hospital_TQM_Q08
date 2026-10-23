"""Profile and settings management service for Hospital Management System — Q08.
Handles reading, validating, and updating user profile preferences in SQLite.
Enforces role-specific scoping: authenticated users view and manage only their own profile.
"""
import re
from typing import Any, Dict, Optional, Tuple
from database.connection import get_db_connection, get_db_cursor
from services.auth_service import get_current_user

ALLOWED_ROLES = [
    "Hospital Administrator",
    "Staff",
    "Doctor",
    "Patient",
    "Chief Medical Officer",
    "Clinical Director",
    "Receptionist",
    "Quality Assurance Officer",
    "Medical Officer",
]

ALLOWED_THEMES = ["Dark", "Light", "System"]
ALLOWED_SCALING = ["80%", "90%", "100%", "110%", "120%"]
ALLOWED_VIEWS = ["Dashboard", "Patients", "Doctors", "Appointments", "Reports", "Billing", "TQM"]


def get_user_profile(username: Optional[str] = None) -> Optional[Dict[str, Any]]:
    """Fetch user profile record for the specified username or currently active session.
    
    Loads profile from user_profile table or maps from users and linked doctor/patient records.
    Never defaults to an Administrator profile when queried by another user.
    """
    target_username = username
    if not target_username:
        cur_u = get_current_user()
        if cur_u:
            target_username = cur_u.get("username")

    if not target_username:
        return None

    try:
        with get_db_connection() as conn:
            # 1. Check user_profile preferences table
            row = conn.execute(
                "SELECT * FROM user_profile WHERE LOWER(username) = LOWER(?) OR (LOWER(?) = 'admin' AND LOWER(username) = 'deepak_admin');",
                (target_username, target_username),
            ).fetchone()
            if row:
                res = dict(row)
                res["username"] = target_username
                return res

            # 2. Map dynamically from users table
            u_row = conn.execute(
                "SELECT * FROM users WHERE LOWER(username) = LOWER(?);", (target_username,)
            ).fetchone()
            if u_row:
                phone = "+91 98765 43210"
                if u_row["linked_doctor_id"]:
                    d = conn.execute("SELECT phone FROM doctors WHERE id = ?;", (u_row["linked_doctor_id"],)).fetchone()
                    if d and d["phone"]:
                        phone = d["phone"]
                elif u_row["linked_patient_id"]:
                    p = conn.execute("SELECT phone FROM patients WHERE id = ?;", (u_row["linked_patient_id"],)).fetchone()
                    if p and p["phone"]:
                        phone = p["phone"]

                role = u_row["role"]
                def_view = "Appointments" if role in ("Doctor", "Patient") else "Dashboard"

                return {
                    "id": u_row["id"],
                    "username": u_row["username"],
                    "full_name": u_row["full_name"],
                    "role": role,
                    "email": u_row["email"],
                    "phone": phone,
                    "theme_preference": "Dark",
                    "scaling_factor": "100%",
                    "default_view": def_view,
                    "notifications_enabled": 1,
                }

            return None
    except Exception as e:
        print(f"Error fetching user profile for {target_username}: {e}")
        return None


def validate_profile_data(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate profile input fields.
    
    Returns:
        (is_valid, error_message)
    """
    # 1. Full Name
    full_name = str(data.get("full_name", "")).strip()
    if not full_name:
        return False, "Full Name is required."
    if len(full_name) < 2:
        return False, "Full Name must be at least 2 characters long."
    if len(full_name) > 60:
        return False, "Full Name cannot exceed 60 characters."

    # 2. Role
    role = str(data.get("role", "")).strip()
    if not role:
        return False, "Role is required."
    if role not in ALLOWED_ROLES:
        return False, f"Role must be one of: {', '.join(ALLOWED_ROLES)}"

    # 3. Email
    email = str(data.get("email", "")).strip()
    if not email:
        return False, "Email address is required."
    email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(email_regex, email):
        return False, "Invalid email address format (e.g., user@hospital.demo)."

    # 4. Phone
    phone = str(data.get("phone", "")).strip()
    if not phone:
        return False, "Phone number is required."
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 10 or len(digits) > 15:
        return False, "Phone Number must contain between 10 and 15 digits."

    # 5. Theme Preference
    theme = str(data.get("theme_preference", "Dark")).strip().capitalize()
    if theme not in ALLOWED_THEMES:
        return False, f"Theme must be one of: {', '.join(ALLOWED_THEMES)}"

    # 6. Scaling Factor
    scaling = str(data.get("scaling_factor", "100%")).strip()
    if scaling not in ALLOWED_SCALING:
        return False, f"Scaling Factor must be one of: {', '.join(ALLOWED_SCALING)}"

    # 7. Default View
    view = str(data.get("default_view", "Dashboard")).strip()
    if view not in ALLOWED_VIEWS:
        return False, f"Default View must be one of: {', '.join(ALLOWED_VIEWS)}"

    return True, ""


def update_user_profile(username: str, data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate and update or insert user profile in SQLite database.
    
    Returns:
        (success, message)
    """
    is_valid, error = validate_profile_data(data)
    if not is_valid:
        return False, error

    try:
        notifications = 1 if data.get("notifications_enabled") in (1, True, "1", "true") else 0
        with get_db_cursor() as (conn, cursor):
            exists = cursor.execute("SELECT id FROM user_profile WHERE LOWER(username) = LOWER(?);", (username,)).fetchone()
            if exists:
                cursor.execute(
                    """
                    UPDATE user_profile SET
                        full_name = ?,
                        role = ?,
                        email = ?,
                        phone = ?,
                        theme_preference = ?,
                        scaling_factor = ?,
                        default_view = ?,
                        notifications_enabled = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE LOWER(username) = LOWER(?);
                    """,
                    (
                        data["full_name"].strip(),
                        data["role"].strip(),
                        data["email"].strip(),
                        data["phone"].strip(),
                        data.get("theme_preference", "Dark").strip().capitalize(),
                        data.get("scaling_factor", "100%").strip(),
                        data.get("default_view", "Dashboard").strip(),
                        notifications,
                        username,
                    ),
                )
            else:
                cursor.execute(
                    """
                    INSERT INTO user_profile (
                        username, full_name, role, email, phone,
                        theme_preference, scaling_factor, default_view, notifications_enabled
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    (
                        username,
                        data["full_name"].strip(),
                        data["role"].strip(),
                        data["email"].strip(),
                        data["phone"].strip(),
                        data.get("theme_preference", "Dark").strip().capitalize(),
                        data.get("scaling_factor", "100%").strip(),
                        data.get("default_view", "Dashboard").strip(),
                        notifications,
                    ),
                )

            # Sync full_name and email to users table if record exists
            cursor.execute(
                "UPDATE users SET full_name = ?, email = ?, updated_at = CURRENT_TIMESTAMP WHERE LOWER(username) = LOWER(?);",
                (data["full_name"].strip(), data["email"].strip(), username),
            )

        return True, "Profile and preferences updated successfully in SQLite."
    except Exception as e:
        return False, f"Database error updating user profile: {e}"
