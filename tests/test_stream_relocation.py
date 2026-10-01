from io import BytesIO
import unittest

from s1_optimizer.errors import PlanError
from s1_optimizer.plate_layout import relocate_build_items, stream_relocate_build_items


class BoundedInput(BytesIO):
    def read(self, size=-1):
        if size < 0 or size > 1024 * 1024:
            raise AssertionError("Unbounded source read")
        return super().read(size)


class StreamRelocationTests(unittest.TestCase):
    def test_large_mesh_bytes_preserved_and_matches_small_patcher(self):
        tag = b'<item objectid="1" transform="1 0 0 0 1 0 0 0 1 120 130 0"/>'
        changes = [{"item_index": 0, "dx": "5", "dy": "-10", "scale": "0.9"}]
        small = b'<model><resources/><!--mesh--><build>' + tag + b'</build></model>'
        expected = relocate_build_items(small, changes)
        padding = b"x" * (26 * 1024 * 1024)
        raw = small.replace(b"mesh", padding)
        result = BytesIO()
        stream_relocate_build_items(BoundedInput(raw), result, changes)
        self.assertEqual(result.getvalue(), expected.replace(b"mesh", padding))

    def test_invalid_xml_and_indexes_emit_no_output(self):
        for raw, changes in (
            (b'<model><build/></model>', [{"item_index": 2}]),
            (b'<!DOCTYPE model><model/>', []),
            (b'<model>', []),
        ):
            with self.subTest(raw=raw):
                result = BytesIO()
                with self.assertRaises(PlanError):
                    stream_relocate_build_items(BoundedInput(raw), result, changes)
                self.assertEqual(result.getvalue(), b"")
