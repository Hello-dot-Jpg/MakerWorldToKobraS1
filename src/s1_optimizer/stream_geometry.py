"""Bounded mesh XML passes for plate planning; no mesh tree is retained."""
from typing import BinaryIO, Iterator
import xml.etree.ElementTree as ET
from xml.parsers import expat

from .constants import MAX_STRUCTURED_MEMBER_BYTES, MAX_XML_MEMBER_BYTES
from .errors import PlanError


def _parser():
    parser = expat.ParserCreate(namespace_separator="}")
    def deny(*args):
        raise PlanError("DTD/entity declarations are not supported in 3MF models")
    parser.StartDoctypeDeclHandler = deny
    parser.EntityDeclHandler = deny
    parser.ExternalEntityRefHandler = deny
    return parser


def _parse_blocks(parser, source):
    size = 0
    try:
        while block := source.read(65536):
            size += len(block)
            if size > MAX_XML_MEMBER_BYTES:
                raise PlanError("Model exceeds streamed XML safety limit")
            parser.Parse(block, False)
            yield None
        parser.Parse(b"", True)
    except expat.ExpatError as exc:
        raise PlanError(f"Cannot parse streamed model: {exc}") from exc


def model_skeleton(source: BinaryIO) -> bytes:
    """Keep resources/components/build metadata, omit vertex/triangle payloads."""
    parser = _parser()
    builder = ET.TreeBuilder()
    skipped = 0
    retained = 0

    def expanded(name):
        return "{" + name if "}" in name else name

    def reserve(size):
        nonlocal retained
        retained += size
        if retained > MAX_STRUCTURED_MEMBER_BYTES:
            raise PlanError("Model graph metadata exceeds structured safety limit")

    def start(name, attrs):
        nonlocal skipped
        if skipped or name.rsplit("}", 1)[-1] in {"vertex", "triangle"}:
            skipped += 1
            return
        reserve(64 + len(name) + sum(len(k) + len(v) + 16 for k, v in attrs.items()))
        builder.start(expanded(name), {expanded(k): v for k, v in attrs.items()})

    def end(name):
        nonlocal skipped
        if skipped:
            skipped -= 1
        else:
            builder.end(expanded(name))

    def data(value):
        if not skipped and value.strip():
            reserve(len(value.encode("utf-8")))
            builder.data(value)

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    parser.CharacterDataHandler = data
    for _ in _parse_blocks(parser, source):
        pass
    return ET.tostring(builder.close(), encoding="utf-8")


def mesh_vertices(source: BinaryIO, object_id: str) -> Iterator[dict[str, str]]:
    """Replay a mesh's vertices in bounded chunks, never retaining triangles."""
    parser = _parser()
    stack = []
    current = None
    pending = []

    def start(name, attrs):
        nonlocal current
        local = name.rsplit("}", 1)[-1]
        if local == "object" and stack and stack[-1] == "resources":
            current = attrs.get("id")
        if local == "vertex" and current == object_id and stack[-3:] == ["object", "mesh", "vertices"]:
            pending.append(dict(attrs))
        stack.append(local)

    def end(name):
        nonlocal current
        if name.rsplit("}", 1)[-1] == "object":
            current = None
        stack.pop()

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    for _ in _parse_blocks(parser, source):
        yield from pending
        pending.clear()
    yield from pending
