"""Conservative, byte-local relocation of multi-plate 3MF build instances."""
from __future__ import annotations

from collections import defaultdict
from decimal import Decimal, InvalidOperation, ROUND_FLOOR
from math import isfinite, isqrt
from pathlib import PurePosixPath
import re
import shutil
import tempfile
from typing import BinaryIO, Callable, Iterable
import xml.etree.ElementTree as ET
from xml.parsers import expat

from .errors import InspectorError, PlanError
from .model_xml import parse_model_settings
from .constants import MAX_XML_MEMBER_BYTES


def stream_relocate_build_items(source: BinaryIO, destination: BinaryIO,
                                changes: list[dict[str, object]]) -> None:
    """Validate and patch build tags with bounded RAM, retaining mesh bytes.

    A disk spool supports exact byte offsets even for non-seekable ZIP input.
    No output is emitted until the XML and all requested indexes validate.
    """
    requested = {}
    for change in changes:
        try:
            index = int(change["item_index"])
        except (KeyError, ValueError, TypeError) as exc:
            raise PlanError("Invalid plate relocation index") from exc
        if index < 0 or index in requested:
            raise PlanError("Invalid or duplicate build-item relocation index")
        requested[index] = change
    with tempfile.TemporaryFile() as spool:
        size = 0
        while block := source.read(1024 * 1024):
            size += len(block)
            if size > MAX_XML_MEMBER_BYTES:
                raise PlanError("Model exceeds streamed XML safety limit")
            spool.write(block)
        parser = expat.ParserCreate()
        stack = []
        count = 0
        edits = []

        def deny(*args):
            raise PlanError("DTD/entity declarations are not supported in 3MF models")

        def start(name, attrs):
            nonlocal count
            local = name.rsplit(":", 1)[-1]
            if local == "item" and stack and stack[-1] == "build":
                if count in requested:
                    offset = parser.CurrentByteIndex
                    position = spool.tell()
                    spool.seek(offset)
                    raw = spool.read(65536)
                    spool.seek(position)
                    tag = _TAG.match(raw)
                    if tag is None:
                        raise PlanError("Build-item tag exceeds bounded patch limit")
                    original = tag.group()
                    # Reuse the reviewed byte-local affine arithmetic on only
                    # this bounded tag; no mesh tree is constructed.
                    prefixes = set(re.findall(rb"\b([A-Za-z_][\w.-]*):[A-Za-z_]", original))
                    header = b"<model" + b"".join(
                        b' xmlns:' + prefix + b'="urn:stream-patch"'
                        for prefix in sorted(prefixes)
                    ) + b"><build>"
                    tag_name = re.match(rb"<([^\s/>]+)", original).group(1)
                    closing = b"" if original.rstrip().endswith(b"/>") else b"</" + tag_name + b">"
                    suffix = closing + b"</build></model>"
                    envelope = header + original + suffix
                    change = dict(requested[count], item_index=0)
                    patched = relocate_build_items(envelope, [change])
                    replacement = patched[len(header):-len(suffix)]
                    edits.append((offset, offset + len(original), replacement))
                count += 1
            stack.append(local)

        parser.StartElementHandler = start
        parser.EndElementHandler = lambda name: stack.pop()
        parser.StartDoctypeDeclHandler = deny
        parser.EntityDeclHandler = deny
        parser.ExternalEntityRefHandler = deny
        spool.seek(0)
        try:
            while block := spool.read(1024 * 1024):
                parser.Parse(block, False)
            parser.Parse(b"", True)
        except expat.ExpatError as exc:
            raise PlanError(f"Cannot parse model while streaming relocation: {exc}") from exc
        if any(index >= count for index in requested) or len(edits) != len(requested):
            raise PlanError("Build item count changed during plate relocation")
        spool.seek(0)
        for begin, end, replacement in edits:
            remaining = begin - spool.tell()
            while remaining:
                block = spool.read(min(1024 * 1024, remaining))
                destination.write(block)
                remaining -= len(block)
            destination.write(replacement)
            spool.seek(end)
        shutil.copyfileobj(spool, destination, length=1024 * 1024)


_TAG = re.compile(rb'''<(?:[^>"']|"[^"]*"|'[^']*')*>''')
_TRANSFORM = re.compile(rb'''\btransform\s*=\s*(["'])(.*?)\1''', re.S)
_POINT = re.compile(r"^(-?\d+(?:\.\d+)?)x(-?\d+(?:\.\d+)?)$")

# Measured with centered native primitives on plates 11 and 12 in Anycubic
# Slicer Next 2.0.0.3 using the stock Kobra S1 250 x 250 mm machine. Its
# multi-plate *pitch* is larger than the printable bed; mesh fit is still
# checked against the 250 mm printable rectangle.
S1_NATIVE_GRID_PITCH = (Decimal("314.4"), Decimal("328.8"))


def _rectangle(area: object) -> tuple[Decimal, Decimal]:
    if not isinstance(area, list) or len(area) != 4:
        raise PlanError("Cannot relocate plates without a four-corner printable area")
    points = []
    for value in area:
        match = _POINT.fullmatch(value) if isinstance(value, str) else None
        if match is None:
            raise PlanError("Cannot relocate plates with a nonrectangular printable area")
        points.append((Decimal(match[1]), Decimal(match[2])))
    width = max(x for x, _ in points)
    depth = max(y for _, y in points)
    if width <= 0 or depth <= 0 or set(points) != {
        (Decimal(0), Decimal(0)), (width, Decimal(0)),
        (width, depth), (Decimal(0), depth),
    }:
        raise PlanError("Cannot relocate plates with an offset or nonrectangular bed")
    return width, depth


def _xml_root(raw: bytes) -> ET.Element:
    if b"<!DOCTYPE" in raw.upper() or b"<!ENTITY" in raw.upper():
        raise PlanError("DTD/entity declarations are not supported in 3MF models")
    try:
        return ET.fromstring(raw)
    except ET.ParseError as exc:
        raise PlanError(f"Cannot parse 3MF model while relocating plates: {exc}") from exc


def _instance_plate_map(raw: bytes) -> tuple[int, dict[tuple[str, int], int]]:
    root = parse_model_settings(raw)
    plates = root.findall("plate")
    result: dict[tuple[str, int], int] = {}
    for plate_index, plate in enumerate(plates):
        for instance in plate.findall("model_instance"):
            values = {item.get("key"): item.get("value") for item in instance.findall("metadata")}
            obj_id = values.get("object_id")
            try:
                instance_id = int(values.get("instance_id", ""))
            except (TypeError, ValueError) as exc:
                raise PlanError("Plate instance lacks a valid instance_id") from exc
            if not obj_id or instance_id < 0 or (obj_id, instance_id) in result:
                raise PlanError("Ambiguous model-to-plate instance mapping")
            result[(obj_id, instance_id)] = plate_index
    return len(plates), result


def _affine(value: str | None) -> tuple[float, ...]:
    if value is None:
        return (1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0, 0.0)
    try:
        result = tuple(float(part) for part in value.split())
    except ValueError as exc:
        raise PlanError("Invalid 3MF object transform in bed-fit audit") from exc
    if len(result) != 12 or not all(isfinite(part) for part in result):
        raise PlanError("Invalid 3MF object transform in bed-fit audit")
    return result


def _apply(point: tuple[float, float, float], matrix: tuple[float, ...]) -> tuple[float, float, float]:
    x, y, z = point
    return (
        x * matrix[0] + y * matrix[3] + z * matrix[6] + matrix[9],
        x * matrix[1] + y * matrix[4] + z * matrix[7] + matrix[10],
        x * matrix[2] + y * matrix[5] + z * matrix[8] + matrix[11],
    )


def _component_path(component: ET.Element, current: str) -> str:
    paths = [value for key, value in component.attrib.items() if key == "path" or key.endswith("}path")]
    if not paths:
        return current
    if len(paths) != 1:
        raise PlanError("Ambiguous 3MF component path in bed-fit audit")
    raw = paths[0].lstrip("/")
    path = PurePosixPath(raw)
    if not raw or "\\" in raw or ".." in path.parts or path.suffix != ".model":
        raise PlanError("Unsafe 3MF component path in bed-fit audit")
    return str(path)


def _plate_mesh_bounds(
    model_raw: bytes, items: list[ET.Element], item_plates: dict[int, int],
    columns: int, width: Decimal, depth: Decimal,
    pitch_x: Decimal, pitch_y: Decimal,
    read_member: Callable[[str], bytes],
    read_vertices: Callable[[str, str], Iterable[dict[str, str]]] | None = None,
) -> dict[int, tuple[float, float, float, float]]:
    """Measure actual transformed mesh bounds relative to each plate centre."""
    roots = {"3D/3dmodel.model": _xml_root(model_raw)}
    objects: dict[str, dict[str, ET.Element]] = {}

    def get_object(path: str, object_id: str) -> ET.Element:
        if path not in roots:
            try:
                roots[path] = _xml_root(read_member(path))
            except (InspectorError, KeyError, OSError) as exc:
                raise PlanError(f"Cannot audit 3MF component model {path!r}: {exc}") from exc
        if path not in objects:
            resources = roots[path].find("{*}resources")
            if resources is None:
                raise PlanError("3MF component model lacks resources")
            found = resources.findall("{*}object")
            objects[path] = {obj.get("id", ""): obj for obj in found}
            if len(objects[path]) != len(found):
                raise PlanError("Duplicate 3MF resource object ID")
        try:
            return objects[path][object_id]
        except KeyError as exc:
            raise PlanError(f"Missing 3MF resource object {object_id!r} in {path!r}") from exc

    bounds: dict[int, list[float]] = defaultdict(lambda: [float("inf"), -float("inf"), float("inf"), -float("inf")])

    def visit(path: str, object_id: str, transforms: tuple[tuple[float, ...], ...],
              plate_index: int, ancestors: frozenset[tuple[str, str]]) -> None:
        key = (path, object_id)
        if key in ancestors or len(ancestors) >= 16:
            raise PlanError("Cyclic or over-deep 3MF component hierarchy")
        obj = get_object(path, object_id)
        mesh = obj.find("{*}mesh")
        components = obj.find("{*}components")
        if mesh is not None:
            vertices = mesh.find("{*}vertices")
            if vertices is None:
                raise PlanError("Cannot prove bed fit for an empty 3MF mesh")
            row, column = divmod(plate_index, columns)
            cx = float(width / 2 + pitch_x * column)
            cy = float(depth / 2 - pitch_y * row)
            b = bounds[plate_index]
            vertex_values = (read_vertices(path, object_id) if read_vertices else
                             (vertex.attrib for vertex in vertices.findall("{*}vertex")))
            vertex_count = 0
            for vertex in vertex_values:
                vertex_count += 1
                try:
                    point = tuple(float(vertex[axis]) for axis in ("x", "y", "z"))
                except (KeyError, ValueError) as exc:
                    raise PlanError("Invalid 3MF mesh vertex in bed-fit audit") from exc
                if not all(isfinite(value) for value in point):
                    raise PlanError("Non-finite 3MF mesh vertex in bed-fit audit")
                for transform in transforms:
                    point = _apply(point, transform)
                x, y, _ = point
                b[0] = min(b[0], x - cx)
                b[1] = max(b[1], x - cx)
                b[2] = min(b[2], y - cy)
                b[3] = max(b[3], y - cy)
            if not vertex_count:
                raise PlanError("Cannot prove bed fit for an empty 3MF mesh")
        if components is not None:
            for component in components.findall("{*}component"):
                child_id = component.get("objectid")
                if not child_id:
                    raise PlanError("3MF component lacks objectid in bed-fit audit")
                child_path = _component_path(component, path)
                visit(child_path, child_id, (_affine(component.get("transform")),) + transforms,
                      plate_index, ancestors | {key})
        if mesh is None and components is None:
            raise PlanError("Cannot prove bed fit for an empty 3MF object")

    for index, plate_index in item_plates.items():
        item = items[index]
        visit("3D/3dmodel.model", item.get("objectid", ""),
              (_affine(item.get("transform")),), plate_index, frozenset())
    for plate_index in set(item_plates.values()):
        b = bounds.get(plate_index)
        if b is None or not all(isfinite(value) for value in b):
            raise PlanError(f"Cannot prove bed fit for plate {plate_index + 1}")
    return {index: tuple(value) for index, value in bounds.items()}


def _audit_smaller_bed(
    model_raw: bytes, items: list[ET.Element], item_plates: dict[int, int],
    columns: int, width: Decimal, depth: Decimal,
    pitch_x: Decimal, pitch_y: Decimal, edge_margin: Decimal,
    read_member: Callable[[str], bytes],
    read_vertices: Callable[[str, str], Iterable[dict[str, str]]] | None = None,
) -> None:
    """Require every transformed mesh vertex to fit the target plate."""
    bounds = _plate_mesh_bounds(model_raw, items, item_plates, columns,
                                width, depth, pitch_x, pitch_y, read_member, read_vertices)
    for plate_index, b in bounds.items():
        if (b[0] < -float(width) / 2 + float(edge_margin)
                or b[1] > float(width) / 2 - float(edge_margin)
                or b[2] < -float(depth) / 2 + float(edge_margin)
                or b[3] > float(depth) / 2 - float(edge_margin)):
            raise PlanError(
                f"Plate {plate_index + 1} has geometry outside the smaller target bed"
                if edge_margin == 0 else
                f"Plate {plate_index + 1} lacks the required {edge_margin} mm edge clearance after scaling"
            )


def plan_plate_relocation(
    model_raw: bytes, settings_raw: bytes, source_area: object, target_area: object,
    *, read_member: Callable[[str], bytes] | None = None,
    read_vertices: Callable[[str, str], Iterable[dict[str, str]]] | None = None,
    target_grid_pitch: tuple[Decimal, Decimal] | None = None,
    scale_percent: Decimal | None = None,
    scale_to_fit: bool = False,
    edge_margin: Decimal = Decimal(0),
) -> list[dict[str, object]]:
    """Plan translations from the source bed grid to the target bed grid.

    Bambu/Orca plate origins use 1.2 times bed width/depth and a
    ceil(sqrt(plate_count)) column grid. A target slicer may use a larger
    measured plate pitch while keeping the same printable bed dimensions.
    Each object's local plate position is preserved. Unknown layouts block.
    """
    plate_count, assignments = _instance_plate_map(settings_raw)
    if plate_count < 2 and scale_percent is None and not scale_to_fit:
        return []
    if scale_to_fit and scale_percent is not None:
        raise PlanError("Choose automatic scale-to-fit or an explicit scale percent, not both")
    if scale_percent is not None and (
        not isinstance(scale_percent, Decimal) or not scale_percent.is_finite()
        or scale_percent <= 0 or scale_percent > 100
    ):
        raise PlanError("Scale percent must be greater than 0 and at most 100")
    if not edge_margin.is_finite() or edge_margin < 0:
        raise PlanError("Scale edge margin must be non-negative")
    scale = scale_percent / 100 if scale_percent is not None else Decimal(1)
    old_width, old_depth = _rectangle(source_area)
    new_width, new_depth = _rectangle(target_area)
    if target_grid_pitch is None:
        pitch_x = Decimal("1.2") * new_width
        pitch_y = Decimal("1.2") * new_depth
    else:
        pitch_x, pitch_y = target_grid_pitch
        if (not all(isinstance(pitch, Decimal) and pitch.is_finite()
                    for pitch in (pitch_x, pitch_y))
                or pitch_x < new_width or pitch_y < new_depth):
            raise PlanError("Invalid target multi-plate grid pitch")
    if (old_width, old_depth) == (new_width, new_depth) and scale_percent is None and not scale_to_fit:
        return []
    smaller_bed = new_width < old_width or new_depth < old_depth
    if (smaller_bed or scale_percent is not None or scale_to_fit) and read_member is None:
        raise PlanError("Plate scaling or conversion to a smaller bed needs mesh-fit verification")
    if not assignments:
        raise PlanError("Multi-plate project has no model-to-plate instance mapping")
    root = _xml_root(model_raw)
    build = root.find("{*}build")
    if build is None:
        raise PlanError("3MF model has no build section for plate relocation")
    items = build.findall("{*}item")
    counts: dict[str, int] = defaultdict(int)
    seen: set[tuple[str, int]] = set()
    item_plates: dict[int, int] = {}
    columns = isqrt(plate_count - 1) + 1
    for item_index, item in enumerate(items):
        if any(name == "path" or name.endswith("}path") for name in item.attrib):
            raise PlanError("Cross-model build items need manual plate review")
        obj_id = item.get("objectid")
        if not obj_id:
            raise PlanError("Build item lacks an objectid")
        key = (obj_id, counts[obj_id])
        counts[obj_id] += 1
        plate_index = assignments.get(key)
        if plate_index is None:
            if item.get("printable", "1") == "0":
                continue
            raise PlanError(f"Printable build item {key} is not assigned to a plate")
        seen.add(key)
        item_plates[item_index] = plate_index
    if seen != set(assignments):
        raise PlanError("Plate assignment references a missing build instance")
    plate_scales: dict[int, Decimal] = {}
    if scale_to_fit:
        assert read_member is not None
        available_x, available_y = new_width / 2 - edge_margin, new_depth / 2 - edge_margin
        if available_x <= 0 or available_y <= 0:
            raise PlanError("Requested brim/edge clearance leaves no printable target bed")
        old_bounds = _plate_mesh_bounds(model_raw, items, item_plates, columns,
                                        old_width, old_depth,
                                        old_width * Decimal("1.2"),
                                        old_depth * Decimal("1.2"), read_member, read_vertices)
        for plate_index, bounds in old_bounds.items():
            extents = (max(abs(bounds[0]), abs(bounds[1])),
                       max(abs(bounds[2]), abs(bounds[3])))
            ratios = [Decimal(1)]
            for available, extent in zip((available_x, available_y), extents):
                if extent > 0:
                    ratios.append(available / Decimal(str(extent)))
            factor = min(ratios)
            percent = (factor * 100).quantize(Decimal("0.1"), rounding=ROUND_FLOOR)
            if percent <= 0:
                raise PlanError(f"Plate {plate_index + 1} cannot fit at a usable scale")
            plate_scales[plate_index] = percent / 100
    else:
        plate_scales = {plate_index: scale for plate_index in set(item_plates.values())}

    changes = []
    for item_index, plate_index in item_plates.items():
        row, column = divmod(plate_index, columns)
        item_scale = plate_scales[plate_index]
        old_cx = old_width / 2 + Decimal(column) * Decimal("1.2") * old_width
        old_cy = old_depth / 2 - Decimal(row) * Decimal("1.2") * old_depth
        new_cx = new_width / 2 + Decimal(column) * pitch_x
        new_cy = new_depth / 2 - Decimal(row) * pitch_y
        dx, dy = new_cx - item_scale * old_cx, new_cy - item_scale * old_cy
        if dx or dy or item_scale != 1 or scale_percent is not None:
            change: dict[str, object] = {
                "item_index": item_index, "dx": format(dx, "f"), "dy": format(dy, "f")
            }
            if scale_to_fit:
                change["plate_index"] = plate_index
                change["scale"] = format(item_scale.normalize(), "f")
            elif scale_percent is not None:
                change["scale"] = format(item_scale, "f")
            changes.append(change)
    transformed = relocate_build_items(model_raw, changes)
    if smaller_bed or scale_percent is not None or scale_to_fit:
        assert read_member is not None
        transformed_items = _xml_root(transformed).find("{*}build").findall("{*}item")
        _audit_smaller_bed(transformed, transformed_items, item_plates, columns,
                           new_width, new_depth, pitch_x, pitch_y, edge_margin,
                           read_member, read_vertices)
    return changes


def relocate_build_items(raw: bytes, changes: list[dict[str, object]]) -> bytes:
    """Apply reviewed XY shifts to build-item transforms without rewriting meshes."""
    root = _xml_root(raw)
    build = root.find("{*}build")
    if build is None:
        raise PlanError("3MF model has no build section")
    count = len(build.findall("{*}item"))
    offsets = {}
    try:
        for change in changes:
            index = int(change["item_index"])
            if index < 0 or index >= count or index in offsets:
                raise PlanError("Invalid or duplicate build-item relocation index")
            offsets[index] = (
                Decimal(str(change["dx"])), Decimal(str(change["dy"])),
                Decimal(str(change.get("scale", "1"))),
            )
    except (KeyError, ValueError, InvalidOperation) as exc:
        raise PlanError("Invalid plate relocation plan") from exc
    parser = expat.ParserCreate()
    stack: list[str] = []
    item_index = 0
    edits: list[tuple[int, int, bytes]] = []

    def start(name, attrs):
        nonlocal item_index
        local_name = name.rsplit(":", 1)[-1]
        if local_name == "item" and stack and stack[-1] == "build":
            if item_index in offsets:
                offset = parser.CurrentByteIndex
                match = _TAG.match(raw, offset)
                value_match = _TRANSFORM.search(match.group()) if match else None
                if value_match is None:
                    raise PlanError("Build item lacks a transform attribute")
                parts = value_match.group(2).decode("ascii").split()
                if len(parts) != 12:
                    raise PlanError("Build item transform is not a 3MF affine transform")
                try:
                    dx, dy, scale = offsets[item_index]
                    if not scale.is_finite() or scale <= 0 or scale > 1:
                        raise PlanError("Invalid plate scale factor")
                    if scale != 1:
                        for axis in range(9):
                            parts[axis] = format((Decimal(parts[axis]) * scale).normalize(), "f")
                    parts[9] = format((Decimal(parts[9]) * scale + dx).normalize(), "f")
                    parts[10] = format((Decimal(parts[10]) * scale + dy).normalize(), "f")
                    if scale != 1:
                        parts[11] = format((Decimal(parts[11]) * scale).normalize(), "f")
                except InvalidOperation as exc:
                    raise PlanError("Build item has invalid XY translation") from exc
                edits.append((offset + value_match.start(2), offset + value_match.end(2),
                              " ".join(parts).encode("ascii")))
            item_index += 1
        stack.append(local_name)

    def end(name):
        stack.pop()

    parser.StartElementHandler = start
    parser.EndElementHandler = end
    try:
        parser.Parse(raw, True)
    except expat.ExpatError as exc:
        raise PlanError(f"Cannot parse model while relocating plates: {exc}") from exc
    if item_index != count or len(edits) != len(offsets):
        raise PlanError("Build item count changed during plate relocation")
    result = raw
    for begin, end_offset, replacement in reversed(edits):
        result = result[:begin] + replacement + result[end_offset:]
    _xml_root(result)
    return result
