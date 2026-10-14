"""Appointment business logic service for SQLite persistence, conflict checks, and CRUD."""
from typing import Dict, List, Optional, Tuple

from database.connection import get_db_connection, get_db_cursor
from services.validation import validate_appointment_data


def get_next_appointment_code() -> str:
    """Generate next sequential appointment code based on existing records."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT appointment_code FROM appointments ORDER BY id DESC LIMIT 1;")
            row = cursor.fetchone()
            if row and row["appointment_code"].startswith("APT-"):
                num_part = row["appointment_code"].replace("APT-", "")
                if num_part.isdigit():
                    return f"APT-{int(num_part) + 1}"
            return "APT-3043"
    except Exception:
        return "APT-3043"


def get_appointment_by_id(appointment_id: int) -> Optional[Dict]:
    """Retrieve single appointment record with patient and doctor details."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT a.*, 
                   p.patient_code, p.first_name AS patient_first_name, p.last_name AS patient_last_name, p.phone AS patient_phone,
                   d.doctor_code, d.first_name AS doctor_first_name, d.last_name AS doctor_last_name, d.specialization, d.room_number
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            JOIN doctors d ON a.doctor_id = d.id
            WHERE a.id = ?;
            """,
            (appointment_id,),
        )
        row = cursor.fetchone()
        return dict(row) if row else None


def get_patient_dropdown_options() -> List[Tuple[int, str]]:
    """Fetch active patients for dropdown selection: [(patient_id, display_label), ...]."""
    options = []
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT id, patient_code, first_name, last_name FROM patients ORDER BY first_name, last_name;"
            )
            for r in cursor.fetchall():
                label = f"{r['patient_code']} — {r['first_name']} {r['last_name']}"
                options.append((r["id"], label))
    except Exception as e:
        print(f"Error fetching patient options: {e}")
    return options


def get_doctor_dropdown_options() -> List[Tuple[int, str]]:
    """Fetch all doctors for dropdown selection: [(doctor_id, display_label), ...]."""
    options = []
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                "SELECT id, doctor_code, first_name, last_name, specialization, status FROM doctors "
                "ORDER BY first_name, last_name;"
            )
            for r in cursor.fetchall():
                leave_tag = " [On Leave]" if r["status"] == "On Leave" else ""
                label = f"{r['doctor_code']} — {r['first_name']} {r['last_name']} ({r['specialization']}){leave_tag}"
                options.append((r["id"], label))
    except Exception as e:
        print(f"Error fetching doctor options: {e}")
    return options


def check_slot_conflict(
    doctor_id: int,
    appointment_date: str,
    time_slot: str,
    current_appointment_id: Optional[int] = None,
    exclude_appointment_id: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """Check if the doctor already has an active appointment in the given date and time slot.
    
    TQM Double-Booking Safeguard:
    Returns:
        (has_conflict, conflicting_appointment_code)
    """
    try:
        excluded_id = current_appointment_id or exclude_appointment_id
        with get_db_connection() as conn:
            sql = """
                SELECT id, appointment_code FROM appointments
                WHERE doctor_id = ? AND appointment_date = ? AND time_slot = ? AND status != 'Cancelled'
            """
            params = [doctor_id, appointment_date, time_slot]

            if excluded_id:
                sql += " AND id != ?"
                params.append(excluded_id)

            row = conn.execute(sql, tuple(params)).fetchone()
            if row:
                return True, row["appointment_code"]
            return False, None
    except Exception as e:
        print(f"Error checking slot conflict: {e}")
        return False, None


def check_patient_slot_conflict(
    patient_id: int,
    appointment_date: str,
    time_slot: str,
    current_appointment_id: Optional[int] = None,
    exclude_appointment_id: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """Check if the patient already has an active appointment in the given date and time slot.
    
    TQM Patient Scheduling Safeguard:
    Prevents scheduling the same patient in two consultations simultaneously.
    Returns:
        (has_conflict, conflicting_appointment_code)
    """
    try:
        excluded_id = current_appointment_id or exclude_appointment_id
        with get_db_connection() as conn:
            sql = """
                SELECT id, appointment_code FROM appointments
                WHERE patient_id = ? AND appointment_date = ? AND time_slot = ? AND status != 'Cancelled'
            """
            params = [patient_id, appointment_date, time_slot]

            if excluded_id:
                sql += " AND id != ?"
                params.append(excluded_id)

            row = conn.execute(sql, tuple(params)).fetchone()
            if row:
                return True, row["appointment_code"]
            return False, None
    except Exception as e:
        print(f"Error checking patient slot conflict: {e}")
        return False, None


def create_appointment(data: Dict[str, any]) -> Tuple[bool, str, Optional[int]]:
    """Validate, verify double-booking prevention, and insert appointment into SQLite.
    
    Returns:
        (success, message, new_id)
    """
    # 1. Input field validation
    is_valid, error = validate_appointment_data(data, is_edit=False)
    if not is_valid:
        return False, error, None

    # 2. Double-booking collision checks (TQM Q08 core requirement)
    doctor_id = int(data["doctor_id"])
    patient_id = int(data["patient_id"])
    appt_date = str(data["appointment_date"]).strip()
    time_slot = str(data["time_slot"]).strip()
    status = str(data.get("status", "Scheduled")).strip()

    if status != "Cancelled":
        has_conflict, conflict_code = check_slot_conflict(doctor_id, appt_date, time_slot)
        if has_conflict:
            return (
                False,
                f"Double-Booking Blocked: Doctor already has an active consultation ({conflict_code}) "
                f"at {time_slot} on {appt_date}. Please choose another slot or physician.",
                None,
            )

        has_patient_conflict, p_conflict_code = check_patient_slot_conflict(patient_id, appt_date, time_slot)
        if has_patient_conflict:
            return (
                False,
                f"Double-Booking Blocked: Patient already has an active consultation ({p_conflict_code}) "
                f"at {time_slot} on {appt_date}. A patient cannot be scheduled in two consultations simultaneously.",
                None,
            )

    # 3. Clean rating value
    rating = data.get("satisfaction_rating")
    rating_val = int(rating) if rating is not None and str(rating).strip() not in ("", "None") else None

    # 4. Insert into SQLite
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO appointments (
                    appointment_code, patient_id, doctor_id, appointment_date,
                    time_slot, reason, priority, status, satisfaction_rating, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    str(data["appointment_code"]).strip().upper(),
                    int(data["patient_id"]),
                    doctor_id,
                    appt_date,
                    time_slot,
                    str(data["reason"]).strip(),
                    str(data.get("priority", "Normal")).strip(),
                    status,
                    rating_val,
                    str(data.get("notes", "")).strip() or None,
                ),
            )
            new_id = cursor.lastrowid
            return True, f"Appointment {data['appointment_code'].upper()} booked successfully.", new_id
    except Exception as e:
        return False, f"Database persistence error: {e}", None


def update_appointment(appointment_id: int, data: Dict[str, any]) -> Tuple[bool, str]:
    """Validate, verify collision, and update appointment in SQLite database.
    
    Returns:
        (success, message)
    """
    is_valid, error = validate_appointment_data(data, is_edit=True, current_appointment_id=appointment_id)
    if not is_valid:
        return False, error

    doctor_id = int(data["doctor_id"])
    appt_date = str(data["appointment_date"]).strip()
    time_slot = str(data["time_slot"]).strip()
    status = str(data.get("status", "Scheduled")).strip()

    if status != "Cancelled":
        has_conflict, conflict_code = check_slot_conflict(
            doctor_id, appt_date, time_slot, current_appointment_id=appointment_id
        )
        if has_conflict:
            return (
                False,
                f"Double-Booking Blocked: Doctor already has an active consultation ({conflict_code}) "
                f"at {time_slot} on {appt_date}. Please choose another slot.",
            )

        has_p_conflict, p_conflict_code = check_patient_slot_conflict(
            int(data["patient_id"]), appt_date, time_slot, current_appointment_id=appointment_id
        )
        if has_p_conflict:
            return (
                False,
                f"Double-Booking Blocked: Patient already has an active consultation ({p_conflict_code}) "
                f"at {time_slot} on {appt_date}. A patient cannot be scheduled in two consultations simultaneously.",
            )

    rating = data.get("satisfaction_rating")
    rating_val = int(rating) if rating is not None and str(rating).strip() not in ("", "None") else None

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                """
                UPDATE appointments SET
                    appointment_code = ?,
                    patient_id = ?,
                    doctor_id = ?,
                    appointment_date = ?,
                    time_slot = ?,
                    reason = ?,
                    priority = ?,
                    status = ?,
                    satisfaction_rating = ?,
                    notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
                """,
                (
                    str(data["appointment_code"]).strip().upper(),
                    int(data["patient_id"]),
                    doctor_id,
                    appt_date,
                    time_slot,
                    str(data["reason"]).strip(),
                    str(data.get("priority", "Normal")).strip(),
                    status,
                    rating_val,
                    str(data.get("notes", "")).strip() or None,
                    appointment_id,
                ),
            )
            return True, f"Appointment {data['appointment_code'].upper()} updated successfully."
    except Exception as e:
        return False, f"Database error updating appointment: {e}"


def cancel_appointment(appointment_id: int) -> Tuple[bool, str]:
    """Cancel appointment and free the doctor's time slot for new bookings."""
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                "UPDATE appointments SET status = 'Cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (appointment_id,),
            )
            return True, "Appointment status set to 'Cancelled'. Slot is now free for booking."
    except Exception as e:
        return False, f"Failed to cancel appointment: {e}"


def delete_appointment(appointment_id: int) -> Tuple[bool, str]:
    """Permanently delete appointment record from SQLite database."""
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("DELETE FROM appointments WHERE id = ?;", (appointment_id,))
            return True, "Appointment deleted permanently from database."
    except Exception as e:
        return False, f"Failed to delete appointment: {e}"
