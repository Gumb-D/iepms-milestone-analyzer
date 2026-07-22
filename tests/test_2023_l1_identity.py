import unittest

from scripts import mapping_guard


class TxRollout2023L1IdentityTests(unittest.TestCase):
    def _headers(self, width=360):
        return [["" for _ in range(width)] for _ in range(4)]

    def _set_column(self, headers, index, field_id, stage, task, display):
        headers[0][index] = field_id
        headers[1][index] = stage
        headers[2][index] = task
        headers[3][index] = display

    def test_resolves_l1_to_qehs_l1_approved_actual_end(self):
        headers = self._headers()
        self._set_column(
            headers,
            289,
            "WPC000011219|AC0000079305|actual_end_date",
            "PAC site binder complete",
            "L1 Report",
            "actual end time",
        )
        self._set_column(
            headers,
            328,
            "WPC000011222|AC0000079322|actual_end_date",
            "Q&EHS",
            "L1 Approved",
            "actual end time",
        )
        self._set_column(
            headers,
            334,
            "WPC000011222|AC0000079323|actual_end_date",
            "Q&EHS",
            "Compliance Check",
            "actual end time",
        )

        resolved = mapping_guard.resolve_mapping_indices(
            "2023_TX_Rollout.csv",
            headers,
            {"L1": 325},
        )

        self.assertEqual(resolved["L1"], 328)

    def test_rejects_l1_report_when_l1_approved_is_missing(self):
        headers = self._headers()
        self._set_column(
            headers,
            289,
            "WPC000011219|AC0000079305|actual_end_date",
            "PAC site binder complete",
            "L1 Report",
            "actual end time",
        )
        self._set_column(
            headers,
            334,
            "WPC000011222|AC0000079323|actual_end_date",
            "Q&EHS",
            "Compliance Check",
            "actual end time",
        )

        with self.assertRaises(mapping_guard.MappingValidationError):
            mapping_guard.resolve_mapping_indices(
                "2023_TX_Rollout.csv",
                headers,
                {"L1": 325},
            )


if __name__ == "__main__":
    unittest.main()
