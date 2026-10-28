"""Interactive modal dialogs for Billing, Payment Recording, Patient Online Checkout, and Receipts.
Engineered with responsive geometry, input validation, role-based protection, and receipt rendering.
"""
from datetime import datetime
from typing import Callable, Dict, List, Optional
import customtkinter as ctk

from config.constants import (
    PAYMENT_METHOD_CARD,
    PAYMENT_METHOD_NET_BANKING,
    PAYMENT_METHOD_UPI,
    PAYMENT_METHODS,
    ROLE_ADMIN,
    ROLE_DOCTOR,
    ROLE_PATIENT,
    ROLE_STAFF,
)
from services.auth_service import get_current_user
from services.billing_service import (
    generate_receipt_text,
    get_bill_by_id,
    get_receipt_by_number,
    record_payment,
)
from services.payment_service import (
    get_payment_gateway_info,
    get_payment_transactions,
    process_patient_online_payment,
)


class RecordPaymentModal(ctk.CTkToplevel):
    """Staff/Admin operational cashier modal to record offline payments (Cash/Terminal/DD)."""

    def __init__(
        self,
        master,
        bill_id: int,
        on_success: Optional[Callable[[Dict], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.bill_id = bill_id
        self.on_success = on_success
        self.bill = get_bill_by_id(bill_id)
        self.current_user = get_current_user()

        if not self.bill:
            self.destroy()
            return

        # Security check: Doctors and Patients cannot access cashier payment recording
        role = self.current_user.get("role") if self.current_user else ""
        if role in (ROLE_DOCTOR, ROLE_PATIENT):
            self.destroy()
            return

        self.title(f"Record Payment — Invoice {self.bill['bill_number']}")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._apply_responsive_geometry(master)
        self._build_ui()

        self.bind("<Escape>", lambda event: self.destroy())
        self.lift()
        self.focus_force()

    def _apply_responsive_geometry(self, master) -> None:
        """Center modal dialog adaptively."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        scaling = self._get_window_scaling()

        target_w = min(540, int((sw - 40) / scaling))
        target_h = min(480, int((sh - 80) / scaling))

        phys_w = int(target_w * scaling)
        phys_h = int(target_h * scaling)
        pos_x = max(0, (sw - phys_w) // 2)
        pos_y = max(10, (sh - phys_h) // 2 - 20)

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")

    def _build_ui(self) -> None:
        """Construct payment form layout."""
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=20, pady=16)

        # Header
        hdr = ctk.CTkFrame(pad, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            hdr,
            text="💳 Record Consultation Payment",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#0284C7", "#06B6D4"),
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            hdr,
            text="Operational desk: Record offline payment (Cash, Terminal swipe, DD) and issue an official receipt.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        ).pack(fill="x")

        # Invoice Summary Card
        card = ctk.CTkFrame(
            pad,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=8,
        )
        card.pack(fill="x", pady=(0, 12), ipady=6)

        c_row1 = ctk.CTkFrame(card, fg_color="transparent")
        c_row1.pack(fill="x", padx=12, pady=2)
        ctk.CTkLabel(c_row1, text=f"Invoice: {self.bill['bill_number']}", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#0F172A", "#F8FAFC")).pack(side="left")
        ctk.CTkLabel(c_row1, text=f"Appointment: {self.bill['appointment_code']}", font=ctk.CTkFont(size=11), text_color=("#64748B", "#94A3B8")).pack(side="right")

        c_row2 = ctk.CTkFrame(card, fg_color="transparent")
        c_row2.pack(fill="x", padx=12, pady=2)
        pat = f"{self.bill['pat_first_name']} {self.bill['pat_last_name']} ({self.bill['patient_code']})"
        doc = f"Dr. {self.bill['doc_first_name']} {self.bill['doc_last_name']} ({self.bill['specialization']})"
        ctk.CTkLabel(c_row2, text=f"Patient: {pat}", font=ctk.CTkFont(size=11), text_color=("#475569", "#CBD5E1")).pack(side="left")
        ctk.CTkLabel(c_row2, text=f"Doctor: {doc}", font=ctk.CTkFont(size=11), text_color=("#475569", "#CBD5E1")).pack(side="right")

        # Amounts Row
        c_row3 = ctk.CTkFrame(card, fg_color=("#F1F5F9", "#16233E"), corner_radius=6)
        c_row3.pack(fill="x", padx=12, pady=(6, 2))
        total = float(self.bill['total_amount'])
        paid = float(self.bill['amount_paid'])
        bal = float(self.bill['outstanding_balance'])
        ctk.CTkLabel(c_row3, text=f"Total: Rs. {total:.2f}   |   Paid: Rs. {paid:.2f}   |   Balance Due: Rs. {bal:.2f}", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#B45309", "#FBBF24"), padx=8, pady=4).pack()

        # Input Fields Frame
        form = ctk.CTkFrame(pad, fg_color="transparent")
        form.pack(fill="x", pady=(0, 10))
        form.grid_columnconfigure((0, 1), weight=1)

        # Amount to pay
        ctk.CTkLabel(form, text="Payment Amount (Rs.) *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=0, column=0, padx=4, pady=(2, 1), sticky="w")
        self.amount_entry = ctk.CTkEntry(form, height=32)
        self.amount_entry.insert(0, f"{bal:.2f}")
        self.amount_entry.grid(row=1, column=0, padx=4, pady=(0, 6), sticky="ew")

        # Payment Method
        ctk.CTkLabel(form, text="Payment Method *", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=0, column=1, padx=4, pady=(2, 1), sticky="w")
        self.method_menu = ctk.CTkOptionMenu(form, values=PAYMENT_METHODS, height=32)
        self.method_menu.set("Cash")
        self.method_menu.grid(row=1, column=1, padx=4, pady=(0, 6), sticky="ew")

        # Reference Number
        ctk.CTkLabel(form, text="Reference / Receipt ID", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=2, column=0, padx=4, pady=(2, 1), sticky="w")
        self.ref_entry = ctk.CTkEntry(form, placeholder_text="e.g. CASH-DESK-01 or Card slip #", height=32)
        self.ref_entry.grid(row=3, column=0, padx=4, pady=(0, 6), sticky="ew")

        # Recorded by
        ctk.CTkLabel(form, text="Recorded By", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=2, column=1, padx=4, pady=(2, 1), sticky="w")
        self.cashier_entry = ctk.CTkEntry(form, height=32)
        operator_name = self.current_user.get("full_name", "Reception Desk") if self.current_user else "Reception Desk"
        self.cashier_entry.insert(0, operator_name)
        self.cashier_entry.grid(row=3, column=1, padx=4, pady=(0, 6), sticky="ew")

        # Error banner
        self.err_lbl = ctk.CTkLabel(pad, text="", font=ctk.CTkFont(size=11), text_color="#EF4444", anchor="w")
        self.err_lbl.pack(fill="x", pady=(0, 6))

        # Footer Actions
        footer = ctk.CTkFrame(pad, fg_color="transparent")
        footer.pack(fill="x", side="bottom")

        cancel_btn = ctk.CTkButton(
            footer,
            text="Dismiss",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            width=90,
            height=34,
            command=self.destroy,
        )
        cancel_btn.pack(side="right", padx=(8, 0))

        self.submit_btn = ctk.CTkButton(
            footer,
            text="💳 Record Payment & Issue Receipt",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#0284C7", "#0284C7"),
            hover_color=("#0369A1", "#0369A1"),
            height=34,
            command=self._do_payment,
        )
        self.submit_btn.pack(side="right")

    def _do_payment(self) -> None:
        """Process payment and launch receipt modal upon success."""
        self.err_lbl.configure(text="")
        amt_str = self.amount_entry.get().strip()

        try:
            amt = float(amt_str)
        except ValueError:
            self.err_lbl.configure(text="Please enter a valid numeric payment amount.")
            return

        method = self.method_menu.get().strip()
        ref_no = self.ref_entry.get().strip() or None
        cashier = self.cashier_entry.get().strip() or "Reception Desk"

        self.submit_btn.configure(state="disabled", text="Processing...")
        self.update_idletasks()

        success, message, receipt_obj = record_payment(
            bill_id=self.bill_id,
            amount=amt,
            payment_method=method,
            reference_number=ref_no,
            recorded_by=cashier,
            user=self.current_user,
        )

        if success:
            master = self.master
            on_succ = self.on_success
            self.destroy()
            if on_succ and receipt_obj:
                on_succ(receipt_obj)
            if receipt_obj and "receipt_number" in receipt_obj:
                try:
                    ReceiptViewModal(master, receipt_number=receipt_obj["receipt_number"])
                except Exception as ex:
                    print(f"Error opening receipt modal: {ex}")
        else:
            self.err_lbl.configure(text=message)
            self.submit_btn.configure(state="normal", text="💳 Record Payment & Issue Receipt")


class PatientPaymentModal(ctk.CTkToplevel):
    """Patient Online Checkout modal featuring Demo Payment Gateway with simulation controls."""

    def __init__(
        self,
        master,
        bill_id: int,
        on_success: Optional[Callable[[Dict], None]] = None,
        **kwargs,
    ):
        super().__init__(master, **kwargs)
        self.bill_id = bill_id
        self.on_success = on_success
        self.bill = get_bill_by_id(bill_id)
        self.current_user = get_current_user()

        if not self.bill:
            self.destroy()
            return

        # Security check: Doctor cannot initiate patient payments
        role = self.current_user.get("role") if self.current_user else ""
        if role == ROLE_DOCTOR:
            self.destroy()
            return

        # Security check: Patients can only pay their own invoices
        if role == ROLE_PATIENT:
            linked_pid = self.current_user.get("linked_patient_id")
            if not linked_pid or int(self.bill["patient_id"]) != int(linked_pid):
                self.destroy()
                return

        # Generate unique idempotency session key
        self.idempotency_key = f"IDEMP-PAY-{bill_id}-{int(datetime.now().timestamp() * 1000)}"

        self.title(f"Patient Online Checkout — Invoice {self.bill['bill_number']}")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        # Responsive geometry tailored to 720p / 1080p and high-DPI scaling
        self._apply_responsive_geometry(master)

        # 1. FIXED HEADER (Packed TOP)
        self._build_header()

        # 2. FIXED FOOTER (Packed BOTTOM FIRST so it is permanently visible)
        self._build_fixed_footer()

        # 3. SCROLLABLE MIDDLE CONTAINER (Packed in remaining central space)
        self._build_scrollable_body()

        # Bind event shortcuts & recursive mouse wheel scrolling
        self._setup_event_bindings()

        self.lift()
        self.focus_force()

    def _apply_responsive_geometry(self, master) -> None:
        """Calculate dimensions so modal fits safely inside screen height with taskbar margins."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        scaling = self._get_window_scaling()

        max_unscaled_h = int((sh - 90) / scaling)
        target_h = min(580, max_unscaled_h)
        target_w = min(580, int((sw - 40) / scaling))

        phys_w = int(target_w * scaling)
        phys_h = int(target_h * scaling)
        pos_x = max(0, (sw - phys_w) // 2)
        pos_y = max(10, (sh - phys_h) // 2 - 20)

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")
        self.minsize(min(480, sw - 40), min(360, sh - 60))

    def _build_header(self) -> None:
        """Fixed header frame with checkout title, subtitle, and demo badge."""
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.pack(side="top", fill="x", padx=20, pady=(12, 4))

        top_row = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        top_row.pack(fill="x")

        ctk.CTkLabel(
            top_row,
            text="💳 Patient Portal — Online Payment Checkout",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#0284C7", "#06B6D4"),
            anchor="w",
        ).pack(side="left")

        demo_badge = ctk.CTkLabel(
            top_row,
            text="⚡ DEMO GATEWAY",
            font=ctk.CTkFont(size=10, weight="bold"),
            fg_color=("#FEF3C7", "#3D2A00"),
            text_color=("#B45309", "#FBBF24"),
            corner_radius=6,
            padx=8,
            pady=2,
        )
        demo_badge.pack(side="right")

        ctk.CTkLabel(
            self.header_frame,
            text=f"Academic Payment Simulation — Settle consultation dues for {self.bill['bill_number']}. (No real money is charged).",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

    def _build_fixed_footer(self) -> None:
        """Fixed footer bar permanently anchored at the bottom with all simulation action buttons."""
        self.footer_frame = ctk.CTkFrame(
            self,
            fg_color=("#F1F5F9", "#1E202E"),
            border_width=1,
            border_color=("#CBD5E1", "#334155"),
            corner_radius=8,
            height=58,
        )
        self.footer_frame.pack(side="bottom", fill="x", padx=16, pady=(4, 12))
        self.footer_frame.pack_propagate(False)

        # Cancel button on left
        self.cancel_btn = ctk.CTkButton(
            self.footer_frame,
            text="⊘ Cancel",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            width=80,
            height=34,
            command=self._do_cancel,
        )
        self.cancel_btn.pack(side="left", padx=(12, 6), pady=12)

        # Simulate Bank Failure button
        self.fail_btn = ctk.CTkButton(
            self.footer_frame,
            text="✕ Simulate Bank Failure",
            font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=("#FEE2E2", "#450A0A"),
            text_color=("#B91C1C", "#F87171"),
            hover_color=("#FCA5A5", "#7F1D1D"),
            border_width=1,
            border_color=("#FCA5A5", "#7F1D1D"),
            height=34,
            command=lambda: self._do_pay("FAILURE"),
        )
        self.fail_btn.pack(side="left", padx=6, pady=12)

        # Simulate Success button (Primary action)
        self.success_btn = ctk.CTkButton(
            self.footer_frame,
            text="✓ Pay Now (Simulate Success)",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#16A34A", "#15803D"),
            hover_color=("#15803D", "#166534"),
            height=34,
            command=lambda: self._do_pay("SUCCESS"),
        )
        self.success_btn.pack(side="right", padx=(6, 12), pady=12)

    def _build_scrollable_body(self) -> None:
        """Middle scrollable container housing bill summary, amount selection, payment method, and walkthrough."""
        self.scroll_body = ctk.CTkScrollableFrame(
            self,
            fg_color=("white", "#181A26"),
            border_width=1,
            border_color=("#E2E8F0", "#334155"),
            corner_radius=8,
        )
        self.scroll_body.pack(side="top", fill="both", expand=True, padx=16, pady=(2, 4))

        # 1. Prominent Demo Gateway Banner (Academic Mode Requirement)
        gateway_info = get_payment_gateway_info()
        demo_banner = ctk.CTkFrame(
            self.scroll_body,
            fg_color=("#FEF3C7", "#3B2206"),
            border_width=1,
            border_color=("#F59E0B", "#B45309"),
            corner_radius=8,
        )
        demo_banner.pack(fill="x", padx=8, pady=(8, 10))

        b_pad = ctk.CTkFrame(demo_banner, fg_color="transparent")
        b_pad.pack(fill="x", padx=12, pady=8)

        ctk.CTkLabel(
            b_pad,
            text="⚡ DEMO PAYMENT MODE — Academic Demonstration",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#92400E", "#FBBF24"),
            anchor="w",
        ).pack(fill="x")

        ctk.CTkLabel(
            b_pad,
            text=gateway_info["notice"],
            font=ctk.CTkFont(size=10),
            text_color=("#B45309", "#FDE68A"),
            wraplength=480,
            justify="left",
            anchor="w",
        ).pack(fill="x", pady=(2, 0))

        # 2. Invoice Summary Card
        card = ctk.CTkFrame(
            self.scroll_body,
            fg_color=("#F8FAFC", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=8,
        )
        card.pack(fill="x", padx=8, pady=(0, 10), ipady=4)

        c_row1 = ctk.CTkFrame(card, fg_color="transparent")
        c_row1.pack(fill="x", padx=12, pady=(8, 2))
        ctk.CTkLabel(c_row1, text=f"Selected Invoice: #{self.bill['bill_number']}", font=ctk.CTkFont(size=12, weight="bold"), text_color=("#0F172A", "#F8FAFC")).pack(side="left")
        ctk.CTkLabel(c_row1, text=f"Consultation: {self.bill['appointment_code']}", font=ctk.CTkFont(size=11), text_color=("#0284C7", "#38BDF8")).pack(side="right")

        c_row2 = ctk.CTkFrame(card, fg_color="transparent")
        c_row2.pack(fill="x", padx=12, pady=2)
        pat_name = f"{self.bill['pat_first_name']} {self.bill['pat_last_name']} ({self.bill['patient_code']})"
        doc_name = f"Dr. {self.bill['doc_first_name']} {self.bill['doc_last_name']} — {self.bill['specialization']}"
        ctk.CTkLabel(c_row2, text=f"Patient: {pat_name}", font=ctk.CTkFont(size=11), text_color=("#475569", "#CBD5E1")).pack(side="left")
        ctk.CTkLabel(c_row2, text=doc_name, font=ctk.CTkFont(size=11), text_color=("#475569", "#CBD5E1")).pack(side="right")

        # Balance highlight
        bal_frame = ctk.CTkFrame(card, fg_color=("#F1F5F9", "#16233E"), corner_radius=6)
        bal_frame.pack(fill="x", padx=12, pady=(6, 8))
        self.outstanding_val = float(self.bill['outstanding_balance'])
        total_val = float(self.bill['total_amount'])
        paid_val = float(self.bill['amount_paid'])

        ctk.CTkLabel(
            bal_frame,
            text=f"Selected Invoice Total: Rs. {total_val:.2f}   |   Paid: Rs. {paid_val:.2f}   |   Invoice Balance Due: Rs. {self.outstanding_val:.2f}",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#B45309", "#FBBF24"),
            padx=8,
            pady=4,
        ).pack(pady=(4, 2))

        # Patient Account Context (clarifying total across all invoices vs this selected invoice)
        from services.billing_service import get_billing_summary_statistics
        stats = get_billing_summary_statistics(patient_id=self.bill["patient_id"], user=self.current_user)
        combined_due = float(stats.get("total_outstanding", 0.0))
        ctk.CTkLabel(
            bal_frame,
            text=f"ℹ️ Total Outstanding Across All Patient Invoices: Rs. {combined_due:.2f}",
            font=ctk.CTkFont(size=10),
            text_color=("#64748B", "#94A3B8"),
            padx=8,
            pady=2,
        ).pack(pady=(0, 4))

        # 3. Payment Amount Selection (Full vs Partial)
        amt_box = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        amt_box.pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkLabel(
            amt_box,
            text="Payment Amount for Selected Invoice:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#475569", "#94A3B8"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        amt_row = ctk.CTkFrame(amt_box, fg_color="transparent")
        amt_row.pack(fill="x")

        self.pay_full_btn = ctk.CTkButton(
            amt_row,
            text=f"🔘 Pay Full (Rs. {self.outstanding_val:.2f})",
            font=ctk.CTkFont(size=11, weight="bold"),
            height=30,
            fg_color=("#0284C7", "#0284C7"),
            hover_color=("#0369A1", "#0369A1"),
            command=self._set_full_amount,
        )
        self.pay_full_btn.pack(side="left", padx=(0, 8))

        half_amt = round(self.outstanding_val / 2, 2)
        self.pay_half_btn = ctk.CTkButton(
            amt_row,
            text=f"🔘 Pay 50% (Rs. {half_amt:.2f})",
            font=ctk.CTkFont(size=11),
            height=30,
            fg_color=("#F1F5F9", "#1E2D4A"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#33456B"),
            border_width=1,
            border_color=("#CBD5E1", "#33456B"),
            command=self._set_half_amount,
        )
        self.pay_half_btn.pack(side="left", padx=(0, 8))

        self.amount_entry = ctk.CTkEntry(amt_row, height=30, width=110)
        self.amount_entry.insert(0, f"{self.outstanding_val:.2f}")
        self.amount_entry.pack(side="left")

        # 4. Payment Method Tabs & Fields
        method_box = ctk.CTkFrame(self.scroll_body, fg_color="transparent")
        method_box.pack(fill="x", padx=8, pady=(0, 8))

        ctk.CTkLabel(
            method_box,
            text="Select Simulated Payment Method:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#475569", "#94A3B8"),
            anchor="w",
        ).pack(fill="x", pady=(0, 4))

        self.method_var = ctk.StringVar(value=PAYMENT_METHOD_UPI)
        self.method_seg = ctk.CTkSegmentedButton(
            method_box,
            values=[PAYMENT_METHOD_UPI, PAYMENT_METHOD_CARD, PAYMENT_METHOD_NET_BANKING],
            variable=self.method_var,
            command=self._on_method_changed,
        )
        self.method_seg.pack(fill="x", pady=(0, 6))

        # Dynamic demo details frame
        self.details_frame = ctk.CTkFrame(
            self.scroll_body,
            fg_color=("#F8FAFC", "#0C152B"),
            border_width=1,
            border_color=("#E2E8F0", "#1E2D4A"),
            corner_radius=8,
        )
        self.details_frame.pack(fill="x", padx=8, pady=(0, 8))
        self.details_lbl = ctk.CTkLabel(
            self.details_frame,
            text="📱 Virtual UPI ID: patient@okhdfcbank\n• Instant virtual UPI switch simulation with automated callback verification.",
            font=ctk.CTkFont(size=11),
            text_color=("#0284C7", "#38BDF8"),
            padx=12,
            pady=10,
            justify="left",
            anchor="w",
        )
        self.details_lbl.pack(fill="x")

        # 5. Academic Demonstration Walkthrough / Procedure Card
        proc_frame = ctk.CTkFrame(
            self.scroll_body,
            fg_color=("#F1F5F9", "#111827"),
            border_width=1,
            border_color=("#CBD5E1", "#1F2937"),
            corner_radius=8,
        )
        proc_frame.pack(fill="x", padx=8, pady=(0, 8))

        proc_hdr = ctk.CTkLabel(
            proc_frame,
            text="📋 Academic Demo Procedure (Classroom Walkthrough)",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#334155", "#94A3B8"),
            anchor="w",
        )
        proc_hdr.pack(fill="x", padx=10, pady=(6, 2))

        steps_text = (
            "1. Review Bill: Verify invoice balance due and total patient account balance.\n"
            "2. Select Method: Choose UPI, Card, or Net Banking test credentials.\n"
            "3. Test Simulation:\n"
            "   • Click 'Pay Now' to simulate successful clearance & instant receipt.\n"
            "   • Click 'Simulate Bank Failure' to verify balance protection on decline.\n"
            "4. Idempotency: Unique session token guards against double-billing."
        )
        proc_lbl = ctk.CTkLabel(
            proc_frame,
            text=steps_text,
            font=ctk.CTkFont(size=10),
            text_color=("#475569", "#94A3B8"),
            justify="left",
            anchor="w",
        )
        proc_lbl.pack(fill="x", padx=10, pady=(0, 6))

        # Error / Status Banner
        self.err_lbl = ctk.CTkLabel(
            self.scroll_body,
            text="",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color="#EF4444",
            wraplength=480,
            anchor="w",
        )
        self.err_lbl.pack(fill="x", padx=8, pady=(0, 6))

    def _setup_event_bindings(self) -> None:
        """Bind mouse wheel scrolling and keyboard shortcuts."""
        self.bind("<Escape>", lambda event: self._do_cancel())
        self._bind_mousewheel_recursive(self.scroll_body)

    def _bind_mousewheel_recursive(self, widget) -> None:
        """Recursively attach mouse wheel scrolling handler."""
        try:
            widget.bind("<MouseWheel>", self._on_mousewheel, add="+")
            widget.bind("<Button-4>", self._on_mousewheel, add="+")
            widget.bind("<Button-5>", self._on_mousewheel, add="+")
        except (NotImplementedError, AttributeError, Exception):
            pass
        for child in widget.winfo_children():
            self._bind_mousewheel_recursive(child)

    def _on_mousewheel(self, event) -> None:
        """Handle mouse wheel scrolling on the checkout form with responsive increments."""
        try:
            if hasattr(self, "scroll_body") and self.scroll_body._parent_canvas:
                delta = getattr(event, "delta", 0)
                num = getattr(event, "num", 0)
                step = int(abs(delta) / 120.0 * 40) if delta else 40
                if num == 5 or delta < 0:
                    self.scroll_body._parent_canvas.yview("scroll", max(1, step), "units")
                elif num == 4 or delta > 0:
                    self.scroll_body._parent_canvas.yview("scroll", -max(1, step), "units")
        except Exception:
            pass

    def _set_full_amount(self) -> None:
        """Pre-fill remaining full balance for selected invoice and update visual selection."""
        self.amount_entry.delete(0, "end")
        self.amount_entry.insert(0, f"{self.outstanding_val:.2f}")
        self.pay_full_btn.configure(
            fg_color=("#0284C7", "#0284C7"),
            text_color="white",
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.pay_half_btn.configure(
            fg_color=("#F1F5F9", "#1E2D4A"),
            text_color=("#0F172A", "#F8FAFC"),
            font=ctk.CTkFont(size=11),
        )

    def _set_half_amount(self) -> None:
        """Pre-fill 50% partial payment for selected invoice and update visual selection."""
        half = round(self.outstanding_val / 2, 2)
        self.amount_entry.delete(0, "end")
        self.amount_entry.insert(0, f"{half:.2f}")
        self.pay_half_btn.configure(
            fg_color=("#0284C7", "#0284C7"),
            text_color="white",
            font=ctk.CTkFont(size=11, weight="bold"),
        )
        self.pay_full_btn.configure(
            fg_color=("#F1F5F9", "#1E2D4A"),
            text_color=("#0F172A", "#F8FAFC"),
            font=ctk.CTkFont(size=11),
        )

    def _on_method_changed(self, value: str) -> None:
        """Update demo payment method simulation instructions."""
        if value == PAYMENT_METHOD_UPI:
            self.details_lbl.configure(
                text="📱 Virtual UPI ID: patient@okhdfcbank\n• Instant virtual UPI switch simulation with automated callback verification."
            )
        elif value == PAYMENT_METHOD_CARD:
            self.details_lbl.configure(
                text="💳 Test Card: 4111-XXXX-XXXX-1111 | Exp: 12/28 | CVV: 123\n• 3D-Secure Test OTP: 123456 (Simulated Visa/Mastercard processing)."
            )
        elif value == PAYMENT_METHOD_NET_BANKING:
            self.details_lbl.configure(
                text="🏦 Simulated Bank: HDFC Bank / SBI / ICICI NetBanking Portal\n• Instant secure redirection and digital signature verification."
            )

    def _do_cancel(self) -> None:
        """User cancels checkout without completing payment."""
        process_patient_online_payment(
            bill_id=self.bill_id,
            amount=self.outstanding_val,
            simulated_outcome="CANCELLED",
            user=self.current_user,
        )
        self.destroy()

    def _do_pay(self, outcome: str) -> None:
        """Process online checkout through payment service with server-side validation and idempotency."""
        self.err_lbl.configure(text="")
        amt_str = self.amount_entry.get().strip()

        try:
            amt = float(amt_str)
        except ValueError:
            self.err_lbl.configure(text="Please enter a valid numeric payment amount.")
            return

        method = self.method_var.get()

        # Prevent double-clicks / repeated callbacks
        self.success_btn.configure(state="disabled", text="Processing Gateway...")
        self.fail_btn.configure(state="disabled")
        self.cancel_btn.configure(state="disabled")
        self.update_idletasks()

        ok, msg, receipt_obj = process_patient_online_payment(
            bill_id=self.bill_id,
            amount=amt,
            payment_method=method,
            simulated_outcome=outcome,
            idempotency_key=self.idempotency_key,
            user=self.current_user,
        )

        if ok and receipt_obj:
            master = self.master
            on_succ = self.on_success
            self.destroy()

            # Refresh caller view automatically
            if on_succ:
                on_succ(receipt_obj)

            # Display confirmation modal with official receipt slip access
            PaymentConfirmationModal(master, receipt_obj=receipt_obj)
        else:
            self.err_lbl.configure(text=msg)
            self.success_btn.configure(state="normal", text="✓ Pay Now (Simulate Success)")
            self.fail_btn.configure(state="normal")
            self.cancel_btn.configure(state="normal")


class PaymentConfirmationModal(ctk.CTkToplevel):
    """Celebratory modal dialog displayed after successful patient online payment."""

    def __init__(self, master, receipt_obj: Dict, **kwargs):
        super().__init__(master, **kwargs)
        self.receipt = receipt_obj
        self.title("Payment Confirmation — Hospital Management System")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._apply_responsive_geometry(master)
        self._build_ui()

        self.bind("<Escape>", lambda event: self.destroy())
        self.lift()
        self.focus_force()

    def _apply_responsive_geometry(self, master) -> None:
        """Center modal dialog adaptively."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        scaling = self._get_window_scaling()

        target_w = min(480, int((sw - 40) / scaling))
        target_h = min(430, int((sh - 80) / scaling))

        phys_w = int(target_w * scaling)
        phys_h = int(target_h * scaling)
        pos_x = max(0, (sw - phys_w) // 2)
        pos_y = max(10, (sh - phys_h) // 2 - 20)

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")

    def _build_ui(self) -> None:
        """Construct confirmation slip layout."""
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=24, pady=20)

        # Success badge
        badge = ctk.CTkLabel(
            pad,
            text="🎉 Payment Successful!",
            font=ctk.CTkFont(size=18, weight="bold"),
            text_color=("#16A34A", "#22C55E"),
        )
        badge.pack(pady=(0, 4))

        ctk.CTkLabel(
            pad,
            text="Your consultation dues have been processed and confirmed.",
            font=ctk.CTkFont(size=11),
            text_color=("#64748B", "#94A3B8"),
        ).pack(pady=(0, 14))

        # Receipt summary card
        card = ctk.CTkFrame(
            pad,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=10,
        )
        card.pack(fill="x", pady=(0, 14), ipady=8)

        items = [
            ("Receipt Number:", self.receipt.get("receipt_number", "N/A")),
            ("Invoice Reference:", self.receipt.get("bill_number", "N/A")),
            ("Amount Paid:", f"Rs. {float(self.receipt.get('amount', 0)):.2f}"),
            ("Payment Method:", f"{self.receipt.get('payment_method', 'N/A')} (Demo Gateway)"),
            ("Remaining Balance:", f"Rs. {float(self.receipt.get('outstanding_balance', 0)):.2f}"),
            ("Payment Date:", self.receipt.get("payment_date", str(datetime.now().date()))),
        ]

        for lbl, val in items:
            row = ctk.CTkFrame(card, fg_color="transparent")
            row.pack(fill="x", padx=16, pady=2)
            ctk.CTkLabel(row, text=lbl, font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8")).pack(side="left")
            ctk.CTkLabel(row, text=str(val), font=ctk.CTkFont(size=11), text_color=("#0F172A", "#F8FAFC")).pack(side="right")

        # Footer Actions
        footer = ctk.CTkFrame(pad, fg_color="transparent")
        footer.pack(fill="x", side="bottom")

        close_btn = ctk.CTkButton(
            footer,
            text="✓ Done",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            width=90,
            height=34,
            command=self.destroy,
        )
        close_btn.pack(side="right", padx=(8, 0))

        slip_btn = ctk.CTkButton(
            footer,
            text="🧾 View Official Receipt",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#0284C7", "#0284C7"),
            hover_color=("#0369A1", "#0369A1"),
            height=34,
            command=self._open_receipt,
        )
        slip_btn.pack(side="right")

    def _open_receipt(self) -> None:
        """Launch complete official receipt modal."""
        master = self.master
        rec_num = self.receipt.get("receipt_number")
        self.destroy()
        if rec_num:
            ReceiptViewModal(master, receipt_number=rec_num)


class PaymentAuditLogModal(ctk.CTkToplevel):
    """Administrator and Staff modal for transaction reconciliation and audit investigation."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.current_user = get_current_user()

        self.title("Payment Transactions Audit & Reconciliation Log")
        self.resizable(True, True)
        self.transient(master)
        self.grab_set()

        self._apply_responsive_geometry(master)
        self._build_ui()
        self.load_transactions()

        self.bind("<Escape>", lambda event: self.destroy())
        self.lift()
        self.focus_force()

    def _apply_responsive_geometry(self, master) -> None:
        """Center modal dialog adaptively."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        scaling = self._get_window_scaling()

        target_w = min(880, int((sw - 40) / scaling))
        target_h = min(560, int((sh - 60) / scaling))

        phys_w = int(target_w * scaling)
        phys_h = int(target_h * scaling)
        pos_x = max(0, (sw - phys_w) // 2)
        pos_y = max(10, (sh - phys_h) // 2 - 20)

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")

    def _build_ui(self) -> None:
        """Construct audit log table and filter controls."""
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=20, pady=16)

        # Header
        hdr = ctk.CTkFrame(pad, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 10))

        ctk.CTkLabel(
            hdr,
            text="📋 Payment Transactions & Reconciliation Audit Log",
            font=ctk.CTkFont(size=16, weight="bold"),
            text_color=("#0284C7", "#06B6D4"),
            anchor="w",
        ).pack(side="left")

        ctk.CTkButton(
            hdr,
            text="🔄 Refresh",
            font=ctk.CTkFont(size=11, weight="bold"),
            width=80,
            height=30,
            fg_color=("#F1F5F9", "#1E2D4A"),
            text_color=("#0F172A", "#F8FAFC"),
            command=self.load_transactions,
        ).pack(side="right")

        # Filters Bar
        filter_bar = ctk.CTkFrame(
            pad,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=8,
        )
        filter_bar.pack(fill="x", pady=(0, 10))

        self.search_entry = ctk.CTkEntry(
            filter_bar,
            placeholder_text="🔍 Search txn code, bill #, patient, reference...",
            width=280,
            height=30,
        )
        self.search_entry.pack(side="left", padx=10, pady=8)
        self.search_entry.bind("<KeyRelease>", lambda e: self.load_transactions())

        ctk.CTkLabel(
            filter_bar,
            text="Status:",
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=("#64748B", "#94A3B8"),
        ).pack(side="left", padx=(10, 4))

        self.status_menu = ctk.CTkOptionMenu(
            filter_bar,
            values=["All", "Success", "Failed"],
            height=28,
            width=110,
            command=lambda v: self.load_transactions(),
        )
        self.status_menu.set("All")
        self.status_menu.pack(side="left", padx=(0, 10))

        # Table Shell
        table_frame = ctk.CTkFrame(
            pad,
            fg_color=("#FFFFFF", "#0F172A"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=8,
        )
        table_frame.pack(fill="both", expand=True, pady=(0, 10))

        # Table Headers
        hdr_row = ctk.CTkFrame(table_frame, height=32, fg_color=("#F1F5F9", "#16233E"))
        hdr_row.pack(fill="x")
        hdr_row.pack_propagate(False)

        col_defs = [
            ("Txn Code", 110),
            ("Bill #", 110),
            ("Patient", 130),
            ("Amount", 80),
            ("Method", 90),
            ("Status", 80),
            ("Recorded By", 130),
            ("Date", 90),
        ]
        for name, w in col_defs:
            ctk.CTkLabel(
                hdr_row,
                text=name,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=("#475569", "#94A3B8"),
                width=w,
                anchor="w",
                padx=6,
            ).pack(side="left")

        # Scrollable Rows
        self.rows_scroll = ctk.CTkScrollableFrame(table_frame, fg_color="transparent")
        self.rows_scroll.pack(fill="both", expand=True)

        # Footer
        footer = ctk.CTkFrame(pad, fg_color="transparent")
        footer.pack(fill="x", side="bottom")

        ctk.CTkButton(
            footer,
            text="Close",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#E2E8F0", "#334155"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#CBD5E1", "#475569"),
            width=90,
            height=32,
            command=self.destroy,
        ).pack(side="right")

    def load_transactions(self) -> None:
        """Fetch and render payment transactions."""
        for child in self.rows_scroll.winfo_children():
            child.destroy()

        search_q = self.search_entry.get().strip()
        status_filter = self.status_menu.get().strip()

        txns = get_payment_transactions(status=status_filter, search_query=search_q)

        if not txns:
            ctk.CTkLabel(
                self.rows_scroll,
                text="No payment transactions found matching criteria.",
                font=ctk.CTkFont(size=11),
                text_color=("#64748B", "#94A3B8"),
                pady=30,
            ).pack()
            return

        for i, t in enumerate(txns):
            bg = ("#F8FAFC", "#0C152B") if i % 2 == 0 else ("#FFFFFF", "#0F172A")
            row = ctk.CTkFrame(self.rows_scroll, height=36, fg_color=bg, corner_radius=0)
            row.pack(fill="x", pady=1)
            row.pack_propagate(False)

            ctk.CTkLabel(row, text=t["payment_code"], font=ctk.CTkFont(size=10, weight="bold"), text_color=("#0F172A", "#F8FAFC"), width=110, anchor="w", padx=6).pack(side="left")
            ctk.CTkLabel(row, text=t["bill_number"], font=ctk.CTkFont(size=10), text_color=("#0284C7", "#38BDF8"), width=110, anchor="w", padx=6).pack(side="left")

            pat = f"{t.get('pat_first_name', '')} {t.get('pat_last_name', '')}"
            ctk.CTkLabel(row, text=pat, font=ctk.CTkFont(size=10), text_color=("#475569", "#CBD5E1"), width=130, anchor="w", padx=6).pack(side="left")

            ctk.CTkLabel(row, text=f"Rs. {float(t['amount']):.0f}", font=ctk.CTkFont(size=10, weight="bold"), text_color=("#16A34A", "#22C55E"), width=80, anchor="w", padx=6).pack(side="left")
            ctk.CTkLabel(row, text=t["payment_method"], font=ctk.CTkFont(size=10), text_color=("#475569", "#CBD5E1"), width=90, anchor="w", padx=6).pack(side="left")

            st = t["status"]
            st_color = ("#15803D", "#34D399") if st == "Success" else ("#B91C1C", "#F87171")
            st_bg = ("#DCFCE7", "#064E3B") if st == "Success" else ("#FEE2E2", "#450A0A")
            s_box = ctk.CTkFrame(row, width=80, fg_color="transparent")
            s_box.pack(side="left")
            ctk.CTkLabel(s_box, text=st, font=ctk.CTkFont(size=9, weight="bold"), fg_color=st_bg, text_color=st_color, corner_radius=4, padx=6, pady=2).pack(side="left")

            ctk.CTkLabel(row, text=t.get("recorded_by", "")[:18], font=ctk.CTkFont(size=9), text_color=("#64748B", "#94A3B8"), width=130, anchor="w", padx=6).pack(side="left")
            ctk.CTkLabel(row, text=str(t["payment_date"])[:10], font=ctk.CTkFont(size=9), text_color=("#64748B", "#94A3B8"), width=90, anchor="w", padx=6).pack(side="left")


class ReceiptViewModal(ctk.CTkToplevel):
    """Modal displaying official consultation receipt with export and copy actions."""

    def __init__(self, master, receipt_number: str, **kwargs):
        super().__init__(master, **kwargs)
        self.receipt_number = receipt_number.strip()
        self.receipt_text = generate_receipt_text(self.receipt_number)

        self.title(f"Official Receipt — {self.receipt_number}")
        self.resizable(False, False)
        self.transient(master)
        self.grab_set()

        self._apply_responsive_geometry(master)
        self._build_ui()

        self.bind("<Escape>", lambda event: self.destroy())
        self.lift()
        self.focus_force()

    def _apply_responsive_geometry(self, master) -> None:
        """Center receipt modal adaptively."""
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        scaling = self._get_window_scaling()

        target_w = min(620, int((sw - 40) / scaling))
        target_h = min(540, int((sh - 80) / scaling))

        phys_w = int(target_w * scaling)
        phys_h = int(target_h * scaling)
        pos_x = max(0, (sw - phys_w) // 2)
        pos_y = max(10, (sh - phys_h) // 2 - 20)

        self.geometry(f"{target_w}x{target_h}+{pos_x}+{pos_y}")

    def _build_ui(self) -> None:
        """Construct receipt slip layout."""
        pad = ctk.CTkFrame(self, fg_color="transparent")
        pad.pack(fill="both", expand=True, padx=20, pady=16)

        # Header
        hdr = ctk.CTkFrame(pad, fg_color="transparent")
        hdr.pack(fill="x", pady=(0, 8))

        ctk.CTkLabel(
            hdr,
            text=f"🧾 Consultation Receipt: {self.receipt_number}",
            font=ctk.CTkFont(size=15, weight="bold"),
            text_color=("#0284C7", "#06B6D4"),
            anchor="w",
        ).pack(side="left")

        # Text Display Box
        self.text_box = ctk.CTkTextbox(
            pad,
            font=ctk.CTkFont(family="Consolas", size=11),
            fg_color=("#FFFFFF", "#0A0F1D"),
            border_width=1,
            border_color=("#CBD5E1", "#1E2D4A"),
            corner_radius=8,
        )
        self.text_box.pack(fill="both", expand=True, pady=(0, 12))
        self.text_box.insert("1.0", self.receipt_text)
        self.text_box.configure(state="disabled")

        # Notification banner
        self.status_lbl = ctk.CTkLabel(pad, text="", font=ctk.CTkFont(size=11), text_color=("#16A34A", "#22C55E"), anchor="w")
        self.status_lbl.pack(fill="x", pady=(0, 6))

        # Footer Actions
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
            height=34,
            command=self.destroy,
        )
        close_btn.pack(side="right", padx=(8, 0))

        copy_btn = ctk.CTkButton(
            footer,
            text="📋 Copy Slip",
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color=("#F1F5F9", "#1E2D4A"),
            text_color=("#0F172A", "#F8FAFC"),
            hover_color=("#E2E8F0", "#2B3E63"),
            border_width=1,
            border_color=("#CBD5E1", "#33456B"),
            height=34,
            command=self._copy_to_clipboard,
        )
        copy_btn.pack(side="right")

    def _copy_to_clipboard(self) -> None:
        """Copy formatted receipt text to system clipboard."""
        try:
            self.clipboard_clear()
            self.clipboard_append(self.receipt_text)
            self.status_lbl.configure(text="✓ Receipt copied to clipboard!")
            self.after(3000, lambda: self.status_lbl.configure(text=""))
        except Exception as e:
            self.status_lbl.configure(text=f"Failed to copy: {e}")
