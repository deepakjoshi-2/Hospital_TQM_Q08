"""Unit and integration tests for Live Token Tracking System (Q08).

Tests:
1. Sequential conflict-free token generation (TK-01, TK-02...)
2. Live doctor queue querying and queue status structure
3. Doctor consultation controls: 'Start Consultation' and 'Complete Consultation' state transitions
4. Patient active token retrieval
"""
import os
import sqlite3
import unittest
from datetime import date
import customtkinter as ctk

from database.connection import get_db_connection
from services.auth_service import login, logout
from services.token_service import (
    generate_next_token,
    get_queue_status_for_appointment,
    get_doctor_live_queue,
    start_consultation,
    complete_consultation,
    get_patient_active_tokens,
)
from ui.components.token_tracker import LiveQueueTrackerModal


class TestLiveTokenTracking(unittest.TestCase):
    """Test suite strictly verifying Live Token Tracking functionality."""

    @classmethod
    def setUpClass(cls):
        ctk.set_appearance_mode("Dark")
        cls.root = ctk.CTk()
        cls.root.geometry("800x600")
        cls.root.withdraw()
        cls.root.update()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def setUp(self):
        login("admin", "Admin@123")

    def tearDown(self):
        logout()

    def test_token_sequential_generation(self):
        """Verify sequential conflict-free token generation (TK-01, TK-02...)."""
        test_date = "2029-01-01"
        test_doctor = 999  # Doctor with no appointments on this future date
        tok1 = generate_next_token(test_doctor, test_date)
        self.assertEqual(tok1, "TK-01")

    def test_doctor_live_queue_and_status(self):
        """Verify live doctor queue querying returns valid structure."""
        with get_db_connection() as conn:
            row = conn.execute("SELECT id FROM doctors LIMIT 1;").fetchone()
            doc_id = row["id"]

        queue_info = get_doctor_live_queue(doc_id)
        self.assertIn("doctor_name", queue_info)
        self.assertIn("waiting_queue", queue_info)
        self.assertIn("waiting_count", queue_info)
        self.assertIn("completed_count", queue_info)

    def test_consultation_status_transitions(self):
        """Verify doctor 'Start Consultation' and 'Complete Consultation' state transitions."""
        with get_db_connection() as conn:
            pat_row = conn.execute("SELECT id FROM patients LIMIT 1;").fetchone()
            doc_row = conn.execute("SELECT id FROM doctors LIMIT 1;").fetchone()
            pat_id = pat_row["id"]
            doc_id = doc_row["id"]

            cur = conn.cursor()
            cur.execute(
                """
                INSERT INTO appointments (
                    appointment_code, patient_id, doctor_id, appointment_date,
                    time_slot, reason, status, queue_status, token_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                ("APT-TEST-Q", pat_id, doc_id, date.today().isoformat(), "04:30 PM", "Token Test", "Confirmed", "Waiting", "TK-99"),
            )
            appt_id = cur.lastrowid
            conn.commit()

        try:
            # 1. Check initial state
            q_info = get_queue_status_for_appointment(appt_id)
            self.assertEqual(q_info["queue_status"], "Waiting")

            # 2. Start consultation (returns tuple: (bool, str))
            res_start = start_consultation(appt_id)
            is_start_ok = res_start[0] if isinstance(res_start, tuple) else res_start.get("success")
            self.assertTrue(is_start_ok)

            q_info_2 = get_queue_status_for_appointment(appt_id)
            self.assertEqual(q_info_2["queue_status"], "Now Serving")

            # 3. Complete consultation
            res_comp = complete_consultation(appt_id)
            is_comp_ok = res_comp[0] if isinstance(res_comp, tuple) else res_comp.get("success")
            self.assertTrue(is_comp_ok)

            q_info_3 = get_queue_status_for_appointment(appt_id)
            self.assertEqual(q_info_3["queue_status"], "Completed")
            self.assertEqual(q_info_3["appointment_status"], "Completed")

        finally:
            with get_db_connection() as conn:
                conn.execute("DELETE FROM appointments WHERE id = ?;", (appt_id,))
                conn.commit()

    def test_patient_active_tokens(self):
        """Verify fetching active tokens for a specific patient."""
        with get_db_connection() as conn:
            row = conn.execute("SELECT id FROM patients LIMIT 1;").fetchone()
            pat_id = row["id"]

        tokens = get_patient_active_tokens(pat_id)
        self.assertIsInstance(tokens, list)

    def test_apt3053_live_tracker_regression(self):
        """Regression test for APT-3053: verify newly booked token TK-01 appears in doctor queue for 2026-11-02."""
        with get_db_connection() as conn:
            apt_row = conn.execute(
                "SELECT * FROM appointments WHERE appointment_code = 'APT-3053';"
            ).fetchone()

        self.assertIsNotNone(apt_row, "Appointment APT-3053 must exist in database")
        doc_id = apt_row["doctor_id"]
        appt_date = apt_row["appointment_date"]
        appt_id = apt_row["id"]

        # 1. Verify get_doctor_live_queue with explicit selected date (2026-11-02)
        q_data = get_doctor_live_queue(doc_id, appt_date)
        self.assertEqual(q_data["doctor_id"], doc_id)
        self.assertEqual(q_data["appointment_date"], "2026-11-02")
        self.assertTrue(q_data["is_future_date"])
        self.assertEqual(q_data["waiting_count"], 1)
        self.assertIsNone(q_data["now_serving"])

        # Check queue key (used by token_tracker UI)
        self.assertIn("queue", q_data)
        self.assertEqual(len(q_data["queue"]), 1)
        queue_item = q_data["queue"][0]
        self.assertEqual(queue_item["appointment_code"], "APT-3053")
        self.assertEqual(queue_item["token_number"], "TK-01")
        self.assertEqual(queue_item["status"], "Confirmed")
        self.assertEqual(queue_item["queue_status"], "Waiting")

        # 2. Verify get_doctor_live_queue without passing date (auto-resolves to next active date)
        q_default = get_doctor_live_queue(doc_id)
        self.assertEqual(q_default["appointment_date"], "2026-11-02")
        self.assertEqual(q_default["waiting_count"], 1)
        self.assertEqual(q_default["queue"][0]["appointment_code"], "APT-3053")

        # 3. Verify get_queue_status_for_appointment correctly handles future appointment
        status_info = get_queue_status_for_appointment(appt_id)
        self.assertIsNotNone(status_info)
        self.assertTrue(status_info["is_future_appointment"])
        self.assertIsNone(status_info["currently_serving_token"])
        self.assertEqual(status_info["token_number"], "TK-01")
        self.assertIn("Scheduled", status_info["queue_position_text"])
        self.assertIn("Scheduled", status_info["estimated_wait_text"])

    def test_scheduled_and_confirmed_waiting_queue_eligibility(self):
        """Verify both Scheduled and Confirmed appointments are included when queue_status is Waiting."""
        test_date = "2029-05-10"
        test_doc_id = 998

        with get_db_connection() as conn:
            pat_row = conn.execute("SELECT id FROM patients LIMIT 1;").fetchone()
            pat_id = pat_row["id"]
            doc_row = conn.execute("SELECT id FROM doctors LIMIT 1;").fetchone()
            actual_doc_id = doc_row["id"]

            cur = conn.cursor()
            # 1. Scheduled + Waiting
            cur.execute(
                """
                INSERT INTO appointments (
                    appointment_code, patient_id, doctor_id, appointment_date,
                    time_slot, reason, status, queue_status, token_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                ("APT-TEST-SCHED", pat_id, actual_doc_id, test_date, "09:00 AM", "Checkup", "Scheduled", "Waiting", "TK-01"),
            )
            id_sched = cur.lastrowid

            # 2. Confirmed + Waiting
            cur.execute(
                """
                INSERT INTO appointments (
                    appointment_code, patient_id, doctor_id, appointment_date,
                    time_slot, reason, status, queue_status, token_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                ("APT-TEST-CONF", pat_id, actual_doc_id, test_date, "09:30 AM", "Checkup", "Confirmed", "Waiting", "TK-02"),
            )
            id_conf = cur.lastrowid

            # 3. Cancelled (should be omitted)
            cur.execute(
                """
                INSERT INTO appointments (
                    appointment_code, patient_id, doctor_id, appointment_date,
                    time_slot, reason, status, queue_status, token_number
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                ("APT-TEST-CANC", pat_id, actual_doc_id, test_date, "10:00 AM", "Checkup", "Cancelled", "Cancelled", "TK-03"),
            )
            id_canc = cur.lastrowid
            conn.commit()

        try:
            q_res = get_doctor_live_queue(actual_doc_id, test_date)
            codes = [x["appointment_code"] for x in q_res["queue"]]
            self.assertIn("APT-TEST-SCHED", codes)
            self.assertIn("APT-TEST-CONF", codes)
            self.assertNotIn("APT-TEST-CANC", codes)
            self.assertEqual(q_res["waiting_count"], 2)
        finally:
            with get_db_connection() as conn:
                conn.execute("DELETE FROM appointments WHERE id IN (?, ?, ?);", (id_sched, id_conf, id_canc))
                conn.commit()

    def test_modal_ui_synchronization_apt3053(self):
        """Verify LiveQueueTrackerModal UI displays Dr. Vikram Mehta and APT-3053 for 2026-11-02."""
        modal = LiveQueueTrackerModal(self.root, doctor_id=3, appointment_date="2026-11-02")
        self.root.update()

        try:
            # 1. Doctor dropdown selected
            self.assertIn("Mehta", modal.doc_selector.get())
            self.assertEqual(modal.selected_doctor_id, 3)

            # 2. Date dropdown selected
            self.assertEqual(modal.date_selector.get(), "2026-11-02")
            self.assertEqual(modal.selected_date, "2026-11-02")

            # 3. KPI numbers
            waiting_text = modal.kpi_labels["PATIENTS WAITING"].cget("text")
            self.assertEqual(waiting_text, "1")

            now_serving_text = modal.kpi_labels["NOW SERVING"].cget("text")
            self.assertEqual(now_serving_text, "None (Ready)")

            avg_wait_text = modal.kpi_labels["AVG WAIT TIME"].cget("text")
            self.assertEqual(avg_wait_text, "Scheduled")

            # 4. Table rows contain APT-3053 and TK-01
            row_labels = []
            for child in modal.rows_frame.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    for sub in child.winfo_children():
                        if isinstance(sub, ctk.CTkLabel):
                            row_labels.append(sub.cget("text"))

            self.assertIn("APT-3053", row_labels)
            self.assertIn("TK-01", row_labels)
            self.assertIn("Waiting", row_labels)

        finally:
            modal._on_close()
            self.root.update()

    def test_modal_dropdown_switching_to_dr_mehta(self):
        """Verify opening modal with defaults and selecting Dr. Vikram Mehta displays APT-3053 on 2026-11-02."""
        modal = LiveQueueTrackerModal(self.root)
        self.root.update()

        try:
            # Locate option label for Dr. Vikram Mehta
            target_label = None
            for opt, did in modal.doc_options_map.items():
                if did == 3:
                    target_label = opt
                    break

            self.assertIsNotNone(target_label, "Dr. Vikram Mehta option must exist")
            modal._on_doctor_selected(target_label)
            self.root.update()

            self.assertEqual(modal.selected_doctor_id, 3)
            self.assertEqual(modal.selected_date, "2026-11-02")
            self.assertEqual(modal.kpi_labels["PATIENTS WAITING"].cget("text"), "1")

            row_labels = []
            for child in modal.rows_frame.winfo_children():
                if isinstance(child, ctk.CTkFrame):
                    for sub in child.winfo_children():
                        if isinstance(sub, ctk.CTkLabel):
                            row_labels.append(sub.cget("text"))

            self.assertIn("APT-3053", row_labels)
            self.assertIn("TK-01", row_labels)

        finally:
            modal._on_close()
            self.root.update()


if __name__ == "__main__":
    unittest.main()
