import unittest

from scripts import mapping_guard


class CelcomdigiBau2024TssIdentityTests(unittest.TestCase):
    def _headers(self, width=80):
        return [["" for _ in range(width)] for _ in range(4)]

    def _set_column(self, headers, index, field_id, stage, task, display):
        headers[0][index] = field_id
        headers[1][index] = stage
        headers[2][index] = task
        headers[3][index] = display

    def test_resolves_tss_to_customer_approval_actual_end(self):
        headers = self._headers()
        self._set_column(
            headers,
            45,
            "WP10400|AC0000122966|actual_end_date",
            "Survey&Design",
            "TSSR Submitted to Customer",
            "actual end time",
        )
        self._set_column(
            headers,
            47,
            "WP10400|AC0000123015|actual_end_date",
            "Survey&Design",
            "TSSR Customer Approval",
            "actual end time",
        )

        resolved = mapping_guard.resolve_mapping_indices(
            "2024_Celcomdigi_BAU.csv",
            headers,
            {"TSS": 45},
        )

        self.assertEqual(resolved["TSS"], 47)

    def test_rejects_submission_when_customer_approval_is_missing(self):
        headers = self._headers()
        self._set_column(
            headers,
            45,
            "WP10400|AC0000122966|actual_end_date",
            "Survey&Design",
            "TSSR Submitted to Customer",
            "actual end time",
        )

        with self.assertRaises(mapping_guard.MappingValidationError):
            mapping_guard.resolve_mapping_indices(
                "2024_Celcomdigi_BAU.csv",
                headers,
                {"TSS": 45},
            )


if __name__ == "__main__":
    unittest.main()
