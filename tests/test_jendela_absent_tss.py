import unittest

from scripts import mapping_guard


class JendelaAbsentTssTests(unittest.TestCase):
    def test_resolves_legacy_tss_hint_to_not_applicable(self):
        headers = [["" for _ in range(40)] for _ in range(4)]
        headers[0][14] = "docata|ZDCSZ641765"
        headers[1][14] = "Installation"
        headers[2][14] = "Wireless RAN"
        headers[3][14] = "Subcon PR - TI"

        resolved = mapping_guard.resolve_mapping_indices(
            "Jendela_TX_Migration.csv",
            headers,
            {"TSS": 14},
        )

        self.assertIsNone(resolved["TSS"])

    def test_keeps_tss_not_applicable_even_when_an_unrelated_actual_end_exists(self):
        headers = [["" for _ in range(40)] for _ in range(4)]
        headers[0][16] = "WP11000|AC0000155784|actual_end_date"
        headers[1][16] = "Ready For Installation"
        headers[2][16] = "Material Collection"
        headers[3][16] = "actual end time"

        resolved = mapping_guard.resolve_mapping_indices(
            "Jendela_TX_Migration.csv",
            headers,
            {"TSS": 14},
        )

        self.assertIsNone(resolved["TSS"])


if __name__ == "__main__":
    unittest.main()
