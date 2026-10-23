"""Appointment business logic service for SQLite persistence, conflict checks, and CRUD.
Enforces double-booking prevention, consultation fee preservation at booking,
status transition state machine, in-app notifications, and confirmation cards.
"""
from typing import Dict, List, Optional, Tuple

from config.constants import (
    APPOINTMENT_STATUSES,
    NOTIF_BOOKING,
    NOTIF_CANCELLATION,
    NOTIF_CONFIRMATION,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_CONFIRMED,
    STATUS_NO_SHOW,
    STATUS_PENDING,
    STATUS_SCHEDULED,
)
from database.connection import get_db_connection, get_db_cursor
from services.billing_service import create_bill_for_appointment
from services.notification_service import create_notification
from services.validation import validate_appointment_data


# ==============================================================================
# 1. Status Transition State Machine
# ==============================================================================

# Allowed state transitions: {current_state: [allowed_next_states]}
VALID_TRANSITIONS = {
    STATUS_PENDING: [STATUS_PENDING, STATUS_CONFIRMED, STATUS_CANCELLED],
    STATUS_CONFIRMED: [STATUS_CONFIRMED, STATUS_COMPLETED, STATUS_CANCELLED, STATUS_NO_SHOW],
    STATUS_SCHEDULED: [STATUS_SCHEDULED, STATUS_CONFIRMED, STATUS_COMPLETED, STATUS_CANCELLED, STATUS_NO_SHOW],
    STATUS_NO_SHOW: [STATUS_NO_SHOW, STATUS_CANCELLED, STATUS_CONFIRMED],
    STATUS_COMPLETED: [STATUS_COMPLETED],  # Terminal
    STATUS_CANCELLED: [STATUS_CANCELLED],  # Terminal
}


def validate_status_transition(current_status: str, new_status: str) -> Tuple[bool, str]:
    """Validate appointment status transition against the clinical lifecycle rules.
    
    Returns:
        (is_valid, explanatory_message)
    """
    curr = str(current_status or "").strip()
    nxt = str(new_status or "").strip()

    if nxt not in APPOINTMENT_STATUSES:
        return False, f"Invalid target status '{nxt}'. Choose from: {', '.join(APPOINTMENT_STATUSES)}"

    if curr == nxt:
        return True, ""

    if curr == STATUS_COMPLETED:
        return False, "Cannot change status of an already 'Completed' consultation (Terminal State)."

    if curr == STATUS_CANCELLED:
        return False, "Cannot change status of a 'Cancelled' appointment (Terminal State). Please book a new slot."

    allowed = VALID_TRANSITIONS.get(curr, [STATUS_CONFIRMED, STATUS_CANCELLED, STATUS_COMPLETED])
    if nxt not in allowed:
        return False, f"Invalid transition from '{curr}' to '{nxt}'. Allowed transitions: {', '.join(allowed)}."

    return True, ""


# ==============================================================================
# 2. Sequential Code Generators & Dropdown Helpers
# ==============================================================================

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
    """Retrieve single appointment record with patient, doctor, and consultation fee details."""
    with get_db_connection() as conn:
        cursor = conn.execute(
            """
            SELECT a.*, 
                   p.patient_code, p.first_name AS patient_first_name, p.last_name AS patient_last_name, p.phone AS patient_phone,
                   d.doctor_code, d.first_name AS doctor_first_name, d.last_name AS doctor_last_name, d.specialization, d.room_number,
                   COALESCE(a.consultation_fee, d.consultation_fee, 500.0) AS effective_fee
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
                "SELECT id, doctor_code, first_name, last_name, specialization, status, consultation_fee "
                "FROM doctors ORDER BY first_name, last_name;"
            )
            for r in cursor.fetchall():
                leave_tag = " [On Leave]" if r["status"] == "On Leave" else ""
                fee_tag = f" (Fee: Rs. {float(r['consultation_fee']):.0f})"
                label = f"{r['doctor_code']} — {r['first_name']} {r['last_name']} ({r['specialization']}){fee_tag}{leave_tag}"
                options.append((r["id"], label))
    except Exception as e:
        print(f"Error fetching doctor options: {e}")
    return options


# ==============================================================================
# 3. Collision & Double-Booking Safeguards
# ==============================================================================

def check_slot_conflict(
    doctor_id: int,
    appointment_date: str,
    time_slot: str,
    current_appointment_id: Optional[int] = None,
    exclude_appointment_id: Optional[int] = None,
) -> Tuple[bool, Optional[str]]:
    """Check if doctor has an active appointment at same date/time (excluding Cancelled)."""
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
    """Check if patient has an active appointment at same date/time (excluding Cancelled)."""
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


# ==============================================================================
# 4. CRUD Operations with Fee Freezing and Notification Dispatch
# ==============================================================================

def create_appointment(data: Dict[str, any]) -> Tuple[bool, str, Optional[int]]:
    """Validate, verify collision, freeze consultation fee, and insert appointment into SQLite.
    
    Dispatches booking confirmation notification and creates initial invoice.
    Returns:
        (success, message, new_id)
    """
    # 1. Validation
    is_valid, error = validate_appointment_data(data, is_edit=False)
    if not is_valid:
        return False, error, None

    doctor_id = int(data["doctor_id"])
    patient_id = int(data["patient_id"])
    appt_date = str(data["appointment_date"]).strip()
    time_slot = str(data["time_slot"]).strip()
    status = str(data.get("status", STATUS_CONFIRMED)).strip()
    appt_code = str(data["appointment_code"]).strip().upper()

    # 2. Collision checks
    if status != STATUS_CANCELLED:
        has_conflict, conflict_code = check_slot_conflict(doctor_id, appt_date, time_slot)
        if has_conflict:
            return (
                False,
                f"Double-Booking Blocked: Doctor already has an active consultation ({conflict_code}) "
                f"at {time_slot} on {appt_date}. Please choose another slot or physician.",
                None,
            )

        has_p_conflict, p_conflict_code = check_patient_slot_conflict(patient_id, appt_date, time_slot)
        if has_p_conflict:
            return (
                False,
                f"Double-Booking Blocked: Patient already has an active consultation ({p_conflict_code}) "
                f"at {time_slot} on {appt_date}. A patient cannot be scheduled in two consultations simultaneously.",
                None,
            )

    # 3. Freeze Consultation Fee from Doctor Table if not provided
    consultation_fee = data.get("consultation_fee")
    if consultation_fee is None:
        try:
            with get_db_connection() as conn:
                doc_row = conn.execute("SELECT consultation_fee FROM doctors WHERE id = ?;", (doctor_id,)).fetchone()
                consultation_fee = float(doc_row["consultation_fee"]) if doc_row else 500.0
        except Exception:
            consultation_fee = 500.0
    else:
        consultation_fee = float(consultation_fee)

    rating = data.get("satisfaction_rating")
    rating_val = int(rating) if rating is not None and str(rating).strip() not in ("", "None") else None

    # 4. Insert into SQLite
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO appointments (
                    appointment_code, patient_id, doctor_id, appointment_date,
                    time_slot, reason, priority, status, consultation_fee, satisfaction_rating, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    appt_code,
                    patient_id,
                    doctor_id,
                    appt_date,
                    time_slot,
                    str(data["reason"]).strip(),
                    str(data.get("priority", "Normal")).strip(),
                    status,
                    consultation_fee,
                    rating_val,
                    str(data.get("notes", "")).strip() or None,
                ),
            )
            new_id = cursor.lastrowid

        # 5. Automatically create invoice/bill
        create_bill_for_appointment(new_id)

        # 6. Dispatch In-App Patient Notification
        doc_details = get_appointment_by_id(new_id)
        doc_name = f"{doc_details['doctor_first_name']} {doc_details['doctor_last_name']}" if doc_details else "Doctor"
        notif_msg = (
            f"Your appointment {appt_code} with Dr. {doc_name} is confirmed for {appt_date} at {time_slot}. "
            f"Consultation Fee: Rs. {consultation_fee:.2f}."
        )
        create_notification(
            patient_id=patient_id,
            title="Appointment Confirmed",
            message=notif_msg,
            notification_type=NOTIF_CONFIRMATION if status == STATUS_CONFIRMED else NOTIF_BOOKING,
            appointment_id=new_id,
        )

        return True, f"Appointment {appt_code} booked successfully.", new_id

    except Exception as e:
        return False, f"Database persistence error: {e}", None


def update_appointment(appointment_id: int, data: Dict[str, any]) -> Tuple[bool, str]:
    """Validate, verify collision and status transition, and update appointment in SQLite.
    
    Returns:
        (success, message)
    """
    is_valid, error = validate_appointment_data(data, is_edit=True, current_appointment_id=appointment_id)
    if not is_valid:
        return False, error

    current_record = get_appointment_by_id(appointment_id)
    if not current_record:
        return False, f"Appointment ID {appointment_id} not found."

    old_status = current_record["status"]
    new_status = str(data.get("status", old_status)).strip()

    # Validate state transition
    valid_trans, trans_err = validate_status_transition(old_status, new_status)
    if not valid_trans:
        return False, trans_err

    doctor_id = int(data["doctor_id"])
    patient_id = int(data["patient_id"])
    appt_date = str(data["appointment_date"]).strip()
    time_slot = str(data["time_slot"]).strip()
    appt_code = str(data["appointment_code"]).strip().upper()

    if new_status != STATUS_CANCELLED:
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
            patient_id, appt_date, time_slot, current_appointment_id=appointment_id
        )
        if has_p_conflict:
            return (
                False,
                f"Double-Booking Blocked: Patient already has an active consultation ({p_conflict_code}) "
                f"at {time_slot} on {appt_date}. A patient cannot be scheduled in two consultations simultaneously.",
            )

    rating = data.get("satisfaction_rating")
    rating_val = int(rating) if rating is not None and str(rating).strip() not in ("", "None") else None

    # Preserve or update consultation fee
    fee = data.get("consultation_fee")
    fee_val = float(fee) if fee is not None else current_record.get("consultation_fee", 500.0)

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
                    consultation_fee = ?,
                    satisfaction_rating = ?,
                    notes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
                """,
                (
                    appt_code,
                    patient_id,
                    doctor_id,
                    appt_date,
                    time_slot,
                    str(data["reason"]).strip(),
                    str(data.get("priority", "Normal")).strip(),
                    new_status,
                    fee_val,
                    rating_val,
                    str(data.get("notes", "")).strip() or None,
                    appointment_id,
                ),
            )

        # Trigger notification on significant status change
        if old_status != new_status:
            doc_name = f"{current_record['doctor_first_name']} {current_record['doctor_last_name']}"
            if new_status == STATUS_CANCELLED:
                create_notification(
                    patient_id=patient_id,
                    title="Appointment Cancelled",
                    message=f"Appointment {appt_code} scheduled on {appt_date} at {time_slot} has been cancelled.",
                    notification_type=NOTIF_CANCELLATION,
                    appointment_id=appointment_id,
                )
            elif new_status == STATUS_COMPLETED:
                create_notification(
                    patient_id=patient_id,
                    title="Consultation Completed",
                    message=f"Your consultation {appt_code} with Dr. {doc_name} is marked as completed.",
                    notification_type=NOTIF_CONFIRMATION,
                    appointment_id=appointment_id,
                )

        return True, f"Appointment {appt_code} updated successfully."
    except Exception as e:
        return False, f"Database error updating appointment: {e}"


def cancel_appointment(appointment_id: int) -> Tuple[bool, str]:
    """Cancel appointment and free the doctor's time slot for new bookings."""
    current = get_appointment_by_id(appointment_id)
    if not current:
        return False, "Appointment not found."

    valid_trans, trans_err = validate_status_transition(current["status"], STATUS_CANCELLED)
    if not valid_trans:
        return False, trans_err

    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                "UPDATE appointments SET status = 'Cancelled', updated_at = CURRENT_TIMESTAMP WHERE id = ?;",
                (appointment_id,),
            )

        create_notification(
            patient_id=current["patient_id"],
            title="Appointment Cancelled",
            message=f"Your appointment {current['appointment_code']} on {current['appointment_date']} at {current['time_slot']} has been cancelled.",
            notification_type=NOTIF_CANCELLATION,
            appointment_id=appointment_id,
        )
        return True, "Appointment status set to 'Cancelled'. Slot is now free for booking."
    except Exception as e:
        return False, f"Failed to cancel appointment: {e}"


def delete_appointment(appointment_id: int) -> Tuple[bool, str]:
    """Permanently delete appointment record from SQLite database."""
    try:
        with get_db_cursor() as (conn, cursor):
            # Check if associated bill exists; delete bill first or handle
            cursor.execute("DELETE FROM bills WHERE appointment_id = ?;", (appointment_id,))
            cursor.execute("DELETE FROM appointments WHERE id = ?;", (appointment_id,))
            return True, "Appointment deleted permanently from database."
    except Exception as e:
        return False, f"Failed to delete appointment: {e}"


# ==============================================================================
# 5. Confirmation Details Slip Builder & Role-Based Filtering
# ==============================================================================

def get_appointment_confirmation_details(appointment_id: int) -> Optional[Dict]:
    """Generate structured confirmation card details including fee and patient instructions."""
    appt = get_appointment_by_id(appointment_id)
    if not appt:
        return None

    patient_instructions = [
        "Please arrive at the clinic 15 minutes before your scheduled appointment time.",
        "Present your Appointment Reference Code and a valid Government ID at the reception.",
        "Bring previous medical records, ongoing prescriptions, and relevant lab reports.",
        "To reschedule or cancel, please notify the hospital desk at least 2 hours in advance.",
    ]

    return {
        "appointment_id": appt["id"],
        "appointment_code": appt["appointment_code"],
        "status": appt["status"],
        "priority": appt["priority"],
        "patient_id": appt["patient_id"],
        "patient_name": f"{appt['patient_first_name']} {appt['patient_last_name']}",
        "patient_code": appt["patient_code"],
        "patient_phone": appt["patient_phone"],
        "doctor_id": appt["doctor_id"],
        "doctor_name": f"Dr. {appt['doctor_first_name']} {appt['doctor_last_name']}",
        "doctor_code": appt["doctor_code"],
        "specialization": appt["specialization"],
        "room_number": appt["room_number"],
        "appointment_date": appt["appointment_date"],
        "time_slot": appt["time_slot"],
        "consultation_fee": float(appt.get("consultation_fee") or appt.get("effective_fee") or 500.0),
        "reason": appt["reason"],
        "instructions": patient_instructions,
    }


def get_filtered_appointments(
    user: Optional[Dict] = None,
    patient_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    status_filter: Optional[str] = None,
    search_query: Optional[str] = None,
) -> List[Dict]:
    """Retrieve appointments with role-based scoping (Patient sees own, Doctor sees own)."""
    target_patient_id = patient_id
    target_doctor_id = doctor_id

    if user:
        role = user.get("role")
        if role == "Patient" and user.get("linked_patient_id"):
            target_patient_id = user["linked_patient_id"]
        elif role == "Doctor" and user.get("linked_doctor_id"):
            target_doctor_id = user["linked_doctor_id"]

    try:
        with get_db_connection() as conn:
            query = """
                SELECT a.*,
                       p.patient_code, p.first_name AS patient_first_name, p.last_name AS patient_last_name, p.phone AS patient_phone,
                       d.doctor_code, d.first_name AS doctor_first_name, d.last_name AS doctor_last_name, d.specialization, d.room_number,
                       COALESCE(a.consultation_fee, d.consultation_fee, 500.0) AS effective_fee
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                JOIN doctors d ON a.doctor_id = d.id
                WHERE 1=1
            """
            params = []

            if target_patient_id:
                query += " AND a.patient_id = ?"
                params.append(target_patient_id)

            if target_doctor_id:
                query += " AND a.doctor_id = ?"
                params.append(target_doctor_id)

            if status_filter and status_filter != "All":
                query += " AND a.status = ?"
                params.append(status_filter)

            if search_query:
                q = f"%{search_query.strip()}%"
                query += """ AND (
                    a.appointment_code LIKE ? OR
                    p.patient_code LIKE ? OR p.first_name LIKE ? OR p.last_name LIKE ? OR
                    d.first_name LIKE ? OR d.last_name LIKE ? OR d.specialization LIKE ?
                )"""
                params.extend([q, q, q, q, q, q, q])

            query += " ORDER BY a.appointment_date DESC, a.time_slot DESC, a.id DESC;"
            cursor = conn.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching filtered appointments: {e}")
        return []
