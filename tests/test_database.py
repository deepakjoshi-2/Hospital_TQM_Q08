"""Unit tests for SQLite database connection, schema, constraints, and transactions."""
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from database.connection import (
    connect_database,
    get_db_connection,
    get_db_cursor,
    init_db,
    reset_db,
)


class TestDatabase(unittest.TestCase):
    """Test suite verifying database initialization, integrity constraints, and transactions."""

    def setUp(self):
        """Create a temporary database file for isolated testing."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_hospital.db")
        init_db(self.db_path)

    def tearDown(self):
        """Clean up the temporary directory."""
        self.temp_dir.cleanup()

    def test_schema_creates_all_expected_tables(self):
        """Verify that all core application tables are generated."""
        expected_tables = {
            "user_profile",
            "patients",
            "doctors",
            "appointments",
            "tqm_defect_logs",
            "tqm_fmea_records",
        }
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%';")
            tables = {row["name"] for row in cursor.fetchall()}
            for table in expected_tables:
                self.assertIn(table, tables, f"Expected table '{table}' was not created.")

    def test_foreign_key_enforcement(self):
        """Verify foreign key constraint blocks orphaned appointments."""
        with self.assertRaises(sqlite3.IntegrityError):
            with get_db_cursor(self.db_path) as (conn, cursor):
                cursor.execute(
                    """
                    INSERT INTO appointments (
                        appointment_code, patient_id, doctor_id, appointment_date, time_slot, reason
                    ) VALUES ('APT-9999', 9999, 8888, '2026-10-15', '10:00 AM', 'General Checkup');
                    """
                )

    def test_unique_doctor_slot_collision_index(self):
        """Verify that doctor cannot be double-booked at same date/time unless cancelled."""
        with get_db_cursor(self.db_path) as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO patients (patient_code, first_name, last_name, dob, gender, phone)
                VALUES ('PAT-101', 'Arjun', 'Sharma', '1995-05-12', 'Male', '9876543210');
                """
            )
            patient_id = cursor.lastrowid

            cursor.execute(
                """
                INSERT INTO doctors (doctor_code, first_name, last_name, specialization, phone, email, room_number)
                VALUES ('DOC-201', 'Dr. Priya', 'Nair', 'Cardiology', '9876500001', 'priya.nair@hospital.org', '101');
                """
            )
            doctor_id = cursor.lastrowid

            # First booking: Success
            cursor.execute(
                """
                INSERT INTO appointments (
                    appointment_code, patient_id, doctor_id, appointment_date, time_slot, reason, status
                ) VALUES ('APT-301', ?, ?, '2026-10-15', '10:00 AM', 'ECG Follow-up', 'Scheduled');
                """,
                (patient_id, doctor_id),
            )

        # Attempt duplicate active booking: Should fail with IntegrityError
        with self.assertRaises(sqlite3.IntegrityError):
            with get_db_cursor(self.db_path) as (conn, cursor):
                cursor.execute(
                    """
                    INSERT INTO appointments (
                        appointment_code, patient_id, doctor_id, appointment_date, time_slot, reason, status
                    ) VALUES ('APT-302', ?, ?, '2026-10-15', '10:00 AM', 'Chest Pain', 'Scheduled');
                    """,
                    (patient_id, doctor_id),
                )

        # However, if previous booking is Cancelled, slot can be reused
        with get_db_cursor(self.db_path) as (conn, cursor):
            cursor.execute("UPDATE appointments SET status = 'Cancelled' WHERE appointment_code = 'APT-301';")
            # Now booking for same slot succeeds
            cursor.execute(
                """
                INSERT INTO appointments (
                    appointment_code, patient_id, doctor_id, appointment_date, time_slot, reason, status
                ) VALUES ('APT-303', ?, ?, '2026-10-15', '10:00 AM', 'Chest Pain', 'Scheduled');
                """,
                (patient_id, doctor_id),
            )
            self.assertIsNotNone(cursor.lastrowid)

    def test_transaction_rollback_on_failure(self):
        """Verify that transactional cursor automatically rolls back on exception."""
        try:
            with get_db_cursor(self.db_path) as (conn, cursor):
                cursor.execute(
                    """
                    INSERT INTO patients (patient_code, first_name, last_name, dob, gender, phone)
                    VALUES ('PAT-102', 'Rohan', 'Verma', '1998-02-14', 'Male', '9812345678');
                    """
                )
                # Intentionally trigger an error
                raise RuntimeError("Simulated crash during transaction")
        except RuntimeError:
            pass

        # Check that patient was NOT committed
        with get_db_connection(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM patients WHERE patient_code = 'PAT-102';")
            row = cursor.fetchone()
            self.assertIsNone(row, "Uncommitted data leaked despite transaction failure!")


if __name__ == "__main__":
    unittest.main()
