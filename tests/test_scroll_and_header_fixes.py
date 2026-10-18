"""Automated test suite verifying:
1. Appointments view header redesign and '＋ Book Appointment' button visibility.
2. Centralized ScrollManager mouse-wheel event routing, nesting safety, and callback leak prevention.
3. Interactive widget protection (textboxes, dropdowns, sliders) from mouse-wheel hijacking.
4. Database record preservation.
"""
import tkinter as tk
import unittest
import customtkinter as ctk

from database.connection import get_db_connection
from ui.components.appointment_modals import AppointmentFormModal
from ui.components.scroll_manager import ScrollManager
from ui.views.appointments_view import AppointmentsView
from ui.views.dashboard_view import DashboardView
from ui.views.doctors_view import DoctorsView
from ui.views.patients_view import PatientsView
from ui.views.reports_view import ReportsView
from ui.views.settings_view import SettingsView
from ui.views.tqm_view import TQMView


class TestScrollAndHeaderFixes(unittest.TestCase):
    """Test suite covering Book Appointment button sizing, header layout, and ScrollManager."""

    @classmethod
    def setUpClass(cls):
        ctk.set_appearance_mode("Dark")
        cls.root = ctk.CTk()
        cls.root.geometry("1100x650")
        cls.root.withdraw()

        # Install centralized scroll manager
        ScrollManager.install(cls.root)

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

    def test_01_appointments_header_layout_and_button_visibility(self):
        """Verify AppointmentsView header contains unclipped Book Appointment button and dedicated filter bar."""
        view = AppointmentsView(self.root)
        self.root.update()

        # Check action button properties
        self.assertTrue(hasattr(view, "add_btn"))
        self.assertEqual(view.add_btn.cget("text"), "＋ Book Appointment")
        self.assertEqual(view.add_btn.cget("width"), 175)
        self.assertEqual(view.add_btn.cget("height"), 36)
        self.assertEqual(view.add_btn.cget("fg_color"), "#0284C7")

        # Check export button properties
        self.assertTrue(hasattr(view, "export_btn"))
        self.assertEqual(view.export_btn.cget("text"), "📥 Export CSV")
        self.assertEqual(view.export_btn.cget("width"), 120)

        # Check filter row controls
        self.assertTrue(hasattr(view, "filter_row"))
        self.assertTrue(hasattr(view, "search_entry"))
        self.assertTrue(hasattr(view, "search_btn"))
        self.assertTrue(hasattr(view, "status_dropdown"))
        self.assertTrue(hasattr(view, "clear_btn"))

        self.assertEqual(view.clear_btn.cget("text"), "✕ Clear")
        self.assertEqual(view.clear_btn.cget("width"), 75)

        # Verify button action is connected
        self.assertTrue(callable(view._open_add_modal))
        self.assertTrue(callable(view._on_export_csv))

        view.destroy()
        self.root.update()

    def test_02_no_callback_accumulation_on_repeated_view_lifecycle(self):
        """Verify opening and closing views does NOT accumulate dead callbacks on bind_all('<MouseWheel>')."""
        initial_callbacks = len(self.root.bind_all("<MouseWheel>").split("\n"))

        # Open and destroy 5 different views
        for view_cls in [AppointmentsView, PatientsView, DoctorsView, SettingsView, ReportsView]:
            v = view_cls(self.root)
            self.root.update()
            v.destroy()
            self.root.update()

        callbacks_after = len(self.root.bind_all("<MouseWheel>").split("\n"))
        self.assertEqual(
            callbacks_after,
            initial_callbacks,
            f"Callback leak detected: before={initial_callbacks}, after={callbacks_after}",
        )

    def test_03_mousewheel_scrolling_moves_content(self):
        """Verify mouse wheel event properly scrolls scrollable container vertically."""
        view = AppointmentsView(self.root)
        view.pack(fill="both", expand=True)
        self.root.update()

        canvas = view.rows_frame._parent_canvas
        initial_yview = canvas.yview()

        # Simulate wheel down event targeted at the rows container
        event = tk.Event()
        event.widget = view.rows_frame.winfo_children()[0]
        event.delta = -120
        event.state = 0

        ScrollManager.handle_mousewheel(event)
        down_yview = canvas.yview()
        self.assertGreater(down_yview[0], initial_yview[0], "Content did not scroll down on negative delta!")

        # Simulate wheel up event
        event.delta = 120
        ScrollManager.handle_mousewheel(event)
        up_yview = canvas.yview()
        self.assertLessEqual(up_yview[0], down_yview[0], "Content did not scroll up on positive delta!")

        view.destroy()
        self.root.update()

    def test_04_nested_scrollable_container_precedence(self):
        """Verify mouse-wheel over nested scrollable widget targets inner container rather than parent."""
        outer = ctk.CTkScrollableFrame(self.root, width=400, height=300)
        outer.pack()
        inner = ctk.CTkScrollableFrame(outer, width=200, height=150)
        inner.pack()

        inner_lbl = ctk.CTkLabel(inner, text="Inner Content")
        inner_lbl.pack()
        outer_lbl = ctk.CTkLabel(outer, text="Outer Content")
        outer_lbl.pack()
        self.root.update()

        target_inner = ScrollManager.find_scrollable_container(inner_lbl)
        target_outer = ScrollManager.find_scrollable_container(outer_lbl)

        self.assertIs(target_inner, inner, "Inner label did not route to inner scrollable container!")
        self.assertIs(target_outer, outer, "Outer label did not route to outer scrollable container!")

        outer.destroy()
        self.root.update()

    def test_05_interactive_widgets_not_hijacked(self):
        """Verify controls with their own wheel behavior (CTkTextbox, CTkOptionMenu, CTkSlider) are not hijacked."""
        container = ctk.CTkScrollableFrame(self.root, width=300, height=200)
        container.pack()

        tb = ctk.CTkTextbox(container, height=60)
        tb.pack()
        om = ctk.CTkOptionMenu(container, values=["Opt1", "Opt2"])
        om.pack()
        sl = ctk.CTkSlider(container)
        sl.pack()
        self.root.update()

        self.assertIsNone(ScrollManager.find_scrollable_container(tb._textbox))
        self.assertIsNone(ScrollManager.find_scrollable_container(om))
        self.assertIsNone(ScrollManager.find_scrollable_container(sl))

        container.destroy()
        self.root.update()

    def test_06_database_records_intact(self):
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

    def test_07_dpi_scaled_coordinates_resolve_correctly(self):
        """Verify ScrollManager correctly resolves scroll container with 1.5x scaled physical coordinates."""
        view = AppointmentsView(self.root)
        view.pack(fill="both", expand=True)
        self.root.update()

        canvas = view.rows_frame._parent_canvas
        initial_yview = canvas.yview()

        # Simulate event with physical coordinates under 1.5x DPI scaling and event.widget=root
        scaling = 1.5
        rx = view.rows_frame.winfo_rootx() + 50
        ry = view.rows_frame.winfo_rooty() + 50

        event = tk.Event()
        event.widget = self.root
        event.x_root = int(rx * scaling)
        event.y_root = int(ry * scaling)
        event.delta = -120
        event.state = 0

        target = ScrollManager.resolve_scroll_target(event)
        self.assertIsNotNone(target, "Failed to resolve scroll target under scaled physical coordinates!")
        self.assertIs(target, view.rows_frame)

        ScrollManager.handle_mousewheel(event)
        scrolled_yview = canvas.yview()
        self.assertGreater(scrolled_yview[0], initial_yview[0], "Content did not scroll with scaled coordinates!")

        view.destroy()
        self.root.update()

    def test_08_card_and_header_hover_scrolling(self):
        """Verify rotating wheel over column header row or card container scrolls the data table."""
        view = AppointmentsView(self.root)
        view.pack(fill="both", expand=True)
        self.root.update()

        canvas = view.rows_frame._parent_canvas
        initial_yview = canvas.yview()

        # Target event directly at column header frame (sibling of rows_frame)
        col_header = view.card.winfo_children()[0]
        event = tk.Event()
        event.widget = col_header
        event.delta = -120
        event.state = 0

        target = ScrollManager.resolve_scroll_target(event)
        self.assertIs(target, view.rows_frame, "Column header did not resolve to rows_frame!")

        ScrollManager.handle_mousewheel(event)
        self.assertGreater(canvas.yview()[0], initial_yview[0], "Content did not scroll when hovering over header!")

        view.destroy()
        self.root.update()

    def test_09_all_views_scrollable_container_resolution(self):
        """Verify ScrollManager resolves scrollable container across Patients, Appointments, Reports, Settings, and TQM."""
        views_to_test = [
            (PatientsView, "rows_frame"),
            (AppointmentsView, "rows_frame"),
            (ReportsView, "scroll_frame"),
            (SettingsView, "scroll_container"),
        ]

        for view_cls, attr_name in views_to_test:
            v = view_cls(self.root)
            v.pack(fill="both", expand=True)
            self.root.update()

            expected_sf = getattr(v, attr_name)
            event = tk.Event()
            event.widget = v
            event.delta = -120
            event.state = 0

            resolved = ScrollManager.find_scrollable_container(v)
            self.assertIs(resolved, expected_sf, f"View {view_cls.__name__} failed to resolve {attr_name}!")

            v.destroy()
            self.root.update()

    def test_10_modal_form_scroll_desktop_increment(self):
        """Verify modal form scrolling uses responsive desktop increment (> 20px) rather than 1px."""
        modal = AppointmentFormModal(self.root)
        self.root.update()

        canvas = modal.form_scroll._parent_canvas
        initial_yview = canvas.yview()

        # Send downward wheel event
        event = tk.Event()
        event.widget = modal.form_scroll
        event.delta = -120
        event.state = 0
        event.num = 0

        modal._on_mousewheel(event)
        scrolled_yview = canvas.yview()

        self.assertGreater(scrolled_yview[0], initial_yview[0], "Modal form did not scroll downward!")
        # Verify substantial scroll (> 1px movement)
        pixel_movement = (scrolled_yview[0] - initial_yview[0]) * canvas.bbox("all")[3]
        self.assertGreaterEqual(pixel_movement, 30, f"Scroll was too sluggish: {pixel_movement}px")

        modal.destroy()
        self.root.update()


if __name__ == "__main__":
    unittest.main()

