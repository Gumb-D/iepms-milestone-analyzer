import json
import os
import tempfile
import unittest

from scripts.mapping_guard import load_config


class MappingConfigMergeTests(unittest.TestCase):
    def test_local_config_overrides_built_in_mapping_without_dropping_other_files_or_milestones(self):
        fallback = {
            "A.csv": {"TSS": 10, "L1": 20},
            "B.csv": {"TSS": 30},
        }
        local = {
            "A.csv": {"TSS": 99},
        }

        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "milestone_config.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(local, handle)

            merged = load_config(path, fallback)

        self.assertEqual(
            merged,
            {
                "A.csv": {"TSS": 99, "L1": 20},
                "B.csv": {"TSS": 30},
            },
        )


if __name__ == "__main__":
    unittest.main()
