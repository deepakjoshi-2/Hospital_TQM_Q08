"""Views package for Hospital Management System."""
from .dashboard_view import DashboardView
from .patients_view import PatientsView
from .doctors_view import DoctorsView
from .appointments_view import AppointmentsView
from .reports_view import ReportsView
from .settings_view import SettingsView
from .tqm_view import TQMView

__all__ = [
    "DashboardView",
    "PatientsView",
    "DoctorsView",
    "AppointmentsView",
    "ReportsView",
    "SettingsView",
    "TQMView",
]
