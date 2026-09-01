import unittest

from scripts.mapping_guard import MappingValidationError, resolve_mapping_indices


class ZteTxMiniTssIdentityTests(unittest.TestCase):
    def _headers(self, columns):
        width = max(columns) + 1
        rows = [[""] * width for _ in range(4)]
        for index, values in columns.items():
            for row_index, value in enumerate(values):
                rows[row_index][index] = value
        return rows

    def test_resolves_tss_to_physical_survey_actual_end(self):
        headers = self._headers(
            {
                45: (
                    "WP10400|AC0000197581|actual_end_date",
                    "Survey&Design",
                    "Physical Survey",
                    "actual end time",
                ),
                48: (
                    "WP10400|AC0000197582|actual_end_date",
                    "Survey&Design",
                    "TSSR Submitted to ZTE",
                    "actual end time",
                ),
                51: (
                    "WP10400|AC0000197583|actual_end_date",
                    "Survey&Design",
                    "TSSR Submitted to Customer",
                    "actual end time",
                ),
                54: (
                    "WP10400|AC0000197584|actual_end_date",
                    "Survey&Design",
                    "TSSR customer Approval",
                    "actual end time",
                ),
            }
        )

        resolved = resolve_mapping_indices(
            "ZTE_TX_MINI.csv",
            headers,
            {"TSS": 43},
        )

        self.assertEqual(resolved["TSS"], 45)

    def test_rejects_later_tssr_tasks_when_physical_survey_is_missing(self):
        headers = self._headers(
            {
                48: (
                    "WP10400|AC0000197582|actual_end_date",
                    "Survey&Design",
                    "TSSR Submitted to ZTE",
                    "actual end time",
                ),
                51: (
                    "WP10400|AC0000197583|actual_end_date",
                    "Survey&Design",
                    "TSSR Submitted to Customer",
                    "actual end time",
                ),
                54: (
                    "WP10400|AC0000197584|actual_end_date",
                    "Survey&Design",
                    "TSSR customer Approval",
                    "actual end time",
                ),
            }
        )

        with self.assertRaises(MappingValidationError) as caught:
            resolve_mapping_indices(
                "ZTE_TX_MINI.csv",
                headers,
                {"TSS": 43},
            )

        self.assertIn("survey&design / physical survey", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
