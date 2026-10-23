"""Patient notification service for Hospital TQM Q08 system.
Manages in-app notifications for appointment confirmations, status transitions,
reminders, cancellations, and billing alerts.
"""
from typing import Dict, List, Optional, Tuple

from config.constants import NOTIF_BOOKING, NOTIF_SYSTEM, NOTIFICATION_TYPES
from database.connection import get_db_connection, get_db_cursor


def create_notification(
    patient_id: Optional[int],
    title: str,
    message: str,
    notification_type: str = NOTIF_BOOKING,
    appointment_id: Optional[int] = None,
    user_id: Optional[int] = None,
) -> Tuple[bool, str, Optional[int]]:
    """Create an in-app notification record.
    
    If user_id is not provided, attempts to find the user linked to patient_id.
    Returns:
        (success, message, new_notification_id)
    """
    clean_title = str(title or "").strip()
    clean_msg = str(message or "").strip()
    clean_type = notification_type if notification_type in NOTIFICATION_TYPES else NOTIF_SYSTEM

    if not clean_title or not clean_msg:
        return False, "Title and message are required for notification.", None

    target_user_id = user_id
    try:
        with get_db_connection() as conn:
            # If user_id not provided but patient_id exists, look up linked user
            if target_user_id is None and patient_id:
                row = conn.execute(
                    "SELECT id FROM users WHERE linked_patient_id = ? LIMIT 1;", (patient_id,)
                ).fetchone()
                if row:
                    target_user_id = row["id"]

        with get_db_cursor() as (conn, cursor):
            cursor.execute("""
                INSERT INTO notifications (
                    user_id, patient_id, appointment_id, title, message, notification_type, is_read
                ) VALUES (?, ?, ?, ?, ?, ?, 0);
            """, (
                target_user_id,
                patient_id,
                appointment_id,
                clean_title,
                clean_msg,
                clean_type,
            ))
            new_id = cursor.lastrowid
            return True, "Notification dispatched successfully.", new_id

    except Exception as e:
        return False, f"Failed to record notification: {e}", None


def get_notifications_for_patient(patient_id: int, unread_only: bool = False) -> List[Dict]:
    """Retrieve all notifications for a specific patient ID."""
    try:
        with get_db_connection() as conn:
            query = "SELECT * FROM notifications WHERE patient_id = ?"
            params = [patient_id]
            if unread_only:
                query += " AND is_read = 0"
            query += " ORDER BY created_at DESC, id DESC;"
            cursor = conn.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching notifications for patient {patient_id}: {e}")
        return []


def get_notifications_for_user(user_id: int, unread_only: bool = False) -> List[Dict]:
    """Retrieve notifications intended for a specific user ID or their linked patient."""
    try:
        with get_db_connection() as conn:
            # Check if this user is linked to a patient
            user_row = conn.execute(
                "SELECT linked_patient_id FROM users WHERE id = ?;", (user_id,)
            ).fetchone()
            linked_patient_id = user_row["linked_patient_id"] if user_row else None

            if linked_patient_id:
                query = "SELECT * FROM notifications WHERE (user_id = ? OR patient_id = ?)"
                params = [user_id, linked_patient_id]
            else:
                query = "SELECT * FROM notifications WHERE user_id = ?"
                params = [user_id]

            if unread_only:
                query += " AND is_read = 0"
            query += " ORDER BY created_at DESC, id DESC;"

            cursor = conn.execute(query, tuple(params))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching notifications for user {user_id}: {e}")
        return []


def get_all_notifications(limit: int = 100) -> List[Dict]:
    """Fetch recent system-wide notifications (for administrative/staff overview)."""
    try:
        with get_db_connection() as conn:
            cursor = conn.execute("""
                SELECT n.*, p.first_name AS pat_fname, p.last_name AS pat_lname, p.patient_code,
                       u.username
                FROM notifications n
                LEFT JOIN patients p ON n.patient_id = p.id
                LEFT JOIN users u ON n.user_id = u.id
                ORDER BY n.created_at DESC, n.id DESC
                LIMIT ?;
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching all notifications: {e}")
        return []


def mark_notification_as_read(notification_id: int) -> bool:
    """Mark a single notification as read."""
    try:
        with get_db_cursor() as (conn, cursor):
            cursor.execute("UPDATE notifications SET is_read = 1 WHERE id = ?;", (notification_id,))
            return True
    except Exception as e:
        print(f"Error marking notification {notification_id} as read: {e}")
        return False


def mark_all_notifications_as_read(user_id: Optional[int] = None, patient_id: Optional[int] = None) -> int:
    """Mark all notifications matching user or patient as read."""
    try:
        with get_db_cursor() as (conn, cursor):
            if user_id and patient_id:
                cursor.execute(
                    "UPDATE notifications SET is_read = 1 WHERE is_read = 0 AND (user_id = ? OR patient_id = ?);",
                    (user_id, patient_id),
                )
            elif user_id:
                cursor.execute(
                    "UPDATE notifications SET is_read = 1 WHERE is_read = 0 AND user_id = ?;",
                    (user_id,),
                )
            elif patient_id:
                cursor.execute(
                    "UPDATE notifications SET is_read = 1 WHERE is_read = 0 AND patient_id = ?;",
                    (patient_id,),
                )
            else:
                cursor.execute("UPDATE notifications SET is_read = 1 WHERE is_read = 0;")
            return cursor.rowcount
    except Exception as e:
        print(f"Error marking all notifications as read: {e}")
        return 0


def get_unread_notification_count(user_id: Optional[int] = None, patient_id: Optional[int] = None) -> int:
    """Count unread notifications for a user or patient."""
    try:
        with get_db_connection() as conn:
            if user_id and patient_id:
                cursor = conn.execute(
                    "SELECT COUNT(*) as c FROM notifications WHERE is_read = 0 AND (user_id = ? OR patient_id = ?);",
                    (user_id, patient_id),
                )
            elif user_id:
                cursor = conn.execute(
                    "SELECT COUNT(*) as c FROM notifications WHERE is_read = 0 AND user_id = ?;",
                    (user_id,),
                )
            elif patient_id:
                cursor = conn.execute(
                    "SELECT COUNT(*) as c FROM notifications WHERE is_read = 0 AND patient_id = ?;",
                    (patient_id,),
                )
            else:
                cursor = conn.execute("SELECT COUNT(*) as c FROM notifications WHERE is_read = 0;")
            row = cursor.fetchone()
            return row["c"] if row else 0
    except Exception as e:
        print(f"Error counting unread notifications: {e}")
        return 0
