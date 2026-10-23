"""Application constants and enumerations for Hospital Management System - Q08."""
import os
from pathlib import Path

# Project Metadata
APP_NAME = "Hospital TQM — Q08 User Satisfaction System"
APP_SUBTITLE = "BBAT104 Fundamentals of Total Quality Management"
STUDENT_NAME = "Deepak Joshi"
STUDENT_BRANCH = "B.Tech CSE"
STUDENT_SECTION = "Section B"
APP_VERSION = "1.0.0"

# Filesystem Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DEFAULT_DB_PATH = str(BASE_DIR / "hospital_tqm.db")

# Status Constants
STATUS_PENDING = "Pending"
STATUS_CONFIRMED = "Confirmed"
STATUS_SCHEDULED = "Scheduled"
STATUS_COMPLETED = "Completed"
STATUS_CANCELLED = "Cancelled"
STATUS_NO_SHOW = "No-Show"
APPOINTMENT_STATUSES = [
    STATUS_PENDING,
    STATUS_CONFIRMED,
    STATUS_SCHEDULED,
    STATUS_COMPLETED,
    STATUS_CANCELLED,
    STATUS_NO_SHOW,
]

# Role-Based Access Control (RBAC) Constants
ROLE_PATIENT = "Patient"
ROLE_DOCTOR = "Doctor"
ROLE_STAFF = "Staff"
ROLE_ADMIN = "Hospital Administrator"
USER_ROLES = [
    ROLE_PATIENT,
    ROLE_DOCTOR,
    ROLE_STAFF,
    ROLE_ADMIN,
]

# Notification Types
NOTIF_BOOKING = "Booking"
NOTIF_CONFIRMATION = "Confirmation"
NOTIF_CANCELLATION = "Cancellation"
NOTIF_REMINDER = "Reminder"
NOTIF_BILLING = "Billing"
NOTIF_SYSTEM = "System"
NOTIFICATION_TYPES = [
    NOTIF_BOOKING,
    NOTIF_CONFIRMATION,
    NOTIF_CANCELLATION,
    NOTIF_REMINDER,
    NOTIF_BILLING,
    NOTIF_SYSTEM,
]

# Billing and Invoicing Constants
BILL_STATUS_UNPAID = "Unpaid"
BILL_STATUS_PARTIALLY_PAID = "Partially Paid"
BILL_STATUS_PAID = "Paid"
BILL_STATUS_REFUNDED = "Refunded"
BILL_STATUSES = [
    BILL_STATUS_UNPAID,
    BILL_STATUS_PARTIALLY_PAID,
    BILL_STATUS_PAID,
    BILL_STATUS_REFUNDED,
]

PAYMENT_METHOD_CASH = "Cash"
PAYMENT_METHOD_CARD = "Card"
PAYMENT_METHOD_UPI = "UPI"
PAYMENT_METHOD_NET_BANKING = "Net Banking"
PAYMENT_METHOD_INSURANCE = "Insurance"
PAYMENT_METHODS = [
    PAYMENT_METHOD_CASH,
    PAYMENT_METHOD_CARD,
    PAYMENT_METHOD_UPI,
    PAYMENT_METHOD_NET_BANKING,
    PAYMENT_METHOD_INSURANCE,
]

# Payment Transaction Statuses
PAYMENT_STATUS_SUCCESS = "Success"
PAYMENT_STATUS_FAILED = "Failed"
PAYMENT_STATUS_CANCELLED = "Cancelled"
PAYMENT_STATUS_REFUNDED = "Refunded"
PAYMENT_STATUSES = [
    PAYMENT_STATUS_SUCCESS,
    PAYMENT_STATUS_FAILED,
    PAYMENT_STATUS_CANCELLED,
    PAYMENT_STATUS_REFUNDED,
]

# Gateway Modes
GATEWAY_MODE_DEMO = "Demo Mode"
GATEWAY_MODE_REAL = "Real Gateway"

PRIORITY_NORMAL = "Normal"
PRIORITY_URGENT = "Urgent"
PRIORITY_FOLLOW_UP = "Follow-up"
APPOINTMENT_PRIORITIES = [
    PRIORITY_NORMAL,
    PRIORITY_URGENT,
    PRIORITY_FOLLOW_UP,
]

DOCTOR_AVAILABLE = "Available"
DOCTOR_IN_CONSULTATION = "In Consultation"
DOCTOR_ON_LEAVE = "On Leave"
DOCTOR_STATUSES = [
    DOCTOR_AVAILABLE,
    DOCTOR_IN_CONSULTATION,
    DOCTOR_ON_LEAVE,
]

PATIENT_ACTIVE = "Active"
PATIENT_DISCHARGED = "Discharged"
PATIENT_ARCHIVED = "Archived"
PATIENT_STATUSES = [
    PATIENT_ACTIVE,
    PATIENT_DISCHARGED,
    PATIENT_ARCHIVED,
]

BLOOD_GROUPS = ["A+", "A-", "B+", "B-", "AB+", "AB-", "O+", "O-"]

SPECIALIZATIONS = [
    "Cardiology",
    "Dermatology",
    "General Medicine",
    "Neurology",
    "Orthopedics",
    "Pediatrics",
    "Psychiatry",
    "Radiology",
    "General Surgery",
]

# TQM Quality Friction Categories (Voice of Customer Defect Types)
TQM_DEFECT_CATEGORIES = [
    "Appointment Booking Error",
    "Confusing Form Layout",
    "UI Lag / Latency",
    "Missing Feedback Toast",
    "Doctor Schedule Overlap",
    "Search Filter Inaccuracy",
    "Report Generation Delay",
    "Theme / Visual Fatigue",
]

TQM_DEFECT_SEVERITIES = ["Critical", "Major", "Minor"]

TIME_SLOTS = [
    "09:00 AM", "09:30 AM", "10:00 AM", "10:30 AM",
    "11:00 AM", "11:30 AM", "12:00 PM", "12:30 PM",
    "02:00 PM", "02:30 PM", "03:00 PM", "03:30 PM",
    "04:00 PM", "04:30 PM", "05:00 PM", "05:30 PM",
]
