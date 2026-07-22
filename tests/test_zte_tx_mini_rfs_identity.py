import unittest

from scripts.mapping_guard import MappingValidationError, resolve_mapping_indices


class ZteTxMiniRfsIdentityTests(unittest.TestCase):
    def _headers(self, columns):
        width = max(columns) + 1
        rows = [[""] * width for _ in range(4)]
        for index, values in columns.items():
            for row_index, value in enumerate(values):
                rows[row_index][index] = value
        return rows

    def test_resolves_rfs_to_site_integrated_actual_end(self):
        headers = self._headers(
            {
                124: (
                    "WP11400|AC0000197593|actual_end_date",
                    "Software Commissioning",
                    "Site Integrated",
                    "actual end time",
                ),
                126: (
                    "docata|ZDCSZ01027727",
                    "Installation",
                    "Microwave",
                    "Cut-over End Date",
                ),
            }
        )

        resolved = resolve_mapping_indices(
            "ZTE_TX_MINI.csv",
            headers,
            {"RFS": 118},
        )

        self.assertEqual(resolved["RFS"], 124)

    def test_rejects_cutover_date_when_site_integrated_is_missing(self):
        headers = self._headers(
            {
                126: (
                    "docata|ZDCSZ01027727",
                    "Installation",
                    "Microwave",
                    "Cut-over End Date",
                ),
            }
        )

        with self.assertRaises(MappingValidationError) as caught:
            resolve_mapping_indices(
                "ZTE_TX_MINI.csv",
                headers,
                {"RFS": 118},
            )

        self.assertIn("software commissioning / site integrated", str(caught.exception))


if __name__ == "__main__":
    unittest.main()
