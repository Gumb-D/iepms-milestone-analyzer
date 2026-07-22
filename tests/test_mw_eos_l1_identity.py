import unittest

from scripts.mapping_guard import MappingValidationError, resolve_mapping_indices


class MwEosL1IdentityTests(unittest.TestCase):
    def test_resolves_l1_to_qehs_l1_approved_actual_end(self):
        headers = [
            [
                "site|code",
                "WPC000013474|AC0000145901|actual_end_date",
                "WPC000011219|AC0000145899|actual_end_date",
            ],
            [
                "Site Basic Info",
                "Q&EHS",
                "PAC site binder complete",
            ],
            [
                "Site Basic Info",
                "L1 Approved",
                "L1 Report",
            ],
            [
                "customer site code",
                "actual end time",
                "actual end time",
            ],
        ]

        resolved = resolve_mapping_indices(
            "MW_EOS_Swap.csv",
            headers,
            {"L1": 162},
        )

        self.assertEqual(resolved["L1"], 1)

    def test_rejects_l1_report_when_l1_approved_is_missing(self):
        headers = [
            [
                "site|code",
                "WPC000011219|AC0000145899|actual_end_date",
            ],
            [
                "Site Basic Info",
                "PAC site binder complete",
            ],
            [
                "Site Basic Info",
                "L1 Report",
            ],
            [
                "customer site code",
                "actual end time",
            ],
        ]

        with self.assertRaises(MappingValidationError):
            resolve_mapping_indices(
                "MW_EOS_Swap.csv",
                headers,
                {"L1": 162},
            )


if __name__ == "__main__":
    unittest.main()
