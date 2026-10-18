"""TQM (Total Quality Management) service for Hospital Management System — Q08.
Provides calculations, aggregations, and data management for FMEA (RPN),
SIPOC process mapping, CTQ trees, Defect Checksheets, Pareto analysis,
Fishbone root-cause categorization, and PDCA continuous improvement cycles.
"""
import csv
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from database.connection import get_db_connection, get_db_cursor

DEFECT_SEVERITIES = ["Critical", "Major", "Minor"]
DEFECT_STATUSES = ["Logged", "In Analysis", "Resolved"]
DEFECT_CATEGORIES = [
    "Appointment Booking Error",
    "Confusing Form Layout",
    "UI Lag / Latency",
    "Missing Feedback Toast",
    "Doctor Schedule Overlap",
    "Search Filter Inaccuracy",
    "Theme / Visual Fatigue",
]


# =============================================================================
# 1. FMEA (Failure Mode and Effects Analysis) & RPN Calculation
# =============================================================================
def calculate_rpn(severity: int, occurrence: int, detection: int) -> int:
    """Calculate Risk Priority Number (RPN) = Severity (S) x Occurrence (O) x Detection (D).
    
    All inputs must be integers between 1 and 10.
    """
    for val, name in [(severity, "Severity"), (occurrence, "Occurrence"), (detection, "Detection")]:
        if not isinstance(val, int) or val < 1 or val > 10:
            raise ValueError(f"{name} must be an integer between 1 and 10.")
    return severity * occurrence * detection


def get_fmea_records() -> List[Dict[str, Any]]:
    """Retrieve distinct FMEA risk assessment records ordered by initial RPN descending."""
    results = []
    try:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT MIN(id) as id, process_step, failure_mode, failure_effect, potential_cause,
                       severity_s, occurrence_o, detection_d, rpn, mitigation_action,
                       target_severity, target_occurrence, target_detection, target_rpn
                FROM tqm_fmea_records
                GROUP BY process_step, failure_mode
                ORDER BY rpn DESC;
                """
            ).fetchall()
            for r in rows:
                item = dict(r)
                # Compute risk reduction percentage: ((initial - target) / initial) * 100
                initial_rpn = item["rpn"]
                target_rpn = item["target_rpn"]
                reduction_pct = round(((initial_rpn - target_rpn) / initial_rpn) * 100, 1) if initial_rpn > 0 else 0.0
                item["reduction_pct"] = reduction_pct
                results.append(item)
    except Exception as e:
        print(f"Error querying FMEA records: {e}")
    return results


def validate_fmea_data(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate FMEA input record."""
    step = str(data.get("process_step", "")).strip()
    if not step or len(step) < 2:
        return False, "Process Step is required (e.g., 'Slot Reservation')."

    mode = str(data.get("failure_mode", "")).strip()
    if not mode or len(mode) < 3:
        return False, "Failure Mode description is required."

    action = str(data.get("mitigation_action", "")).strip()
    if not action or len(action) < 3:
        return False, "Mitigation Action description is required."

    for key, name in [
        ("severity_s", "Severity (S)"),
        ("occurrence_o", "Occurrence (O)"),
        ("detection_d", "Detection (D)"),
        ("target_severity", "Target Severity"),
        ("target_occurrence", "Target Occurrence"),
        ("target_detection", "Target Detection"),
    ]:
        val = data.get(key)
        try:
            val_int = int(val)
            if val_int < 1 or val_int > 10:
                return False, f"{name} rating must be an integer between 1 and 10."
        except (ValueError, TypeError):
            return False, f"{name} must be a valid integer between 1 and 10."

    initial_rpn = int(data["severity_s"]) * int(data["occurrence_o"]) * int(data["detection_d"])
    target_rpn = int(data["target_severity"]) * int(data["target_occurrence"]) * int(data["target_detection"])
    if target_rpn > initial_rpn:
        return (
            False,
            f"Target RPN ({target_rpn}) cannot exceed Initial RPN ({initial_rpn}). "
            "Mitigation actions must reduce or maintain risk level.",
        )

    return True, ""


def check_fmea_duplicate(process_step: str, failure_mode: str) -> bool:
    """Check if an FMEA failure mode already exists for a given process step (case-insensitive)."""
    step = str(process_step or "").strip().lower()
    mode = str(failure_mode or "").strip().lower()
    if not step or not mode:
        return False
    try:
        with get_db_connection() as conn:
            row = conn.execute(
                """
                SELECT id FROM tqm_fmea_records
                WHERE LOWER(TRIM(process_step)) = ? AND LOWER(TRIM(failure_mode)) = ?
                LIMIT 1;
                """,
                (step, mode),
            ).fetchone()
            return row is not None
    except Exception as e:
        print(f"Error checking FMEA duplicate: {e}")
        return False


def get_fmea_summary_stats() -> Dict[str, Any]:
    """Calculate summary statistics for distinct FMEA records in SQLite database.

    Returns:
        dict containing:
            - 'total_failure_modes': count of distinct failure modes
            - 'avg_initial_rpn': average initial RPN across distinct failure modes
            - 'avg_target_rpn': average target RPN across distinct failure modes
            - 'overall_reduction_pct': overall percentage risk reduction
            - 'high_risk_count': count of distinct failure modes with RPN >= 200
    """
    stats = {
        "total_failure_modes": 0,
        "avg_initial_rpn": 0.0,
        "avg_target_rpn": 0.0,
        "overall_reduction_pct": 0.0,
        "high_risk_count": 0,
    }
    try:
        with get_db_connection() as conn:
            row = conn.execute(
                """
                WITH distinct_modes AS (
                    SELECT process_step, failure_mode,
                           MAX(rpn) as rpn,
                           MAX(target_rpn) as target_rpn
                    FROM tqm_fmea_records
                    GROUP BY process_step, failure_mode
                )
                SELECT COUNT(*) as total,
                       AVG(rpn) as avg_init,
                       AVG(target_rpn) as avg_target,
                       SUM(CASE WHEN rpn >= 200 THEN 1 ELSE 0 END) as high_risk
                FROM distinct_modes;
                """
            ).fetchone()
            if row and row["total"] and row["total"] > 0:
                stats["total_failure_modes"] = int(row["total"])
                avg_init = round(float(row["avg_init"] or 0), 1)
                avg_target = round(float(row["avg_target"] or 0), 1)
                stats["avg_initial_rpn"] = avg_init
                stats["avg_target_rpn"] = avg_target
                stats["high_risk_count"] = int(row["high_risk"] or 0)
                if avg_init > 0:
                    stats["overall_reduction_pct"] = round(
                        ((avg_init - avg_target) / avg_init) * 100, 1
                    )
    except Exception as e:
        print(f"Error calculating FMEA summary stats: {e}")
    return stats


def add_fmea_record(data: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
    """Validate and insert a new FMEA record into SQLite database, preventing duplicate entries."""
    is_valid, msg = validate_fmea_data(data)
    if not is_valid:
        return False, msg, None

    if check_fmea_duplicate(data["process_step"], data["failure_mode"]):
        return (
            False,
            f"Failure mode '{data['failure_mode'].strip()}' already exists for step '{data['process_step'].strip()}'. Duplicate entries are not permitted.",
            None,
        )

    try:
        s = int(data["severity_s"])
        o = int(data["occurrence_o"])
        d = int(data["detection_d"])
        rpn = calculate_rpn(s, o, d)

        ts = int(data["target_severity"])
        to = int(data["target_occurrence"])
        td = int(data["target_detection"])
        target_rpn = calculate_rpn(ts, to, td)

        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO tqm_fmea_records (
                    process_step, failure_mode, failure_effect, potential_cause,
                    severity_s, occurrence_o, detection_d, rpn, mitigation_action,
                    target_severity, target_occurrence, target_detection, target_rpn
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    data["process_step"].strip(),
                    data["failure_mode"].strip(),
                    str(data.get("failure_effect", "")).strip(),
                    str(data.get("potential_cause", "")).strip(),
                    s, o, d, rpn,
                    data["mitigation_action"].strip(),
                    ts, to, td, target_rpn,
                ),
            )
            new_id = cursor.lastrowid
            return True, f"FMEA failure mode logged successfully (RPN: {rpn} -> Target: {target_rpn}).", new_id
    except Exception as e:
        return False, f"Database error adding FMEA record: {e}", None


# =============================================================================
# 2. Defect Checksheet Logging & Pareto Analysis
# =============================================================================
def get_defect_logs(
    category: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Query logged defects with optional category, severity, and status filtering."""
    results = []
    try:
        with get_db_connection() as conn:
            sql = "SELECT id, defect_code, category, severity, description, reported_by, resolution_status, created_at, resolved_at FROM tqm_defect_logs WHERE 1=1"
            params = []
            if category and category != "All Categories":
                sql += " AND category = ?"
                params.append(category)
            if severity and severity != "All Severities":
                sql += " AND severity = ?"
                params.append(severity)
            if status and status != "All Statuses":
                sql += " AND resolution_status = ?"
                params.append(status)
            sql += " ORDER BY id DESC;"
            rows = conn.execute(sql, tuple(params)).fetchall()
            results = [dict(r) for r in rows]
    except Exception as e:
        print(f"Error querying defect logs: {e}")
    return results


def export_defects_to_csv(
    filepath: str,
    category: Optional[str] = None,
    severity: Optional[str] = None,
    status: Optional[str] = None,
) -> Tuple[bool, str, int]:
    """Export filtered defect logs to a CSV file.

    Returns:
        (success, message, record_count)
    """
    try:
        defects = get_defect_logs(category=category, severity=severity, status=status)
        fieldnames = [
            "Defect Code",
            "Category",
            "Severity",
            "Description",
            "Reported By",
            "Resolution Status",
            "Logged At",
            "Resolved At",
        ]
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for d in defects:
                writer.writerow({
                    "Defect Code": d.get("defect_code", ""),
                    "Category": d.get("category", ""),
                    "Severity": d.get("severity", ""),
                    "Description": d.get("description", ""),
                    "Reported By": d.get("reported_by", ""),
                    "Resolution Status": d.get("resolution_status", ""),
                    "Logged At": d.get("created_at", ""),
                    "Resolved At": d.get("resolved_at", "") or "N/A",
                })
        return True, f"Successfully exported {len(defects)} defect logs to CSV.", len(defects)
    except Exception as e:
        return False, f"Failed to export defects to CSV: {str(e)}", 0


def get_defect_pareto_data() -> Dict[str, Any]:
    """Calculate Pareto distribution (80/20 rule) metrics for defect categories.
    
    Returns:
        dict containing:
            - 'categories': sorted list of category names (descending frequency)
            - 'counts': sorted list of integer counts
            - 'cumulative_pct': cumulative percentage list (0 to 100%)
            - 'total_defects': total number of logged defects
            - 'vital_few': categories contributing to the first 80% of issues
    """
    categories = []
    counts = []
    total = 0

    try:
        with get_db_connection() as conn:
            rows = conn.execute(
                """
                SELECT category, COUNT(*) as c
                FROM tqm_defect_logs
                GROUP BY category
                ORDER BY c DESC;
                """
            ).fetchall()
            for r in rows:
                categories.append(r["category"])
                counts.append(r["c"])
                total += r["c"]
    except Exception as e:
        print(f"Error calculating Pareto data: {e}")

    cumulative_pct = []
    running_sum = 0
    vital_few = []

    for cat, cnt in zip(categories, counts):
        running_sum += cnt
        pct = round((running_sum / total) * 100, 1) if total > 0 else 0.0
        cumulative_pct.append(pct)
        if pct <= 80.0 or (not vital_few and pct > 80.0):
            vital_few.append(cat)

    return {
        "categories": categories,
        "counts": counts,
        "cumulative_pct": cumulative_pct,
        "total_defects": total,
        "vital_few": vital_few,
    }


def validate_defect_data(data: Dict[str, Any]) -> Tuple[bool, str]:
    """Validate defect incident logging data."""
    cat = str(data.get("category", "")).strip()
    if not cat:
        return False, "Defect Category is required."

    sev = str(data.get("severity", "Major")).strip()
    if sev not in DEFECT_SEVERITIES:
        return False, f"Severity must be one of: {', '.join(DEFECT_SEVERITIES)}"

    desc = str(data.get("description", "")).strip()
    if not desc or len(desc) < 5:
        return False, "Description must be at least 5 characters long."

    rep = str(data.get("reported_by", "")).strip()
    if not rep or len(rep) < 2:
        return False, "Reported By operator name is required."

    status = str(data.get("resolution_status", "Logged")).strip()
    if status not in DEFECT_STATUSES:
        return False, f"Status must be one of: {', '.join(DEFECT_STATUSES)}"

    return True, ""


def get_next_defect_code() -> str:
    """Generate next sequential defect code (DEF-XXXX)."""
    try:
        with get_db_connection() as conn:
            row = conn.execute(
                "SELECT defect_code FROM tqm_defect_logs WHERE defect_code LIKE 'DEF-%' ORDER BY id DESC LIMIT 1;"
            ).fetchone()
            if row and row["defect_code"]:
                last_code = row["defect_code"]
                parts = last_code.split("-")
                if len(parts) == 2 and parts[1].isdigit():
                    next_num = int(parts[1]) + 1
                    return f"DEF-{next_num}"
    except Exception:
        pass
    return "DEF-4022"


def log_defect(data: Dict[str, Any]) -> Tuple[bool, str, Optional[int]]:
    """Validate and insert a new quality defect into SQLite database."""
    is_valid, msg = validate_defect_data(data)
    if not is_valid:
        return False, msg, None

    code = str(data.get("defect_code", "")).strip() or get_next_defect_code()

    try:
        resolved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if data.get("resolution_status") == "Resolved" else None
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                """
                INSERT INTO tqm_defect_logs (
                    defect_code, category, severity, description, reported_by, resolution_status, resolved_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?);
                """,
                (
                    code,
                    data["category"].strip(),
                    data["severity"].strip(),
                    data["description"].strip(),
                    data["reported_by"].strip(),
                    data.get("resolution_status", "Logged").strip(),
                    resolved_at,
                ),
            )
            new_id = cursor.lastrowid
            return True, f"Defect incident '{code}' logged successfully in checksheet.", new_id
    except Exception as e:
        return False, f"Database error logging defect: {e}", None


def update_defect_status(defect_id: int, new_status: str) -> Tuple[bool, str]:
    """Update defect incident resolution status."""
    if new_status not in DEFECT_STATUSES:
        return False, f"Status must be one of: {', '.join(DEFECT_STATUSES)}"

    try:
        resolved_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S") if new_status == "Resolved" else None
        with get_db_cursor() as (conn, cursor):
            cursor.execute(
                "UPDATE tqm_defect_logs SET resolution_status = ?, resolved_at = ? WHERE id = ?;",
                (new_status, resolved_at, defect_id),
            )
            return True, f"Defect status updated to '{new_status}'."
    except Exception as e:
        return False, f"Database error updating defect status: {e}"


# =============================================================================
# 3. SIPOC Framework (Hospital Appointment Process)
# =============================================================================
def get_sipoc_data() -> Dict[str, List[str]]:
    """Return structured SIPOC mapping for outpatient appointment booking."""
    return {
        "Suppliers": [
            "Patients & Families (Demographics, schedule preferences)",
            "Referring Doctors / Clinics (Clinical referrals & test notes)",
            "Medical Specialists / Doctors (Consultation availability roster)",
            "Hospital Front Desk & IT Staff (System operators, credentialing)",
            "Regulatory & Accreditation Bodies (NABH / TQM Quality standards)",
        ],
        "Inputs": [
            "Patient Full Name, Date of Birth, Gender, Blood Group",
            "Contact Phone & Emergency Contact Number",
            "Doctor Specialization & Roster Shift Times",
            "Reason for Outpatient Consultation & Urgency Level",
            "Preferred Appointment Date & Clinic Time Slot",
        ],
        "Process": [
            "Step 1: Patient Identification & Demographics Verification",
            "Step 2: Specialty Selection & Doctor Availability Check",
            "Step 3: Slot Collision Prevention & Real-time Roster Lock",
            "Step 4: Clinical Consultation Details & Priority Classification",
            "Step 5: Record Persistence & Digital Appointment Receipt Generation",
        ],
        "Outputs": [
            "Guaranteed Non-Overlapping Appointment Booking (APT-XXXX)",
            "Physician Outpatient Daily Consultation Roster",
            "Patient SMS / Verbal Consultation Schedule Confirmation",
            "Verified Patient Demographic Record in Hospital SQLite DB",
            "TQM Defect-Free Consultation Slot Entry",
        ],
        "Customers": [
            "Outpatient Clinic Visitors (Punctual, zero-wait access)",
            "Consulting Doctors (Evenly distributed patient workload)",
            "Nursing & Clinical Triage Staff (Organized queue visibility)",
            "Hospital Operations & Administration (TQM efficiency metrics)",
            "Billing & Pharmacy Units (Synchronized clinical patient data)",
        ],
    }


# =============================================================================
# 4. CTQ Tree (Critical to Quality)
# =============================================================================
def get_ctq_tree_data() -> List[Dict[str, Any]]:
    """Return Critical to Quality (CTQ) tree linking Patient Needs to Measurable Specs."""
    return [
        {
            "need": "Fast & Effortless Outpatient Booking",
            "driver": "Booking Workflow Speed & Usability",
            "ctq": "Total time to book an appointment <= 60 seconds",
            "metric": "Registration cycle time",
            "target": "< 60 seconds / patient",
            "status": "Achieved (Streamlined 5-field modal + responsive layout)",
        },
        {
            "need": "Guaranteed Doctor Availability (Zero Collisions)",
            "driver": "Scheduling Accuracy & Reliability",
            "ctq": "Zero double-booked consultations for same doctor & slot",
            "metric": "Slot collision rate",
            "target": "0.0% double-bookings",
            "status": "Achieved (SQLite partial unique index + validation guard)",
        },
        {
            "need": "No Frustrating Clinic Visit When Doctor is On Leave",
            "driver": "Physician Roster Synchronization",
            "ctq": "100% detection of on-leave physicians prior to confirmation",
            "metric": "On-leave booking prevention",
            "target": "100% blocked",
            "status": "Achieved (Doctor dropdown tags '[On Leave]' + backend blocker)",
        },
        {
            "need": "Reduced Visual Eye Fatigue for Operators",
            "driver": "Operator Interface Ergonomics",
            "ctq": "High-contrast night-shift mode reducing screen glare",
            "metric": "Theme toggle availability & contrast ratio",
            "target": ">= 4.5:1 contrast in Dark Mode",
            "status": "Achieved (Real-time Dark/Light theme toggle + Ctrl+T hotkey)",
        },
        {
            "need": "High Clinical User Satisfaction (CSAT)",
            "driver": "Overall Service Experience",
            "ctq": "Average Patient Satisfaction Score >= 4.0 / 5.0 stars",
            "metric": "CSAT rating average",
            "target": ">= 4.00 / 5.00 ⭐",
            "status": "Achieved (Current CSAT: 4.45 / 5.00 ⭐ | 95.0% Positive)",
        },
    ]


# =============================================================================
# 5. Fishbone / Ishikawa Root-Cause Analysis
# =============================================================================
def get_fishbone_data() -> Dict[str, Any]:
    """Return Ishikawa 4P/6M root-cause structure for appointment scheduling defects."""
    return {
        "problem": "Outpatient Booking Delays & Slot Collisions (Pre-Improvement)",
        "branches": {
            "People (Staff & Patients)": [
                "Front-desk operator fatigue during peak morning rush (8-10 AM)",
                "Lack of standardized operator keyboard navigation training",
                "Patient phone number transcription typos on paper slips",
            ],
            "Process (Workflow Methods)": [
                "Legacy paper registers lacked concurrent slot locking",
                "No automated check for doctor leave status before booking",
                "Absence of two-step confirmation on record deletion",
            ],
            "Technology & Tools (Software / DB)": [
                "Unindexed database queries caused search lag on large rosters",
                "Absence of database-enforced partial unique collision constraints",
                "Monochromatic bright UI caused eye strain on 12-hour shifts",
            ],
            "Measurement & Environment": [
                "Ambiguous date format entries (DD/MM vs MM/DD confusion)",
                "No real-time feedback toast on successful background saves",
                "Voice of customer defect tally was not systematically tracked",
            ],
        },
        "root_cause_summary": (
            "Primary Root Cause: Legacy system lacked atomic database constraint guards "
            "and operator-friendly keyboard entry shortcuts, leading to race-condition double bookings "
            "and slow data entry during peak outpatient check-in hours."
        ),
    }


# =============================================================================
# 6. PDCA Continuous Improvement Cycles
# =============================================================================
def get_pdca_cycles_data() -> List[Dict[str, Any]]:
    """Return PDCA continuous improvement cycle stages."""
    return [
        {
            "stage": "PLAN",
            "phase": "Problem Definition & Quality Baseline",
            "description": (
                "Identified key outpatient dissatisfaction drivers from Voice of Customer checksheets: "
                "Appointment double bookings (RPN 384), search lag, and visual fatigue during late shifts. "
                "Target: Zero booking collisions, registration time < 60s, CSAT >= 4.2."
            ),
            "deliverables": "FMEA Matrix, SIPOC Diagram, CTQ Tree, Defect Checksheet.",
            "status": "Completed",
        },
        {
            "stage": "DO",
            "phase": "Solution Implementation & Tooling",
            "description": (
                "Implemented modern CustomTkinter GUI with screen-adaptive layouts, "
                "SQLite transactional connection manager, partial unique collision index, "
                "doctor on-leave protection, and global keyboard shortcuts (Ctrl+1..7, Ctrl+T, F1)."
            ),
            "deliverables": "Appointments CRUD Module, Doctors CRUD, Patients CRUD, Theme Engine.",
            "status": "Completed",
        },
        {
            "stage": "CHECK",
            "phase": "Verification & Quantitative Analytics",
            "description": (
                "Executed comprehensive 32+ automated tests covering CRUD operations, "
                "collision safety, foreign-key cascade integrity, and Matplotlib visual analytics. "
                "Verified: Double booking collision rate dropped from 15% to 0.0%, CSAT achieved 4.45/5.0."
            ),
            "deliverables": "Automated Unit Tests, Pareto Distribution Chart, CSAT Analytics.",
            "status": "Verified (32/32 tests passing)",
        },
        {
            "stage": "ACT",
            "phase": "Standardization & Continuous Improvement",
            "description": (
                "Standardized modular architecture across all clinic screens. "
                "Documented BBAT104 TQM Coursework toolkit with interactive FMEA calculator, "
                "incident logger, and real-time database safeguards to prevent process backsliding."
            ),
            "deliverables": "TQM Quality Toolkit View, Standard Operating Procedures, Final SRS Package.",
            "status": "Standardized",
        },
    ]
