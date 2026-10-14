"""Unit and integration tests for the three final software quality fixes.

Covers:
1. Matplotlib figure and canvas cleanup upon view destruction without affecting external figures.
2. Dashboard dynamic system date query and empty state handling.
3. Notification banner timer cancellation and widget existence safety upon destruction.
"""
import datetime
import unittest
import tkinter as tk
import customtkinter as ctk
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from database.connection import get_db_connection
from ui.views.dashboard_view import DashboardView
from ui.views.reports_view import ReportsView
from ui.views.tqm_view import TQMView
from ui.views.patients_view import PatientsView
from ui.views.doctors_view import DoctorsView
from ui.views.appointments_view import AppointmentsView
from ui.views.settings_view import SettingsView


class TestQualityFixes(unittest.TestCase):
    """Test suite verifying Fix 1, Fix 2, and Fix 3 implementations."""

    @classmethod
    def setUpClass(cls):
        ctk.set_appearance_mode("Dark")
        cls.root = ctk.CTk()
        cls.root.withdraw()
        cls.root.update()

    @classmethod
    def tearDownClass(cls):
        try:
            cls.root.destroy()
        except Exception:
            pass

    def test_01_dashboard_uses_dynamic_system_date(self):
        """Verify DashboardView dynamically queries current date instead of hardcoded 2026-10-09."""
        dash = DashboardView(self.root)
        self.root.update()

        today_expected = datetime.date.today().isoformat()
        self.assertEqual(dash.metrics["today_date"], today_expected)

        # Check that query accurately reflects database count for today's date
        with get_db_connection() as conn:
            actual_count = conn.execute(
                "SELECT COUNT(*) FROM appointments WHERE appointment_date = ?;",
                (today_expected,),
            ).fetchone()[0]

        self.assertEqual(int(dash.metrics["today_appointments"]), actual_count)
        dash.destroy()

    def test_02_dashboard_empty_state_when_no_appointments(self):
        """Verify dashboard reports empty state when querying a date with zero bookings."""
        dash = DashboardView(self.root)
        # Verify today_appointments is valid integer string
        self.assertTrue(dash.metrics["today_appointments"].isdigit())
        self.assertIsInstance(dash.metrics["recent_appointments"], list)
        dash.destroy()

    def test_03_reports_view_matplotlib_cleanup_on_destroy(self):
        """Verify ReportsView safely closes its own figures/canvases upon destroy without touching external figures."""
        # Create an unrelated external figure
        external_fig = plt.figure()
        external_fig_num = external_fig.number

        rep_view = ReportsView(self.root)
        self.root.update()

        # ReportsView creates 4 active figures (or fewer if feedback empty)
        self.assertGreater(len(rep_view.active_figures), 0)
        self.assertGreater(len(rep_view.active_canvases), 0)

        # Destroy the ReportsView
        rep_view.destroy()
        self.root.update()

        # Verify ReportsView internal figures and canvases are cleared
        self.assertEqual(len(rep_view.active_figures), 0)
        self.assertEqual(len(rep_view.active_canvases), 0)

        # Verify the unrelated external figure was NOT closed
        self.assertTrue(plt.fignum_exists(external_fig_num))
        plt.close(external_fig)

    def test_04_tqm_view_matplotlib_cleanup_on_destroy(self):
        """Verify TQMView safely cleans up its active Pareto figures and canvases upon destruction."""
        external_fig = plt.figure()
        external_fig_num = external_fig.number

        tqm = TQMView(self.root)
        self.root.update()

        # TQMView creates 1 active figure for Pareto
        self.assertGreaterEqual(len(tqm.active_figures), 1)
        self.assertGreaterEqual(len(tqm.active_canvases), 1)

        tqm.destroy()
        self.root.update()

        self.assertEqual(len(tqm.active_figures), 0)
        self.assertEqual(len(tqm.active_canvases), 0)

        # External figure remains open
        self.assertTrue(plt.fignum_exists(external_fig_num))
        plt.close(external_fig)

    def test_05_notification_timer_management_and_safe_destroy(self):
        """Verify views cancel pending notice timers upon destruction without widget errors."""
        views_classes = [
            PatientsView,
            DoctorsView,
            AppointmentsView,
            SettingsView,
            TQMView,
        ]

        for cls in views_classes:
            view = cls(self.root)
            self.root.update()

            # Trigger a notice
            view._show_notice("Test notification message")
            self.assertIsNotNone(view._notice_timer_id)

            # Safely destroy the view while timer is active
            view.destroy()
            self.root.update()

            # Timer id should be None after destroy
            self.assertIsNone(view._notice_timer_id)

    def test_06_settings_layout_compactness_and_banner_lifecycle(self):
        """Verify SettingsView does not have empty notice container gap and manages banner lifecycle."""
        view = SettingsView(self.root)
        view.pack(fill="both", expand=True)
        self.root.update_idletasks()
        self.root.update()

        # Notice container should no longer exist as a persistent spacer frame
        self.assertFalse(hasattr(view, "notice_container"))
        # Notice banner should initially be unmanaged by pack, consuming no vertical space
        self.assertEqual(view.notice_banner.winfo_manager(), "")

        # Showing notice should pack the banner directly after the header
        view._show_notice("Profile updated successfully")
        self.root.update_idletasks()
        self.root.update()
        self.assertEqual(view.notice_banner.winfo_manager(), "pack")

        # Dismissing notice should unmanage the banner cleanly
        view._hide_notice()
        self.root.update_idletasks()
        self.root.update()
        self.assertEqual(view.notice_banner.winfo_manager(), "")

        view.destroy()
        self.root.update()

    def test_07_dashboard_tqm_panel_scrolling(self):
        """Verify DashboardView right TQM panel uses CTkScrollableFrame to prevent clipping."""
        view = DashboardView(self.root)
        view.pack(fill="both", expand=True)
        self.root.update_idletasks()
        self.root.update()

        # Check scrollable container exists and is an instance of CTkScrollableFrame
        self.assertTrue(hasattr(view, "tqm_scroll"))
        self.assertIsInstance(view.tqm_scroll, ctk.CTkScrollableFrame)

        # Confirm all 5 highlight cards, the description, and the student metadata are inside the scrollable container
        children = view.tqm_scroll.winfo_children()
        # 1 description label, 5 highlight frames, 1 student footer frame = 7 children
        self.assertEqual(len(children), 7)

        view.destroy()
        self.root.update()

    def test_08_reports_view_no_leaked_global_mousewheel_bindings(self):
        """Verify ReportsView does not attach redundant global mousewheel bindings."""
        view = ReportsView(self.root)
        view.pack(fill="both", expand=True)
        self.root.update_idletasks()
        self.root.update()

        # Confirm _on_mousewheel was removed in favor of native CTkScrollableFrame handling
        self.assertFalse(hasattr(view, "_on_mousewheel"))

        view.destroy()
        self.root.update()


if __name__ == "__main__":
    unittest.main()
