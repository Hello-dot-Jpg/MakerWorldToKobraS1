"""Byte-local edits of Anycubic's per-plate bed selection."""
from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from xml.parsers import expat

from .errors import PlanError
from .model_xml import parse_model_settings


SUPPORTED_BED_TYPES = ("Textured PEI Plate", "Cool Plate", "Engineering Plate",
                       "High Temp Plate", "Textured Cool Plate", "Supertack Plate")
# Anycubic's BedType enum uses btDefault=0, then PC/EP/PEI/PTE/PCT/SuperTack.
# Its machine default falls back to btPEI (Smooth Plate) when omitted.
BED_TYPE_ENUM_VALUES = {
    "Cool Plate": "1",
    "Engineering Plate": "2",
    "High Temp Plate": "3",
    "Textured PEI Plate": "4",
    "Textured Cool Plate": "5",
    "Supertack Plate": "6",
}
_TAG = re.compile(rb'''<(?:[^>"']|"[^"]*"|'[^']*')*>''')
_VALUE = re.compile(rb'''(\svalue\s*=\s*)(["'])(.*?)\2''', re.S)


def patch_plate_bed_types(raw: bytes, bed_type: str) -> bytes:
    """Change only plate bed metadata; preserve all other original bytes."""
    if bed_type not in SUPPORTED_BED_TYPES:
        raise PlanError(f"Unsupported bed type: {bed_type!r}")
    try:
        raw.decode("utf-8-sig")
        parse_model_settings(raw)  # Reject entities, malformed XML/unknown prefixes.
        parser = expat.ParserCreate()
        stack: list[dict] = []
        edits: list[tuple[int, int, bytes]] = []
        value = bed_type.encode("ascii")
        metadata = b'<metadata key="bed_type" value="' + value + b'"/>'

        def start(name, attrs):
            offset = parser.CurrentByteIndex
            match = _TAG.match(raw, offset)
            if match is None:
                raise PlanError("Cannot locate plate XML opening tag")
            token = match.group()
            entry = {"name": name, "start": offset, "end": match.end(),
                     "empty": token.rstrip().endswith(b"/>"), "beds": 0}
            if name == "metadata" and stack and stack[-1]["name"] == "plate" and attrs.get("key") == "bed_type":
                stack[-1]["beds"] += 1
                if stack[-1]["beds"] > 1:
                    raise PlanError("Duplicate bed_type metadata in a plate")
                if attrs.get("value") != bed_type:
                    value_match = _VALUE.search(token)
                    if value_match is None:
                        raise PlanError("Plate bed_type metadata has no value attribute")
                    edits.append((offset + value_match.start(3), offset + value_match.end(3), value))
            stack.append(entry)

        def end(name):
            entry = stack.pop()
            if name != "plate" or entry["beds"]:
                return
            if entry["empty"]:
                token = raw[entry["start"]:entry["end"]]
                expanded = token[:-2] + b">" + metadata + b"</plate>"
                edits.append((entry["start"], entry["end"], expanded))
            else:
                offset = parser.CurrentByteIndex
                edits.append((offset, offset, metadata))

        parser.StartElementHandler = start
        parser.EndElementHandler = end
        parser.Parse(raw, True)
        result = raw
        for start_offset, end_offset, replacement in sorted(edits, reverse=True):
            result = result[:start_offset] + replacement + result[end_offset:]
        parse_model_settings(result)
        return result
    except (ValueError, ET.ParseError, expat.ExpatError) as exc:
        raise PlanError(f"Cannot set per-plate bed type: {exc}") from exc


def clear_plate_bed_types(raw: bytes) -> bytes:
    """Remove Bambu per-plate overrides so the S1 global plate picker works.

    Anycubic disables the per-plate picker for non-Bambu printers, even when a
    saved project contains per-plate overrides. Leave all other XML bytes as
    they were, including bed metadata on objects or volumes.
    """
    try:
        raw.decode("utf-8-sig")
        parse_model_settings(raw)
        parser = expat.ParserCreate()
        stack: list[str] = []
        edits: list[tuple[int, int]] = []

        def start(name, attrs):
            if name == "metadata" and stack and stack[-1] == "plate" and attrs.get("key") == "bed_type":
                offset = parser.CurrentByteIndex
                match = _TAG.match(raw, offset)
                if match is None or not match.group().rstrip().endswith(b"/>"):
                    raise PlanError("Unsupported nonempty plate bed_type metadata")
                edits.append((offset, match.end()))
            stack.append(name)

        def end(name):
            stack.pop()

        parser.StartElementHandler = start
        parser.EndElementHandler = end
        parser.Parse(raw, True)
        result = raw
        for begin, end_offset in reversed(edits):
            result = result[:begin] + result[end_offset:]
        parse_model_settings(result)
        return result
    except (ValueError, ET.ParseError, expat.ExpatError) as exc:
        raise PlanError(f"Cannot clear per-plate bed type: {exc}") from exc
