import unittest

from scripts import mapping_guard


class TxRollout2023TssIdentityTests(unittest.TestCase):
    def _headers(self, width=180):
        return [["" for _ in range(width)] for _ in range(4)]

    def _set_column(self, headers, index, field_id, stage, task, display):
        headers[0][index] = field_id
        headers[1][index] = stage
        headers[2][index] = task
        headers[3][index] = display

    def test_resolves_tss_to_physical_survey_actual_end(self):
        headers = self._headers()
        candidates = {
            135: ("WP10400|AC0000079293|actual_end_date", "Physical Survey"),
            140: ("WP10400|AC0000081753|actual_end_date", "TSSR Submitted to ZTE"),
            148: ("WP10400|AC0000079294|actual_end_date", "TSSR Submitted to Customer"),
            154: ("WP10400|AC0000079296|actual_end_date", "TSSR customer Approval"),
        }
        for index, (field_id, task) in candidates.items():
            self._set_column(
                headers,
                index,
                field_id,
                "Survey&Design",
                task,
                "actual end time",
            )

        resolved = mapping_guard.resolve_mapping_indices(
            "2023_TX_Rollout.csv",
            headers,
            {"TSS": 132},
        )

        self.assertEqual(resolved["TSS"], 135)

    def test_rejects_later_tssr_tasks_when_physical_survey_is_missing(self):
        headers = self._headers()
        for index, task in (
            (140, "TSSR Submitted to ZTE"),
            (148, "TSSR Submitted to Customer"),
            (154, "TSSR customer Approval"),
        ):
            self._set_column(
                headers,
                index,
                f"WP10400|OTHER|actual_end_date|{index}",
                "Survey&Design",
                task,
                "actual end time",
            )

        with self.assertRaises(mapping_guard.MappingValidationError):
            mapping_guard.resolve_mapping_indices(
                "2023_TX_Rollout.csv",
                headers,
                {"TSS": 132},
            )


if __name__ == "__main__":
    unittest.main()
