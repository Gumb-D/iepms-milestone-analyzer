import unittest

from scripts import mapping_guard


class MilestoneMappingGuardTests(unittest.TestCase):
    def _headers(self, width=180):
        return [["" for _ in range(width)] for _ in range(4)]

    def _set_column(self, headers, index, field_id, stage, task, display):
        headers[0][index] = field_id
        headers[1][index] = stage
        headers[2][index] = task
        headers[3][index] = display

    def _resolve(self, headers, configured):
        return mapping_guard.resolve_mapping_indices(
            "TX_Mini_Project.csv",
            headers,
            configured,
        )

    def test_rebinds_tx_mini_rfs_to_tx_integrated_actual_end_not_nearby_mrcf(self):
        headers = self._headers()
        self._set_column(
            headers,
            119,
            "WP11200|AC0000111568|plan_end_date",
            "Hardware Dismantling",
            "MRCF",
            "planned end time",
        )
        self._set_column(
            headers,
            121,
            "WP11200|AC0000111568|actual_end_date",
            "Hardware Dismantling",
            "MRCF",
            "actual end time",
        )
        self._set_column(
            headers,
            146,
            "WP11400|AC0000111569|plan_end_date",
            "Software Commissioning",
            "TX Integrated",
            "planned end time",
        )
        self._set_column(
            headers,
            148,
            "WP11400|AC0000111569|actual_end_date",
            "Software Commissioning",
            "TX Integrated",
            "actual end time",
        )

        resolved = self._resolve(headers, {"RFS": 119})

        self.assertEqual(resolved["RFS"], 148)

    def test_rejects_other_rfs_like_task_when_tx_integrated_is_missing(self):
        headers = self._headers()
        self._set_column(
            headers,
            137,
            "WP11400|OTHER|actual_end_date",
            "Operation",
            "Site Integrated",
            "actual end time",
        )

        with self.assertRaises(mapping_guard.MappingValidationError):
            self._resolve(headers, {"RFS": 119})

    def test_rejects_planned_tx_integrated_when_no_actual_completion_exists(self):
        headers = self._headers()
        self._set_column(
            headers,
            146,
            "WP11400|AC0000111569|plan_end_date",
            "Software Commissioning",
            "TX Integrated",
            "planned end time",
        )

        with self.assertRaises(mapping_guard.MappingValidationError):
            self._resolve(headers, {"RFS": 119})

    def test_rejects_ambiguous_tx_integrated_actual_completion_candidates(self):
        headers = self._headers()
        for index in (148, 152):
            self._set_column(
                headers,
                index,
                f"WP11400|AC0000111569|actual_end_date|{index}",
                "Software Commissioning",
                "TX Integrated",
                "actual end time",
            )

        with self.assertRaises(mapping_guard.MappingValidationError):
            self._resolve(headers, {"RFS": 119})

    def test_keeps_a_valid_tx_integrated_actual_completion_hint(self):
        headers = self._headers()
        self._set_column(
            headers,
            148,
            "WP11400|AC0000111569|actual_end_date",
            "Software Commissioning",
            "TX Integrated",
            "actual end time",
        )

        resolved = self._resolve(headers, {"RFS": 148})

        self.assertEqual(resolved["RFS"], 148)


if __name__ == "__main__":
    unittest.main()
