"""Unit tests for Billing, Consultation Fees, Payment Processing, and Receipts."""
import os
import tempfile
import unittest

from config.constants import (
    BILL_STATUS_PAID,
    BILL_STATUS_PARTIALLY_PAID,
    BILL_STATUS_UNPAID,
    STATUS_CONFIRMED,
)
from database.connection import get_db_connection
from database.seed_data import seed_database
from services.appointment_service import create_appointment
from services.billing_service import (
    create_bill_for_appointment,
    generate_receipt_text,
    get_bill_by_appointment_id,
    get_bill_by_id,
    get_billing_summary_statistics,
    get_bills,
    get_payments_for_bill,
    get_receipt_by_number,
    record_payment,
)


class TestBillingAndReceipts(unittest.TestCase):
    """Test suite verifying invoice creation, payment recording, balance tracking, and receipts."""

    def setUp(self):
        """Set up clean isolated database for billing test execution."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = os.path.join(self.temp_dir.name, "test_billing.db")
        os.environ["HOSPITAL_DB_PATH"] = self.test_db_path
        seed_database(self.test_db_path)

        with get_db_connection(self.test_db_path) as conn:
            p_row = conn.execute("SELECT id FROM patients LIMIT 1;").fetchone()
            d_row = conn.execute("SELECT id, consultation_fee FROM doctors LIMIT 1;").fetchone()
            self.patient_id = p_row["id"]
            self.doctor_id = d_row["id"]
            self.doctor_fee = float(d_row["consultation_fee"])

    def tearDown(self):
        """Clean up test environment and temporary files."""
        os.environ.pop("HOSPITAL_DB_PATH", None)
        self.temp_dir.cleanup()

    def test_01_automatic_bill_generation_on_booking(self):
        """Verify an invoice is automatically created when an appointment is booked."""
        appt_data = {
            "appointment_code": "APT-8801",
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "appointment_date": "2026-11-25",
            "time_slot": "09:30 AM",
            "reason": "Consultation",
            "priority": "Normal",
            "status": STATUS_CONFIRMED,
        }
        ok, msg, appt_id = create_appointment(appt_data)
        self.assertTrue(ok)

        # Retrieve generated bill
        bill = get_bill_by_appointment_id(appt_id)
        self.assertIsNotNone(bill)
        self.assertTrue(bill["bill_number"].startswith("BILL-"))
        self.assertEqual(float(bill["consultation_fee"]), self.doctor_fee)
        self.assertEqual(float(bill["total_amount"]), self.doctor_fee)
        self.assertEqual(float(bill["outstanding_balance"]), self.doctor_fee)
        self.assertEqual(float(bill["amount_paid"]), 0.0)
        self.assertEqual(bill["payment_status"], BILL_STATUS_UNPAID)

    def test_02_full_payment_flow_and_receipt(self):
        """Verify full payment recording updates bill status to Paid and generates official receipt."""
        appt_data = {
            "appointment_code": "APT-8802",
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "appointment_date": "2026-11-26",
            "time_slot": "10:30 AM",
            "reason": "Routine Checkup",
            "priority": "Normal",
            "status": STATUS_CONFIRMED,
        }
        _, _, appt_id = create_appointment(appt_data)
        bill = get_bill_by_appointment_id(appt_id)

        # Record full payment
        pay_ok, pay_msg, receipt = record_payment(
            bill_id=bill["id"],
            amount=self.doctor_fee,
            payment_method="UPI",
            reference_number="UPI-TXN-12345",
            recorded_by="Front Desk Operator",
        )
        self.assertTrue(pay_ok, pay_msg)
        self.assertIsNotNone(receipt)
        self.assertTrue(receipt["receipt_number"].startswith("REC-"))
        self.assertEqual(float(receipt["amount"]), self.doctor_fee)
        self.assertEqual(receipt["payment_method"], "UPI")

        # Verify bill state
        updated_bill = get_bill_by_id(bill["id"])
        self.assertEqual(updated_bill["payment_status"], BILL_STATUS_PAID)
        self.assertEqual(float(updated_bill["outstanding_balance"]), 0.0)
        self.assertEqual(float(updated_bill["amount_paid"]), self.doctor_fee)

        # Verify payments list
        payments = get_payments_for_bill(bill["id"])
        self.assertEqual(len(payments), 1)
        self.assertEqual(payments[0]["receipt_number"], receipt["receipt_number"])

    def test_03_partial_payments_flow(self):
        """Verify incremental partial payments update balances and status transitions correctly."""
        appt_data = {
            "appointment_code": "APT-8803",
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "appointment_date": "2026-11-27",
            "time_slot": "11:30 AM",
            "reason": "Specialist Visit",
            "priority": "Normal",
            "status": STATUS_CONFIRMED,
        }
        _, _, appt_id = create_appointment(appt_data)
        bill = get_bill_by_appointment_id(appt_id)

        first_pay = self.doctor_fee / 2.0
        second_pay = self.doctor_fee - first_pay

        # First partial payment
        ok1, _, rec1 = record_payment(bill["id"], first_pay, payment_method="Cash")
        self.assertTrue(ok1)
        b1 = get_bill_by_id(bill["id"])
        self.assertEqual(b1["payment_status"], BILL_STATUS_PARTIALLY_PAID)
        self.assertEqual(float(b1["amount_paid"]), first_pay)
        self.assertEqual(float(b1["outstanding_balance"]), second_pay)

        # Second payment completing balance
        ok2, _, rec2 = record_payment(bill["id"], second_pay, payment_method="Card")
        self.assertTrue(ok2)
        b2 = get_bill_by_id(bill["id"])
        self.assertEqual(b2["payment_status"], BILL_STATUS_PAID)
        self.assertEqual(float(b2["amount_paid"]), self.doctor_fee)
        self.assertEqual(float(b2["outstanding_balance"]), 0.0)

        # Each payment has distinct receipt
        self.assertNotEqual(rec1["receipt_number"], rec2["receipt_number"])

    def test_04_payment_validation_and_safeguards(self):
        """Verify overpayment, zero, and negative payments are rejected."""
        appt_data = {
            "appointment_code": "APT-8804",
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "appointment_date": "2026-11-28",
            "time_slot": "02:30 PM",
            "reason": "Test Validation",
            "priority": "Normal",
            "status": STATUS_CONFIRMED,
        }
        _, _, appt_id = create_appointment(appt_data)
        bill = get_bill_by_appointment_id(appt_id)

        # Overpayment rejection
        ok, msg, _ = record_payment(bill["id"], self.doctor_fee + 100.0)
        self.assertFalse(ok)
        self.assertIn("cannot exceed outstanding", msg)

        # Zero amount rejection
        ok, msg, _ = record_payment(bill["id"], 0.0)
        self.assertFalse(ok)
        self.assertIn("greater than zero", msg)

        # Negative amount rejection
        ok, msg, _ = record_payment(bill["id"], -50.0)
        self.assertFalse(ok)

        # Invalid payment method rejection
        ok, msg, _ = record_payment(bill["id"], 100.0, payment_method="Crypto")
        self.assertFalse(ok)
        self.assertIn("Invalid payment method", msg)

    def test_05_formatted_receipt_text_generation(self):
        """Verify generated receipt ASCII slip contains hospital metadata, student info, and details."""
        appt_data = {
            "appointment_code": "APT-8805",
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "appointment_date": "2026-11-29",
            "time_slot": "03:30 PM",
            "reason": "Receipt Print Test",
            "priority": "Normal",
            "status": STATUS_CONFIRMED,
        }
        _, _, appt_id = create_appointment(appt_data)
        bill = get_bill_by_appointment_id(appt_id)

        _, _, receipt = record_payment(bill["id"], self.doctor_fee, payment_method="UPI")
        receipt_text = generate_receipt_text(receipt["receipt_number"])

        self.assertIn("OFFICIAL CONSULTATION RECEIPT", receipt_text)
        self.assertIn(receipt["receipt_number"], receipt_text)
        self.assertIn(bill["bill_number"], receipt_text)
        self.assertIn("Deepak Joshi", receipt_text)
        self.assertIn("Q08", receipt_text)
        self.assertIn("TERMS & CONDITIONS", receipt_text)

    def test_06_billing_summary_statistics(self):
        """Verify billing KPI aggregator sums correctly."""
        appt_data = {
            "appointment_code": "APT-8806",
            "patient_id": self.patient_id,
            "doctor_id": self.doctor_id,
            "appointment_date": "2026-11-30",
            "time_slot": "04:30 PM",
            "reason": "Stats check",
            "priority": "Normal",
            "status": STATUS_CONFIRMED,
        }
        create_appointment(appt_data)

        stats = get_billing_summary_statistics()
        self.assertIn("total_bills", stats)
        self.assertIn("total_invoiced", stats)
        self.assertIn("total_collected", stats)
        self.assertIn("total_outstanding", stats)
        self.assertGreater(stats["total_bills"], 0)


if __name__ == "__main__":
    unittest.main()
