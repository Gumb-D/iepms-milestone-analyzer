import unittest

from scripts import mapping_guard


class MilestoneMappingGuardTests(unittest.TestCase):
    def _headers(self, width=130):
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

    def test_rebinds_tx_mini_rfs_from_planned_end_119_to_actual_end_121(self):
        headers = self._headers()
        self._set_column(
            headers,
            119,
            "WP11400|AC0000111569|planned_end_date",
            "Software Commissioning",
            "TX Integrated",
            "planned end time",
        )
        self._set_column(
            headers,
            120,
            "WP11400|AC0000111569|actual_start_date",
            "Software Commissioning",
            "TX Integrated",
            "actual start time",
        )
        self._set_column(
            headers,
            121,
            "WP11400|AC0000111569|actual_end_date",
            "Software Commissioning",
            "TX Integrated",
            "actual end time",
        )

        resolved = self._resolve(headers, {"RFS": 119})

        self.assertEqual(resolved["RFS"], 121)

    def test_rejects_planned_end_when_no_actual_completion_column_exists(self):
        headers = self._headers()
        self._set_column(
            headers,
            119,
            "WP11400|AC0000111569|planned_end_date",
            "Software Commissioning",
            "TX Integrated",
            "planned end time",
        )

        with self.assertRaises(mapping_guard.MappingValidationError):
            self._resolve(headers, {"RFS": 119})

    def test_rejects_ambiguous_actual_completion_candidates(self):
        headers = self._headers()
        for index in (121, 125):
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

    def test_keeps_a_valid_actual_completion_hint(self):
        headers = self._headers()
        self._set_column(
            headers,
            121,
            "WP11400|AC0000111569|actual_end_date",
            "Software Commissioning",
            "TX Integrated",
            "actual end time",
        )

        resolved = self._resolve(headers, {"RFS": 121})

        self.assertEqual(resolved["RFS"], 121)


if __name__ == "__main__":
    unittest.main()
