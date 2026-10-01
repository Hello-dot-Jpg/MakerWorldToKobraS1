from decimal import Decimal
import unittest

from s1_optimizer.validation import audit_variable_heights


class VariableHeightTests(unittest.TestCase):
    def test_repeated_z_transition_is_valid_and_bounds_are_inclusive(self):
        raw = b"object_id=8|0;0.12;0.2;0.28;0.2;0.2\n"
        warnings, blockers = audit_variable_heights(raw, Decimal("0.12"), Decimal("0.28"))
        self.assertFalse(blockers)
        self.assertIn("object 8", warnings[0])

    def test_object_linkage_and_mesh_extent_are_verified(self):
        raw = b"object_id=8|0;0.12;1;0.2;2;0.28\n"
        warnings, blockers = audit_variable_heights(
            raw, Decimal("0.12"), Decimal("0.28"),
            {8: (Decimal("2.0004"),)},
        )
        self.assertFalse(blockers)
        self.assertTrue(any("linkage" in item and "extent" in item for item in warnings))

    def test_missing_ambiguous_and_overrun_mesh_links_block(self):
        raw = b"object_id=8|0;0.12;1;0.2;2;0.28\n"
        for extents, phrase in (
            ({}, "no matching mesh"),
            ({8: (Decimal("2"), Decimal("2"))}, "multiple mesh"),
            ({8: (Decimal("1.9"),)}, "exceeds mesh"),
        ):
            with self.subTest(extents=extents):
                _, blockers = audit_variable_heights(
                    raw, Decimal("0.12"), Decimal("0.28"), extents
                )
                self.assertTrue(any(phrase in item for item in blockers))

    def test_short_profile_extent_is_retained_with_review_warning(self):
        raw = b"object_id=8|0;0.12;0.5;0.2;1;0.28\n"
        warnings, blockers = audit_variable_heights(
            raw, Decimal("0.12"), Decimal("0.28"), {8: (Decimal("2"),)}
        )
        self.assertFalse(blockers)
        self.assertTrue(any("below the mesh" in item for item in warnings))

    def test_incompatible_profile_blocks_without_clamping(self):
        raw = b"object_id=1|0;0.4;0.4;0.5;1;0.56"
        _, blockers = audit_variable_heights(raw, Decimal("0.08"), Decimal("0.28"))
        self.assertIn("not flattened or clamped", blockers[0])
        self.assertIn(b"0.56", raw)

    def test_malformed_profiles_and_duplicate_ids_block(self):
        for raw in (b"object_id=0|0;0.2;1;0.2;2;0.2", b"object_id=1|0;0.2;1",
                    b"object_id=1|0;NaN;1;0.2;2;0.2", b"object_id=1|0;0;1;0.2;2;0.2",
                    b"object_id=1|0;0.2;2;0.2;1;0.2",
                    b"object_id=1|0;0.2;1;0.2;2;0.2\nobject_id=1|0;0.2;1;0.2;2;0.2"):
            with self.subTest(raw=raw):
                self.assertTrue(audit_variable_heights(raw, None, None)[1])
