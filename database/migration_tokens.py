"""Migration script adding token_number and queue_status to appointments table safely."""
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.connection import get_db_connection, get_db_cursor


def run_token_migration(db_path: str = None) -> None:
    """Safely apply schema additions and backfill tokens for existing appointment rows."""
    with get_db_cursor(db_path) as (conn, cursor):
        cursor.execute("PRAGMA table_info(appointments);")
        cols = [r["name"] for r in cursor.fetchall()]
        if "token_number" not in cols:
            cursor.execute("ALTER TABLE appointments ADD COLUMN token_number TEXT;")
            print("Added token_number column to appointments.")
        if "queue_status" not in cols:
            cursor.execute("ALTER TABLE appointments ADD COLUMN queue_status TEXT DEFAULT 'Waiting';")
            print("Added queue_status column to appointments.")

    with get_db_connection(db_path) as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT doctor_id, appointment_date FROM appointments ORDER BY doctor_id, appointment_date;")
        groups = cursor.fetchall()

    with get_db_cursor(db_path) as (conn2, c2):
        for g in groups:
            doc_id = g["doctor_id"]
            a_date = g["appointment_date"]
            cur = conn2.cursor()
            cur.execute(
                "SELECT id, status, time_slot FROM appointments WHERE doctor_id = ? AND appointment_date = ? ORDER BY time_slot, id;",
                (doc_id, a_date)
            )
            appts = cur.fetchall()
            for idx, appt in enumerate(appts, 1):
                tok = f"TK-{idx:02d}"
                q_stat = "Completed" if appt["status"] == "Completed" else ("Cancelled" if appt["status"] == "Cancelled" else "Waiting")
                c2.execute(
                    "UPDATE appointments SET token_number = ?, queue_status = ? WHERE id = ? AND (token_number IS NULL OR token_number = '');",
                    (tok, q_stat, appt["id"])
                )

    print("Tokens migration completed successfully.")


if __name__ == "__main__":
    run_token_migration()
