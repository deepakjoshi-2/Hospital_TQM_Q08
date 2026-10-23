"""Fictional demo seed data generator for Hospital Management System — Q08.
Generates realistic clinical records, user settings, and TQM defect logs.
"""
from typing import Optional

from database.connection import get_db_cursor, init_db


def seed_database(db_path: Optional[str] = None) -> None:
    """Populate database with fictional demo records."""
    init_db(db_path)

    with get_db_cursor(db_path) as (conn, cursor):
        # 1. User Profile Settings (Q08 Features 3 & 5)
        cursor.execute(
            """
            INSERT OR REPLACE INTO user_profile (
                id, username, full_name, role, email, phone, 
                theme_preference, scaling_factor, default_view, notifications_enabled
            ) VALUES (
                1, 'deepak_admin', 'Deepak Joshi', 'Hospital Administrator',
                'deepak.joshi.tqm@hospital.demo', '+91 98765 43210',
                'Dark', '100%', 'Dashboard', 1
            );
            """
        )

        # 2. Doctors (10 fictional specialists)
        doctors_data = [
            ("DOC-2001", "Dr. Rajesh", "Sharma", "Cardiology", "+91 98111 22001", "rajesh.sharma@hospital.demo", 800.0, "Cardio-101", "Available"),
            ("DOC-2002", "Dr. Ananya", "Sen", "Pediatrics", "+91 98111 22002", "ananya.sen@hospital.demo", 600.0, "Pedia-104", "Available"),
            ("DOC-2003", "Dr. Vikram", "Mehta", "Orthopedics", "+91 98111 22003", "vikram.mehta@hospital.demo", 750.0, "Ortho-202", "In Consultation"),
            ("DOC-2004", "Dr. Sunita", "Patel", "General Medicine", "+91 98111 22004", "sunita.patel@hospital.demo", 500.0, "GenMed-103", "Available"),
            ("DOC-2005", "Dr. Amit", "Khurana", "Neurology", "+91 98111 22005", "amit.khurana@hospital.demo", 900.0, "Neuro-301", "Available"),
            ("DOC-2006", "Dr. Sneha", "Reddy", "Dermatology", "+91 98111 22006", "sneha.reddy@hospital.demo", 650.0, "Derma-105", "Available"),
            ("DOC-2007", "Dr. Farhan", "Qureshi", "General Surgery", "+91 98111 22007", "farhan.qureshi@hospital.demo", 1000.0, "Surg-401", "On Leave"),
            ("DOC-2008", "Dr. Kavita", "Iyer", "Psychiatry", "+91 98111 22008", "kavita.iyer@hospital.demo", 700.0, "Psych-204", "Available"),
            ("DOC-2009", "Dr. Manish", "Gupta", "Radiology", "+91 98111 22009", "manish.gupta@hospital.demo", 850.0, "Radio-B02", "Available"),
            ("DOC-2010", "Dr. Pooja", "Bansal", "General Medicine", "+91 98111 22010", "pooja.bansal@hospital.demo", 500.0, "GenMed-106", "In Consultation"),
        ]

        cursor.executemany(
            """
            INSERT OR IGNORE INTO doctors (
                doctor_code, first_name, last_name, specialization, phone, email, consultation_fee, room_number, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            doctors_data,
        )

        # 3. Patients (25 fictional patient records)
        patients_data = [
            ("PAT-1001", "Aarav", "Verma", "1992-04-15", "Male", "+91 98222 10001", "aarav.verma@example.demo", "B+", "+91 98222 99001", "Flat 402, Lotus Towers, City Center", "Active"),
            ("PAT-1002", "Diya", "Kapoor", "1998-08-22", "Female", "+91 98222 10002", "diya.k@example.demo", "O+", "+91 98222 99002", "12 Park Street, Green View", "Active"),
            ("PAT-1003", "Kabir", "Singhania", "1985-11-03", "Male", "+91 98222 10003", "kabir.s@example.demo", "A+", "+91 98222 99003", "45 Sector 14, Urban Enclave", "Active"),
            ("PAT-1004", "Meera", "Nambiar", "2001-02-18", "Female", "+91 98222 10004", "meera.n@example.demo", "AB+", "+91 98222 99004", "8 Hill Road, Lake District", "Active"),
            ("PAT-1005", "Rohan", "Bose", "1976-06-30", "Male", "+91 98222 10005", "rohan.bose@example.demo", "O-", "+91 98222 99005", "77 Lake Gardens, South Ext.", "Active"),
            ("PAT-1006", "Tara", "Deshmukh", "2015-09-12", "Female", "+91 98222 10006", "tara.desh@example.demo", "A+", "+91 98222 99006", "Plot 33, Royal Palms", "Active"),
            ("PAT-1007", "Aditya", "Rao", "1968-12-05", "Male", "+91 98222 10007", "aditya.rao@example.demo", "B+", "+91 98222 99007", "Block B, Sunrise Residency", "Active"),
            ("PAT-1008", "Ishita", "Chopra", "1994-01-27", "Female", "+91 98222 10008", "ishita.c@example.demo", "O+", "+91 98222 99008", "House 10, Civil Lines", "Active"),
            ("PAT-1009", "Nikhil", "Saxena", "1989-07-19", "Male", "+91 98222 10009", "nikhil.sax@example.demo", "AB-", "+91 98222 99009", "C-24 Defence Colony", "Active"),
            ("PAT-1010", "Ananya", "Mishra", "2003-10-14", "Female", "+91 98222 10010", "ananya.m@example.demo", "A-", "+91 98222 99010", "5th Cross, Malleshwaram", "Active"),
            ("PAT-1011", "Kunal", "Trivedi", "1982-03-08", "Male", "+91 98222 10011", "kunal.t@example.demo", "B-", "+91 98222 99011", "Sector 22, Vashi", "Discharged"),
            ("PAT-1012", "Rhea", "Pillai", "1996-05-25", "Female", "+91 98222 10012", "rhea.p@example.demo", "O+", "+91 98222 99012", "19 Jubilee Hills", "Active"),
            ("PAT-1013", "Siddharth", "Ghosh", "1973-11-17", "Male", "+91 98222 10013", "sid.ghosh@example.demo", "A+", "+91 98222 99013", "Flat 101, Salt Lake City", "Active"),
            ("PAT-1014", "Pooja", "Menon", "1990-12-02", "Female", "+91 98222 10014", "pooja.menon@example.demo", "B+", "+91 98222 99014", "22 MG Road, Cantonment", "Active"),
            ("PAT-1015", "Harsh", "Vardhan", "2018-04-11", "Male", "+91 98222 10015", "harsh.v@example.demo", "O+", "+91 98222 99015", "Silver Oak Apartments", "Active"),
            ("PAT-1016", "Tanvi", "Kulkarni", "1995-09-09", "Female", "+91 98222 10016", "tanvi.k@example.demo", "AB+", "+91 98222 99016", "Kothrud, Pune", "Active"),
            ("PAT-1017", "Varun", "Malhotra", "1987-01-31", "Male", "+91 98222 10017", "varun.m@example.demo", "O-", "+91 98222 99017", "Model Town, Phase II", "Active"),
            ("PAT-1018", "Simran", "Bhatia", "2000-07-21", "Female", "+91 98222 10018", "simran.b@example.demo", "B+", "+91 98222 99018", "Preet Vihar, Delhi", "Active"),
            ("PAT-1019", "Gaurav", "Pandey", "1980-08-14", "Male", "+91 98222 10019", "gaurav.p@example.demo", "A+", "+91 98222 99019", "Aliganj, Lucknow", "Active"),
            ("PAT-1020", "Zoya", "Khan", "1993-03-04", "Female", "+91 98222 10020", "zoya.khan@example.demo", "O+", "+91 98222 99020", "Banjara Hills, Hyderabad", "Active"),
            ("PAT-1021", "Manish", "Tiwari", "1965-06-16", "Male", "+91 98222 10021", "manish.t@example.demo", "B+", "+91 98222 99021", "Civil Lines, Kanpur", "Discharged"),
            ("PAT-1022", "Kritika", "Jain", "1999-10-29", "Female", "+91 98222 10022", "kritika.j@example.demo", "A-", "+91 98222 99022", "Malviya Nagar, Jaipur", "Active"),
            ("PAT-1023", "Arnav", "Chatterjee", "1984-12-24", "Male", "+91 98222 10023", "arnav.c@example.demo", "AB+", "+91 98222 99023", "New Town, Kolkata", "Active"),
            ("PAT-1024", "Shruti", "Sarin", "1991-05-19", "Female", "+91 98222 10024", "shruti.s@example.demo", "O+", "+91 98222 99024", "Whitefield, Bangalore", "Active"),
            ("PAT-1025", "Dev", "Narayan", "1978-02-11", "Male", "+91 98222 10025", "dev.n@example.demo", "B+", "+91 98222 99025", "Kadavanthra, Kochi", "Active"),
        ]

        cursor.executemany(
            """
            INSERT OR IGNORE INTO patients (
                patient_code, first_name, last_name, dob, gender, phone, email, blood_group, emergency_contact, address, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            patients_data,
        )

        # 4. Fetch Patient and Doctor ID mapping for relational appointment keys
        cursor.execute("SELECT id, patient_code FROM patients;")
        pat_map = {row["patient_code"]: row["id"] for row in cursor.fetchall()}

        cursor.execute("SELECT id, doctor_code FROM doctors;")
        doc_map = {row["doctor_code"]: row["id"] for row in cursor.fetchall()}

        # 5. Appointments (42 fictional appointments with ratings, status, and dates)
        appointments_data = [
            ("APT-3001", pat_map["PAT-1001"], doc_map["DOC-2001"], "2026-10-05", "09:00 AM", "Annual cardiac assessment", "Normal", "Completed", 5, "BP stable, ECG normal"),
            ("APT-3002", pat_map["PAT-1002"], doc_map["DOC-2004"], "2026-10-05", "10:30 AM", "Persistent migraine & fever", "Urgent", "Completed", 4, "Prescribed analgesics"),
            ("APT-3003", pat_map["PAT-1003"], doc_map["DOC-2003"], "2026-10-05", "02:00 PM", "Right knee joint pain", "Normal", "Completed", 5, "X-ray recommended"),
            ("APT-3004", pat_map["PAT-1004"], doc_map["DOC-2006"], "2026-10-06", "09:30 AM", "Skin allergy consultation", "Normal", "Completed", 4, "Prescribed topical ointment"),
            ("APT-3005", pat_map["PAT-1005"], doc_map["DOC-2001"], "2026-10-06", "11:00 AM", "Hypertension follow-up", "Follow-up", "Completed", 5, "Dosage adjusted"),
            ("APT-3006", pat_map["PAT-1006"], doc_map["DOC-2002"], "2026-10-06", "03:00 PM", "Pediatric immunization check", "Normal", "Completed", 5, "Vaccination administered"),
            ("APT-3007", pat_map["PAT-1007"], doc_map["DOC-2005"], "2026-10-07", "10:00 AM", "Tremors and nerve pain", "Urgent", "Completed", 3, "MRI requested"),
            ("APT-3008", pat_map["PAT-1008"], doc_map["DOC-2004"], "2026-10-07", "11:30 AM", "Seasonal flu checkup", "Normal", "Completed", 5, "Hydration advised"),
            ("APT-3009", pat_map["PAT-1009"], doc_map["DOC-2008"], "2026-10-07", "02:30 PM", "Anxiety counseling", "Normal", "Completed", 4, "Therapy session 1 complete"),
            ("APT-3010", pat_map["PAT-1010"], doc_map["DOC-2006"], "2026-10-07", "04:00 PM", "Acne treatment follow-up", "Follow-up", "Completed", 5, "Significant improvement"),
            ("APT-3011", pat_map["PAT-1011"], doc_map["DOC-2003"], "2026-10-08", "09:30 AM", "Post-cast removal check", "Follow-up", "Completed", 4, "Physiotherapy started"),
            ("APT-3012", pat_map["PAT-1012"], doc_map["DOC-2009"], "2026-10-08", "11:00 AM", "Chest X-Ray interpretation", "Normal", "Completed", 5, "Clear scan confirmed"),
            ("APT-3013", pat_map["PAT-1013"], doc_map["DOC-2001"], "2026-10-08", "02:00 PM", "Chest tightness evaluation", "Urgent", "Completed", 4, "Treadmill test scheduled"),
            ("APT-3014", pat_map["PAT-1014"], doc_map["DOC-2010"], "2026-10-08", "03:30 PM", "Routine executive health screen", "Normal", "Completed", 5, "All vitals optimal"),
            ("APT-3015", pat_map["PAT-1015"], doc_map["DOC-2002"], "2026-10-08", "04:30 PM", "Childhood asthma checkup", "Normal", "Completed", 4, "Inhaler review done"),
            
            # Today's appointments (2026-10-09)
            ("APT-3016", pat_map["PAT-1016"], doc_map["DOC-2001"], "2026-10-09", "09:00 AM", "Post-angioplasty review", "Urgent", "Completed", 5, "Recovery on track"),
            ("APT-3017", pat_map["PAT-1017"], doc_map["DOC-2004"], "2026-10-09", "09:30 AM", "High fever & body ache", "Urgent", "Completed", 4, "Blood panel drawn"),
            ("APT-3018", pat_map["PAT-1018"], doc_map["DOC-2003"], "2026-10-09", "10:00 AM", "Lumbar spine discomfort", "Normal", "Scheduled", None, "Awaiting patient arrival"),
            ("APT-3019", pat_map["PAT-1019"], doc_map["DOC-2002"], "2026-10-09", "10:30 AM", "Pediatric ear infection", "Normal", "Scheduled", None, "In waiting area"),
            ("APT-3020", pat_map["PAT-1020"], doc_map["DOC-2005"], "2026-10-09", "11:30 AM", "Chronic migraine management", "Normal", "Scheduled", None, "Pre-consultation notes ready"),
            ("APT-3021", pat_map["PAT-1021"], doc_map["DOC-2006"], "2026-10-09", "02:00 PM", "Eczema flare-up review", "Follow-up", "Scheduled", None, "Confirmed by receptionist"),
            ("APT-3022", pat_map["PAT-1022"], doc_map["DOC-2008"], "2026-10-09", "02:30 PM", "Stress & sleep disturbance", "Normal", "Scheduled", None, "Confirmed"),
            ("APT-3023", pat_map["PAT-1023"], doc_map["DOC-2009"], "2026-10-09", "03:30 PM", "Abdominal ultrasound review", "Normal", "Scheduled", None, "Fast track queue"),
            ("APT-3024", pat_map["PAT-1024"], doc_map["DOC-2010"], "2026-10-09", "04:00 PM", "Diabetes type 2 follow-up", "Follow-up", "Scheduled", None, "HbA1c test reports ready"),
            ("APT-3025", pat_map["PAT-1025"], doc_map["DOC-2001"], "2026-10-09", "04:30 PM", "Arrhythmia screening", "Normal", "Scheduled", None, "Confirmed"),

            # Upcoming appointments
            ("APT-3026", pat_map["PAT-1001"], doc_map["DOC-2003"], "2026-10-10", "09:00 AM", "Ankle sprain check", "Normal", "Scheduled", None, "Booked via front desk"),
            ("APT-3027", pat_map["PAT-1002"], doc_map["DOC-2006"], "2026-10-10", "10:00 AM", "Dermatology follow-up", "Follow-up", "Scheduled", None, "Follow-up session"),
            ("APT-3028", pat_map["PAT-1003"], doc_map["DOC-2005"], "2026-10-10", "11:00 AM", "Neuropathy consultation", "Normal", "Scheduled", None, "Referral from GenMed"),
            ("APT-3029", pat_map["PAT-1004"], doc_map["DOC-2002"], "2026-10-10", "02:00 PM", "Child health wellness check", "Normal", "Scheduled", None, "Routine"),
            ("APT-3030", pat_map["PAT-1005"], doc_map["DOC-2004"], "2026-10-11", "09:30 AM", "Cholesterol follow-up", "Follow-up", "Scheduled", None, "LIPID profile required"),
            ("APT-3031", pat_map["PAT-1006"], doc_map["DOC-2008"], "2026-10-11", "10:30 AM", "Behavioral guidance session", "Normal", "Scheduled", None, "Scheduled"),
            ("APT-3032", pat_map["PAT-1007"], doc_map["DOC-2009"], "2026-10-11", "03:00 PM", "Spine MRI review", "Urgent", "Scheduled", None, "High priority"),
            ("APT-3033", pat_map["PAT-1008"], doc_map["DOC-2001"], "2026-10-12", "09:00 AM", "Preventive heart screening", "Normal", "Scheduled", None, "Preventive package"),
            ("APT-3034", pat_map["PAT-1009"], doc_map["DOC-2010"], "2026-10-12", "11:30 AM", "Thyroid profile review", "Follow-up", "Scheduled", None, "Lab results pending"),
            ("APT-3035", pat_map["PAT-1010"], doc_map["DOC-2003"], "2026-10-12", "02:30 PM", "Shoulder stiffness eval", "Normal", "Scheduled", None, "Physical therapy referral"),
            
            # Historical Cancelled & No-Show records
            ("APT-3036", pat_map["PAT-1011"], doc_map["DOC-2004"], "2026-10-04", "10:00 AM", "General health checkup", "Normal", "Cancelled", None, "Patient rescheduled due to travel"),
            ("APT-3037", pat_map["PAT-1012"], doc_map["DOC-2005"], "2026-10-04", "02:00 PM", "Headache evaluation", "Normal", "Cancelled", None, "Doctor emergency surgery"),
            ("APT-3038", pat_map["PAT-1013"], doc_map["DOC-2006"], "2026-10-03", "11:30 AM", "Skin allergy patch test", "Normal", "No-Show", None, "Patient did not attend"),
            ("APT-3039", pat_map["PAT-1014"], doc_map["DOC-2002"], "2026-10-03", "03:00 PM", "Vaccination round 2", "Normal", "Cancelled", None, "Child had mild fever"),
            ("APT-3040", pat_map["PAT-1015"], doc_map["DOC-2001"], "2026-10-02", "09:00 AM", "ECG Routine screening", "Normal", "Completed", 4, "Satisfactory clinic visit"),
            ("APT-3041", pat_map["PAT-1016"], doc_map["DOC-2004"], "2026-10-02", "10:30 AM", "Gastric discomfort", "Normal", "Completed", 5, "Prompt relief after medication"),
            ("APT-3042", pat_map["PAT-1017"], doc_map["DOC-2008"], "2026-10-01", "04:00 PM", "Follow-up consultation", "Follow-up", "Completed", 4, "Treatment plan renewed"),
        ]

        cursor.executemany(
            """
            INSERT OR IGNORE INTO appointments (
                appointment_code, patient_id, doctor_id, appointment_date, time_slot, 
                reason, priority, status, satisfaction_rating, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            appointments_data,
        )

        # 6. TQM Defect Log (Fictional Voice of Customer Defect Checksheet data for Pareto analysis)
        defects_data = [
            ("DEF-4001", "Appointment Booking Error", "Critical", "Duplicate booking attempted for same doctor time slot", "Front Desk Operator", "Resolved"),
            ("DEF-4002", "Appointment Booking Error", "Major", "Selected slot displayed as available despite being filled", "Receptionist B", "Resolved"),
            ("DEF-4003", "Appointment Booking Error", "Critical", "Time slot timezone shift confusion during weekend change", "Receptionist A", "Resolved"),
            ("DEF-4004", "Appointment Booking Error", "Major", "Unable to select doctor from inactive specialty dropdown", "Admin Assistant", "Resolved"),
            ("DEF-4005", "Appointment Booking Error", "Major", "Patient appointment ID collision on concurrent entry", "Front Desk Operator", "Resolved"),
            ("DEF-4006", "Confusing Form Layout", "Major", "Mandatory emergency contact field not clearly highlighted", "Staff Nurse", "Resolved"),
            ("DEF-4007", "Confusing Form Layout", "Minor", "Date picker format ambiguous (MM/DD vs DD/MM)", "Receptionist B", "Resolved"),
            ("DEF-4008", "Confusing Form Layout", "Minor", "Action button hierarchy unclear between Save and Reset", "Front Desk Operator", "Resolved"),
            ("DEF-4009", "Confusing Form Layout", "Major", "Doctor specialization list was unsorted alphabetically", "Receptionist A", "Resolved"),
            ("DEF-4010", "UI Lag / Latency", "Critical", "Table freeze when loading more than 100 historical appointments", "System Admin", "Resolved"),
            ("DEF-4011", "UI Lag / Latency", "Major", "Search box lagged on rapid keystrokes without debouncing", "Staff Nurse", "Resolved"),
            ("DEF-4012", "UI Lag / Latency", "Major", "Reports chart took over 3 seconds to redraw upon filter change", "Data Analyst", "Resolved"),
            ("DEF-4013", "Missing Feedback Toast", "Minor", "No visual confirmation toast after successful patient edit", "Receptionist B", "Resolved"),
            ("DEF-4014", "Missing Feedback Toast", "Minor", "Save button gave no visual indication of background persistence", "Receptionist A", "Resolved"),
            ("DEF-4015", "Missing Feedback Toast", "Minor", "Delete confirmation dialog lacked warning severity icon", "Front Desk Operator", "Resolved"),
            ("DEF-4016", "Doctor Schedule Overlap", "Critical", "Doctor marked Available while simultaneously scheduled for surgery", "Duty Manager", "Resolved"),
            ("DEF-4017", "Doctor Schedule Overlap", "Major", "On Leave doctor appeared in quick-booking recommendation list", "Receptionist B", "Resolved"),
            ("DEF-4018", "Search Filter Inaccuracy", "Minor", "Partial phone number search required exact full 10 digits", "Receptionist A", "Resolved"),
            ("DEF-4019", "Search Filter Inaccuracy", "Minor", "Case-sensitive patient name search missed lowercase queries", "Front Desk Operator", "Resolved"),
            ("DEF-4020", "Theme / Visual Fatigue", "Minor", "High glare during late evening shifts without dark mode", "Night Shift Nurse", "Resolved"),
            ("DEF-4021", "Theme / Visual Fatigue", "Minor", "Poor chart contrast when printing or switching high-DPI displays", "Quality Officer", "Resolved"),
        ]

        cursor.executemany(
            """
            INSERT OR IGNORE INTO tqm_defect_logs (
                defect_code, category, severity, description, reported_by, resolution_status
            ) VALUES (?, ?, ?, ?, ?, ?);
            """,
            defects_data,
        )

        # 7. TQM FMEA Records (Outpatient Service Failure Modes & Effects)
        fmea_data = [
            ("Patient Check-in", "Manual data entry typo in phone/email", "Missed appointment SMS alert", "Fatigue during peak hours", 6, 7, 5, 210, "Input regex validation & live field masks", 6, 2, 2, 24),
            ("Slot Reservation", "Double booking same doctor slot", "Patient wait time exceeds 60m, dispute", "Race condition in booking UI", 8, 8, 6, 384, "SQLite partial unique index + atomic lock", 8, 1, 1, 8),
            ("Doctor Assignment", "Scheduling doctor on leave", "Patient turns up but doctor unavailable", "Disconnected roster database", 9, 6, 5, 270, "Real-time doctor status guard before save", 9, 1, 2, 18),
            ("Form Submission", "Silent submission failure", "Lost appointment record in queue", "Uncaught database constraint crash", 8, 5, 7, 280, "Transaction rollback & non-blocking toast", 8, 1, 2, 16),
            ("Records Lookup", "Search timeout on large patient list", "Reception queue builds up (> 5 mins/patient)", "Full table scan without indexing", 7, 7, 4, 196, "B-Tree indexing on phone, names, and status", 7, 2, 2, 28),
            ("User Interaction", "Accidental record deletion", "Permanent loss of clinical demographic data", "Single click without confirmation", 9, 4, 3, 108, "Two-step modal confirmation dialog", 9, 1, 1, 9),
            ("Visual Analytics", "Chart freeze during report export", "Executive reporting delayed", "Synchronous Matplotlib rendering", 5, 5, 6, 150, "Optimized canvas redraws with pre-computed aggregations", 5, 2, 2, 20),
            ("Night Operations", "Visual eye strain & fatigue", "Operator error rate rises after 8 PM", "Bright monochromatic white UI only", 6, 8, 4, 192, "High-contrast Dark/Light toggle (Q08 Core)", 6, 2, 2, 24),
        ]

        for item in fmea_data:
            cursor.execute(
                "SELECT id FROM tqm_fmea_records WHERE process_step = ? AND failure_mode = ? LIMIT 1;",
                (item[0], item[1]),
            )
            if not cursor.fetchone():
                cursor.execute(
                    """
                    INSERT INTO tqm_fmea_records (
                        process_step, failure_mode, failure_effect, potential_cause,
                        severity_s, occurrence_o, detection_d, rpn, mitigation_action,
                        target_severity, target_occurrence, target_detection, target_rpn
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                    """,
                    item,
                )

        # 8. Seed RBAC Users (Feature 2)
        import hashlib
        import secrets

        def _seed_hash(password: str, salt: str) -> str:
            return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000).hex()

        seed_users = [
            ("admin", "deepak.admin@hospital.demo", "Admin@123", "Hospital Administrator", "Deepak Joshi (Administrator)", None, None),
            ("staff_reception", "reception@hospital.demo", "Staff@123", "Staff", "Pooja Verma (Reception Desk)", None, None),
            ("dr_arun", "rajesh.sharma@hospital.demo", "Doctor@123", "Doctor", "Dr. Rajesh Sharma", None, doc_map.get("DOC-2001", 1)),
            ("patient_aarav", "aarav.verma@example.demo", "Patient@123", "Patient", "Aarav Verma", pat_map.get("PAT-1001", 1), None),
        ]

        for uname, email, raw_pwd, role, fname, pat_id, doc_id in seed_users:
            cursor.execute("SELECT id FROM users WHERE username = ?;", (uname,))
            if not cursor.fetchone():
                salt = secrets.token_hex(16)
                pwd_hash = _seed_hash(raw_pwd, salt)
                cursor.execute(
                    """
                    INSERT INTO users (username, email, password_hash, salt, role, full_name, linked_patient_id, linked_doctor_id, is_active)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1);
                    """,
                    (uname, email, pwd_hash, salt, role, fname, pat_id, doc_id),
                )


if __name__ == "__main__":
    seed_database()
    print("Database successfully seeded with fictional demo clinical data!")
