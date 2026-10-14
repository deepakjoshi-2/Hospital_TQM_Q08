"""Patient business logic service for SQLite persistence and CRUD workflows."""
from typing import Dict, List, Optional, Tuple

from database.connection import get_db_connection, get_db_cursor
from services.validation import validate_patient_data


def get_next_patient_code() -> str:
    """Generate next sequential patient code based on existing records."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT patient_code FROM patients ORDER BY id DESC LIMIT 1;")
            row = cursor.fetchone()
            if row and row["patient_code"].startswith("PAT-"):
                num_part = row["patient_code"].replace("PAT-", "")
                if num_part.isdigit():
                    return f"PAT-{int(num_part) + 1}"
            return "PAT-1026"
    except Exception:
        return "PAT-1026"


def get_patient_by_id(patient_id: int) -> Optional[Dict]:
    """Retrieve single patient record by internal ID."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT * FROM patients WHERE id = ?;", (patient_id,)).fetchone()
        return dict(row) if row else None


def get_patient_appointment_count(patient_id: int) -> int:
    """Count how many appointments are linked to this patient."""
    with get_db_connection() as conn:
        row = conn.execute("SELECT COUNT(*) as c FROM appointments WHERE patient_id = ?;", (patient_id,)).fetchone()
        return row["c"] if row else 0


def create_patient(data: Dict[str, str]) -> Tuple[bool, str, Optional[int]]:
    """Validate and insert a new patient into SQLite database.
    
    Returns:
        (success, message, new_id)
    """
    is_valid, error = validate_patient_data(data, is_edit=False)
    if not is_valid:
        return False, error, None

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO patients (
                    patient_code, first_name, last_name, dob, gender,
                    phone, email, blood_group, emergency_contact, address, status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    data["patient_code"].strip().upper(),
                    data["first_name"].strip(),
                    data["last_name"].strip(),
                    data["dob"].strip(),
                    data["gender"].strip(),
                    data["phone"].strip(),
                    data.get("email", "").strip() or None,
                    data.get("blood_group", "").strip() or None,
                    data.get("emergency_contact", "").strip() or None,
                    data.get("address", "").strip() or None,
                    data.get("status", "Active").strip(),
                ),
            )
            new_id = cursor.lastrowid
            return True, f"Patient {data['patient_code'].upper()} created successfully.", new_id
    except Exception as e:
        return False, f"Database persistence error: {e}", None


def update_patient(patient_id: int, data: Dict[str, str]) -> Tuple[bool, str]:
    """Validate and update an existing patient in SQLite database.
    
    Returns:
        (success, message)
    """
    is_valid, error = validate_patient_data(data, is_edit=True, current_patient_id=patient_id)
    if not is_valid:
        return False, error

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                """
                UPDATE patients SET
                    patient_code = ?,
                    first_name = ?,
                    last_name = ?,
                    dob = ?,
                    gender = ?,
                    phone = ?,
                    email = ?,
                    blood_group = ?,
                    emergency_contact = ?,
                    address = ?,
                    status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
                """,
                (
                    data["patient_code"].strip().upper(),
                    data["first_name"].strip(),
                    data["last_name"].strip(),
                    data["dob"].strip(),
                    data["gender"].strip(),
                    data["phone"].strip(),
                    data.get("email", "").strip() or None,
                    data.get("blood_group", "").strip() or None,
                    data.get("emergency_contact", "").strip() or None,
                    data.get("address", "").strip() or None,
                    data.get("status", "Active").strip(),
                    patient_id,
                ),
            )
            return True, f"Patient {data['patient_code'].upper()} updated successfully."
    except Exception as e:
        return False, f"Database error updating patient: {e}"


def archive_patient(patient_id: int) -> Tuple[bool, str]:
    """Soft-delete patient by changing their status to 'Archived'."""
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                "UPDATE patients SET status = 'Archived', updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (patient_id,),
            )
            return True, "Patient status changed to Archived successfully."
    except Exception as e:
        return False, f"Failed to archive patient: {e}"


def delete_patient(patient_id: int) -> Tuple[bool, str]:
    """Permanently delete patient record from SQLite database if no linked appointments exist.
    
    TQM Patient Safety Guard:
    Prevents cascading deletion of clinical history. Archived status should be used instead.
    """
    appt_count = get_patient_appointment_count(patient_id)
    if appt_count > 0:
        return (
            False,
            f"Cannot delete permanently: Patient has {appt_count} linked clinical appointment(s). "
            f"Please archive the patient record instead to preserve clinical audit history.",
        )

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("DELETE FROM patients WHERE id = ?;", (patient_id,))
            return True, "Patient deleted permanently from database."
    except Exception as e:
        return False, f"Failed to delete patient: {e}"
