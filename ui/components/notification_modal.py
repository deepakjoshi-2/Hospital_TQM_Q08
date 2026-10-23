"""In-app Patient and User Notification Center modal dialog.
Displays clinical alerts, booking confirmations, payment receipts, and cancellations.
"""
from typing import Callable, Optional
import customtkinter as ctk

from services.notification_service import (
    get_all_notifications,
    get_notifications_for_patient,
    get_notifications_for_user,
    mark_all_notifications_as_read,
    mark_notification_as_read,
)


class NotificationCenterModal(ctk.CTkToplevel):
    """Interactive modal showing recent in-app notifications and alerts."""

    def __init__(
        self,
        master,
        user_id: Optional[int] = None,
        patient_id: Optional[int] = None,
        on_update: Optional[Callable[[], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.user_id = user_id
        self.patient_id = patient_id
        self.on_update = on_update

        self.title("In-App Notification Center — Hospital TQM")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._apply_responsive_geometry(master)
        self._build_ui()
        self._load_notifications()

        self.bind("<Escape>", lambda event: self.destroy())
        self.lift()
        self.focus_force()

    def _apply_responsive_geometry(self, master) -> None:
        """Center modal adaptively."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        scaling = self._get_window_scaling()

        target_w = min(560, int((sw - 40) / scaling))
        target_h = min(500, int((sh - 80) / scaling))

        phys_w = int(target_w * scaling)
        phys_h = int(target_h * scaling)
        pos_x = max(0, (sw - phys_w) // 2)
        pos_y = max(10, (sh - phys_h) // 2 - 20)

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")

    def _build_ui(self) -> None:
        """Construct notification center layout."""
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=20, pady=16)

        # Header
        hdr = ctk.CTkFrame(pad, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 10))

        title_box = ctk.CTkFrame(hdr, fg_color="transparent")
        title_box.pack(side="left")

        ctk.CTkLabel(
            title_box,
            text="🔔 Notifications & Clinical Alerts",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#0284C7", "#06B6D4"),
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            title_box,
            text="Real-time appointment confirmations, reminders, and payment receipts.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        ).pack(fill="x")

        # Mark all read button
        mark_all_btn = ctk.CTkButton(
            hdr,
            text="✓ Mark All Read",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#F1F5F9", "#1E2D4A"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#E2E8F0", "#2B3E63"),
            border_width=1,
            border_color=("#CBD5E1", "#33456B"),
            height=30,
            command=self._mark_all_read,
        )
        mark_all_btn.pack(side="right")

        # Scrollable Notifications Container
        self.scroll_list = ctk.CTkScrollableFrame(
            pad,
            fg_color="transparent",
            corner_radius=8,
        )
        self.scroll_list.pack(fill="both", expand=True, pady=(0, 12))

        # Footer
        footer = ctk.CTkFrame(pad, fg_color="transparent")
        footer.pack(fill="x", side="bottom")

        close_btn = ctk.CTkButton(
            footer,
            text="Close",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            width=80,
            height=32,
            command=self.destroy,
        )
        close_btn.pack(side="right")

    def _load_notifications(self) -> None:
        """Fetch and render notification cards."""
        for child in self.scroll_list.winfo_children():
            child.destroy()

        if self.patient_id:
            notifs = get_notifications_for_patient(self.patient_id)
        elif self.user_id:
            notifs = get_notifications_for_user(self.user_id)
        else:
            notifs = get_all_notifications(limit=40)

        if not notifs:
            empty_lbl = ctk.CTkLabel(
                self.scroll_list,
                text="No notifications found.",
                font=ctk.CTkFont(size=12),
                text_color=("#64748B", "#94A3B8"),
                pady=40,
            )
            empty_lbl.pack()
            return

        type_icons = {
            "Booking": "📅",
            "Confirmation": "✅",
            "Cancellation": "❌",
            "Reminder": "⏰",
            "Billing": "💳",
            "System": "ℹ️",
        }

        for n in notifs:
            is_unread = n.get("is_read") == 0
            border_c = ("#0284C7", "#06B6D4") if is_unread else ("#E2E8F0", "#1E2D4A")
            bg_c = ("#F0F9FF", "#0E1A33") if is_unread else ("#FFFFFF", "#0F172A")

            card = ctk.CTkFrame(
                self.scroll_list,
                fg_color=bg_c,
                border_width=1,
                border_color=border_c,
                corner_radius=8,
            )
            card.pack(fill="x", pady=4, padx=2)

            top_row = ctk.CTkFrame(card, fg_color="transparent")
            top_row.pack(fill="x", padx=12, pady=(8, 2))

            icon = type_icons.get(n.get("notification_type"), "📢")
            unread_tag = " ● UNREAD" if is_unread else ""
            t_lbl = ctk.CTkLabel(
                top_row,
                text=f"{icon} {n['title']}{unread_tag}",
                font=ctk.CTkFont(size=12, weight="bold"),
                text_color=("#0284C7", "#38BDF8") if is_unread else ("#0F172A", "#F8FAFC"),
                anchor="w",
            )
            t_lbl.pack(side="left")

            dt_lbl = ctk.CTkLabel(
                top_row,
                text=str(n.get("created_at", ""))[:16],
                font=ctk.CTkFont(size=10),
                text_color=("#64748B", "#94A3B8"),
            )
            dt_lbl.pack(side="right")

            msg_lbl = ctk.CTkLabel(
                card,
                text=n["message"],
                font=ctk.CTkFont(size=11),
                text_color=("#334155", "#CBD5E1"),
                wraplength=480,
                justify="left",
                anchor="w",
            )
            msg_lbl.pack(fill="x", padx=12, pady=(0, 6))

            if is_unread:
                bot_row = ctk.CTkFrame(card, fg_color="transparent")
                bot_row.pack(fill="x", padx=12, pady=(0, 6))
                read_btn = ctk.CTkButton(
                    bot_row,
                    text="Mark Read",
                    font=ctk.CTkFont(size=10),
                    fg_color=("#E0F2FE", "#1E293B"),
                    text_color=("#0284C7", "#38BDF8"),
                    hover_color=("#BAE6FD", "#334155"),
                    height=22,
                    width=75,
                    command=lambda nid=n["id"]: self._mark_read(nid),
                )
                read_btn.pack(side="right")

    def _mark_read(self, notif_id: int) -> None:
        """Mark single notification as read."""
        mark_notification_as_read(notif_id)
        self._load_notifications()
        if self.on_update:
            self.on_update()

    def _mark_all_read(self) -> None:
        """Mark all visible notifications as read."""
        mark_all_notifications_as_read(user_id=self.user_id, patient_id=self.patient_id)
        self._load_notifications()
        if self.on_update:
            self.on_update()
