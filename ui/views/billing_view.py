"""Billing, Invoices, and Payments View for Hospital Management System — Q08.
Provides KPI cards, payment status filtering, invoice table, role-scoped controls,
Patient Online Pay Now checkout, and audit transaction logs.
"""
from typing import Dict, List, Optional
import customtkinter as ctk

from services.auth_service import get_current_user, has_permission
from services.billing_service import (
    get_billing_summary_statistics,
    get_bills,
    get_payments_for_bill,
    sync_unbilled_appointments,
)
from ui.components.billing_modals import (
    PatientPaymentModal,
    PaymentAuditLogModal,
    ReceiptViewModal,
    RecordPaymentModal,
)
from ui.components.scroll_manager import ScrollManager


class BillingView(ctk.CTkFrame):
    """Clinical Analytics Billing, Patient Online Checkout, and Invoicing View."""

    def __init__(self, master, current_user=None, **kwargs):
        super().__init__(master, fg_color="transparent", **kwargs)
        self.current_user = current_user or get_current_user()
        self.user_role = self.current_user.get("role", "Administrator") if self.current_user else "Administrator"

        self._build_header()
        self._build_kpi_cards()
        self._build_filter_bar()
        self._build_table_container()

        self.refresh_data()

    def _build_header(self) -> None:
        """Header with module title, transaction audit access, and refresh button."""
        hdr = ctk.CTkFrame(self, fg_color="transparent")
        hdr.pack(fill="x", padx=24, pady=(20, 10))

        title_box = ctk.CTkFrame(hdr, fg_color="transparent")
        title_box.pack(side="left")

        self.t_lbl = ctk.CTkLabel(
            title_box,
            text="💳 Consultation Billing & Receipt Management",
            font=ctk.CTkFont(size=20, weight="bold"),
            text_color=("#0F172A", "#F8FAFC"),
            anchor="w",
        )
        self.t_lbl.pack(fill="x")

        self.sub_lbl = ctk.CTkLabel(
            title_box,
            text="Real-time outpatient consultation invoices, payment processing, and official receipts.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        )
        self.sub_lbl.pack(fill="x")

        # Right actions container
        self.r_box = ctk.CTkFrame(hdr, fg_color="transparent")
        self.r_box.pack(side="right")

        self.audit_btn = ctk.CTkButton(
            self.r_box,
            text="📋 All Transactions",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#F1F5F9", "#1E2D4A"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#E2E8F0", "#2B3E63"),
            border_width=1,
            border_color=("#CBD5E1", "#33456B"),
            height=34,
            command=self._open_audit_modal,
        )

        refresh_btn = ctk.CTkButton(
            self.r_box,
            text="🔄 Refresh",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#F1F5F9", "#1E2D4A"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#E2E8F0", "#2B3E63"),
            border_width=1,
            border_color=("#CBD5E1", "#33456B"),
            height=34,
            command=self.refresh_data,
        )
        refresh_btn.pack(side="right")

    def _build_kpi_cards(self) -> None:
        """3 Clinical KPI Cards: Total Invoiced, Collected, and Outstanding."""
        self.kpi_container = ctk.CTkFrame(self, fg_color="transparent")
        self.kpi_container.pack(fill="x", padx=24, pady=(0, 12))
        self.kpi_container.grid_columnconfigure((0, 1, 2), weight=1)

        # 1. Total Invoiced Card
        self.card_invoiced, self.card_invoiced_title, self.card_invoiced_desc = self._create_metric_card(
            self.kpi_container, 0, "TOTAL INVOICED", "Rs. 0.00", "Consultation fees billed", ("#0284C7", "#06B6D4")
        )

        # 2. Total Collected Card
        self.card_collected, self.card_collected_title, self.card_collected_desc = self._create_metric_card(
            self.kpi_container, 1, "TOTAL COLLECTED", "Rs. 0.00", "Settled patient payments", ("#16A34A", "#22C55E")
        )

        # 3. Total Outstanding Card
        self.card_outstanding, self.card_outstanding_title, self.card_outstanding_desc = self._create_metric_card(
            self.kpi_container, 2, "OUTSTANDING DUES", "Rs. 0.00", "Unpaid consultation balance", ("#D97706", "#F59E0B")
        )

    def _create_metric_card(self, parent, col, title, initial_val, desc, accent_color):
        card = ctk.CTkFrame(
            parent,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=10,
        )
        card.grid(row=0, column=col, padx=6 if col == 1 else (0 if col == 0 else 0), pady=4, sticky="nsew")

        top = ctk.CTkFrame(card, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 2))
        t_lbl = ctk.CTkLabel(top, text=title, font=ctk.CTkFont(size=10, weight="bold"), text_color=("#64748B", "#94A3B8"), anchor="w")
        t_lbl.pack(side="left")

        val_lbl = ctk.CTkLabel(
            card,
            text=initial_val,
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=accent_color,
            anchor="w",
        )
        val_lbl.pack(fill="x", padx=14, pady=(2, 2))

        d_lbl = ctk.CTkLabel(
            card,
            text=desc,
            font=ctk.CTkFont(size=10),
            text_color=("#64748B", "#64748B"),
            anchor="w",
        )
        d_lbl.pack(fill="x", padx=14, pady=(0, 10))

        return val_lbl, t_lbl, d_lbl

    def _build_filter_bar(self) -> None:
        """Search input and status filter controls."""
        bar = ctk.CTkFrame(
            self,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=8,
        )
        bar.pack(fill="x", padx=24, pady=(0, 10))

        # Search Entry
        self.search_entry = ctk.CTkEntry(
            bar,
            placeholder_text="🔍 Search bill #, patient code, patient name, doctor...",
            height=34,
            width=320,
        )
        self.search_entry.pack(side="left", padx=12, pady=8)
        self.search_entry.bind("<KeyRelease>", lambda e: self._on_filter_changed())

        # Status Filter Menu
        ctk.CTkLabel(
            bar,
            text="Status:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
        ).pack(side="left", padx=(10, 4))

        self.status_filter_menu = ctk.CTkOptionMenu(
            bar,
            values=["All", "Unpaid", "Partially Paid", "Paid"],
            height=30,
            command=lambda v: self._on_filter_changed(),
        )
        self.status_filter_menu.set("All")
        self.status_filter_menu.pack(side="left", padx=(0, 12))

    def _build_table_container(self) -> None:
        """Scrollable table frame holding billing invoice records."""
        table_shell = ctk.CTkFrame(
            self,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=8,
        )
        table_shell.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        # Table Column Headers
        hdr_row = ctk.CTkFrame(table_shell, height=36, fg_color=("#F1F5F9", "#16233E"), corner_radius=0)
        hdr_row.pack(fill="x")
        hdr_row.pack_propagate(False)

        headers = [
            ("Invoice #", 110),
            ("Appt Ref", 90),
            ("Patient Details", 160),
            ("Physician", 150),
            ("Invoiced", 85),
            ("Paid", 85),
            ("Balance", 85),
            ("Status", 100),
            ("Actions", 140),
        ]

        for title, w in headers:
            ctk.CTkLabel(
                hdr_row,
                text=title,
                font=ctk.CTkFont(size=11, weight="bold"),
                text_color=("#475569", "#94A3B8"),
                width=w,
                anchor="w" if title != "Actions" else "center",
                padx=8,
            ).pack(side="left")

        # Scrollable rows area
        self.rows_scroll = ctk.CTkScrollableFrame(table_shell, fg_color="transparent")
        self.rows_scroll.pack(fill="both", expand=True)

    def _on_filter_changed(self) -> None:
        """Trigger reload with current filters."""
        self.load_bills()

    def refresh_data(self) -> None:
        """Reload KPIs and bill records from SQLite database with role-based scoping."""
        self.current_user = get_current_user()
        sync_unbilled_appointments()
        self._update_header_by_role()
        self.load_kpis()
        self.load_bills()

    def _update_header_by_role(self) -> None:
        """Update header titles and transaction audit button per active role."""
        role = self.current_user.get("role") if self.current_user else ""
        if role == "Patient":
            self.t_lbl.configure(text="💳 My Invoices & Online Payment Portal")
            self.sub_lbl.configure(text="View your consultation invoices, pay outstanding balance online, and download receipts.")
            self.audit_btn.pack_forget()
        elif role == "Doctor":
            self.t_lbl.configure(text="💳 Assigned Consultations Billing Roster")
            self.sub_lbl.configure(text="Overview of consultation fee settlement status for your clinical appointments.")
            self.audit_btn.pack_forget()
        else:
            self.t_lbl.configure(text="💳 Consultation Billing & Receipt Management")
            self.sub_lbl.configure(text="Real-time outpatient consultation invoices, payment processing, and official receipts.")
            if not self.audit_btn.winfo_ismapped():
                self.audit_btn.pack(side="right", padx=(0, 8), before=self.r_box.winfo_children()[-1])

    def load_kpis(self) -> None:
        """Update 3 metric cards with role-appropriate financial aggregates."""
        self.current_user = get_current_user()
        p_id = None
        d_id = None
        role = self.current_user.get("role") if self.current_user else "Hospital Administrator"

        if role == "Patient":
            p_id = self.current_user.get("linked_patient_id")
            self.card_invoiced_title.configure(text="MY TOTAL INVOICED")
            self.card_invoiced_desc.configure(text="Total consultation charges billed")
            self.card_collected_title.configure(text="MY PAYMENTS SETTLED")
            self.card_collected_desc.configure(text="Total amount paid to date")
            self.card_outstanding_title.configure(text="MY BALANCE DUE (ALL INVOICES)")
            self.card_outstanding_desc.configure(text="Total pending balance across all your invoices")
        elif role == "Doctor":
            d_id = self.current_user.get("linked_doctor_id")
            self.card_invoiced_title.configure(text="MY ASSIGNED BILLING")
            self.card_invoiced_desc.configure(text="Billed for your consultations")
            self.card_collected_title.configure(text="FEES COLLECTED")
            self.card_collected_desc.configure(text="Collected consultation revenue")
            self.card_outstanding_title.configure(text="PENDING PATIENT DUES")
            self.card_outstanding_desc.configure(text="Unpaid dues for your visits")
        else:
            self.card_invoiced_title.configure(text="TOTAL INVOICED")
            self.card_invoiced_desc.configure(text="Consultation fees billed across OPD")
            self.card_collected_title.configure(text="TOTAL COLLECTED")
            self.card_collected_desc.configure(text="Settled revenue received across OPD")
            self.card_outstanding_title.configure(text="OUTSTANDING DUES")
            self.card_outstanding_desc.configure(text="Unpaid consultation balance")

        stats = get_billing_summary_statistics(patient_id=p_id, doctor_id=d_id, user=self.current_user)
        self.card_invoiced.configure(text=f"Rs. {float(stats.get('total_invoiced', 0)):,.2f}")
        self.card_collected.configure(text=f"Rs. {float(stats.get('total_collected', 0)):,.2f}")
        self.card_outstanding.configure(text=f"Rs. {float(stats.get('total_outstanding', 0)):,.2f}")

    def load_bills(self) -> None:
        """Fetch and render bills matching current search query and status filter with strict role controls."""
        for child in self.rows_scroll.winfo_children():
            child.destroy()

        search_text = self.search_entry.get().strip()
        status_val = self.status_filter_menu.get().strip()

        # Role scoping
        p_id = None
        d_id = None
        role = self.current_user.get("role") if self.current_user else ""
        if role == "Patient":
            p_id = self.current_user.get("linked_patient_id")
        elif role == "Doctor":
            d_id = self.current_user.get("linked_doctor_id")

        bills = get_bills(patient_id=p_id, doctor_id=d_id, payment_status=status_val, search_query=search_text)

        if not bills:
            empty = ctk.CTkLabel(
                self.rows_scroll,
                text="No billing records match the current criteria.",
                font=ctk.CTkFont(size=12),
                text_color=("#64748B", "#94A3B8"),
                pady=40,
            )
            empty.pack()
            return

        can_record = has_permission("record_payments", self.current_user)

        for i, b in enumerate(bills):
            row_bg = ("#F8FAFC", "#0C152B") if i % 2 == 0 else ("#FFFFFF", "#0F172A")
            row = ctk.CTkFrame(self.rows_scroll, height=42, fg_color=row_bg, corner_radius=0)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            # Bill number
            ctk.CTkLabel(row, text=b["bill_number"], font=ctk.CTkFont(size=11, weight="bold"), text_color=("#0F172A", "#F8FAFC"), width=110, anchor="w", padx=8).pack(side="left")

            # Appt Code
            ctk.CTkLabel(row, text=b["appointment_code"], font=ctk.CTkFont(size=11), text_color=("#0284C7", "#38BDF8"), width=90, anchor="w", padx=8).pack(side="left")

            # Patient
            pat_text = f"{b['pat_first_name']} {b['pat_last_name']} ({b['patient_code']})"
            ctk.CTkLabel(row, text=pat_text, font=ctk.CTkFont(size=11), text_color=("#0F172A", "#F8FAFC"), width=160, anchor="w", padx=8).pack(side="left")

            # Doctor
            doc_text = f"Dr. {b['doc_first_name']} {b['doc_last_name']}"
            ctk.CTkLabel(row, text=doc_text, font=ctk.CTkFont(size=11), text_color=("#475569", "#CBD5E1"), width=150, anchor="w", padx=8).pack(side="left")

            # Invoiced
            ctk.CTkLabel(row, text=f"Rs. {float(b['total_amount']):.0f}", font=ctk.CTkFont(size=11), text_color=("#0F172A", "#F8FAFC"), width=85, anchor="w", padx=8).pack(side="left")

            # Paid
            ctk.CTkLabel(row, text=f"Rs. {float(b['amount_paid']):.0f}", font=ctk.CTkFont(size=11), text_color=("#16A34A", "#22C55E"), width=85, anchor="w", padx=8).pack(side="left")

            # Balance
            bal_val = float(b['outstanding_balance'])
            bal_color = ("#D97706", "#F59E0B") if bal_val > 0 else ("#16A34A", "#22C55E")
            ctk.CTkLabel(row, text=f"Rs. {bal_val:.0f}", font=ctk.CTkFont(size=11, weight="bold"), text_color=bal_color, width=85, anchor="w", padx=8).pack(side="left")

            # Status Badge
            status_colors = {
                "Paid": (("#DCFCE7", "#064E3B"), ("#15803D", "#34D399")),
                "Partially Paid": (("#FEF3C7", "#451A03"), ("#B45309", "#FBBF24")),
                "Unpaid": (("#FEE2E2", "#450A0A"), ("#B91C1C", "#F87171")),
            }
            bg_c, txt_c = status_colors.get(b["payment_status"], (("#F1F5F9", "#1E293B"), ("#64748B", "#94A3B8")))

            status_frame = ctk.CTkFrame(row, width=100, fg_color="transparent")
            status_frame.pack(side="left")
            status_pill = ctk.CTkLabel(
                status_frame,
                text=b["payment_status"],
                font=ctk.CTkFont(size=10, weight="bold"),
                fg_color=bg_c,
                text_color=txt_c,
                corner_radius=6,
                padx=8,
                pady=2,
            )
            status_pill.pack(side="left", padx=4)

            # Actions Box
            act_box = ctk.CTkFrame(row, width=140, fg_color="transparent")
            act_box.pack(side="left")

            # 1. Patient Portal Action: Pay Now (Direct online checkout for own invoices)
            if role == "Patient":
                if bal_val > 0:
                    pay_btn = ctk.CTkButton(
                        act_box,
                        text="💳 Pay Now",
                        font=ctk.CTkFont(size=10, weight="bold"),
                        fg_color=("#16A34A", "#15803D"),
                        hover_color=("#15803D", "#166534"),
                        height=24,
                        width=68,
                        command=lambda bid=b["id"]: self._open_patient_payment_modal(bid),
                    )
                    pay_btn.pack(side="left", padx=2)
                else:
                    settled_lbl = ctk.CTkLabel(
                        act_box,
                        text="✓ Settled",
                        font=ctk.CTkFont(size=10, weight="bold"),
                        fg_color=("#DCFCE7", "#064E3B"),
                        text_color=("#15803D", "#34D399"),
                        corner_radius=4,
                        padx=6,
                        pady=2,
                    )
                    settled_lbl.pack(side="left", padx=2)

            # 2. Staff & Admin Action: Record Payment (Cashier operational recording)
            elif role in ("Hospital Administrator", "Staff"):
                if bal_val > 0 and can_record:
                    pay_btn = ctk.CTkButton(
                        act_box,
                        text="💳 Record",
                        font=ctk.CTkFont(size=10, weight="bold"),
                        fg_color=("#0284C7", "#0284C7"),
                        hover_color=("#0369A1", "#0369A1"),
                        height=24,
                        width=60,
                        command=lambda bid=b["id"]: self._open_payment_modal(bid),
                    )
                    pay_btn.pack(side="left", padx=2)

            # 3. Doctor Action: Strict read-only. No Pay Now, No Record payment button.

            # Receipt Slip Button (Available for all roles if any payment has been settled)
            if float(b["amount_paid"]) > 0:
                rec_btn = ctk.CTkButton(
                    act_box,
                    text="🧾 Slip",
                    font=ctk.CTkFont(size=10, weight="bold"),
                    fg_color=("#F1F5F9", "#1E2D4A"),
                    text_color=("#0F172A", "#F8FAFC"),
                    hover_color=("#E2E8F0", "#2B3E63"),
                    border_width=1,
                    border_color=("#CBD5E1", "#33456B"),
                    height=24,
                    width=50,
                    command=lambda bid=b["id"]: self._view_receipt_for_bill(bid),
                )
                rec_btn.pack(side="left", padx=2)

    def _open_payment_modal(self, bill_id: int) -> None:
        """Launch operational cashier payment recording modal for Staff / Admin."""
        RecordPaymentModal(self.winfo_toplevel(), bill_id=bill_id, on_success=lambda r: self.refresh_data())

    def _open_patient_payment_modal(self, bill_id: int) -> None:
        """Launch patient online payment checkout modal."""
        PatientPaymentModal(self.winfo_toplevel(), bill_id=bill_id, on_success=lambda r: self.refresh_data())

    def _open_audit_modal(self) -> None:
        """Launch payment transactions audit reconciliation modal."""
        PaymentAuditLogModal(self.winfo_toplevel())

    def _view_receipt_for_bill(self, bill_id: int) -> None:
        """Retrieve latest receipt for bill and display."""
        payments = get_payments_for_bill(bill_id)
        if payments and payments[0].get("receipt_number"):
            ReceiptViewModal(self.winfo_toplevel(), receipt_number=payments[0]["receipt_number"])
