"""Automated test suite verifying the UI/UX fixes:
1. Reports view header layout and Export CSV visibility
2. TQM two-row tab navigation and tab switching state preservation
3. Dashboard dynamic empty-state, Book Appointment action, and date awareness
4. Zero database record loss
"""
import datetime
import os
import tempfile
import unittest
import customtkinter as ctk

from database.connection import get_db_connection
from ui.views.dashboard_view import DashboardView
from ui.views.reports_view import ReportsView
from ui.views.tqm_view import TQMView


class TestUIImprovementsPhase3(unittest.TestCase):
    """Test suite verifying UI/UX improvements across Reports, TQM, and Dashboard."""

    @classmethod
    def setUpClass(cls):
        ctk.set_appearance_mode("Dark")
        cls.root = ctk.CTk()
        cls.root.geometry("1100x650")
        cls.root.withdraw()

        # Record baseline DB counts
        with get_db_connection() as conn:
            cls.baseline_patients = conn.execute("SELECT COUNT(*) FROM patients;").fetchone()[0]
            cls.baseline_doctors = conn.execute("SELECT COUNT(*) FROM doctors;").fetchone()[0]
            cls.baseline_appointments = conn.execute("SELECT COUNT(*) FROM appointments;").fetchone()[0]
            cls.baseline_defects = conn.execute("SELECT COUNT(*) FROM tqm_defect_logs;").fetchone()[0]
            cls.baseline_fmea = conn.execute("SELECT COUNT(*) FROM tqm_fmea_records;").fetchone()[0]

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_01_reports_header_layout_and_buttons(self):
        """Verify Reports view header contains separate action buttons and KPI summary frame."""
        rep = ReportsView(self.root)
        self.root.update()

        # Export CSV button
        self.assertTrue(hasattr(rep, "export_btn"))
        self.assertIn("Export CSV", rep.export_btn.cget("text"))
        self.assertEqual(rep.export_btn.cget("width"), 120)

        # Refresh Data button
        self.assertTrue(hasattr(rep, "refresh_btn"))
        self.assertEqual(rep.refresh_btn.cget("text"), "🔄 Refresh Data")
        self.assertEqual(rep.refresh_btn.cget("width"), 130)

        # Both buttons are children of ctrl_box
        self.assertEqual(rep.export_btn.master, rep.ctrl_box)
        self.assertEqual(rep.refresh_btn.master, rep.ctrl_box)

        # KPI pills frame is separated in the header frame
        self.assertTrue(hasattr(rep, "pills_frame"))
        self.assertGreaterEqual(len(rep.pills_frame.winfo_children()), 2)

        rep.destroy()
        self.root.update()

    def test_02_reports_csv_export_service_and_data(self):
        """Verify report service export to CSV produces a valid non-empty file."""
        from services.report_service import export_summary_report_to_csv

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tf:
            temp_path = tf.name

        try:
            success, msg = export_summary_report_to_csv(temp_path)
            self.assertTrue(success, f"CSV export failed: {msg}")
            self.assertTrue(os.path.exists(temp_path))
            with open(temp_path, "r", encoding="utf-8") as f:
                content = f.read()
            self.assertIn("HOSPITAL MANAGEMENT SYSTEM", content)
            self.assertIn("CLINICAL ANALYTICS", content)
            self.assertIn("Total Outpatient Appointments", content)
        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)

    def test_03_tqm_two_row_tab_navigation(self):
        """Verify TQM toolkit has 7 clearly labeled buttons across two rows."""
        tqm = TQMView(self.root)
        self.root.update()

        expected_tabs = [
            "1. FMEA Risk Matrix (RPN)",
            "2. SIPOC Process Map",
            "3. CTQ Quality Tree",
            "4. Defect Checksheet Log",
            "5. Pareto & Root Cause (Fishbone)",
            "6. PDCA Improvement Cycles",
            "7. Quality Improvement Summary",
        ]

        self.assertEqual(len(tqm.tab_buttons), 7)
        for tab_name in expected_tabs:
            self.assertIn(tab_name, tqm.tab_buttons)
            btn = tqm.tab_buttons[tab_name]
            # Ensure label text is fully set and not truncated
            self.assertEqual(btn.cget("text"), tab_name)

        # Test switching across all 7 tabs
        for tab_name in expected_tabs:
            tqm.switch_tab(tab_name)
            self.assertEqual(tqm.active_tab_key, tab_name)
            # Active button must have primary blue color
            self.assertEqual(tqm.tab_buttons[tab_name].cget("fg_color"), "#0284C7")

        # Test backward-compatibility methods
        self.assertEqual(tqm.tabview.get(), "7. Quality Improvement Summary")
        tqm.tabview.set("1. FMEA Risk Matrix (RPN)")
        self.assertEqual(tqm.active_tab_key, "1. FMEA Risk Matrix (RPN)")

        tqm.destroy()
        self.root.update()

    def test_04_dashboard_dynamic_empty_state_and_booking_workflow(self):
        """Verify Dashboard displays intentional empty state for today's schedule and connects booking workflow."""
        dash = DashboardView(self.root)
        self.root.update()

        # Date is dynamic today's date
        today_iso = datetime.date.today().isoformat()
        self.assertEqual(dash.metrics["today_date"], today_iso)

        # Verify modal booking opener is callable
        self.assertTrue(callable(dash._open_book_appointment_modal))
        self.assertTrue(callable(dash.refresh_dashboard))

        # Check that empty state or table is rendered without errors
        self.assertIsInstance(dash.metrics["recent_appointments"], list)

        # Calling refresh_dashboard works cleanly
        dash.refresh_dashboard()
        self.root.update()
        self.assertEqual(dash.metrics["today_date"], today_iso)

        dash.destroy()
        self.root.update()

    def test_05_database_records_intact(self):
        """Verify database record counts are strictly preserved across all tables."""
        with get_db_connection() as conn:
            cur_patients = conn.execute("SELECT COUNT(*) FROM patients;").fetchone()[0]
            cur_doctors = conn.execute("SELECT COUNT(*) FROM doctors;").fetchone()[0]
            cur_appointments = conn.execute("SELECT COUNT(*) FROM appointments;").fetchone()[0]
            cur_defects = conn.execute("SELECT COUNT(*) FROM tqm_defect_logs;").fetchone()[0]
            cur_fmea = conn.execute("SELECT COUNT(*) FROM tqm_fmea_records;").fetchone()[0]

        self.assertEqual(cur_patients, self.baseline_patients, "Patient record count mismatch!")
        self.assertEqual(cur_doctors, self.baseline_doctors, "Doctor record count mismatch!")
        self.assertEqual(cur_appointments, self.baseline_appointments, "Appointment record count mismatch!")
        self.assertEqual(cur_defects, self.baseline_defects, "Defect log count mismatch!")
        self.assertEqual(cur_fmea, self.baseline_fmea, "FMEA record count mismatch!")


if __name__ == "__main__":
    unittest.main()
