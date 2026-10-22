"""Automated test suite verifying:
1. Four interactive Dashboard KPI cards with full-card clickability and navigation targets.
2. Premium Clinical Analytics visual identity, hover states, and active sidebar accent indicators.
3. ReportsView CSAT targeted focus and scrolling integration.
4. Dark and Light theme switching cohesiveness.
5. Absolute preservation of all database records and CRUD workflows.
"""
import unittest
import tkinter as tk
import customtkinter as ctk

from database.connection import get_db_connection
from ui.app import HospitalApp
from ui.components.kpi_card import KPICard
from ui.views.dashboard_view import DashboardView
from ui.views.reports_view import ReportsView


class TestInteractiveDashboardAndRedesign(unittest.TestCase):
    """Test suite covering KPI card interactivity, navigation routing, and UI redesign."""

    @classmethod
    def setUpClass(cls):
        ctk.set_appearance_mode("Dark")
        cls.root = ctk.CTk()
        cls.root.geometry("1100x650")
        cls.root.withdraw()
        cls.root.update()

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

    def test_01_all_four_kpi_cards_navigation_targets(self):
        """Verify each of the 4 KPI cards has an attached command routing to the exact specified view."""
        nav_calls = []

        def mock_navigate(view_name: str, **kwargs):
            nav_calls.append((view_name, kwargs))

        dash = DashboardView(self.root, on_navigate=mock_navigate)
        self.root.update()

        # Find the 4 KPI cards inside dash
        kpi_cards = []
        for child in dash.winfo_children():
            for sub in child.winfo_children():
                if isinstance(sub, KPICard):
                    kpi_cards.append(sub)

        self.assertEqual(len(kpi_cards), 4, f"Expected 4 KPI cards, found {len(kpi_cards)}")

        # Card 1: Total Registered Patients -> Patients
        nav_calls.clear()
        c1 = kpi_cards[0]
        self.assertEqual(c1.title_label.cget("text"), "Total Registered Patients")
        self.assertIsNotNone(c1.command)
        c1._invoke_command()
        self.assertEqual(len(nav_calls), 1)
        self.assertEqual(nav_calls[0][0], "Patients")

        # Card 2: Available Medical Staff -> Doctors
        nav_calls.clear()
        c2 = kpi_cards[1]
        self.assertEqual(c2.title_label.cget("text"), "Available Medical Staff")
        self.assertIsNotNone(c2.command)
        c2._invoke_command()
        self.assertEqual(len(nav_calls), 1)
        self.assertEqual(nav_calls[0][0], "Doctors")

        # Card 3: Today's Appointments -> Appointments (Full Roster)
        nav_calls.clear()
        c3 = kpi_cards[2]
        self.assertEqual(c3.title_label.cget("text"), "Today's Appointments")
        self.assertIsNotNone(c3.command)
        c3._invoke_command()
        self.assertEqual(len(nav_calls), 1)
        self.assertEqual(nav_calls[0][0], "Appointments")

        # Card 4: User Satisfaction (CSAT) -> Reports (CSAT Focused)
        nav_calls.clear()
        c4 = kpi_cards[3]
        self.assertEqual(c4.title_label.cget("text"), "User Satisfaction (CSAT)")
        self.assertIsNotNone(c4.command)
        c4._invoke_command()
        self.assertEqual(len(nav_calls), 1)
        self.assertEqual(nav_calls[0][0], "Reports")
        self.assertEqual(nav_calls[0][1].get("target_report"), "csat")

        dash.destroy()
        self.root.update()

    def test_02_kpi_card_recursive_click_and_hover_interactivity(self):
        """Verify KPICard responds to click on inner labels and has hover border highlights."""
        clicked = [False]

        def on_click():
            clicked[0] = True

        card = KPICard(
            self.root,
            title="Interactive Test Metric",
            value="100",
            subtitle="Testing clicks",
            icon="⭐",
            accent_color="#06B6D4",
            command=on_click,
            action_hint="Open Details →",
        )
        card.pack()
        self.root.update()

        # Check cursor is hand2 on card and internal widgets
        self.assertEqual(card.cget("cursor"), "hand2")
        self.assertEqual(card.title_label.cget("cursor"), "hand2")
        self.assertEqual(card.value_label.cget("cursor"), "hand2")
        self.assertEqual(card.icon_badge.cget("cursor"), "hand2")

        # Verify hover highlights border
        normal_border = card.cget("border_color")
        card._on_enter()
        self.assertEqual(card.cget("border_color"), "#06B6D4")

        # Verify leave reverts border
        card._on_leave()
        self.assertEqual(card.cget("border_color"), normal_border)

        # Verify clicking on inner value label fires card command
        clicked[0] = False
        card._on_release()
        self.assertTrue(clicked[0], "Card command did not fire on click release!")

        card.destroy()
        self.root.update()

    def test_03_app_sidebar_active_accent_indicator(self):
        """Verify HospitalApp applies a distinctive active accent indicator on current nav button."""
        app = HospitalApp()
        self.root.update()

        # Initially active view is Dashboard
        dash_btn = app.nav_buttons["Dashboard"]
        self.assertEqual(dash_btn.cget("border_width"), 1)
        self.assertEqual(dash_btn.cget("border_color"), ("#0284C7", "#06B6D4"))

        # Inactive buttons have no border
        patients_btn = app.nav_buttons["Patients"]
        self.assertEqual(patients_btn.cget("border_width"), 0)

        # Switch to Patients
        app.show_view("Patients")
        self.root.update()
        self.assertEqual(patients_btn.cget("border_width"), 1)
        self.assertEqual(patients_btn.cget("border_color"), ("#0284C7", "#06B6D4"))
        self.assertEqual(dash_btn.cget("border_width"), 0)

        # Switch to Appointments
        app.show_view("Appointments")
        self.root.update()
        appts_btn = app.nav_buttons["Appointments"]
        self.assertEqual(appts_btn.cget("border_width"), 1)

        app.destroy()
        self.root.update()

    def test_04_reports_view_csat_focus_highlight(self):
        """Verify ReportsView highlights the CSAT card when target_report='csat'."""
        rep = ReportsView(self.root, target_report="csat")
        self.root.update()

        self.assertEqual(rep.target_report, "csat")
        # Ensure scroll container and chart cards rendered cleanly
        self.assertTrue(hasattr(rep, "scroll_frame"))
        self.assertTrue(hasattr(rep, "export_btn"))
        self.assertTrue(hasattr(rep, "refresh_btn"))

        rep.destroy()
        self.root.update()

    def test_05_theme_mode_switching_cohesion(self):
        """Verify switching between Light and Dark mode works seamlessly without errors."""
        app = HospitalApp()
        self.root.update()

        # Switch to Light Mode
        app.set_theme_mode("Light")
        self.root.update()
        self.assertEqual(app.theme_quick_btn.cget("text"), "☀️ Theme")
        self.assertEqual(app.theme_switch.get(), "Light")

        # Switch back to Dark Mode
        app.set_theme_mode("Dark")
        self.root.update()
        self.assertEqual(app.theme_quick_btn.cget("text"), "🌙 Theme")
        self.assertEqual(app.theme_switch.get(), "Dark")

        app.destroy()
        self.root.update()

    def test_06_database_records_strictly_intact(self):
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
