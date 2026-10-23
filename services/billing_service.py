"""Billing, consultation fees, payment transactions, and receipt management service.
Handles invoice calculation, partial/full payment recording, unique receipt generation,
and formatted receipt export.
"""
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from config.constants import (
    BILL_STATUS_PAID,
    BILL_STATUS_PARTIALLY_PAID,
    BILL_STATUS_UNPAID,
    BILL_STATUSES,
    PAYMENT_METHODS,
    STUDENT_BRANCH,
    STUDENT_NAME,
    STUDENT_SECTION,
)
from database.connection import get_db_connection, get_db_cursor
from services.notification_service import create_notification


# ==============================================================================
# 1. Sequential Code Generators
# ==============================================================================

def get_next_bill_number() -> str:
    """Generate sequential bill invoice number: BILL-YYYYMM-XXXX."""
    ym = datetime.now().strftime("%Y%m")
    prefix = f"BILL-{ym}-"
    try:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT bill_number FROM bills WHERE bill_number LIKE ? ORDER BY id DESC LIMIT 1;",
                (f"{prefix}%",),
            ).fetchone()
            if row and row["bill_number"].startswith(prefix):
                seq = int(row["bill_number"].replace(prefix, "")) + 1
                return f"{prefix}{seq:04d}"
            return f"{prefix}0001"
    except Exception:
        return f"{prefix}0001"


def get_next_payment_code() -> str:
    """Generate sequential payment transaction code: PAY-YYYYMM-XXXX."""
    ym = datetime.now().strftime("%Y%m")
    prefix = f"PAY-{ym}-"
    try:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT payment_code FROM payments WHERE payment_code LIKE ? ORDER BY id DESC LIMIT 1;",
                (f"{prefix}%",),
            ).fetchone()
            if row and row["payment_code"].startswith(prefix):
                seq = int(row["payment_code"].replace(prefix, "")) + 1
                return f"{prefix}{seq:04d}"
            return f"{prefix}0001"
    except Exception:
        return f"{prefix}0001"


def get_next_receipt_number() -> str:
    """Generate sequential receipt number: REC-YYYYMM-XXXX."""
    ym = datetime.now().strftime("%Y%m")
    prefix = f"REC-{ym}-"
    try:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT receipt_number FROM receipts WHERE receipt_number LIKE ? ORDER BY id DESC LIMIT 1;",
                (f"{prefix}%",),
            ).fetchone()
            if row and row["receipt_number"].startswith(prefix):
                seq = int(row["receipt_number"].replace(prefix, "")) + 1
                return f"{prefix}{seq:04d}"
            return f"{prefix}0001"
    except Exception:
        return f"{prefix}0001"


# ==============================================================================
# 2. Bill Invoice Management
# ==============================================================================

def create_bill_for_appointment(appointment_id: int) -> Tuple[bool, str, Optional[int]]:
    """Automatically generate an invoice for a newly booked or existing appointment."""
    try:
        with get_db_connection() as conn:
            # Check if bill already exists for this appointment
            existing = conn.execute(
                "SELECT id, bill_number FROM bills WHERE appointment_id = ?;", (appointment_id,)
            ).fetchone()
            if existing:
                return True, f"Bill {existing['bill_number']} already exists.", existing["id"]

            # Fetch appointment details
            appt = conn.execute(
                """
                SELECT a.id, a.patient_id, a.doctor_id, a.consultation_fee, a.status,
                       d.consultation_fee AS doc_fee
                FROM appointments a
                JOIN doctors d ON a.doctor_id = d.id
                WHERE a.id = ?;
                """,
                (appointment_id,),
            ).fetchone()
            if not appt:
                return False, f"Appointment ID {appointment_id} not found.", None

            consultation_fee = float(appt["consultation_fee"] or appt["doc_fee"] or 500.0)
            total_amount = consultation_fee

            bill_number = get_next_bill_number()

            with get_db_cursor() as (conn2, cursor):
                cursor.execute("""
                    INSERT INTO bills (
                        bill_number, appointment_id, patient_id, doctor_id,
                        consultation_fee, additional_charges, discount_amount,
                        total_amount, amount_paid, outstanding_balance,
                        payment_status, notes
                    ) VALUES (?, ?, ?, ?, ?, 0.0, 0.0, ?, 0.0, ?, 'Unpaid', 'Standard consultation invoice.');
                """, (
                    bill_number,
                    appointment_id,
                    appt["patient_id"],
                    appt["doctor_id"],
                    consultation_fee,
                    total_amount,
                    total_amount,
                ))
                new_bill_id = cursor.lastrowid
                return True, f"Bill {bill_number} generated successfully.", new_bill_id

    except Exception as e:
        return False, f"Error generating bill: {e}", None


def get_bill_by_id(bill_id: int) -> Optional[Dict]:
    """Retrieve complete bill details with patient, doctor, and appointment metadata."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT b.*,
                       a.appointment_code, a.appointment_date, a.time_slot, a.status AS appointment_status,
                       p.patient_code, p.first_name AS pat_first_name, p.last_name AS pat_last_name, p.phone AS pat_phone, p.email AS pat_email,
                       d.doctor_code, d.first_name AS doc_first_name, d.last_name AS doc_last_name, d.specialization, d.room_number
                FROM bills b
                JOIN appointments a ON b.appointment_id = a.id
                JOIN patients p ON b.patient_id = p.id
                JOIN doctors d ON b.doctor_id = d.id
                WHERE b.id = ?;
            """, (bill_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error fetching bill {bill_id}: {e}")
        return None


def get_bill_by_appointment_id(appointment_id: int) -> Optional[Dict]:
    """Retrieve bill details by appointment ID."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT id FROM bills WHERE appointment_id = ?;", (appointment_id,))
            row = cursor.fetchone()
            if row:
                return get_bill_by_id(row["id"])
            return None
    except Exception as e:
        print(f"Error fetching bill for appointment {appointment_id}: {e}")
        return None


def get_bills(
    patient_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    payment_status: Optional[str] = None,
    search_query: Optional[str] = None,
) -> List[Dict]:
    """Fetch bills matching role or filter criteria."""
    try:
        with get_db_connection() as conn:
            query = """
                SELECT b.*,
                       a.appointment_code, a.appointment_date, a.time_slot,
                       p.patient_code, p.first_name AS pat_first_name, p.last_name AS pat_last_name, p.phone AS pat_phone,
                       d.doctor_code, d.first_name AS doc_first_name, d.last_name AS doc_last_name, d.specialization
                FROM bills b
                JOIN appointments a ON b.appointment_id = a.id
                JOIN patients p ON b.patient_id = p.id
                JOIN doctors d ON b.doctor_id = d.id
                WHERE 1=1
            """
            params = []

            if patient_id:
                query += " AND b.patient_id = ?"
                params.append(patient_id)

            if doctor_id:
                query += " AND b.doctor_id = ?"
                params.append(doctor_id)

            if payment_status and payment_status != "All":
                query += " AND b.payment_status = ?"
                params.append(payment_status)

            if search_query:
                q = f"%{search_query.strip()}%"
                query += """ AND (
                    b.bill_number LIKE ? OR a.appointment_code LIKE ? OR
                    p.patient_code LIKE ? OR p.first_name LIKE ? OR p.last_name LIKE ? OR
                    d.first_name LIKE ? OR d.last_name LIKE ?
                )"""
                params.extend([q, q, q, q, q, q, q])

            query += " ORDER BY b.id DESC;"
            cursor = conn.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching bills: {e}")
        return []


def get_billing_summary_statistics(
    patient_id: Optional[int] = None,
    doctor_id: Optional[int] = None,
    user: Optional[Dict] = None,
) -> Dict[str, float]:
    """Calculate aggregated billing KPIs scoped strictly by role or specific patient/doctor.
    
    Hospital Administrator & Staff: Authorized panoramic or operational totals.
    Doctor: Specific to consultations assigned to the doctor.
    Patient: Specific only to patient's own invoices and payments (never hospital-wide revenue).
    """
    target_patient_id = patient_id
    target_doctor_id = doctor_id
    if user:
        r = user.get("role")
        if r == "Patient" and user.get("linked_patient_id"):
            target_patient_id = user["linked_patient_id"]
        elif r == "Doctor" and user.get("linked_doctor_id"):
            target_doctor_id = user["linked_doctor_id"]

    try:
        with get_db_connection() as conn:
            sql = """
                SELECT 
                    COUNT(*) as total_bills,
                    COALESCE(SUM(total_amount), 0.0) as total_invoiced,
                    COALESCE(SUM(amount_paid), 0.0) as total_collected,
                    COALESCE(SUM(outstanding_balance), 0.0) as total_outstanding,
                    SUM(CASE WHEN payment_status = 'Paid' THEN 1 ELSE 0 END) as paid_count,
                    SUM(CASE WHEN payment_status = 'Partially Paid' THEN 1 ELSE 0 END) as partial_count,
                    SUM(CASE WHEN payment_status = 'Unpaid' THEN 1 ELSE 0 END) as unpaid_count
                FROM bills
                WHERE 1=1
            """
            params = []
            if target_patient_id:
                sql += " AND patient_id = ?"
                params.append(target_patient_id)
            elif target_doctor_id:
                sql += " AND doctor_id = ?"
                params.append(target_doctor_id)

            cursor = conn.execute(sql, tuple(params))
            row = cursor.fetchone()
            return dict(row) if row else {
                "total_bills": 0, "total_invoiced": 0.0, "total_collected": 0.0,
                "total_outstanding": 0.0, "paid_count": 0, "partial_count": 0, "unpaid_count": 0,
            }
    except Exception as e:
        print(f"Error computing billing stats: {e}")
        return {
            "total_bills": 0, "total_invoiced": 0.0, "total_collected": 0.0,
            "total_outstanding": 0.0, "paid_count": 0, "partial_count": 0, "unpaid_count": 0,
        }


def sync_unbilled_appointments() -> int:
    """Ensure every existing appointment in SQLite has a corresponding billing record."""
    synced_count = 0
    try:
        with get_db_connection() as conn:
            missing = conn.execute("""
                SELECT id FROM appointments
                WHERE id NOT IN (SELECT appointment_id FROM bills WHERE appointment_id IS NOT NULL);
            """).fetchall()
            for r in missing:
                ok, _, _ = create_bill_for_appointment(r["id"])
                if ok:
                    synced_count += 1
    except Exception as e:
        print(f"Error syncing unbilled appointments: {e}")
    return synced_count


# ==============================================================================
# 3. Payment Transactions & Receipt Generation
# ==============================================================================

def record_payment(
    bill_id: int,
    amount: float,
    payment_method: str = "Cash",
    reference_number: Optional[str] = None,
    recorded_by: str = "Front Desk Operator",
    notes: Optional[str] = None,
    user: Optional[Dict] = None,
) -> Tuple[bool, str, Optional[Dict]]:
    """Process full or partial payment against a bill, generate payment record and receipt.
    
    Returns:
        (success, message, receipt_dict)
    """
    from services.auth_service import get_current_user
    cur_u = user or get_current_user()
    if cur_u:
        role = cur_u.get("role")
        if role == "Doctor":
            return False, "Unauthorized: Doctors cannot collect or record payments.", None

    try:
        amt = float(amount)
        if amt <= 0:
            return False, "Payment amount must be greater than zero.", None
    except (ValueError, TypeError):
        return False, "Invalid payment amount entered.", None

    if payment_method not in PAYMENT_METHODS:
        return False, f"Invalid payment method. Choose from: {', '.join(PAYMENT_METHODS)}", None

    try:
        with get_db_connection() as conn:
            bill = conn.execute("SELECT * FROM bills WHERE id = ?;", (bill_id,)).fetchone()
            if not bill:
                return False, f"Bill ID {bill_id} not found.", None

            # Ownership check for patient role
            if cur_u and cur_u.get("role") == "Patient":
                linked_pid = cur_u.get("linked_patient_id")
                if not linked_pid or int(bill["patient_id"]) != int(linked_pid):
                    return False, "Security Violation: You can only pay your own invoices.", None

            # Idempotency check if reference number provided
            if reference_number:
                existing_p = conn.execute(
                    "SELECT id FROM payments WHERE bill_id = ? AND reference_number = ? AND status = 'Success';",
                    (bill_id, reference_number),
                ).fetchone()
                if existing_p:
                    rec_row = conn.execute("SELECT receipt_number FROM receipts WHERE payment_id = ?;", (existing_p["id"],)).fetchone()
                    if rec_row:
                        return True, "Payment already recorded (idempotent request).", get_receipt_by_number(rec_row["receipt_number"])

            outstanding = float(bill["outstanding_balance"])
            if outstanding <= 0:
                return False, "This bill is already fully settled (No balance due).", None

            if amt > (outstanding + 0.001):
                return False, f"Payment amount (Rs. {amt:.2f}) cannot exceed outstanding balance (Rs. {outstanding:.2f}).", None

            # Calculate new balances
            new_paid = float(bill["amount_paid"]) + amt
            new_outstanding = max(0.0, float(bill["total_amount"]) - new_paid)
            new_status = BILL_STATUS_PAID if new_outstanding == 0.0 else BILL_STATUS_PARTIALLY_PAID

            payment_code = get_next_payment_code()
            receipt_number = get_next_receipt_number()
            today_str = datetime.now().strftime("%Y-%m-%d")

            with get_db_cursor() as (conn2, cursor):
                # 1. Update Bill
                cursor.execute("""
                    UPDATE bills SET
                        amount_paid = ?,
                        outstanding_balance = ?,
                        payment_status = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?;
                """, (new_paid, new_outstanding, new_status, bill_id))

                # 2. Insert Payment
                cursor.execute("""
                    INSERT INTO payments (
                        payment_code, bill_id, amount, payment_date, payment_method,
                        reference_number, recorded_by, status, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Success', ?);
                """, (
                    payment_code,
                    bill_id,
                    amt,
                    today_str,
                    payment_method,
                    reference_number or payment_code,
                    recorded_by,
                    notes or "Payment recorded successfully.",
                ))
                payment_id = cursor.lastrowid

                # 3. Create Receipt details
                receipt_details = (
                    f"Bill No: {bill['bill_number']} | Paid: Rs. {amt:.2f} | "
                    f"Method: {payment_method} | Balance Due: Rs. {new_outstanding:.2f}"
                )
                cursor.execute("""
                    INSERT INTO receipts (
                        receipt_number, payment_id, bill_id, receipt_date, issued_by, receipt_details
                    ) VALUES (?, ?, ?, ?, ?, ?);
                """, (
                    receipt_number,
                    payment_id,
                    bill_id,
                    today_str,
                    recorded_by,
                    receipt_details,
                ))
                receipt_id = cursor.lastrowid

        # Trigger in-app notification for patient
        notif_msg = (
            f"Payment of Rs. {amt:.2f} recorded for Bill {bill['bill_number']} via {payment_method}. "
            f"Official Receipt: {receipt_number}."
        )
        create_notification(
            patient_id=bill["patient_id"],
            title="Payment Received & Receipt Generated",
            message=notif_msg,
            notification_type="Billing",
            appointment_id=bill["appointment_id"],
        )

        receipt_obj = get_receipt_by_number(receipt_number)
        return True, f"Payment recorded successfully. Receipt #{receipt_number} issued.", receipt_obj

    except Exception as e:
        return False, f"Failed to record payment: {e}", None


def get_payments_for_bill(bill_id: int) -> List[Dict]:
    """Retrieve all payment transactions recorded for a bill."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT p.*, r.receipt_number
                FROM payments p
                LEFT JOIN receipts r ON r.payment_id = p.id
                WHERE p.bill_id = ?
                ORDER BY p.id DESC;
            """, (bill_id,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching payments for bill {bill_id}: {e}")
        return []


def get_receipt_by_number(receipt_number: str) -> Optional[Dict]:
    """Retrieve complete receipt information including payment, bill, patient, and doctor."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT r.*,
                       pay.payment_code, pay.amount, pay.payment_method, pay.reference_number, pay.payment_date, pay.recorded_by,
                       b.bill_number, b.total_amount, b.amount_paid, b.outstanding_balance, b.payment_status,
                       a.appointment_code, a.appointment_date, a.time_slot,
                       p.patient_code, p.first_name AS pat_first_name, p.last_name AS pat_last_name, p.phone AS pat_phone,
                       d.doctor_code, d.first_name AS doc_first_name, d.last_name AS doc_last_name, d.specialization, d.room_number
                FROM receipts r
                JOIN payments pay ON r.payment_id = pay.id
                JOIN bills b ON r.bill_id = b.id
                JOIN appointments a ON b.appointment_id = a.id
                JOIN patients p ON b.patient_id = p.id
                JOIN doctors d ON b.doctor_id = d.id
                WHERE r.receipt_number = ?;
            """, (receipt_number.strip(),))
            row = cursor.fetchone()
            return dict(row) if row else None
    except Exception as e:
        print(f"Error fetching receipt {receipt_number}: {e}")
        return None


def get_receipt_by_payment_id(payment_id: int) -> Optional[Dict]:
    """Retrieve receipt associated with a payment ID."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("SELECT receipt_number FROM receipts WHERE payment_id = ?;", (payment_id,))
            row = cursor.fetchone()
            if row:
                return get_receipt_by_number(row["receipt_number"])
            return None
    except Exception as e:
        print(f"Error fetching receipt for payment {payment_id}: {e}")
        return None


def generate_receipt_text(receipt_number: str) -> str:
    """Format a clean, printable ASCII receipt slip suitable for viewing or exporting."""
    rec = get_receipt_by_number(receipt_number)
    if not rec:
        return f"Error: Receipt '{receipt_number}' not found."

    line_sep = "═" * 68
    dash_sep = "─" * 68

    slip = f"""
{line_sep}
                  HOSPITAL MANAGEMENT SYSTEM
            Clinical Quality & User Satisfaction (Q08)
                 OFFICIAL CONSULTATION RECEIPT
{line_sep}
  Receipt Number    : {rec['receipt_number']}
  Issue Date        : {rec['receipt_date']}
  Issued By         : {rec['issued_by']}
{dash_sep}
  PATIENT INFORMATION:
    Patient Code    : {rec['patient_code']}
    Patient Name    : {rec['pat_first_name']} {rec['pat_last_name']}
    Contact Phone   : {rec['pat_phone']}

  CONSULTATION DETAILS:
    Appointment Ref : {rec['appointment_code']}
    Consulting Dr.  : {rec['doc_first_name']} {rec['doc_last_name']} ({rec['specialization']})
    OPD / Room No.  : {rec['room_number']}
    Date & Time     : {rec['appointment_date']} at {rec['time_slot']}
{dash_sep}
  PAYMENT BREAKDOWN:
    Invoice Number  : {rec['bill_number']}
    Total Invoiced  : Rs. {float(rec['total_amount']):.2f}
    Amount Received : Rs. {float(rec['amount']):.2f}
    Payment Mode    : {rec['payment_method']}
    Payment Ref     : {rec['reference_number'] or 'N/A'}
    Transaction Code: {rec['payment_code']}
    Cumulative Paid : Rs. {float(rec['amount_paid']):.2f}
    Balance Due     : Rs. {float(rec['outstanding_balance']):.2f}
    Bill Status     : {rec['payment_status']}
{dash_sep}
  TERMS & CONDITIONS:
  1. This receipt is computer-generated and valid without physical seal.
  2. Consultation fee is valid only for the scheduled date and slot.
  3. Keep this receipt for any follow-up consultations or refund inquiries.
  4. Project: BBAT104 Fundamentals of TQM | Student: {STUDENT_NAME} ({STUDENT_SECTION})
{line_sep}
"""
    return slip
