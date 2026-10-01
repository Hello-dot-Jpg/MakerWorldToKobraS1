from __future__ import annotations

import json
from pathlib import Path
import tempfile
import unittest

from s1_optimizer.errors import PlanError
from s1_optimizer.rules import load_rules


class RuleTests(unittest.TestCase):
    def test_external_json_can_replace_default_clamp_names(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.json"
            path.write_text(json.dumps({"clamp": ["outer_wall_speed"]}), encoding="utf-8")
            rules = load_rules(path)
            self.assertEqual(rules.clamp, frozenset({"outer_wall_speed"}))

    def test_unknown_rule_sections_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "rules.json"
            path.write_text(json.dumps({"replace": ["printer_model"]}), encoding="utf-8")
            with self.assertRaises(PlanError):
                load_rules(path)


if __name__ == "__main__":
    unittest.main()
