import unittest

from scripts.mapping_guard import MappingValidationError, resolve_mapping_indices


class TxMiniL1IdentityTests(unittest.TestCase):
    def _headers(self, columns):
        width = max(columns) + 1
        rows = [[""] * width for _ in range(4)]
        for index, values in columns.items():
            for row_index, value in enumerate(values):
                rows[row_index][index] = value
        return rows

    def test_resolves_l1_to_qehs_l1_approved_actual_end(self):
        headers = self._headers(
            {
                136: (
                    "WPC000011222|AC0000111592|actual_end_date",
                    "Q&EHS",
                    "L1 Approved",
                    "actual end time",
                ),
                210: (
                    "WPC000014000|AC0000111700|actual_end_date",
                    "PAC site binder complete",
                    "L1 Report",
                    "actual end time",
                ),
            }
        )

        resolved = resolve_mapping_indices(
            "TX_Mini_Project.csv",
            headers,
            {"L1": 128},
        )

        self.assertEqual(resolved["L1"], 136)

    def test_rejects_l1_report_when_l1_approved_is_missing(self):
        headers = self._headers(
            {
                210: (
                    "WPC000014000|AC0000111700|actual_end_date",
                    "PAC site binder complete",
                    "L1 Report",
                    "actual end time",
                ),
            }
        )

        with self.assertRaises(MappingValidationError) as caught:
            resolve_mapping_indices(
                "TX_Mini_Project.csv",
                headers,
                {"L1": 128},
            )

        self.assertIn("q&ehs / l1 approved", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
