# Hospital Management System — Q08: Improve User Satisfaction

**Course:** BBAT104 — Fundamentals of Total Quality Management (TQM)  
**Student Name:** Deepak Joshi  
**Branch:** Computer Science & Engineering (B.Tech CSE)  
**Section:** B  
**Academic Focus:** Quality Improvement & User Satisfaction Engineering (Project Track Q08)

---

## 🏥 Project Overview

The **Hospital Management System (HMS) — Q08** is a desktop application engineered to resolve user satisfaction and cognitive friction bottlenecks in healthcare administrative workflows. Applying Total Quality Management (TQM) methodologies—specifically **DMAIC (Define, Measure, Analyze, Improve, Control)**, **Pareto Analysis (80/20 Rule)**, and **Failure Mode & Effects Analysis (FMEA)**—the system re-architects outpatient scheduling, medical staff tracking, and patient records to dramatically improve user satisfaction metrics (CSAT / SUS).

### 🎯 Mandatory Q08 Features
1. **Interactive Dashboard:** Real-time KPI summaries, today's schedule, and fast-action command cards.
2. **Visual Reports:** Embedded Matplotlib analytics featuring appointment volume trends, departmental workload breakdown, customer satisfaction distribution, and a live Pareto 80/20 defect chart.
3. **Light/Dark Theme Toggle:** Seamless runtime appearance switcher with persistent user preference storage and theme-adaptive chart styling.
4. **Keyboard Shortcuts:** Global hotkey dispatcher (`Ctrl+1`..`6`, `Ctrl+N`, `Ctrl+T`, `Ctrl+F`, `F1`) designed to reduce user task completion time and error rates.
5. **User Profile Settings:** Customization panel for interface scaling, operator profile, and database management.

### 🧩 Core Clinical Modules
- **Patient Management:** Full CRUD operations with medical demographics and search filters.
- **Doctor Management:** Full CRUD operations with departmental categorization and availability tracking.
- **Appointment Scheduling:** Full CRUD operations with collision prevention and satisfaction feedback collection.

---

## 🛠️ Technology Stack
- **Programming Language:** Python 3 (3.12+)
- **User Interface:** [CustomTkinter](https://customtkinter.tomschimansky.com/) (modern, high-DPI desktop GUI)
- **Database Engine:** SQLite 3 (ACID-compliant relational database with foreign key constraints)
- **Data Visualization:** Matplotlib (embedded dynamic charts via `FigureCanvasTkAgg`)
- **Version Control:** Git & GitHub

---

## 📊 TQM Quality Deliverables Included
All formal coursework deliverables are maintained in `tqm_docs/`:
- `SRS.md`: IEEE 830 Software Requirements Specification
- `ARCHITECTURE_FLOWCHART.md`: Layered system architecture & workflows
- `CTQ_TREE.md`: Critical-To-Quality Tree translating Voice of Customer (VoC) to measurable metrics
- `SIPOC.md`: High-level process mapping (Suppliers, Inputs, Process, Outputs, Customers)
- `FMEA_RPN.md`: Failure Mode and Effects Analysis with pre- and post-mitigation RPN scores
- `DEFECT_CHECKSHEET.md`: Operational defect frequency collection sheet
- `PARETO_ANALYSIS.md`: 80/20 statistical analysis on usability pain points
- `FISHBONE_DIAGRAM.md`: Ishikawa 6M root cause analysis diagram
- `PDCA_LOG.md`: Plan-Do-Check-Act iterative quality improvement log
- `USER_MANUAL.md`: User manual with keyboard shortcuts cheat sheet

---

## 🚀 Quick Start Guide

### Prerequisites
- Python 3.10+ installed on your system.

### Installation
1. Clone this repository:
   ```bash
   git clone https://github.com/deepakjoshi-cse/Hospital_TQM_Q08.git
   cd Hospital_TQM_Q08
   ```
2. Create and activate a virtual environment:
   ```bash
   python -m venv .venv
   # Windows:
   .venv\Scripts\activate
   # Linux/macOS:
   source .venv/bin/activate
   ```
3. Install required packages:
   ```bash
   pip install -r requirements.txt
   ```
4. Run the application:
   ```bash
   python run.py
   ```

### Running Test Suite
Execute the comprehensive automated test suite (no GUI display required):
```bash
python -m unittest discover -s tests -p "test_*.py" -v
```
