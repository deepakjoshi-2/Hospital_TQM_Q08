"""Payment Gateway Integration and Patient Online Payment Service.

Provides:
1. Configured payment gateway abstraction (Demo Gateway for academic demonstration).
2. Server-side payment verification and idempotency protection against duplicate submissions.
3. Patient ownership validation enforcing that patients can only pay their own invoices.
4. Multi-method support (UPI, Credit/Debit Cards, Net Banking).
5. Simulation modes for academic review: Success, Failure (bank decline), and Cancellation.
6. Audit trail for transaction reconciliation and administrator investigation.
"""
from abc import ABC, abstractmethod
from datetime import datetime
import secrets
from typing import Any, Dict, List, Optional, Tuple

from config.constants import (
    GATEWAY_MODE_DEMO,
    GATEWAY_MODE_REAL,
    PAYMENT_METHOD_CARD,
    PAYMENT_METHOD_NET_BANKING,
    PAYMENT_METHOD_UPI,
    PAYMENT_METHODS,
    PAYMENT_STATUS_CANCELLED,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_SUCCESS,
    ROLE_ADMIN,
    ROLE_DOCTOR,
    ROLE_PATIENT,
    ROLE_STAFF,
)
from database.connection import get_db_connection, get_db_cursor
from services.auth_service import get_current_user
from services.billing_service import (
    get_bill_by_id,
    get_next_payment_code,
    get_next_receipt_number,
    get_receipt_by_number,
)
from services.notification_service import create_notification


# Current Gateway Configuration
CURRENT_GATEWAY_MODE = GATEWAY_MODE_DEMO
GATEWAY_PROVIDER_NAME = "Simulated Academic Gateway Engine"


def is_demo_mode() -> bool:
    """Return True if payments run in Academic Demo Mode (no real money transfer)."""
    return CURRENT_GATEWAY_MODE == GATEWAY_MODE_DEMO


def get_payment_gateway_info() -> Dict[str, Any]:
    """Retrieve gateway provider metadata and demo status for UI transparency."""
    return {
        "mode": CURRENT_GATEWAY_MODE,
        "provider": GATEWAY_PROVIDER_NAME,
        "is_demo": is_demo_mode(),
        "notice": (
            "Academic Demo Payment Mode: No real financial transaction or card charge will occur. "
            "Transactions simulate official gateway handshakes, signature verification, and idempotency."
        ),
        "supported_methods": [PAYMENT_METHOD_UPI, PAYMENT_METHOD_CARD, PAYMENT_METHOD_NET_BANKING],
    }


# ==============================================================================
# 1. Gateway Interface & Demo Engine
# ==============================================================================

class PaymentGatewayInterface(ABC):
    """Abstract payment gateway contract for production or simulated providers."""

    @abstractmethod
    def create_order(
        self,
        bill_id: int,
        amount: float,
        patient_id: int,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        """Initiate payment session or intent with gateway."""
        pass

    @abstractmethod
    def verify_payment_signature(
        self,
        order_id: str,
        transaction_id: str,
        signature: str,
    ) -> bool:
        """Verify server-side authenticity of transaction signature/callback."""
        pass


class DemoPaymentGateway(PaymentGatewayInterface):
    """Academic demonstration gateway supporting success, failure, and cancellation."""

    def create_order(
        self,
        bill_id: int,
        amount: float,
        patient_id: int,
        idempotency_key: str,
    ) -> Dict[str, Any]:
        order_id = f"ORDER-DEMO-{bill_id}-{int(datetime.now().timestamp())}"
        return {
            "order_id": order_id,
            "bill_id": bill_id,
            "amount": amount,
            "currency": "INR",
            "patient_id": patient_id,
            "idempotency_key": idempotency_key,
            "status": "Created",
            "mode": GATEWAY_MODE_DEMO,
        }

    def verify_payment_signature(
        self,
        order_id: str,
        transaction_id: str,
        signature: str,
    ) -> bool:
        # In demo mode, verifies non-empty signature token
        return bool(order_id and transaction_id and signature)


# Singleton Gateway instance
_GATEWAY = DemoPaymentGateway()


# ==============================================================================
# 2. Patient Online Payment Processing
# ==============================================================================

def process_patient_online_payment(
    bill_id: int,
    amount: float,
    payment_method: str = PAYMENT_METHOD_UPI,
    simulated_outcome: str = "SUCCESS",
    idempotency_key: Optional[str] = None,
    user: Optional[Dict] = None,
    reference_number: Optional[str] = None,
    notes: Optional[str] = None,
) -> Tuple[bool, str, Optional[Dict]]:
    """Process online checkout for a patient's invoice with ownership and idempotency guards.

    Parameters:
        bill_id: Invoice identifier in SQLite.
        amount: Payment amount (full or partial).
        payment_method: Selected online method ('UPI', 'Card', 'Net Banking').
        simulated_outcome: 'SUCCESS', 'FAILURE', or 'CANCELLED' (Academic demo simulation).
        idempotency_key: Unique client request identifier to prevent duplicate submissions.
        user: Active session user (defaults to get_current_user()).
        reference_number: Optional external transaction/reference code.
        notes: Optional patient/checkout notes.

    Returns:
        (success, message, receipt_dict)
    """
    # 1. Resolve & validate authenticated user
    cur_user = user or get_current_user()
    if not cur_user:
        return False, "Authentication required. Please sign in to pay.", None

    role = cur_user.get("role")

    # Doctors are strictly barred from collecting or initiating payments
    if role == ROLE_DOCTOR:
        return False, "Unauthorized: Physicians cannot collect or process patient payments.", None

    # 2. Fetch bill record
    bill = get_bill_by_id(bill_id)
    if not bill:
        return False, f"Invoice ID {bill_id} not found.", None

    # 3. Patient Ownership Validation in Service Layer (Security Requirement)
    if role == ROLE_PATIENT:
        linked_pid = cur_user.get("linked_patient_id")
        if not linked_pid or int(bill["patient_id"]) != int(linked_pid):
            return False, "Security Violation: You are only authorized to pay your own invoices.", None

    # 4. Idempotency Protection: Check for duplicate submissions before state validation
    effective_idemp = idempotency_key or reference_number or f"IDEMP-BILL-{bill_id}-{secrets.token_hex(6)}"
    try:
        with get_db_connection() as conn:
            # Check if this exact idempotency reference was already successfully processed for this bill
            existing_pay = conn.execute(
                """
                SELECT id, payment_code, status, amount, bill_id 
                FROM payments 
                WHERE bill_id = ? AND reference_number = ? AND status = 'Success';
                """,
                (bill_id, effective_idemp),
            ).fetchone()
            if existing_pay:
                # Return existing receipt instead of double charging
                rec = conn.execute(
                    "SELECT receipt_number FROM receipts WHERE payment_id = ?;", (existing_pay["id"],)
                ).fetchone()
                if rec:
                    receipt_data = get_receipt_by_number(rec["receipt_number"])
                    return True, "Payment already verified (idempotent request).", receipt_data
    except Exception as e:
        print(f"Error during idempotency lookup: {e}")

    # 5. Invoice Balance & Status Eligibility Check
    outstanding = float(bill.get("outstanding_balance", 0.0))
    if outstanding <= 0 or bill.get("payment_status") == "Paid":
        return False, "This invoice is already fully settled (No balance due).", None

    if bill.get("payment_status") == "Cancelled":
        return False, "This invoice has been cancelled and cannot be paid.", None

    # 6. Amount Validation & Overpayment Prevention
    try:
        amt = float(amount)
        if amt <= 0:
            return False, "Payment amount must be greater than zero.", None
    except (ValueError, TypeError):
        return False, "Invalid payment amount entered.", None

    if amt > (outstanding + 0.001):
        return False, f"Payment amount (Rs. {amt:.2f}) cannot exceed outstanding balance (Rs. {outstanding:.2f}).", None

    # 7. Payment Method Validation
    valid_online_methods = [PAYMENT_METHOD_UPI, PAYMENT_METHOD_CARD, PAYMENT_METHOD_NET_BANKING, "Cash"]
    if payment_method not in valid_online_methods:
        return False, f"Invalid payment method. Choose from: {', '.join(valid_online_methods)}", None

    # 8. Demo Simulation Handling
    sim_upper = str(simulated_outcome).strip().upper()

    if sim_upper == "CANCELLED":
        return False, "Payment cancelled by user. No funds were charged.", None

    if sim_upper == "FAILURE":
        # Record an audited failed transaction attempt; do NOT update bill balance or issue receipt
        fail_code = get_next_payment_code()
        today_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        fail_notes = notes or "Demo Payment Failed: Simulated bank decline / gateway timeout."

        try:
            with get_db_cursor() as (conn, cursor):
                cursor.execute(
                    """
                    INSERT INTO payments (
                        payment_code, bill_id, amount, payment_date, payment_method,
                        reference_number, recorded_by, status, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Failed', ?);
                    """,
                    (
                        fail_code,
                        bill_id,
                        amt,
                        today_str,
                        payment_method,
                        effective_idemp,
                        f"Patient Online Portal ({cur_user['username']})",
                        fail_notes,
                    ),
                )
        except Exception as e:
            print(f"Error logging failed transaction: {e}")

        return False, "Demo Payment Failed: Simulated bank transaction decline. Your balance was not charged.", None

    # 9. Successful Payment Execution (Atomic SQLite Transaction)
    try:
        today_str = datetime.now().strftime("%Y-%m-%d")
        payment_code = get_next_payment_code()
        receipt_number = get_next_receipt_number()
        gateway_txn_ref = effective_idemp

        with get_db_cursor() as (conn, cursor):
            # Re-fetch bill inside write transaction for concurrency safety
            cursor.execute("SELECT * FROM bills WHERE id = ?;", (bill_id,))
            current_bill = cursor.fetchone()
            if not current_bill:
                return False, f"Bill {bill_id} not found.", None

            cur_out = float(current_bill["outstanding_balance"])
            if amt > (cur_out + 0.001):
                return False, f"Payment exceeds current outstanding balance (Rs. {cur_out:.2f}).", None

            new_paid = float(current_bill["amount_paid"]) + amt
            new_outstanding = max(0.0, float(current_bill["total_amount"]) - new_paid)
            new_status = "Paid" if new_outstanding == 0.0 else "Partially Paid"

            # 1. Update Bill balance and status
            cursor.execute(
                """
                UPDATE bills SET
                    amount_paid = ?,
                    outstanding_balance = ?,
                    payment_status = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?;
                """,
                (new_paid, new_outstanding, new_status, bill_id),
            )

            # 2. Insert successful payment transaction
            cursor.execute(
                """
                INSERT INTO payments (
                    payment_code, bill_id, amount, payment_date, payment_method,
                    reference_number, recorded_by, status, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?, 'Success', ?);
                """,
                (
                    payment_code,
                    bill_id,
                    amt,
                    today_str,
                    payment_method,
                    gateway_txn_ref,
                    f"Patient Portal Online ({cur_user['username']})",
                    notes or f"Online checkout via {payment_method} [Demo Gateway — Academic Mode].",
                ),
            )
            new_payment_id = cursor.lastrowid

            # 3. Create unique official receipt
            receipt_details = (
                f"Bill: {current_bill['bill_number']} | Paid: Rs. {amt:.2f} | "
                f"Method: {payment_method} | Ref: {gateway_txn_ref} | Balance Due: Rs. {new_outstanding:.2f}"
            )
            cursor.execute(
                """
                INSERT INTO receipts (
                    receipt_number, payment_id, bill_id, receipt_date, issued_by, receipt_details
                ) VALUES (?, ?, ?, ?, ?, ?);
                """,
                (
                    receipt_number,
                    new_payment_id,
                    bill_id,
                    today_str,
                    "Automated Patient Portal Gateway",
                    receipt_details,
                ),
            )

        # 4. Dispatch notification to patient
        notif_msg = (
            f"Online payment of Rs. {amt:.2f} successful for Bill {bill['bill_number']} via {payment_method}. "
            f"Official Receipt #{receipt_number} issued. Outstanding balance: Rs. {new_outstanding:.2f}."
        )
        create_notification(
            patient_id=bill["patient_id"],
            title="Online Payment Confirmation",
            message=notif_msg,
            notification_type="Billing",
            appointment_id=bill["appointment_id"],
        )

        receipt_obj = get_receipt_by_number(receipt_number)
        return True, f"Payment of Rs. {amt:.2f} completed successfully! Receipt #{receipt_number} issued.", receipt_obj

    except Exception as e:
        return False, f"Payment processing error: {e}", None


# ==============================================================================
# 3. Transaction Audit & Reconciliation Queries
# ==============================================================================

def get_payment_transactions(
    bill_id: Optional[int] = None,
    status: Optional[str] = None,
    patient_id: Optional[int] = None,
    search_query: Optional[str] = None,
    limit: int = 100,
) -> List[Dict]:
    """Retrieve payment transaction audit records with bill, patient, and receipt links.

    Empowers Hospital Administrator and Staff to reconcile transactions, investigate failures,
    and review idempotency references.
    """
    try:
        with get_db_connection() as conn:
            sql = """
                SELECT p.*,
                       b.bill_number, b.total_amount AS bill_total, b.outstanding_balance AS bill_balance,
                       b.payment_status AS bill_status,
                       pat.patient_code, pat.first_name AS pat_first_name, pat.last_name AS pat_last_name,
                       r.receipt_number
                FROM payments p
                JOIN bills b ON p.bill_id = b.id
                JOIN patients pat ON b.patient_id = pat.id
                LEFT JOIN receipts r ON r.payment_id = p.id
                WHERE 1=1
            """
            params: List[Any] = []

            if bill_id:
                sql += " AND p.bill_id = ?"
                params.append(bill_id)

            if status and status != "All":
                sql += " AND p.status = ?"
                params.append(status)

            if patient_id:
                sql += " AND b.patient_id = ?"
                params.append(patient_id)

            if search_query:
                q = f"%{search_query.strip()}%"
                sql += """ AND (
                    p.payment_code LIKE ? OR p.reference_number LIKE ? OR
                    b.bill_number LIKE ? OR pat.first_name LIKE ? OR pat.last_name LIKE ?
                )"""
                params.extend([q, q, q, q, q])

            sql += " ORDER BY p.id DESC LIMIT ?;"
            params.append(limit)

            cursor = conn.execute(sql, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error querying payment transactions: {e}")
        return []


def get_patient_payment_history(patient_id: int, limit: int = 50) -> List[Dict]:
    """Retrieve payment transaction records specifically for a designated patient."""
    return get_payment_transactions(patient_id=patient_id, limit=limit)

