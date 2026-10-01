from decimal import Decimal
import unittest

from s1_optimizer.errors import PlanError
from s1_optimizer.plan import _layer_height_bounds


class LayerBoundsTests(unittest.TestCase):
    def test_automatic_bounds_match_reviewed_slicer_for_each_nozzle(self):
        for nozzle in ("0.25", "0.4", "0.6", "0.8"):
            with self.subTest(nozzle=nozzle):
                self.assertEqual(_layer_height_bounds({
                    "min_layer_height": ["0"], "max_layer_height": ["0"],
                    "nozzle_diameter": [nozzle],
                }), (Decimal("0.07"), Decimal(nozzle) * Decimal("0.75")))

    def test_explicit_minimum_floor_and_maximum_not_below_minimum(self):
        self.assertEqual(_layer_height_bounds({"min_layer_height": "0.001", "max_layer_height": "0.4"}),
                         (Decimal("0.01"), Decimal("0.4")))
        self.assertEqual(_layer_height_bounds({"min_layer_height": "0.2", "max_layer_height": "0.1"}),
                         (Decimal("0.2"), Decimal("0.2")))

    def test_missing_limits_stay_unknown_not_invented(self):
        self.assertEqual(_layer_height_bounds({}), (None, None))

    def test_invalid_limits_and_automatic_max_without_nozzle_reject(self):
        for settings in ({"max_layer_height": "0"}, {"min_layer_height": "NaN"},
                         {"max_layer_height": "-1"}, {"min_layer_height": "20%"}):
            with self.subTest(settings=settings), self.assertRaises(PlanError):
                _layer_height_bounds(settings)
