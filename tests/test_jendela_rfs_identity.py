import unittest

from scripts import mapping_guard


class JendelaRfsIdentityTests(unittest.TestCase):
    def _headers(self, width=180):
        return [["" for _ in range(width)] for _ in range(4)]

    def _set_column(self, headers, index, field_id, stage, task, display):
        headers[0][index] = field_id
        headers[1][index] = stage
        headers[2][index] = task
        headers[3][index] = display

    def test_rebinds_legacy_rfs_hint_to_cut_over_actual_end(self):
        headers = self._headers()
        self._set_column(
            headers,
            12,
            "docata|ZDCSZ01016455",
            "Installation",
            "Wireless RAN",
            "TX Ready Date",
        )
        self._set_column(
            headers,
            22,
            "WP11401|AC0000156514|actual_end_date",
            "Software Commissioning",
            "Cut Over",
            "actual end time",
        )
        self._set_column(
            headers,
            25,
            "WP11200|AC0000155787|actual_end_date",
            "Hardware Dismantling",
            "MRCF",
            "actual end time",
        )

        resolved = mapping_guard.resolve_mapping_indices(
            "Jendela_TX_Migration.csv",
            headers,
            {"RFS": 143},
        )

        self.assertEqual(resolved["RFS"], 22)

    def test_rejects_other_actual_end_when_cut_over_is_missing(self):
        headers = self._headers()
        self._set_column(
            headers,
            25,
            "WP11200|AC0000155787|actual_end_date",
            "Hardware Dismantling",
            "MRCF",
            "actual end time",
        )

        with self.assertRaises(mapping_guard.MappingValidationError):
            mapping_guard.resolve_mapping_indices(
                "Jendela_TX_Migration.csv",
                headers,
                {"RFS": 143},
            )


if __name__ == "__main__":
    unittest.main()
