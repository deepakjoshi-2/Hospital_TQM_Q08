"""Entry point for Hospital Management System — Q08.
Student: Deepak Joshi | B.Tech CSE (Section B)
Course: BBAT104 Fundamentals of Total Quality Management
"""
import sys
from pathlib import Path

# Ensure project root is in sys.path
BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from ui.app import main

if __name__ == "__main__":
    main()
