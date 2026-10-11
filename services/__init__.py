"""Services package for Hospital Management System."""
from .appointment_service import (
    cancel_appointment,
    check_slot_conflict,
    create_appointment,
    delete_appointment,
    get_appointment_by_id,
    get_doctor_dropdown_options,
    get_next_appointment_code,
    get_patient_dropdown_options,
    update_appointment,
)
from .doctor_service import (
    archive_doctor,
    create_doctor,
    delete_doctor,
    get_doctor_appointment_count,
    get_doctor_by_id,
    get_next_doctor_code,
    update_doctor,
)
from .patient_service import (
    archive_patient,
    create_patient,
    delete_patient,
    get_next_patient_code,
    get_patient_appointment_count,
    get_patient_by_id,
    update_patient,
)
from .profile_service import (
    ALLOWED_ROLES,
    ALLOWED_SCALING,
    ALLOWED_THEMES,
    ALLOWED_VIEWS,
    get_user_profile,
    update_user_profile,
    validate_profile_data,
)
from .tqm_service import (
    DEFECT_CATEGORIES,
    DEFECT_SEVERITIES,
    DEFECT_STATUSES,
    add_fmea_record,
    calculate_rpn,
    get_ctq_tree_data,
    get_defect_logs,
    get_defect_pareto_data,
    get_fishbone_data,
    get_fmea_records,
    get_next_defect_code,
    get_pdca_cycles_data,
    get_sipoc_data,
    log_defect,
    update_defect_status,
    validate_defect_data,
    validate_fmea_data,
)
from .report_service import (
    get_appointments_by_status,
    get_appointments_over_time,
    get_doctor_workload,
    get_patient_satisfaction_data,
    get_reports_summary_stats,
)
from .validation import (
    validate_appointment_data,
    validate_doctor_data,
    validate_patient_data,
)

__all__ = [
    # Patient service
    "validate_patient_data",
    "get_next_patient_code",
    "get_patient_by_id",
    "get_patient_appointment_count",
    "create_patient",
    "update_patient",
    "archive_patient",
    "delete_patient",
    # Doctor service
    "validate_doctor_data",
    "get_next_doctor_code",
    "get_doctor_by_id",
    "get_doctor_appointment_count",
    "create_doctor",
    "update_doctor",
    "archive_doctor",
    "delete_doctor",
    # Appointment service
    "validate_appointment_data",
    "get_next_appointment_code",
    "get_appointment_by_id",
    "get_patient_dropdown_options",
    "get_doctor_dropdown_options",
    "check_slot_conflict",
    "create_appointment",
    "update_appointment",
    "cancel_appointment",
    "delete_appointment",
    # Report service
    "get_appointments_by_status",
    "get_appointments_over_time",
    "get_doctor_workload",
    "get_patient_satisfaction_data",
    "get_reports_summary_stats",
    # Profile service
    "get_user_profile",
    "validate_profile_data",
    "update_user_profile",
    "ALLOWED_ROLES",
    "ALLOWED_THEMES",
    "ALLOWED_SCALING",
    "ALLOWED_VIEWS",
    # TQM service
    "calculate_rpn",
    "get_fmea_records",
    "validate_fmea_data",
    "add_fmea_record",
    "get_defect_logs",
    "get_defect_pareto_data",
    "validate_defect_data",
    "log_defect",
    "update_defect_status",
    "get_next_defect_code",
    "get_sipoc_data",
    "get_ctq_tree_data",
    "get_fishbone_data",
    "get_pdca_cycles_data",
    "DEFECT_SEVERITIES",
    "DEFECT_STATUSES",
    "DEFECT_CATEGORIES",
]



