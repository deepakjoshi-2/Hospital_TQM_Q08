-- ============================================================================
-- Hospital Management System — Q08: Improve User Satisfaction
-- Relational Database DDL Schema (SQLite 3)
-- Student: Deepak Joshi | Branch: CSE | Section: B
-- Course: BBAT104 Fundamentals of Total Quality Management
-- ============================================================================

PRAGMA foreign_keys = ON;

-- 1. User Profile & Settings Table (Q08 Features 3 & 5)
CREATE TABLE IF NOT EXISTS user_profile (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    full_name TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'Receptionist',
    email TEXT,
    phone TEXT,
    theme_preference TEXT NOT NULL DEFAULT 'Dark' CHECK(theme_preference IN ('Dark', 'Light', 'System')),
    scaling_factor TEXT NOT NULL DEFAULT '100%' CHECK(scaling_factor IN ('80%', '90%', '100%', '110%', '120%')),
    default_view TEXT NOT NULL DEFAULT 'Dashboard',
    notifications_enabled INTEGER NOT NULL DEFAULT 1 CHECK(notifications_enabled IN (0, 1)),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Patients Table (Base Module 1)
CREATE TABLE IF NOT EXISTS patients (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_code TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    dob TEXT NOT NULL,
    gender TEXT NOT NULL CHECK(gender IN ('Male', 'Female', 'Other')),
    phone TEXT NOT NULL,
    email TEXT,
    blood_group TEXT CHECK(blood_group IN ('A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-')),
    emergency_contact TEXT,
    address TEXT,
    status TEXT NOT NULL DEFAULT 'Active' CHECK(status IN ('Active', 'Discharged', 'Archived')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Doctors Table (Base Module 2)
CREATE TABLE IF NOT EXISTS doctors (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    doctor_code TEXT UNIQUE NOT NULL,
    first_name TEXT NOT NULL,
    last_name TEXT NOT NULL,
    specialization TEXT NOT NULL,
    phone TEXT NOT NULL,
    email TEXT NOT NULL,
    consultation_fee REAL NOT NULL DEFAULT 500.0 CHECK(consultation_fee >= 0),
    room_number TEXT NOT NULL,
    status TEXT NOT NULL DEFAULT 'Available' CHECK(status IN ('Available', 'In Consultation', 'On Leave')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 4. Appointments Table (Base Module 3)
CREATE TABLE IF NOT EXISTS appointments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    appointment_code TEXT UNIQUE NOT NULL,
    patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
    doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE RESTRICT,
    appointment_date TEXT NOT NULL,
    time_slot TEXT NOT NULL,
    reason TEXT NOT NULL,
    priority TEXT NOT NULL DEFAULT 'Normal' CHECK(priority IN ('Normal', 'Urgent', 'Follow-up')),
    status TEXT NOT NULL DEFAULT 'Scheduled' CHECK(status IN ('Scheduled', 'Completed', 'Cancelled', 'No-Show')),
    satisfaction_rating INTEGER CHECK(satisfaction_rating IS NULL OR (satisfaction_rating BETWEEN 1 AND 5)),
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Partial Unique Index: Prevent doctor double-booking unless appointment is Cancelled
CREATE UNIQUE INDEX IF NOT EXISTS idx_appointments_slot_collision 
ON appointments(doctor_id, appointment_date, time_slot) 
WHERE status != 'Cancelled';

-- 5. TQM Defect Log Table (Q08 TQM Quality Deliverables)
CREATE TABLE IF NOT EXISTS tqm_defect_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    defect_code TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL,
    severity TEXT NOT NULL CHECK(severity IN ('Critical', 'Major', 'Minor')),
    description TEXT NOT NULL,
    reported_by TEXT NOT NULL,
    resolution_status TEXT NOT NULL DEFAULT 'Logged' CHECK(resolution_status IN ('Logged', 'In Analysis', 'Resolved')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    resolved_at TIMESTAMP
);

-- 6. TQM FMEA Matrix Table
CREATE TABLE IF NOT EXISTS tqm_fmea_records (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    process_step TEXT NOT NULL,
    failure_mode TEXT NOT NULL,
    failure_effect TEXT NOT NULL,
    potential_cause TEXT NOT NULL,
    severity_s INTEGER NOT NULL CHECK(severity_s BETWEEN 1 AND 10),
    occurrence_o INTEGER NOT NULL CHECK(occurrence_o BETWEEN 1 AND 10),
    detection_d INTEGER NOT NULL CHECK(detection_d BETWEEN 1 AND 10),
    rpn INTEGER NOT NULL,
    mitigation_action TEXT NOT NULL,
    target_severity INTEGER NOT NULL CHECK(target_severity BETWEEN 1 AND 10),
    target_occurrence INTEGER NOT NULL CHECK(target_occurrence BETWEEN 1 AND 10),
    target_detection INTEGER NOT NULL CHECK(target_detection BETWEEN 1 AND 10),
    target_rpn INTEGER NOT NULL
);

-- Relational Performance Indexes
CREATE INDEX IF NOT EXISTS idx_patients_name ON patients(last_name, first_name);
CREATE INDEX IF NOT EXISTS idx_patients_phone ON patients(phone);
CREATE INDEX IF NOT EXISTS idx_doctors_specialization ON doctors(specialization);
CREATE INDEX IF NOT EXISTS idx_doctors_status ON doctors(status);
CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);
CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);
CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);
CREATE INDEX IF NOT EXISTS idx_appointments_doctor ON appointments(doctor_id);
CREATE INDEX IF NOT EXISTS idx_tqm_defects_category ON tqm_defect_logs(category);
