"""Interactive modal dialogs for Billing, Payment Recording, and Receipt viewing/export.
Engineered with responsive geometry, input validation, and receipt rendering.
"""
from typing import Callable, Dict, Optional
import customtkinter as ctk

from config.constants import PAYMENT_METHODS
from services.billing_service import (
    generate_receipt_text,
    get_bill_by_id,
    get_receipt_by_number,
    record_payment,
)


class RecordPaymentModal(ctk.CTkToplevel):
    """Modal dialog to collect payment against an invoice and generate receipt."""

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

        if not self.bill:
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
        target_h = min(460, int((sh - 80) / scaling))

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
            text="Record cash, card, UPI, or insurance payment and issue an official receipt.",
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
        self.method_menu.set("UPI")
        self.method_menu.grid(row=1, column=1, padx=4, pady=(0, 6), sticky="ew")

        # Reference Number
        ctk.CTkLabel(form, text="Reference / Transaction ID", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=2, column=0, padx=4, pady=(2, 1), sticky="w")
        self.ref_entry = ctk.CTkEntry(form, placeholder_text="e.g. UPI-REF-4821 or Cash receipt", height=32)
        self.ref_entry.grid(row=3, column=0, padx=4, pady=(0, 6), sticky="ew")

        # Recorded by
        ctk.CTkLabel(form, text="Received / Recorded By", font=ctk.CTkFont(size=11, weight="bold"), text_color=("#475569", "#94A3B8"), anchor="w").grid(row=2, column=1, padx=4, pady=(2, 1), sticky="w")
        self.cashier_entry = ctk.CTkEntry(form, height=32)
        self.cashier_entry.insert(0, "Reception Desk")
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
        cashier = self.cashier_entry.get().strip() or "Front Desk"

        self.submit_btn.configure(state="disabled", text="Processing...")
        self.update_idletasks()

        success, message, receipt_obj = record_payment(
            bill_id=self.bill_id,
            amount=amt,
            payment_method=method,
            reference_number=ref_no,
            recorded_by=cashier,
        )

        if success:
            master = self.master
            on_succ = self.on_success
            self.destroy()
            if on_succ and receipt_obj:
                on_succ(receipt_obj)
            # Automatically show receipt modal
            if receipt_obj and "receipt_number" in receipt_obj:
                try:
                    ReceiptViewModal(master, receipt_number=receipt_obj["receipt_number"])
                except Exception as ex:
                    print(f"Error opening receipt modal: {ex}")
        else:
            self.err_lbl.configure(text=message)
            self.submit_btn.configure(state="normal", text="💳 Record Payment & Issue Receipt")


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
