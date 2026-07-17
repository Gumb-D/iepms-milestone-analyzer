import unittest

from scripts.mapping_guard import MappingValidationError, resolve_mapping_indices


class ZteTxMiniL1IdentityTests(unittest.TestCase):
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
                133: (
                    "WPC000013474|AC0000197764|actual_end_date",
                    "Q&EHS",
                    "L1 Approved",
                    "actual end time",
                ),
                166: (
                    "WPC000013472|AC0000197601|actual_end_date",
                    "PAC site binder complete",
                    "L1 Report",
                    "actual end time",
                ),
            }
        )

        resolved = resolve_mapping_indices(
            "ZTE_TX_MINI.csv",
            headers,
            {"L1": 127},
        )

        self.assertEqual(resolved["L1"], 133)

    def test_rejects_l1_report_when_l1_approved_is_missing(self):
        headers = self._headers(
            {
                166: (
                    "WPC000013472|AC0000197601|actual_end_date",
                    "PAC site binder complete",
                    "L1 Report",
                    "actual end time",
                ),
            }
        )

        with self.assertRaises(MappingValidationError) as caught:
            resolve_mapping_indices(
                "ZTE_TX_MINI.csv",
                headers,
                {"L1": 127},
            )

        self.assertIn("q&ehs / l1 approved", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
