"""Form input validation service for patient records and hospital workflows."""
import re
from datetime import datetime
from typing import Dict, Optional, Tuple

from config.constants import BLOOD_GROUPS, PATIENT_STATUSES
from database.connection import get_db_connection


def validate_patient_data(
    data: Dict[str, str],
    is_edit: bool = False,
    current_patient_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """Validate patient fields and verify uniqueness in SQLite database.
    
    Returns:
        (is_valid, error_message): tuple with boolean and explanatory message.
    """
    # 1. Required First Name
    first_name = data.get("first_name", "").strip()
    if not first_name:
        return False, "First Name is required."
    if len(first_name) < 2:
        return False, "First Name must be at least 2 characters long."

    # 2. Required Last Name
    last_name = data.get("last_name", "").strip()
    if not last_name:
        return False, "Last Name is required."

    # 3. Required Patient Code & Format
    patient_code = data.get("patient_code", "").strip().upper()
    if not patient_code:
        return False, "Patient Code is required (e.g. PAT-1026)."
    if not re.match(r"^PAT-[A-Za-z0-9-]+$", patient_code):
        return False, "Patient Code must start with 'PAT-' followed by letters or digits."

    # 4. Check Patient Code Uniqueness in Database
    try:
        with get_db_connection() as conn:
            if is_edit and current_patient_id:
                query = "SELECT id FROM patients WHERE patient_code = ? AND id != ?;"
                row = conn.execute(query, (patient_code, current_patient_id)).fetchone()
            else:
                query = "SELECT id FROM patients WHERE patient_code = ?;"
                row = conn.execute(query, (patient_code,)).fetchone()

            if row:
                return False, f"Patient Code '{patient_code}' is already assigned to another patient."
    except Exception as e:
        return False, f"Database error verifying code uniqueness: {e}"

    # 5. Date of Birth Validation (YYYY-MM-DD)
    dob = data.get("dob", "").strip()
    if not dob:
        return False, "Date of Birth is required (format: YYYY-MM-DD)."
    try:
        parsed_dob = datetime.strptime(dob, "%Y-%m-%d").date()
        today = datetime.now().date()
        if parsed_dob > today:
            return False, "Date of Birth cannot be in the future."
        if parsed_dob.year < 1900:
            return False, "Date of Birth year must be 1900 or later."
    except ValueError:
        return False, "Invalid Date of Birth. Please use format YYYY-MM-DD (e.g., 1995-04-20)."

    # 6. Gender Check
    gender = data.get("gender", "").strip()
    if gender not in ("Male", "Female", "Other"):
        return False, "Gender must be 'Male', 'Female', or 'Other'."

    # 7. Phone Number Validation
    phone = data.get("phone", "").strip()
    if not phone:
        return False, "Contact Phone Number is required."
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 10 or len(digits) > 15:
        return False, "Phone Number must contain between 10 and 15 digits."

    # 8. Email Validation (if provided)
    email = data.get("email", "").strip()
    if email:
        email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
        if not re.match(email_regex, email):
            return False, "Invalid email address format (e.g., user@example.com)."

    # 9. Blood Group Check (if provided)
    blood_group = data.get("blood_group", "").strip()
    if blood_group and blood_group not in BLOOD_GROUPS:
        return False, f"Invalid Blood Group. Choose from: {', '.join(BLOOD_GROUPS)}"

    # 10. Status Check
    status = data.get("status", "Active").strip()
    if status not in PATIENT_STATUSES:
        return False, f"Invalid Status. Choose from: {', '.join(PATIENT_STATUSES)}"

    return True, ""


def validate_doctor_data(
    data: Dict[str, any],
    is_edit: bool = False,
    current_doctor_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """Validate doctor fields and verify uniqueness in SQLite database.
    
    Returns:
        (is_valid, error_message): tuple with boolean and explanatory message.
    """
    # 1. Required First Name
    first_name = str(data.get("first_name", "")).strip()
    if not first_name:
        return False, "First Name is required."
    if len(first_name) < 2:
        return False, "First Name must be at least 2 characters long."

    # 2. Required Last Name
    last_name = str(data.get("last_name", "")).strip()
    if not last_name:
        return False, "Last Name is required."

    # 3. Required Doctor Code & Format
    doctor_code = str(data.get("doctor_code", "")).strip().upper()
    if not doctor_code:
        return False, "Doctor Code is required (e.g. DOC-2011)."
    if not re.match(r"^DOC-[A-Za-z0-9-]+$", doctor_code):
        return False, "Doctor Code must start with 'DOC-' followed by letters or digits."

    # 4. Check Doctor Code Uniqueness in SQLite Database
    try:
        with get_db_connection() as conn:
            if is_edit and current_doctor_id:
                query = "SELECT id FROM doctors WHERE doctor_code = ? AND id != ?;"
                row = conn.execute(query, (doctor_code, current_doctor_id)).fetchone()
            else:
                query = "SELECT id FROM doctors WHERE doctor_code = ?;"
                row = conn.execute(query, (doctor_code,)).fetchone()

            if row:
                return False, f"Doctor Code '{doctor_code}' is already assigned to another doctor."
    except Exception as e:
        return False, f"Database error verifying doctor code uniqueness: {e}"

    # 5. Required Specialization
    specialization = str(data.get("specialization", "")).strip()
    if not specialization:
        return False, "Clinical Specialization is required."

    # 6. Contact Phone Number
    phone = str(data.get("phone", "")).strip()
    if not phone:
        return False, "Contact Phone Number is required."
    digits = re.sub(r"\D", "", phone)
    if len(digits) < 10 or len(digits) > 15:
        return False, "Phone Number must contain between 10 and 15 digits."

    # 7. Email Address (Mandatory per Schema)
    email = str(data.get("email", "")).strip()
    if not email:
        return False, "Doctor Email Address is required."
    email_regex = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"
    if not re.match(email_regex, email):
        return False, "Invalid email address format (e.g., doctor@hospital.demo)."

    # 8. Consultation Fee (Non-negative numeric)
    fee_val = data.get("consultation_fee", "")
    try:
        fee_float = float(fee_val)
        if fee_float < 0:
            return False, "Consultation Fee must be zero or a positive amount."
    except (ValueError, TypeError):
        return False, "Consultation Fee must be a valid number (e.g., 500 or 750.0)."

    # 9. Room / OPD Number
    room_number = str(data.get("room_number", "")).strip()
    if not room_number:
        return False, "Consultation Room / OPD Number is required (e.g., Room-101)."

    # 10. Doctor Availability Status
    status = str(data.get("status", "Available")).strip()
    from config.constants import DOCTOR_STATUSES
    if status not in DOCTOR_STATUSES:
        return False, f"Invalid Status. Choose from: {', '.join(DOCTOR_STATUSES)}"

    return True, ""


def validate_appointment_data(
    data: Dict[str, any],
    is_edit: bool = False,
    current_appointment_id: Optional[int] = None,
) -> Tuple[bool, str]:
    """Validate appointment fields, format, foreign key existence, and code uniqueness.
    
    Returns:
        (is_valid, error_message): tuple with boolean and explanatory message.
    """
    from config.constants import APPOINTMENT_PRIORITIES, APPOINTMENT_STATUSES, TIME_SLOTS

    # 1. Required Appointment Code & Format
    appointment_code = str(data.get("appointment_code", "")).strip().upper()
    if not appointment_code:
        return False, "Appointment Code is required (e.g. APT-3043)."
    if not re.match(r"^APT-[A-Za-z0-9-]+$", appointment_code):
        return False, "Appointment Code must start with 'APT-' followed by letters or digits."

    # 2. Check Code Uniqueness in SQLite Database
    try:
        with get_db_connection() as conn:
            if is_edit and current_appointment_id:
                query = "SELECT id FROM appointments WHERE appointment_code = ? AND id != ?;"
                row = conn.execute(query, (appointment_code, current_appointment_id)).fetchone()
            else:
                query = "SELECT id FROM appointments WHERE appointment_code = ?;"
                row = conn.execute(query, (appointment_code,)).fetchone()

            if row:
                return False, f"Appointment Code '{appointment_code}' is already assigned to another appointment."
    except Exception as e:
        return False, f"Database error verifying appointment code uniqueness: {e}"

    # 3. Patient Foreign Key & Availability Validation
    patient_id = data.get("patient_id")
    appt_status = str(data.get("status", "Scheduled")).strip()
    try:
        patient_id = int(patient_id)
        with get_db_connection() as conn:
            p_row = conn.execute("SELECT id, status, first_name, last_name FROM patients WHERE id = ?;", (patient_id,)).fetchone()
            if not p_row:
                return False, f"Selected Patient (ID {patient_id}) does not exist in the database."
            if p_row["status"] == "Archived" and appt_status != "Cancelled":
                return False, f"Cannot schedule appointment for Archived patient ({p_row['first_name']} {p_row['last_name']}). Please reactivate the patient record first."
    except (ValueError, TypeError):
        return False, "A valid Patient must be selected from the list."

    # 4. Doctor Foreign Key & Availability Validation
    doctor_id = data.get("doctor_id")
    try:
        doctor_id = int(doctor_id)
        with get_db_connection() as conn:
            d_row = conn.execute("SELECT id, status, first_name, last_name FROM doctors WHERE id = ?;", (doctor_id,)).fetchone()
            if not d_row:
                return False, f"Selected Doctor (ID {doctor_id}) does not exist in the database."
            if d_row["status"] == "On Leave" and appt_status != "Cancelled":
                return False, f"Cannot schedule appointment: {d_row['first_name']} {d_row['last_name']} is currently marked 'On Leave'. Please choose an available physician."
    except (ValueError, TypeError):
        return False, "A valid Doctor must be selected from the list."

    # 5. Appointment Date Validation (YYYY-MM-DD)
    appt_date = str(data.get("appointment_date", "")).strip()
    if not appt_date:
        return False, "Appointment Date is required (format: YYYY-MM-DD)."
    try:
        datetime.strptime(appt_date, "%Y-%m-%d").date()
    except ValueError:
        return False, "Invalid Appointment Date. Please use format YYYY-MM-DD (e.g., 2026-10-15)."

    # 6. Time Slot Validation
    time_slot = str(data.get("time_slot", "")).strip()
    if not time_slot:
        return False, "Time Slot is required."
    if time_slot not in TIME_SLOTS:
        return False, f"Invalid Time Slot. Choose from standard clinic slots (e.g. '10:00 AM')."

    # 7. Reason for Visit
    reason = str(data.get("reason", "")).strip()
    if not reason:
        return False, "Reason for Visit is required (e.g., Cardiac screening, Routine checkup)."
    if len(reason) < 3:
        return False, "Reason for Visit must be at least 3 characters long."

    # 8. Priority Check
    priority = str(data.get("priority", "Normal")).strip()
    if priority not in APPOINTMENT_PRIORITIES:
        return False, f"Invalid Priority. Choose from: {', '.join(APPOINTMENT_PRIORITIES)}"

    # 9. Status Check
    status = str(data.get("status", "Scheduled")).strip()
    if status not in APPOINTMENT_STATUSES:
        return False, f"Invalid Status. Choose from: {', '.join(APPOINTMENT_STATUSES)}"

    # 10. Satisfaction Rating (Optional 1-5 integer)
    rating = data.get("satisfaction_rating")
    if rating is not None and str(rating).strip() != "" and str(rating).strip() != "None":
        try:
            r_int = int(rating)
            if r_int < 1 or r_int > 5:
                return False, "Satisfaction Rating must be between 1 and 5 stars."
        except ValueError:
            return False, "Satisfaction Rating must be an integer between 1 and 5."

    return True, ""


