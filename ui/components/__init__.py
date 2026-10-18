"""Reusable UI components package."""
from .appointment_modals import AppointmentFormModal, ConfirmAppointmentActionModal
from .doctor_modals import ConfirmDoctorActionModal, DoctorFormModal
from .kpi_card import KPICard
from .patient_modals import ConfirmPatientActionModal, PatientFormModal
from .scroll_manager import ScrollManager
from .tqm_modals import AddFMEAModal, LogDefectModal

__all__ = [
    "KPICard",
    "PatientFormModal",
    "ConfirmPatientActionModal",
    "DoctorFormModal",
    "ConfirmDoctorActionModal",
    "AppointmentFormModal",
    "ConfirmAppointmentActionModal",
    "LogDefectModal",
    "AddFMEAModal",
    "ScrollManager",
]


