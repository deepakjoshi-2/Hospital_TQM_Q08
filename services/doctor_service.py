"""Doctor business logic service for SQLite persistence and CRUD workflows."""
from typing import Dict, List, Optional, Tuple

from database.connection import get_db_connection, get_db_cursor
from services.validation import validate_doctor_data


def get_next_doctor_code() -> str:
    """Generate next sequential doctor code based on existing records."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT doctor_code FROM doctors ORDER BY id DESC LIMIT 1;")
            row = cursor.fetchone()
            if row and row["doctor_code"].startswith("DOC-"):
                num_part = row["doctor_code"].replace("DOC-", "")
                if num_part.isdigit():
                    return f"DOC-{int(num_part) + 1}"
            return "DOC-2011"
    except Exception:
        return "DOC-2011"


def get_doctor_by_id(doctor_id: int) -> Optional[Dict]:
    """Retrieve single doctor record by internal ID."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM doctors WHERE id = ?;", (doctor_id,)).fetchone()
        return dict(row) if row else None


def get_doctor_appointment_count(doctor_id: int) -> int:
    """Count how many clinical appointments are scheduled with this doctor."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM appointments WHERE doctor_id = ?;", (doctor_id,)).fetchone()
        return row["c"] if row else 0


def create_doctor(data: Dict[str, any]) -> Tuple[bool, str, Optional[int]]:
    """Validate and insert a new physician record into SQLite database.
    
    Returns:
        (success, message, new_id)
    """
    is_valid, error = validate_doctor_data(data, is_edit=False)
    if not is_valid:
        return False, error, None

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO doctors (
                    doctor_code, first_name, last_name, specialization,
                    phone, email, consultation_fee, room_number, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    str(data["doctor_code"]).strip().upper(),
                    str(data["first_name"]).strip(),
                    str(data["last_name"]).strip(),
                    str(data["specialization"]).strip(),
                    str(data["phone"]).strip(),
                    str(data["email"]).strip(),
                    float(data["consultation_fee"]),
                    str(data["room_number"]).strip(),
                    str(data.get("status", "Available")).strip(),
                ),
            )
            new_id = cursor.lastrowid
            return True, f"Doctor {data['doctor_code'].upper()} registered successfully.", new_id
    except Exception as e:
        return False, f"Database persistence error: {e}", None


def update_doctor(doctor_id: int, data: Dict[str, any]) -> Tuple[bool, str]:
    """Validate and update an existing doctor record in SQLite database.
    
    Returns:
        (success, message)
    """
    is_valid, error = validate_doctor_data(data, is_edit=True, current_doctor_id=doctor_id)
    if not is_valid:
        return False, error

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                """
                UPDATE doctors SET
                    doctor_code = ?,
                    first_name = ?,
                    last_name = ?,
                    specialization = ?,
                    phone = ?,
                    email = ?,
                    consultation_fee = ?,
                    room_number = ?,
                    status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
                """,
                (
                    str(data["doctor_code"]).strip().upper(),
                    str(data["first_name"]).strip(),
                    str(data["last_name"]).strip(),
                    str(data["specialization"]).strip(),
                    str(data["phone"]).strip(),
                    str(data["email"]).strip(),
                    float(data["consultation_fee"]),
                    str(data["room_number"]).strip(),
                    str(data.get("status", "Available")).strip(),
                    doctor_id,
                ),
            )
            return True, f"Doctor {data['doctor_code'].upper()} updated successfully."
    except Exception as e:
        return False, f"Database error updating doctor: {e}"


def archive_doctor(doctor_id: int) -> Tuple[bool, str]:
    """Soft-archive a doctor by updating their availability status to 'On Leave'."""
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                "UPDATE doctors SET status = 'On Leave', updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (doctor_id,),
            )
            return True, "Doctor availability status set to 'On Leave' successfully."
    except Exception as e:
        return False, f"Failed to update doctor status: {e}"


def delete_doctor(doctor_id: int) -> Tuple[bool, str]:
    """Permanently delete doctor record if no active appointments exist.
    
    TQM Integrity Rule: Foreign key RESTRICT prevents removing doctors with existing appointments.
    """
    appt_count = get_doctor_appointment_count(doctor_id)
    if appt_count > 0:
        return (
            False,
            f"Cannot delete permanently: Doctor has {appt_count} linked appointment(s). "
            f"Use 'Mark On Leave' to deactivate instead."
        )

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("DELETE FROM doctors WHERE id = ?;", (doctor_id,))
            return True, "Doctor deleted permanently from database."
    except Exception as e:
        return False, f"Failed to delete doctor: {e}"
