"""Comprehensive Unit & Integration Test Suite for Patient Online Payment & Role-Based Billing Controls.

Covers:
1. Payment Gateway Mode & Academic Demo metadata (is_demo_mode, get_payment_gateway_info).
2. Patient Portal Online Checkout: Full and Partial payments with balance tracking and receipts.
3. Patient Ownership Security: Strict rejection when attempting to pay another patient's bill.
4. Demo Simulation - Bank Failure: Status 'Failed' logged in audit trail, bill untouched, no receipt.
5. Demo Simulation - Cancellation: Checkout cancelled, bill untouched, no receipt.
6. Idempotency Protection: Duplicate submission prevention with identical idempotency key.
7. Overpayment Protection: Strict rejection of amounts exceeding outstanding balance or <= 0.
8. Doctor Billing Restrictions: Strictly barred from online checkout or recording cashier payments.
9. Staff Operational Billing: Authorized offline recording (Cash, Card, DD), auto-attribution.
10. Administrator Control & Reconciliation: Full audit trail queries and transaction investigation.
11. Patient Payment History Scoping: Patient-specific transaction retrieval.
12. UI Role Billing View Scoping: Instantiation and role view rendering across all four user roles.
"""
import os
import tempfile
import unittest
import customtkinter as ctk

from config.constants import (
    BILL_STATUS_PAID,
    BILL_STATUS_PARTIALLY_PAID,
    BILL_STATUS_UNPAID,
    GATEWAY_MODE_DEMO,
    PAYMENT_METHOD_CARD,
    PAYMENT_METHOD_NET_BANKING,
    PAYMENT_METHOD_UPI,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_SUCCESS,
    ROLE_ADMIN,
    ROLE_DOCTOR,
    ROLE_PATIENT,
    ROLE_STAFF,
    STATUS_CONFIRMED,
    TIME_SLOTS,
)
from database.connection import get_db_connection
from database.seed_data import seed_database
from services.appointment_service import create_appointment
from services.auth_service import (
    ROLE_PERMISSIONS,
    authenticate_user,
    has_permission,
    login,
    logout,
    set_current_user,
)
from services.billing_service import (
    create_bill_for_appointment,
    get_bill_by_appointment_id,
    get_bill_by_id,
    get_billing_summary_statistics,
    get_bills,
    get_receipt_by_number,
    record_payment,
)
from services.payment_service import (
    get_patient_payment_history,
    get_payment_gateway_info,
    get_payment_transactions,
    is_demo_mode,
    process_patient_online_payment,
)
from ui.components.billing_modals import PatientPaymentModal
from ui.views.billing_view import BillingView


class TestPatientPaymentAndBillingControls(unittest.TestCase):
    """Test suite verifying online payments, demo gateway simulations, and role permissions."""

    @classmethod
    def setUpClass(cls):
        ctk.set_appearance_mode("Dark")
        cls.root = ctk.CTk()
        cls.root.geometry("1100x650")
        cls.root.withdraw()
        cls.root.update()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        """Set up clean isolated database for each test case."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = os.path.join(self.temp_dir.name, "test_payments.db")
        os.environ["HOSPITAL_DB_PATH"] = self.test_db_path
        seed_database(self.test_db_path)
        logout()
        self._appt_seq = 100

        with get_db_connection(self.test_db_path) as conn:
            patients = conn.execute("SELECT id, patient_code FROM patients ORDER BY id LIMIT 2;").fetchall()
            doctors = conn.execute("SELECT id, doctor_code, consultation_fee FROM doctors ORDER BY id LIMIT 2;").fetchall()
            self.p1_id = patients[0]["id"]
            self.p2_id = patients[1]["id"]
            self.d1_id = doctors[0]["id"]
            self.d1_fee = float(doctors[0]["consultation_fee"])

            # User accounts
            admin_u = conn.execute("SELECT * FROM users WHERE username = 'admin';").fetchone()
            staff_u = conn.execute("SELECT * FROM users WHERE username = 'staff_reception';").fetchone()
            doc_u = conn.execute("SELECT * FROM users WHERE username = 'dr_arun';").fetchone()
            pat_u = conn.execute("SELECT * FROM users WHERE username = 'patient_aarav';").fetchone()

            self.admin_user = dict(admin_u) if admin_u else {}
            self.staff_user = dict(staff_u) if staff_u else {}
            self.doc_user = dict(doc_u) if doc_u else {}
            self.pat_user = dict(pat_u) if pat_u else {}

            # Ensure patient user is linked to p1_id for tests
            self.pat_user["linked_patient_id"] = self.p1_id
            conn.execute("UPDATE users SET linked_patient_id = ? WHERE username = 'patient_aarav';", (self.p1_id,))

    def tearDown(self):
        """Clean up test environment."""
        logout()
        os.environ.pop("HOSPITAL_DB_PATH", None)
        self.temp_dir.cleanup()

    def _create_test_bill(self, patient_id: int, doctor_id: int) -> int:
        """Helper to create an appointment and its linked bill with unique slot."""
        self._appt_seq += 1
        day = 10 + (self._appt_seq % 18)
        slot_idx = self._appt_seq % len(TIME_SLOTS)
        time_slot = TIME_SLOTS[slot_idx]
        appt_data = {
            "appointment_code": f"APT-TST-{self._appt_seq}",
            "patient_id": patient_id,
            "doctor_id": doctor_id,
            "appointment_date": f"2026-12-{day:02d}",
            "time_slot": time_slot,
            "reason": "Test Consultation",
            "priority": "Normal",
            "status": STATUS_CONFIRMED,
        }
        ok, msg, appt_id = create_appointment(appt_data)
        self.assertTrue(ok, f"Failed to create test appointment: {msg}")
        bill = get_bill_by_appointment_id(appt_id)
        self.assertIsNotNone(bill)
        return bill["id"]

    # --------------------------------------------------------------------------
    # 1. Gateway Mode and Metadata
    # --------------------------------------------------------------------------
    def test_01_gateway_mode_and_metadata(self):
        """Verify get_payment_gateway_info returns Demo mode metadata and academic disclaimer."""
        self.assertTrue(is_demo_mode())
        info = get_payment_gateway_info()
        self.assertEqual(info["mode"], GATEWAY_MODE_DEMO)
        self.assertTrue(info["is_demo"])
        self.assertIn("Academic Demo Payment Mode", info["notice"])
        self.assertIn("Simulated", info["provider"])
        self.assertIn(PAYMENT_METHOD_UPI, info["supported_methods"])
        self.assertIn(PAYMENT_METHOD_CARD, info["supported_methods"])
        self.assertIn(PAYMENT_METHOD_NET_BANKING, info["supported_methods"])

    # --------------------------------------------------------------------------
    # 2. Patient Online Payment - Full Payment
    # --------------------------------------------------------------------------
    def test_02_patient_pay_own_bill_full_payment(self):
        """Verify patient can pay full invoice online, updating bill to Paid and generating receipt."""
        bill_id = self._create_test_bill(self.p1_id, self.d1_id)
        bill = get_bill_by_id(bill_id)
        due_amount = float(bill["outstanding_balance"])

        ok, msg, receipt = process_patient_online_payment(
            bill_id=bill_id,
            amount=due_amount,
            payment_method=PAYMENT_METHOD_UPI,
            simulated_outcome="SUCCESS",
            idempotency_key="IDEMP-FULL-001",
            user=self.pat_user,
        )

        self.assertTrue(ok, msg)
        self.assertIn("completed successfully", msg)
        self.assertIsNotNone(receipt)
        self.assertTrue(receipt["receipt_number"].startswith("REC-"))

        # Verify bill state in database
        updated_bill = get_bill_by_id(bill_id)
        self.assertEqual(updated_bill["payment_status"], BILL_STATUS_PAID)
        self.assertEqual(float(updated_bill["amount_paid"]), due_amount)
        self.assertEqual(float(updated_bill["outstanding_balance"]), 0.0)

        # Verify transaction in payments table
        transactions = get_payment_transactions(bill_id=bill_id)
        self.assertEqual(len(transactions), 1)
        self.assertEqual(transactions[0]["status"], PAYMENT_STATUS_SUCCESS)
        self.assertEqual(transactions[0]["payment_method"], PAYMENT_METHOD_UPI)

    # --------------------------------------------------------------------------
    # 3. Patient Online Payment - Partial Payment Progression
    # --------------------------------------------------------------------------
    def test_03_patient_pay_own_bill_partial_payment(self):
        """Verify partial payment updates bill to Partially Paid, and subsequent payment settles it."""
        bill_id = self._create_test_bill(self.p1_id, self.d1_id)
        bill = get_bill_by_id(bill_id)
        total_fee = float(bill["outstanding_balance"])
        part1 = round(total_fee / 2.0, 2)
        part2 = round(total_fee - part1, 2)

        # 1st Payment: Partial
        ok1, msg1, rec1 = process_patient_online_payment(
            bill_id=bill_id,
            amount=part1,
            payment_method=PAYMENT_METHOD_CARD,
            simulated_outcome="SUCCESS",
            idempotency_key="IDEMP-PARTIAL-001",
            user=self.pat_user,
        )
        self.assertTrue(ok1, msg1)
        self.assertIsNotNone(rec1)

        bill_step1 = get_bill_by_id(bill_id)
        self.assertEqual(bill_step1["payment_status"], BILL_STATUS_PARTIALLY_PAID)
        self.assertEqual(float(bill_step1["amount_paid"]), part1)
        self.assertEqual(float(bill_step1["outstanding_balance"]), part2)

        # 2nd Payment: Settle remaining balance
        ok2, msg2, rec2 = process_patient_online_payment(
            bill_id=bill_id,
            amount=part2,
            payment_method=PAYMENT_METHOD_NET_BANKING,
            simulated_outcome="SUCCESS",
            idempotency_key="IDEMP-PARTIAL-002",
            user=self.pat_user,
        )
        self.assertTrue(ok2, msg2)
        self.assertIsNotNone(rec2)

        bill_step2 = get_bill_by_id(bill_id)
        self.assertEqual(bill_step2["payment_status"], BILL_STATUS_PAID)
        self.assertEqual(float(bill_step2["amount_paid"]), total_fee)
        self.assertEqual(float(bill_step2["outstanding_balance"]), 0.0)

        # Total 2 payment records in payments table
        txns = get_payment_transactions(bill_id=bill_id)
        self.assertEqual(len(txns), 2)

    # --------------------------------------------------------------------------
    # 4. Patient Ownership Validation (Security Constraint)
    # --------------------------------------------------------------------------
    def test_04_patient_cannot_pay_another_patients_bill(self):
        """Verify service layer strictly prevents Patient A from paying Patient B's invoice."""
        # Bill belongs to Patient 2 (p2_id)
        bill_id_p2 = self._create_test_bill(self.p2_id, self.d1_id)
        bill_before = get_bill_by_id(bill_id_p2)
        due_p2 = float(bill_before["outstanding_balance"])

        # Patient 1 tries to pay Patient 2's bill
        ok, msg, receipt = process_patient_online_payment(
            bill_id=bill_id_p2,
            amount=due_p2,
            payment_method=PAYMENT_METHOD_UPI,
            simulated_outcome="SUCCESS",
            idempotency_key="IDEMP-ATTACK-001",
            user=self.pat_user,  # linked to p1_id
        )

        self.assertFalse(ok)
        self.assertIn("Security Violation", msg)
        self.assertIsNone(receipt)

        # Bill for Patient 2 must remain completely untouched
        bill_after = get_bill_by_id(bill_id_p2)
        self.assertEqual(bill_after["payment_status"], BILL_STATUS_UNPAID)
        self.assertEqual(float(bill_after["amount_paid"]), 0.0)
        self.assertEqual(float(bill_after["outstanding_balance"]), due_p2)

    # --------------------------------------------------------------------------
    # 5. Demo Simulation: Bank Failure
    # --------------------------------------------------------------------------
    def test_05_demo_simulation_bank_failure(self):
        """Verify simulated bank failure logs 'Failed' audit transaction, leaves bill balance untouched, no receipt."""
        bill_id = self._create_test_bill(self.p1_id, self.d1_id)
        bill_before = get_bill_by_id(bill_id)
        due = float(bill_before["outstanding_balance"])

        ok, msg, receipt = process_patient_online_payment(
            bill_id=bill_id,
            amount=due,
            payment_method=PAYMENT_METHOD_CARD,
            simulated_outcome="FAILURE",
            idempotency_key="IDEMP-FAIL-001",
            user=self.pat_user,
        )

        self.assertFalse(ok)
        self.assertIn("Demo Payment Failed", msg)
        self.assertIsNone(receipt)

        # Bill balance must remain completely untouched
        bill_after = get_bill_by_id(bill_id)
        self.assertEqual(bill_after["payment_status"], BILL_STATUS_UNPAID)
        self.assertEqual(float(bill_after["amount_paid"]), 0.0)
        self.assertEqual(float(bill_after["outstanding_balance"]), due)

        # Failed transaction record must exist for audit reconciliation
        failed_txns = get_payment_transactions(bill_id=bill_id, status=PAYMENT_STATUS_FAILED)
        self.assertEqual(len(failed_txns), 1)
        self.assertEqual(failed_txns[0]["status"], PAYMENT_STATUS_FAILED)
        self.assertIsNone(failed_txns[0]["receipt_number"])

    # --------------------------------------------------------------------------
    # 6. Demo Simulation: Cancellation
    # --------------------------------------------------------------------------
    def test_06_demo_simulation_cancellation(self):
        """Verify checkout cancellation aborts safely without balance alteration or receipt."""
        bill_id = self._create_test_bill(self.p1_id, self.d1_id)
        bill_before = get_bill_by_id(bill_id)
        due = float(bill_before["outstanding_balance"])

        ok, msg, receipt = process_patient_online_payment(
            bill_id=bill_id,
            amount=due,
            payment_method=PAYMENT_METHOD_UPI,
            simulated_outcome="CANCELLED",
            idempotency_key="IDEMP-CANCEL-001",
            user=self.pat_user,
        )

        self.assertFalse(ok)
        self.assertIn("cancelled by user", msg)
        self.assertIsNone(receipt)

        bill_after = get_bill_by_id(bill_id)
        self.assertEqual(bill_after["payment_status"], BILL_STATUS_UNPAID)
        self.assertEqual(float(bill_after["outstanding_balance"]), due)

    # --------------------------------------------------------------------------
    # 7. Idempotency Protection (Duplicate Submission Prevention)
    # --------------------------------------------------------------------------
    def test_07_idempotency_duplicate_submission_prevention(self):
        """Verify repeated submissions with same idempotency key return existing receipt without double charging."""
        bill_id = self._create_test_bill(self.p1_id, self.d1_id)
        bill = get_bill_by_id(bill_id)
        due = float(bill["outstanding_balance"])
        idemp_key = "IDEMP-RETRY-TEST-999"

        # 1st Submission
        ok1, msg1, rec1 = process_patient_online_payment(
            bill_id=bill_id,
            amount=due,
            payment_method=PAYMENT_METHOD_UPI,
            simulated_outcome="SUCCESS",
            idempotency_key=idemp_key,
            user=self.pat_user,
        )
        self.assertTrue(ok1, msg1)
        self.assertIsNotNone(rec1)
        first_receipt_num = rec1["receipt_number"]

        # 2nd Duplicate Submission with same idempotency key
        ok2, msg2, rec2 = process_patient_online_payment(
            bill_id=bill_id,
            amount=due,
            payment_method=PAYMENT_METHOD_UPI,
            simulated_outcome="SUCCESS",
            idempotency_key=idemp_key,
            user=self.pat_user,
        )
        self.assertTrue(ok2, msg2)
        self.assertIn("idempotent request", msg2)
        self.assertEqual(rec2["receipt_number"], first_receipt_num)

        # Verify only ONE payment record exists for this bill
        txns = get_payment_transactions(bill_id=bill_id)
        self.assertEqual(len(txns), 1)

        # Verify bill amount paid didn't double
        updated_bill = get_bill_by_id(bill_id)
        self.assertEqual(float(updated_bill["amount_paid"]), due)
        self.assertEqual(float(updated_bill["outstanding_balance"]), 0.0)

    # --------------------------------------------------------------------------
    # 8. Overpayment Protection
    # --------------------------------------------------------------------------
    def test_08_overpayment_protection(self):
        """Verify system rejects payments greater than outstanding balance or non-positive amounts."""
        bill_id = self._create_test_bill(self.p1_id, self.d1_id)
        bill = get_bill_by_id(bill_id)
        due = float(bill["outstanding_balance"])

        # Attempt to pay amount > outstanding balance
        ok, msg, _ = process_patient_online_payment(
            bill_id=bill_id,
            amount=due + 100.0,
            user=self.pat_user,
        )
        self.assertFalse(ok)
        self.assertIn("cannot exceed outstanding balance", msg)

        # Attempt zero amount
        ok_zero, msg_zero, _ = process_patient_online_payment(
            bill_id=bill_id,
            amount=0.0,
            user=self.pat_user,
        )
        self.assertFalse(ok_zero)
        self.assertIn("must be greater than zero", msg_zero)

        # Attempt negative amount
        ok_neg, msg_neg, _ = process_patient_online_payment(
            bill_id=bill_id,
            amount=-50.0,
            user=self.pat_user,
        )
        self.assertFalse(ok_neg)
        self.assertIn("must be greater than zero", msg_neg)

    # --------------------------------------------------------------------------
    # 9. Doctor Role Restrictions
    # --------------------------------------------------------------------------
    def test_09_doctor_role_blocked_from_payments(self):
        """Verify doctors are strictly barred from processing online payments or recording cashier payments."""
        bill_id = self._create_test_bill(self.p1_id, self.d1_id)
        bill = get_bill_by_id(bill_id)
        due = float(bill["outstanding_balance"])

        # Doctor calling online checkout
        ok1, msg1, _ = process_patient_online_payment(
            bill_id=bill_id,
            amount=due,
            user=self.doc_user,
        )
        self.assertFalse(ok1)
        self.assertIn("Physicians cannot collect", msg1)

        # Doctor calling record_payment
        ok2, msg2, _ = record_payment(
            bill_id=bill_id,
            amount=due,
            user=self.doc_user,
        )
        self.assertFalse(ok2)
        self.assertIn("Doctors cannot collect", msg2)

    # --------------------------------------------------------------------------
    # 10. Staff Operational Billing Recording
    # --------------------------------------------------------------------------
    def test_10_staff_operational_billing_recording(self):
        """Verify staff can record offline payments at desk, auto-attributed to front desk operator."""
        bill_id = self._create_test_bill(self.p1_id, self.d1_id)
        bill = get_bill_by_id(bill_id)
        due = float(bill["outstanding_balance"])

        ok, msg, receipt = record_payment(
            bill_id=bill_id,
            amount=due,
            payment_method="Cash",
            recorded_by="Front Desk Operator (staff_reception)",
            user=self.staff_user,
        )
        self.assertTrue(ok, msg)
        self.assertIsNotNone(receipt)

        updated_bill = get_bill_by_id(bill_id)
        self.assertEqual(updated_bill["payment_status"], BILL_STATUS_PAID)
        self.assertEqual(float(updated_bill["outstanding_balance"]), 0.0)

    # --------------------------------------------------------------------------
    # 11. Administrator Full Control & Audit Reconciliation
    # --------------------------------------------------------------------------
    def test_11_admin_full_control_and_audit_reconciliation(self):
        """Verify administrator can query complete audit log, filter by status, and search transactions."""
        bill_id = self._create_test_bill(self.p1_id, self.d1_id)
        bill = get_bill_by_id(bill_id)
        due = float(bill["outstanding_balance"])
        part = round(due / 3.0, 2)

        # Generate 1 success and 1 failed transaction
        process_patient_online_payment(
            bill_id=bill_id,
            amount=part,
            simulated_outcome="SUCCESS",
            idempotency_key="IDEMP-ADMIN-001",
            user=self.pat_user,
        )
        process_patient_online_payment(
            bill_id=bill_id,
            amount=part,
            simulated_outcome="FAILURE",
            idempotency_key="IDEMP-ADMIN-002",
            user=self.pat_user,
        )

        # Admin queries all transactions
        all_txns = get_payment_transactions(bill_id=bill_id)
        self.assertEqual(len(all_txns), 2)

        # Admin queries failed transactions
        failed_txns = get_payment_transactions(bill_id=bill_id, status=PAYMENT_STATUS_FAILED)
        self.assertEqual(len(failed_txns), 1)
        self.assertEqual(failed_txns[0]["status"], PAYMENT_STATUS_FAILED)

        # Admin queries successful transactions
        success_txns = get_payment_transactions(bill_id=bill_id, status=PAYMENT_STATUS_SUCCESS)
        self.assertEqual(len(success_txns), 1)
        self.assertEqual(success_txns[0]["status"], PAYMENT_STATUS_SUCCESS)

    # --------------------------------------------------------------------------
    # 12. Patient Payment History Scoping
    # --------------------------------------------------------------------------
    def test_12_patient_payment_history_scoping(self):
        """Verify get_patient_payment_history returns only the designated patient's transactions."""
        bill1 = self._create_test_bill(self.p1_id, self.d1_id)
        bill2 = self._create_test_bill(self.p2_id, self.d1_id)

        bill1_due = float(get_bill_by_id(bill1)["outstanding_balance"])
        bill2_due = float(get_bill_by_id(bill2)["outstanding_balance"])

        # Pay for patient 1
        process_patient_online_payment(
            bill_id=bill1,
            amount=bill1_due,
            simulated_outcome="SUCCESS",
            idempotency_key="IDEMP-HIST-001",
            user=self.pat_user,
        )

        # Pay for patient 2 (using admin user override for test setup)
        process_patient_online_payment(
            bill_id=bill2,
            amount=bill2_due,
            simulated_outcome="SUCCESS",
            idempotency_key="IDEMP-HIST-002",
            user=self.admin_user,
        )

        # Query history for patient 1
        p1_history = get_patient_payment_history(self.p1_id)
        self.assertEqual(len(p1_history), 1)
        self.assertEqual(p1_history[0]["bill_id"], bill1)

        # Query history for patient 2
        p2_history = get_patient_payment_history(self.p2_id)
        self.assertEqual(len(p2_history), 1)
        self.assertEqual(p2_history[0]["bill_id"], bill2)

    # --------------------------------------------------------------------------
    # 13. UI BillingView Initialization & Role Capabilities
    # --------------------------------------------------------------------------
    def test_13_ui_billing_view_role_scoping(self):
        """Verify BillingView instantiates correctly for all four roles without exceptions."""
        roles_to_test = [ROLE_PATIENT, ROLE_DOCTOR, ROLE_STAFF, ROLE_ADMIN]
        container = ctk.CTkFrame(self.root)
        container.pack(fill="both", expand=True)

        for role in roles_to_test:
            user_data = {"username": f"test_{role.lower()}", "role": role}
            if role == ROLE_PATIENT:
                user_data["linked_patient_id"] = self.p1_id
            elif role == ROLE_DOCTOR:
                user_data["linked_doctor_id"] = self.d1_id

            set_current_user(user_data)
            view = BillingView(container, current_user=user_data)
            self.assertIsNotNone(view)
            self.assertEqual(view.user_role, role)
            view.destroy()

        container.destroy()

    # --------------------------------------------------------------------------
    # 14. Balance Calculations, Multi-Invoice Integrity & Modal Clarity
    # --------------------------------------------------------------------------
    def test_14_patient_balance_calculations_and_checkout_modal_clarity(self):
        """Verify patient combined balance matches eligible invoices, partial payments update correctly,
        failed payments do not reduce dues, and checkout modal clarifies invoice vs account balance."""
        # Baseline balance for patient 1
        initial_stats = get_billing_summary_statistics(patient_id=self.p1_id)
        base_outstanding = float(initial_stats.get("total_outstanding", 0.0))

        # Create two distinct appointments & bills for patient 1
        bill_a_id = self._create_test_bill(self.p1_id, self.d1_id)
        bill_b_id = self._create_test_bill(self.p1_id, self.d1_id)

        bill_a = get_bill_by_id(bill_a_id)
        bill_b = get_bill_by_id(bill_b_id)
        bill_a_tot = float(bill_a["total_amount"])
        bill_b_tot = float(bill_b["total_amount"])

        # 1. Verify patient-wide outstanding balance matches eligible invoice balances
        stats_after_add = get_billing_summary_statistics(patient_id=self.p1_id)
        expected_combined = base_outstanding + bill_a_tot + bill_b_tot
        self.assertAlmostEqual(float(stats_after_add["total_outstanding"]), expected_combined, places=2)

        # 2. Selected invoice balance matches valid payments: 50% partial payment
        half_a = round(bill_a_tot / 2, 2)
        rem_a = round(bill_a_tot - half_a, 2)

        pay_ok, pay_msg, receipt = process_patient_online_payment(
            bill_id=bill_a_id,
            amount=half_a,
            simulated_outcome="SUCCESS",
            idempotency_key="IDEMP-BAL-TEST-001",
            user=self.pat_user,
        )
        self.assertTrue(pay_ok)
        self.assertIsNotNone(receipt)

        # Re-fetch Bill A
        bill_a_after = get_bill_by_id(bill_a_id)
        self.assertEqual(float(bill_a_after["amount_paid"]), half_a)
        self.assertEqual(float(bill_a_after["outstanding_balance"]), rem_a)
        self.assertEqual(bill_a_after["payment_status"], "Partially Paid")

        # Patient-wide outstanding must reflect the exact payment reduction
        stats_after_part = get_billing_summary_statistics(patient_id=self.p1_id)
        self.assertAlmostEqual(float(stats_after_part["total_outstanding"]), expected_combined - half_a, places=2)

        # 3. Failed simulated payments must NOT reduce the balance
        fail_ok, fail_msg, _ = process_patient_online_payment(
            bill_id=bill_a_id,
            amount=rem_a,
            simulated_outcome="FAILURE",
            idempotency_key="IDEMP-BAL-FAIL-001",
            user=self.pat_user,
        )
        self.assertFalse(fail_ok)
        bill_a_fail = get_bill_by_id(bill_a_id)
        self.assertEqual(float(bill_a_fail["outstanding_balance"]), rem_a, "Failed payment must not alter balance")
        stats_after_fail = get_billing_summary_statistics(patient_id=self.p1_id)
        self.assertAlmostEqual(float(stats_after_fail["total_outstanding"]), expected_combined - half_a, places=2)

        # 4. Fully settled invoices do not contribute to outstanding balance
        full_ok, full_msg, _ = process_patient_online_payment(
            bill_id=bill_a_id,
            amount=rem_a,
            simulated_outcome="SUCCESS",
            idempotency_key="IDEMP-BAL-FULL-001",
            user=self.pat_user,
        )
        self.assertTrue(full_ok)
        bill_a_settled = get_bill_by_id(bill_a_id)
        self.assertEqual(float(bill_a_settled["outstanding_balance"]), 0.0)
        self.assertEqual(bill_a_settled["payment_status"], "Paid")

        # Now only Bill B + base_outstanding remains
        stats_after_settle = get_billing_summary_statistics(patient_id=self.p1_id)
        self.assertAlmostEqual(float(stats_after_settle["total_outstanding"]), base_outstanding + bill_b_tot, places=2)

        # 5. Invoices for cancelled consultations are excluded from total_outstanding
        bill_b_record = get_bill_by_id(bill_b_id)
        with get_db_connection(self.test_db_path) as conn:
            conn.execute("UPDATE appointments SET status = 'Cancelled' WHERE id = ?;", (bill_b_record["appointment_id"],))
            conn.commit()
        stats_after_cancel = get_billing_summary_statistics(patient_id=self.p1_id)
        self.assertAlmostEqual(float(stats_after_cancel["total_outstanding"]), base_outstanding, places=2)

        # Re-enable appointment status for UI test
        with get_db_connection(self.test_db_path) as conn:
            conn.execute("UPDATE appointments SET status = 'Confirmed' WHERE id = ?;", (bill_b_record["appointment_id"],))
            conn.commit()

        # 6. Refunded bills are also excluded from total_outstanding
        with get_db_connection(self.test_db_path) as conn:
            conn.execute("UPDATE bills SET payment_status = 'Refunded' WHERE id = ?;", (bill_b_id,))
            conn.commit()
        stats_after_refund = get_billing_summary_statistics(patient_id=self.p1_id)
        self.assertAlmostEqual(float(stats_after_refund["total_outstanding"]), base_outstanding, places=2)

        # Restore bill B to Unpaid for checkout modal test
        with get_db_connection(self.test_db_path) as conn:
            conn.execute("UPDATE bills SET payment_status = 'Unpaid' WHERE id = ?;", (bill_b_id,))
            conn.commit()

        # 7. Verify PatientPaymentModal UI labels, Pay Full & Pay 50% amounts
        set_current_user(self.pat_user)
        modal = PatientPaymentModal(self.root, bill_id=bill_b_id)
        self.assertEqual(modal.outstanding_val, bill_b_tot)
        self.assertFalse(modal.resizable()[0])

        # Test Pay 50%
        modal._set_half_amount()
        self.assertEqual(modal.amount_entry.get().strip(), f"{round(bill_b_tot / 2, 2):.2f}")

        # Test Pay Full
        modal._set_full_amount()
        self.assertEqual(modal.amount_entry.get().strip(), f"{bill_b_tot:.2f}")

        modal.destroy()

    # --------------------------------------------------------------------------
    # 15. Checkout Modal Fixed Footer & Scrollable Architecture (Review 2 Issue 1)
    # --------------------------------------------------------------------------
    def test_15_checkout_modal_fixed_footer_and_scrollable_architecture(self):
        """Verify PatientPaymentModal implements fixed header, fixed footer with action buttons,
        scrollable middle body, and dynamic payment method switching without clipping."""
        bill_id = self._create_test_bill(self.p1_id, self.d1_id)
        set_current_user(self.pat_user)

        modal = PatientPaymentModal(self.root, bill_id=bill_id)

        # 1. Fixed Header & Footer Frames exist
        self.assertTrue(hasattr(modal, "header_frame"))
        self.assertTrue(hasattr(modal, "footer_frame"))
        self.assertTrue(hasattr(modal, "scroll_body"))
        self.assertIsInstance(modal.scroll_body, ctk.CTkScrollableFrame)

        # 2. Action buttons are strictly anchored in footer frame (never clipped)
        self.assertEqual(modal.cancel_btn.master, modal.footer_frame)
        self.assertEqual(modal.fail_btn.master, modal.footer_frame)
        self.assertEqual(modal.success_btn.master, modal.footer_frame)

        # 3. Method switching dynamically updates gateway simulation details
        modal._on_method_changed(PAYMENT_METHOD_UPI)
        self.assertIn("Virtual UPI ID", modal.details_lbl.cget("text"))

        modal._on_method_changed(PAYMENT_METHOD_CARD)
        self.assertIn("Test Card", modal.details_lbl.cget("text"))

        modal._on_method_changed(PAYMENT_METHOD_NET_BANKING)
        self.assertIn("Simulated Bank", modal.details_lbl.cget("text"))

        modal.destroy()


if __name__ == "__main__":
    unittest.main()
