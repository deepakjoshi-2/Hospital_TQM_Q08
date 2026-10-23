"""Views package for Hospital Management System."""
from .dashboard_view import DashboardView
from .patients_view import PatientsView
from .doctors_view import DoctorsView
from .appointments_view import AppointmentsView
from .reports_view import ReportsView
from .settings_view import SettingsView
from .tqm_view import TQMView
from .billing_view import BillingView
from .login_view import LoginView
from .user_management_view import UserManagementView

__all__ = [
    "DashboardView",
    "PatientsView",
    "DoctorsView",
    "AppointmentsView",
    "ReportsView",
    "SettingsView",
    "TQMView",
    "BillingView",
    "LoginView",
    "UserManagementView",
]
