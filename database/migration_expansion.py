"""Database migration script for Hospital TQM Q08 Major Feature Expansion.
Safely updates appointments schema (adds consultation_fee and expanded statuses),
creates users, notifications, bills, payments, and receipts tables,
and seeds initial RBAC role accounts and demo billing records.
"""
import hashlib
import os
import secrets
import sqlite3
from pathlib import Path
from typing import Optional, Tuple

from config.constants import DEFAULT_DB_PATH


def hash_password(password: str, salt: Optional[str] = None) -> Tuple[str, str]:
    """Compute PBKDF2 HMAC-SHA256 hash with 100,000 iterations and 16-byte salt."""
    if not salt:
        salt = secrets.token_hex(16)
    key = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt.encode("utf-8"), 100_000)
    return key.hex(), salt


def verify_password(password: str, stored_hash: str, salt: str) -> bool:
    """Verify raw password against stored PBKDF2 hash using constant-time comparison."""
    computed_hash, _ = hash_password(password, salt)
    return secrets.compare_digest(computed_hash, stored_hash)


def run_migration(db_path: Optional[str] = None) -> bool:
    """Execute migration on the target SQLite database safely preserving all records."""
    target_path = db_path or os.environ.get("HOSPITAL_DB_PATH", DEFAULT_DB_PATH)
    print(f"Starting expansion migration on: {target_path}")

    conn = sqlite3.connect(target_path, timeout=20.0)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()

    try:
        # Check current columns in appointments
        cursor.execute("PRAGMA table_info(appointments);")
        columns = [col["name"] for col in cursor.fetchall()]
        has_fee = "consultation_fee" in columns

        cursor.execute("PRAGMA foreign_keys = OFF;")
        conn.commit()

        # Step 1: Migrate appointments table if consultation_fee is missing
        if not has_fee:
            print("Migrating appointments table to include consultation_fee and expanded status check...")
            cursor.execute("SELECT COUNT(*) FROM appointments;")
            appt_count_before = cursor.fetchone()[0]
            print(f"Appointments count before: {appt_count_before}")

            cursor.execute("""
            CREATE TABLE appointments_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                appointment_code TEXT UNIQUE NOT NULL,
                patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE CASCADE,
                doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE RESTRICT,
                appointment_date TEXT NOT NULL,
                time_slot TEXT NOT NULL,
                reason TEXT NOT NULL,
                priority TEXT NOT NULL DEFAULT 'Normal' CHECK(priority IN ('Normal', 'Urgent', 'Follow-up')),
                status TEXT NOT NULL DEFAULT 'Confirmed' CHECK(status IN ('Pending', 'Confirmed', 'Scheduled', 'Completed', 'Cancelled', 'No-Show')),
                consultation_fee REAL NOT NULL DEFAULT 500.0 CHECK(consultation_fee >= 0),
                satisfaction_rating INTEGER CHECK(satisfaction_rating IS NULL OR (satisfaction_rating BETWEEN 1 AND 5)),
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            """)

            cursor.execute("""
            INSERT INTO appointments_new (
                id, appointment_code, patient_id, doctor_id, appointment_date,
                time_slot, reason, priority, status, consultation_fee, satisfaction_rating, notes, created_at, updated_at
            )
            SELECT 
                a.id, a.appointment_code, a.patient_id, a.doctor_id, a.appointment_date,
                a.time_slot, a.reason, a.priority, 
                CASE WHEN a.status = 'Scheduled' THEN 'Confirmed' ELSE a.status END,
                COALESCE(d.consultation_fee, 500.0),
                a.satisfaction_rating, a.notes, a.created_at, a.updated_at
            FROM appointments a
            LEFT JOIN doctors d ON a.doctor_id = d.id;
            """)

            cursor.execute("DROP TABLE appointments;")
            cursor.execute("ALTER TABLE appointments_new RENAME TO appointments;")

            # Recreate appointment indexes
            cursor.execute("""
            CREATE UNIQUE INDEX IF NOT EXISTS idx_appointments_slot_collision 
            ON appointments(doctor_id, appointment_date, time_slot) 
            WHERE status != 'Cancelled';
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_date ON appointments(appointment_date);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_status ON appointments(status);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_patient ON appointments(patient_id);")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_appointments_doctor ON appointments(doctor_id);")
            conn.commit()

            cursor.execute("SELECT COUNT(*) FROM appointments;")
            appt_count_after = cursor.fetchone()[0]
            print(f"Appointments count after: {appt_count_after}")
            assert appt_count_before == appt_count_after, "Record count mismatch during appointment migration!"
        else:
            print("Appointments table already has consultation_fee.")

        # Step 2: Create users table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            salt TEXT NOT NULL,
            role TEXT NOT NULL CHECK(role IN ('Patient', 'Doctor', 'Staff', 'Hospital Administrator')),
            full_name TEXT NOT NULL,
            linked_patient_id INTEGER REFERENCES patients(id) ON DELETE SET NULL,
            linked_doctor_id INTEGER REFERENCES doctors(id) ON DELETE SET NULL,
            is_active INTEGER NOT NULL DEFAULT 1 CHECK(is_active IN (0, 1)),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_role ON users(role);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_patient ON users(linked_patient_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_users_doctor ON users(linked_doctor_id);")

        # Step 3: Create notifications table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS notifications (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
            patient_id INTEGER REFERENCES patients(id) ON DELETE CASCADE,
            appointment_id INTEGER REFERENCES appointments(id) ON DELETE SET NULL,
            title TEXT NOT NULL,
            message TEXT NOT NULL,
            notification_type TEXT NOT NULL DEFAULT 'Booking' CHECK(notification_type IN ('Booking', 'Confirmation', 'Cancellation', 'Reminder', 'Billing', 'System')),
            is_read INTEGER NOT NULL DEFAULT 0 CHECK(is_read IN (0, 1)),
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_user ON notifications(user_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_patient ON notifications(patient_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_notifications_read ON notifications(is_read);")

        # Step 4: Create bills table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS bills (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            bill_number TEXT UNIQUE NOT NULL,
            appointment_id INTEGER UNIQUE NOT NULL REFERENCES appointments(id) ON DELETE RESTRICT,
            patient_id INTEGER NOT NULL REFERENCES patients(id) ON DELETE RESTRICT,
            doctor_id INTEGER NOT NULL REFERENCES doctors(id) ON DELETE RESTRICT,
            consultation_fee REAL NOT NULL DEFAULT 0.0 CHECK(consultation_fee >= 0),
            additional_charges REAL NOT NULL DEFAULT 0.0 CHECK(additional_charges >= 0),
            discount_amount REAL NOT NULL DEFAULT 0.0 CHECK(discount_amount >= 0),
            total_amount REAL NOT NULL CHECK(total_amount >= 0),
            amount_paid REAL NOT NULL DEFAULT 0.0 CHECK(amount_paid >= 0),
            outstanding_balance REAL NOT NULL CHECK(outstanding_balance >= 0),
            payment_status TEXT NOT NULL DEFAULT 'Unpaid' CHECK(payment_status IN ('Unpaid', 'Partially Paid', 'Paid', 'Refunded')),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_appointment ON bills(appointment_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_patient ON bills(patient_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_doctor ON bills(doctor_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_bills_status ON bills(payment_status);")

        # Step 5: Create payments table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            payment_code TEXT UNIQUE NOT NULL,
            bill_id INTEGER NOT NULL REFERENCES bills(id) ON DELETE RESTRICT,
            amount REAL NOT NULL CHECK(amount > 0),
            payment_date TEXT NOT NULL,
            payment_method TEXT NOT NULL CHECK(payment_method IN ('Cash', 'Card', 'UPI', 'Net Banking', 'Insurance')),
            reference_number TEXT,
            recorded_by TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Success' CHECK(status IN ('Success', 'Failed', 'Refunded')),
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_bill ON payments(bill_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_payments_date ON payments(payment_date);")

        # Step 6: Create receipts table
        cursor.execute("""
        CREATE TABLE IF NOT EXISTS receipts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            receipt_number TEXT UNIQUE NOT NULL,
            payment_id INTEGER UNIQUE NOT NULL REFERENCES payments(id) ON DELETE RESTRICT,
            bill_id INTEGER NOT NULL REFERENCES bills(id) ON DELETE RESTRICT,
            receipt_date TEXT NOT NULL,
            issued_by TEXT NOT NULL,
            receipt_details TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_receipts_payment ON receipts(payment_id);")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_receipts_bill ON receipts(bill_id);")

        conn.commit()

        # Step 7: Turn FK back on and verify integrity
        cursor.execute("PRAGMA foreign_keys = ON;")
        conn.commit()

        cursor.execute("PRAGMA foreign_key_check;")
        fk_errors = cursor.fetchall()
        if fk_errors:
            print(f"Foreign key check errors: {fk_errors}")
            conn.rollback()
            return False

        # Step 8: Seed RBAC Default Users
        seed_users = [
            ("admin", "deepak.admin@hospital.demo", "Admin@123", "Hospital Administrator", "Deepak Joshi (Administrator)", None, None),
            ("staff_reception", "reception@hospital.demo", "Staff@123", "Staff", "Pooja Verma (Reception Desk)", None, None),
            ("dr_arun", "rajesh.sharma@hospital.demo", "Doctor@123", "Doctor", "Dr. Rajesh Sharma", None, 1),
            ("patient_aarav", "aarav.verma@example.demo", "Patient@123", "Patient", "Aarav Verma", 1, None),
        ]

        for uname, email, raw_pwd, role, fname, pat_id, doc_id in seed_users:
            cursor.execute("SELECT id FROM users WHERE username = ?;", (uname,))
            row = cursor.fetchone()
            if not row:
                pwd_hash, salt = hash_password(raw_pwd)
                cursor.execute("""
                INSERT INTO users (username, email, password_hash, salt, role, full_name, linked_patient_id, linked_doctor_id, is_active)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1);
                """, (uname, email, pwd_hash, salt, role, fname, pat_id, doc_id))
                print(f"Created user: {uname} ({role})")

        conn.commit()

        # Step 9: Seed Initial Bills for existing appointments (if no bills exist)
        cursor.execute("SELECT COUNT(*) FROM bills;")
        bill_count = cursor.fetchone()[0]
        if bill_count == 0:
            print("Generating initial bills for existing appointments...")
            cursor.execute("""
            SELECT a.id, a.appointment_code, a.patient_id, a.doctor_id, a.consultation_fee, a.status, a.appointment_date,
                   p.first_name AS pat_fname, p.last_name AS pat_lname,
                   d.first_name AS doc_fname, d.last_name AS doc_lname
            FROM appointments a
            JOIN patients p ON a.patient_id = p.id
            JOIN doctors d ON a.doctor_id = d.id
            ORDER BY a.id ASC;
            """)
            appts = cursor.fetchall()
            bill_idx = 1
            pay_idx = 1
            rec_idx = 1

            for appt in appts:
                bill_num = f"BILL-202610-{bill_idx:04d}"
                fee = float(appt["consultation_fee"] or 500.0)
                add_charges = 0.0
                discount = 0.0
                total = fee

                # For completed appointments, mark Paid with Payment & Receipt
                if appt["status"] == "Completed":
                    paid = total
                    bal = 0.0
                    p_status = "Paid"
                    cursor.execute("""
                    INSERT INTO bills (bill_number, appointment_id, patient_id, doctor_id, consultation_fee, additional_charges, discount_amount, total_amount, amount_paid, outstanding_balance, payment_status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Standard consultation fee billed.');
                    """, (bill_num, appt["id"], appt["patient_id"], appt["doctor_id"], fee, add_charges, discount, total, paid, bal, p_status))
                    bill_id = cursor.lastrowid

                    pay_code = f"PAY-202610-{pay_idx:04d}"
                    rec_num = f"REC-202610-{rec_idx:04d}"
                    pay_idx += 1
                    rec_idx += 1

                    cursor.execute("""
                    INSERT INTO payments (payment_code, bill_id, amount, payment_date, payment_method, reference_number, recorded_by, status, notes)
                    VALUES (?, ?, ?, ?, 'UPI', 'UPI-REF-9921', 'Pooja Verma (Reception Desk)', 'Success', 'Full payment received at desk.');
                    """, (pay_code, bill_id, paid, appt["appointment_date"]))
                    pay_id = cursor.lastrowid

                    rec_details = f"Patient: {appt['pat_fname']} {appt['pat_lname']} | Doctor: {appt['doc_fname']} {appt['doc_lname']} | Total: Rs. {total:.2f} | Method: UPI"
                    cursor.execute("""
                    INSERT INTO receipts (receipt_number, payment_id, bill_id, receipt_date, issued_by, receipt_details)
                    VALUES (?, ?, ?, ?, 'Front Desk System', ?);
                    """, (rec_num, pay_id, bill_id, appt["appointment_date"], rec_details))

                elif appt["status"] in ("Confirmed", "Scheduled"):
                    # Partial or unpaid
                    if bill_idx % 2 == 0:
                        paid = fee / 2.0
                        bal = fee - paid
                        p_status = "Partially Paid"
                    else:
                        paid = 0.0
                        bal = fee
                        p_status = "Unpaid"

                    cursor.execute("""
                    INSERT INTO bills (bill_number, appointment_id, patient_id, doctor_id, consultation_fee, additional_charges, discount_amount, total_amount, amount_paid, outstanding_balance, payment_status, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'Consultation booking invoice generated.');
                    """, (bill_num, appt["id"], appt["patient_id"], appt["doctor_id"], fee, add_charges, discount, total, paid, bal, p_status))
                    bill_id = cursor.lastrowid

                    if paid > 0:
                        pay_code = f"PAY-202610-{pay_idx:04d}"
                        rec_num = f"REC-202610-{rec_idx:04d}"
                        pay_idx += 1
                        rec_idx += 1

                        cursor.execute("""
                        INSERT INTO payments (payment_code, bill_id, amount, payment_date, payment_method, reference_number, recorded_by, status, notes)
                        VALUES (?, ?, ?, ?, 'Cash', 'CASH-REC-101', 'Pooja Verma (Reception Desk)', 'Success', 'Advance partial payment received.');
                        """, (pay_code, bill_id, paid, appt["appointment_date"]))
                        pay_id = cursor.lastrowid

                        rec_details = f"Patient: {appt['pat_fname']} {appt['pat_lname']} | Advance Deposit: Rs. {paid:.2f} | Balance Due: Rs. {bal:.2f}"
                        cursor.execute("""
                        INSERT INTO receipts (receipt_number, payment_id, bill_id, receipt_date, issued_by, receipt_details)
                        VALUES (?, ?, ?, ?, 'Front Desk System', ?);
                        """, (rec_num, pay_id, bill_id, appt["appointment_date"], rec_details))

                bill_idx += 1

            conn.commit()
            print(f"Seeded {bill_idx - 1} bills, {pay_idx - 1} payments, and {rec_idx - 1} receipts.")

        # Step 10: Seed Initial Notifications for Patient Aarav Verma (ID 1)
        cursor.execute("SELECT COUNT(*) FROM notifications;")
        notif_count = cursor.fetchone()[0]
        if notif_count == 0:
            cursor.execute("SELECT id FROM users WHERE username = 'patient_aarav';")
            pat_user = cursor.fetchone()
            pat_user_id = pat_user["id"] if pat_user else None

            sample_notifs = [
                (pat_user_id, 1, 1, "Appointment Confirmed", "Your consultation with Dr. Rajesh Sharma is confirmed for 2026-10-05 at 09:00 AM.", "Confirmation", 1),
                (pat_user_id, 1, 1, "Payment Receipt Available", "Payment of Rs. 800.00 for Bill BILL-202610-0001 has been recorded. Receipt is ready.", "Billing", 1),
                (pat_user_id, 1, 26, "Upcoming Appointment Reminder", "Reminder: You have an upcoming appointment with Dr. Vikram Mehta on 2026-10-10 at 09:00 AM.", "Reminder", 0),
                (None, 1, None, "Welcome to Hospital TQM Portal", "Welcome to your patient portal. You can view your appointments, prescriptions, and billing receipts here.", "System", 0),
            ]
            cursor.executemany("""
            INSERT INTO notifications (user_id, patient_id, appointment_id, title, message, notification_type, is_read)
            VALUES (?, ?, ?, ?, ?, ?, ?);
            """, sample_notifs)
            conn.commit()
            print("Seeded initial notifications.")

        print("Expansion migration completed successfully!")
        return True

    except Exception as e:
        print(f"Error during migration: {e}")
        conn.rollback()
        raise e
    finally:
        conn.close()


if __name__ == "__main__":
    run_migration()
