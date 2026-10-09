"""Unit tests verifying fictional demo seed data integrity, counts, and referential validity."""
import os
import tempfile
import unittest

from database.connection import get_db_connection
from database.seed_data import seed_database


class TestSeedDataIntegrity(unittest.TestCase):
    """Verify seed data generates expected entities with zero relational integrity violations."""

    def setUp(self):
        """Seed a clean temporary database."""
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_seed.db")
        seed_database(self.db_path)

    def tearDown(self):
        """Clean up temporary directory."""
        self.temp_dir.cleanup()

    def test_user_profile_seeded(self):
        """Verify admin user profile is created with correct defaults."""
        with get_db_connection(self.db_path) as conn:
            row = conn.execute("SELECT * FROM user_profile WHERE username = 'deepak_admin';").fetchone()
            self.assertIsNotNone(row)
            self.assertEqual(row["full_name"], "Deepak Joshi")
            self.assertEqual(row["theme_preference"], "Dark")
            self.assertEqual(row["scaling_factor"], "100%")

    def test_entity_record_counts(self):
        """Verify minimum required counts for demo data entities."""
        with get_db_connection(self.db_path) as conn:
            doctor_count = conn.execute("SELECT COUNT(*) as c FROM doctors;").fetchone()["c"]
            patient_count = conn.execute("SELECT COUNT(*) as c FROM patients;").fetchone()["c"]
            appointment_count = conn.execute("SELECT COUNT(*) as c FROM appointments;").fetchone()["c"]
            defect_count = conn.execute("SELECT COUNT(*) as c FROM tqm_defect_logs;").fetchone()["c"]
            fmea_count = conn.execute("SELECT COUNT(*) as c FROM tqm_fmea_records;").fetchone()["c"]

            self.assertEqual(doctor_count, 10, "Expected exactly 10 demo doctors.")
            self.assertEqual(patient_count, 25, "Expected exactly 25 demo patients.")
            self.assertEqual(appointment_count, 42, "Expected exactly 42 demo appointments.")
            self.assertEqual(defect_count, 21, "Expected exactly 21 TQM defect logs.")
            self.assertEqual(fmea_count, 8, "Expected exactly 8 FMEA records.")

    def test_foreign_key_referential_integrity(self):
        """Ensure no orphaned appointments exist in the seeded database."""
        with get_db_connection(self.db_path) as conn:
            orphaned_patients = conn.execute(
                """
                SELECT a.id FROM appointments a
                LEFT JOIN patients p ON a.patient_id = p.id
                WHERE p.id IS NULL;
                """
            ).fetchall()
            self.assertEqual(len(orphaned_patients), 0, "Found appointments with invalid patient_id!")

            orphaned_doctors = conn.execute(
                """
                SELECT a.id FROM appointments a
                LEFT JOIN doctors d ON a.doctor_id = d.id
                WHERE d.id IS NULL;
                """
            ).fetchall()
            self.assertEqual(len(orphaned_doctors), 0, "Found appointments with invalid doctor_id!")

    def test_fmea_mathematical_consistency(self):
        """Verify RPN calculations in FMEA table match S * O * D."""
        with get_db_connection(self.db_path) as conn:
            rows = conn.execute("SELECT severity_s, occurrence_o, detection_d, rpn, target_severity, target_occurrence, target_detection, target_rpn FROM tqm_fmea_records;").fetchall()
            for r in rows:
                calculated_rpn = r["severity_s"] * r["occurrence_o"] * r["detection_d"]
                self.assertEqual(r["rpn"], calculated_rpn, f"RPN mismatch: {r['rpn']} != {calculated_rpn}")
                calculated_target = r["target_severity"] * r["target_occurrence"] * r["target_detection"]
                self.assertEqual(r["target_rpn"], calculated_target, f"Target RPN mismatch: {r['target_rpn']} != {calculated_target}")
                self.assertLess(r["target_rpn"], r["rpn"], "Mitigated RPN must be lower than original RPN!")


if __name__ == "__main__":
    unittest.main()
