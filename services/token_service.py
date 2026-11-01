"""Live Token Tracking and Queue Management Service for MedCare Hospital Management System (Q08).

Provides real-time outpatient queue management:
- Sequential, conflict-free token generation per doctor and date (e.g., TK-01, TK-02).
- Queue position tracking (e.g., "Now Serving", "2 ahead of you").
- Dynamic estimated wait time calculation based on actual workload and priority.
- Clinical workflow transitions: Waiting -> Now Serving -> Completed / No-Show / Cancelled.
- Doctor consultation queue controls (Start Consultation / Complete Consultation).
- Auto-refresh support for live OPD boards and patient remote tracking.
"""
from datetime import datetime, date
from typing import Any, Dict, List, Optional, Tuple

from config.constants import (
    DOCTOR_AVAILABLE,
    DOCTOR_IN_CONSULTATION,
    NOTIF_CONFIRMATION,
    NOTIF_SYSTEM,
    STATUS_CANCELLED,
    STATUS_COMPLETED,
    STATUS_CONFIRMED,
    STATUS_NO_SHOW,
    STATUS_PENDING,
    STATUS_SCHEDULED,
)
from database.connection import get_db_connection, get_db_cursor
from services.notification_service import create_notification


class ConsultationResult(tuple):
    """Result tuple (bool, str) that also supports dictionary-style .get() access."""

    def __new__(cls, success: bool, message: str):
        return super().__new__(cls, (success, message))

    @property
    def success(self) -> bool:
        return self[0]

    @property
    def message(self) -> str:
        return self[1]

    def get(self, key: str, default: Any = None) -> Any:
        if key == "success":
            return self[0]
        if key in ("message", "msg"):
            return self[1]
        if key == "error":
            return self[1] if not self[0] else None
        return default


def format_doctor_name(first_name: str, last_name: str) -> str:
    """Format doctor name cleanly without duplicate 'Dr. Dr.' prefix."""
    fn = (first_name or "").strip()
    ln = (last_name or "").strip()
    if fn.lower().startswith("dr.") or fn.lower().startswith("dr "):
        return f"{fn} {ln}".strip()
    return f"Dr. {fn} {ln}".strip()


def parse_time_slot(slot: Optional[str]):
    """Parse 12-hour time slot string (e.g. '09:30 AM') into sortable time object."""
    if not slot:
        return datetime.min.time()
    try:
        return datetime.strptime(slot.strip(), "%I:%M %p").time()
    except Exception:
        return datetime.min.time()


# Standard consultation duration estimates in minutes
AVG_CONSULTATION_MINS_NORMAL = 15
AVG_CONSULTATION_MINS_URGENT = 25
AVG_CONSULTATION_MINS_FOLLOWUP = 10


def generate_next_token(doctor_id: int, appointment_date: str) -> str:
    """Generate the next conflict-free sequential token for a specific doctor on a given date.
    
    Format: TK-01, TK-02, etc. (resets sequentially per doctor per day).
    """
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT token_number FROM appointments
                WHERE doctor_id = ? AND appointment_date = ? AND token_number IS NOT NULL AND token_number != ''
                ORDER BY id DESC;
                """,
                (doctor_id, appointment_date),
            )
            rows = cursor.fetchall()
            max_num = 0
            for r in rows:
                tok = r["token_number"]
                if tok and tok.startswith("TK-"):
                    num_part = tok.replace("TK-", "")
                    if num_part.isdigit():
                        max_num = max(max_num, int(num_part))
            return f"TK-{max_num + 1:02d}"
    except Exception as e:
        print(f"Error generating token: {e}")
        return "TK-01"


def get_queue_status_for_appointment(appointment_id: int) -> Optional[Dict[str, Any]]:
    """Retrieve full live queue metrics for a specific patient appointment."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT a.*,
                       p.first_name AS patient_first_name, p.last_name AS patient_last_name, p.patient_code,
                       d.first_name AS doctor_first_name, d.last_name AS doctor_last_name, d.specialization,
                       d.room_number, d.status AS doctor_status
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                JOIN doctors d ON a.doctor_id = d.id
                WHERE a.id = ?;
                """,
                (appointment_id,),
            )
            row = cursor.fetchone()
            if not row:
                return None

            appt = dict(row)
            doc_id = appt["doctor_id"]
            appt_date = appt["appointment_date"]
            today_str = date.today().isoformat()
            is_future = appt_date > today_str
            my_token = appt.get("token_number") or "TK-01"
            my_q_status = appt.get("queue_status") or "Waiting"

            # Fetch all active appointments for this doctor on this day
            q_cursor = conn.execute(
                """
                SELECT id, appointment_code, token_number, queue_status, status, priority, time_slot
                FROM appointments
                WHERE doctor_id = ? AND appointment_date = ? AND status != 'Cancelled' AND status != 'No-Show'
                ORDER BY id ASC;
                """,
                (doc_id, appt_date),
            )
            all_appts = [dict(r) for r in q_cursor.fetchall()]
            all_appts.sort(key=lambda x: parse_time_slot(x.get("time_slot", "")))

            # Determine currently serving token
            now_serving = None
            if not is_future:
                for a in all_appts:
                    if a.get("queue_status") == "Now Serving":
                        now_serving = a.get("token_number")
                        break

                # If no one is actively marked 'Now Serving' on today's clinic, earliest 'Waiting' token is next
                if not now_serving:
                    for a in all_appts:
                        if a.get("queue_status") == "Waiting" and a.get("status") in (STATUS_CONFIRMED, STATUS_SCHEDULED, STATUS_PENDING):
                            now_serving = a.get("token_number")
                            break

            # Calculate queue position (how many patients ahead who are either Now Serving or Waiting)
            position = 0
            wait_time = 0
            for a in all_appts:
                if a["id"] == appointment_id:
                    break
                if a.get("queue_status") in ("Waiting", "Now Serving") and a.get("status") in (STATUS_CONFIRMED, STATUS_SCHEDULED, STATUS_PENDING):
                    position += 1
                    pri = a.get("priority", "Normal")
                    if pri == "Urgent":
                        wait_time += AVG_CONSULTATION_MINS_URGENT
                    elif pri == "Follow-up":
                        wait_time += AVG_CONSULTATION_MINS_FOLLOWUP
                    else:
                        wait_time += AVG_CONSULTATION_MINS_NORMAL

            # Completed count
            completed_count = sum(1 for a in all_appts if a.get("queue_status") == "Completed" or a.get("status") == STATUS_COMPLETED)
            total_count = len(all_appts)

            # Human-readable position and wait time
            if is_future:
                # Future date: do not imply patient is waiting in the clinic lobby right now
                if position == 0:
                    position_text = f"Scheduled on {appt_date} at {appt['time_slot']} • 1st in doctor queue."
                else:
                    position_text = f"Scheduled on {appt_date} at {appt['time_slot']} • {position} patient(s) ahead."
                wait_time_text = f"Scheduled ({appt_date})"
            elif my_q_status == "Now Serving":
                position_text = "It's your turn! Please proceed to the consultation room."
                wait_time_text = "0 mins (Serving Now)"
            elif my_q_status == "Completed":
                position_text = "Consultation completed."
                wait_time_text = "Completed"
            elif my_q_status in ("Cancelled", "No-Show"):
                position_text = f"Appointment {my_q_status}."
                wait_time_text = "--"
            else:
                if position == 0:
                    position_text = "You are next in line! Please wait near the room."
                    wait_time_text = "~5 mins"
                elif position == 1:
                    position_text = "1 patient ahead of you in queue."
                    wait_time_text = f"~{wait_time} mins"
                else:
                    position_text = f"{position} patients ahead of you in queue."
                    wait_time_text = f"~{wait_time} mins"

            return {
                "appointment_id": appt["id"],
                "appointment_code": appt["appointment_code"],
                "appointment_status": appt["status"],
                "status": appt["status"],
                "token_number": my_token,
                "queue_status": my_q_status,
                "patient_name": f"{appt['patient_first_name']} {appt['patient_last_name']}",
                "patient_code": appt["patient_code"],
                "doctor_name": format_doctor_name(appt["doctor_first_name"], appt["doctor_last_name"]),
                "doctor_id": doc_id,
                "specialization": appt["specialization"],
                "room_number": appt["room_number"] or "OPD-101",
                "appointment_date": appt_date,
                "time_slot": appt["time_slot"],
                "currently_serving_token": now_serving,
                "queue_position": position,
                "queue_position_text": position_text,
                "estimated_wait_minutes": wait_time,
                "estimated_wait_text": wait_time_text,
                "total_in_queue": total_count,
                "completed_count": completed_count,
                "doctor_status": appt["doctor_status"] or DOCTOR_AVAILABLE,
                "is_future_appointment": is_future,
            }
    except Exception as e:
        print(f"Error fetching queue status: {e}")
        return None


def get_doctor_live_queue(doctor_id: int, appointment_date: Optional[str] = None) -> Dict[str, Any]:
    """Retrieve full OPD waiting queue for a specific doctor on a specific date."""
    today_str = date.today().isoformat()

    try:
        with get_db_connection() as conn:
            # Doctor details
            doc = conn.execute("SELECT * FROM doctors WHERE id = ?;", (doctor_id,)).fetchone()
            if not doc:
                return {"error": "Doctor not found", "queue": [], "waiting_queue": [], "completed_queue": []}

            # If appointment_date is omitted, intelligently pick the most relevant date:
            # 1. Today if appointments exist for today.
            # 2. Next earliest upcoming date with appointments.
            # 3. Default to today.
            if not appointment_date:
                has_today = conn.execute(
                    "SELECT 1 FROM appointments WHERE doctor_id = ? AND appointment_date = ? AND status != 'Cancelled' LIMIT 1;",
                    (doctor_id, today_str),
                ).fetchone()
                if has_today:
                    appointment_date = today_str
                else:
                    next_row = conn.execute(
                        """
                        SELECT appointment_date FROM appointments
                        WHERE doctor_id = ? AND appointment_date >= ? AND status != 'Cancelled'
                        ORDER BY appointment_date ASC LIMIT 1;
                        """,
                        (doctor_id, today_str),
                    ).fetchone()
                    if next_row:
                        appointment_date = next_row["appointment_date"]
                    else:
                        appointment_date = today_str

            is_future_date = appointment_date > today_str

            cursor = conn.execute(
                """
                SELECT a.id, a.appointment_code, a.token_number, a.queue_status, a.status,
                       a.time_slot, a.priority, a.reason, a.appointment_date,
                       p.first_name || ' ' || p.last_name AS patient_name, p.patient_code, p.phone AS patient_phone
                FROM appointments a
                JOIN patients p ON a.patient_id = p.id
                WHERE a.doctor_id = ? AND a.appointment_date = ? AND a.status != 'Cancelled' AND a.status != 'No-Show'
                ORDER BY a.id ASC;
                """,
                (doctor_id, appointment_date),
            )
            rows = [dict(r) for r in cursor.fetchall()]
            rows.sort(key=lambda x: parse_time_slot(x.get("time_slot", "")))

            now_serving = None
            waiting = []
            completed = []

            for r in rows:
                q_stat = r.get("queue_status") or "Waiting"
                stat = r.get("status")
                if q_stat == "Now Serving":
                    now_serving = r
                elif q_stat == "Completed" or stat == STATUS_COMPLETED:
                    completed.append(r)
                elif q_stat == "Waiting" and stat in (STATUS_CONFIRMED, STATUS_SCHEDULED, STATUS_PENDING):
                    waiting.append(r)
                else:
                    waiting.append(r)

            # Calculate queue positions and wait times for waiting rows
            for idx, w_item in enumerate(waiting):
                w_item["queue_position"] = idx + 1
                if is_future_date:
                    w_item["estimated_wait_minutes"] = idx * 15
                    w_item["estimated_wait_text"] = f"Scheduled ({w_item.get('time_slot', '')})"
                else:
                    w_item["estimated_wait_minutes"] = idx * 15 + (10 if now_serving else 0)
                    w_item["estimated_wait_text"] = f"~{w_item['estimated_wait_minutes']} mins"

            # Full queue list containing now_serving first, then waiting, then completed
            full_queue = []
            if now_serving:
                full_queue.append(now_serving)
            full_queue.extend(waiting)
            full_queue.extend(completed)

            doc_name = format_doctor_name(doc["first_name"], doc["last_name"])

            return {
                "doctor_id": doc["id"],
                "doctor_name": doc_name,
                "doctor": {
                    "id": doc["id"],
                    "name": doc_name,
                    "specialization": doc["specialization"],
                    "room_number": doc["room_number"] or "OPD-101",
                    "status": doc["status"] or DOCTOR_AVAILABLE,
                },
                "specialization": doc["specialization"],
                "room_number": doc["room_number"] or "OPD-101",
                "doctor_status": doc["status"] or DOCTOR_AVAILABLE,
                "appointment_date": appointment_date,
                "is_future_date": is_future_date,
                "is_today": appointment_date == today_str,
                "now_serving": now_serving,
                "waiting_queue": waiting,
                "completed_queue": completed,
                "queue": full_queue,
                "total_count": len(rows),
                "waiting_count": len(waiting),
                "completed_count": len(completed),
            }
    except Exception as e:
        print(f"Error getting doctor queue: {e}")
        return {"error": str(e), "queue": [], "waiting_queue": [], "completed_queue": []}


def start_consultation(appointment_id: int, user: Optional[Dict] = None) -> Tuple[bool, str]:
    """Mark appointment as 'Now Serving' and set doctor status to 'In Consultation'."""
    try:
        with get_db_connection() as conn:
            row = conn.execute("SELECT * FROM appointments WHERE id = ?;", (appointment_id,)).fetchone()
            if not row:
                return False, f"Appointment {appointment_id} not found."

            doc_id = row["doctor_id"]
            appt_date = row["appointment_date"]
            token = row["token_number"] or "Token"

            with get_db_cursor() as (conn2, cursor):
                # 1. Any existing 'Now Serving' appointment for this doctor on this date is completed
                cursor.execute(
                    """
                    UPDATE appointments
                    SET queue_status = 'Completed', status = 'Completed', updated_at = CURRENT_TIMESTAMP
                    WHERE doctor_id = ? AND appointment_date = ? AND queue_status = 'Now Serving' AND id != ?;
                    """,
                    (doc_id, appt_date, appointment_id),
                )

                # 2. Set this appointment to 'Now Serving'
                cursor.execute(
                    """
                    UPDATE appointments
                    SET queue_status = 'Now Serving', status = 'Confirmed', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?;
                    """,
                    (appointment_id,),
                )

                # 3. Update doctor's status
                cursor.execute(
                    "UPDATE doctors SET status = ? WHERE id = ?;",
                    (DOCTOR_IN_CONSULTATION, doc_id),
                )

            # 4. Notify patient
            create_notification(
                patient_id=row["patient_id"],
                title="Token Now Serving!",
                message=f"Your token {token} ({row['appointment_code']}) is now being called! Please proceed to the doctor's room.",
                notification_type=NOTIF_SYSTEM,
                appointment_id=appointment_id,
            )

            return ConsultationResult(True, f"Token {token} is now serving.")
    except Exception as e:
        return ConsultationResult(False, f"Error starting consultation: {e}")


def complete_consultation(appointment_id: int, user: Optional[Dict] = None, notes: Optional[str] = None) -> ConsultationResult:
    """Mark consultation as Completed, free the doctor, and advance the queue."""
    try:
        with get_db_connection() as conn:
            row = conn.execute("SELECT * FROM appointments WHERE id = ?;", (appointment_id,)).fetchone()
            if not row:
                return ConsultationResult(False, f"Appointment {appointment_id} not found.")

            doc_id = row["doctor_id"]
            token = row["token_number"] or "Token"

            with get_db_cursor() as (conn2, cursor):
                cursor.execute(
                    """
                    UPDATE appointments
                    SET queue_status = 'Completed', status = 'Completed', updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?;
                    """,
                    (appointment_id,),
                )

                # If doctor has no other active "Now Serving" appointments, mark as Available
                active_count = cursor.execute(
                    "SELECT COUNT(*) FROM appointments WHERE doctor_id = ? AND queue_status = 'Now Serving';",
                    (doc_id,),
                ).fetchone()[0]

                if active_count == 0:
                    cursor.execute(
                        "UPDATE doctors SET status = ? WHERE id = ?;",
                        (DOCTOR_AVAILABLE, doc_id),
                    )

            # Notify patient
            create_notification(
                patient_id=row["patient_id"],
                title="Consultation Completed",
                message=f"Your consultation for token {token} ({row['appointment_code']}) is marked as completed.",
                notification_type=NOTIF_CONFIRMATION,
                appointment_id=appointment_id,
            )

            return ConsultationResult(True, f"Consultation for token {token} marked completed.")
    except Exception as e:
        return ConsultationResult(False, f"Error completing consultation: {e}")


def get_patient_active_tokens(patient_id: int) -> List[Dict[str, Any]]:
    """Retrieve all upcoming or waiting tokens for a specific patient."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute(
                """
                SELECT id FROM appointments
                WHERE patient_id = ? AND status IN ('Confirmed', 'Scheduled', 'Pending') AND queue_status IN ('Waiting', 'Now Serving')
                ORDER BY appointment_date ASC, id ASC;
                """,
                (patient_id,),
            )
            appts = [dict(r) for r in cursor.fetchall()]
            results = []
            for a in appts:
                status_info = get_queue_status_for_appointment(a["id"])
                if status_info:
                    results.append(status_info)
            return results
    except Exception as e:
        print(f"Error fetching patient tokens: {e}")
        return []
